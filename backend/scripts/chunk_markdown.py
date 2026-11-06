
import json
import re
import hashlib
from pathlib import Path

# =========================
# CẤU HÌNH ĐƯỜNG DẪN
# =========================

ROOT_DIR = Path(__file__).resolve().parents[2]

# Đọc dữ liệu đã được làm sạch
INPUT_DIR = ROOT_DIR / "data" / "processed" / "crawled"

# File lưu kết quả chunking
OUTPUT_FILE = ROOT_DIR / "data" / "processed" / "chunks.json"

# Độ dài chunk và phần chồng lặp giữa hai chunk
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 250


# =========================
# ĐỌC VÀ TRÍCH XUẤT METADATA
# =========================

def read_markdown(path: Path) -> str:
    """Đọc file Markdown bằng UTF-8."""
    return path.read_text(encoding="utf-8")


def extract_metadata(content: str) -> tuple[str, str, str]:
    """Lấy tiêu đề, URL nguồn và nhóm dữ liệu."""
    lines = content.splitlines()

    title = lines[0].lstrip("# ").strip() if lines else ""

    url_match = re.search(
        r"(?m)^-\s*URL nguồn:\s*(.+)$",
        content,
    )

    category_match = re.search(
        r"(?m)^-\s*Nhóm:\s*(.+)$",
        content,
    )

    source_url = url_match.group(1).strip() if url_match else ""
    category = category_match.group(1).strip() if category_match else "khac"

    return title, source_url, category


# =========================
# LÀM SẠCH NỘI DUNG
# =========================




def clean_content(content: str, source_url: str = "") -> str:
    """Loại bỏ metadata, menu điều hướng và footer không cần thiết."""

    # 1. Bỏ metadata đầu file.
    if "\n---\n" in content:
        content = content.split("\n---\n", 1)[1]

    url = source_url.lower()

    # 2. Trang quy chế, quy định CTSV.
    # Giữ toàn bộ nội dung quy chế phía sau tiêu đề chuyên trang.
    if "quyche-quydinh" in url:
        marker = "## CHUYÊN TRANG THÔNG TIN TỪ PHÒNG CÔNG TÁC SINH VIÊN"
        pos = content.find(marker)

        if pos != -1:
            content = content[pos:]

    # 3. Trang các cơ sở đào tạo.
    elif "cac-co-so-dao-tao" in url:
        marker = "# **CÁC CƠ SỞ ĐÀO TẠO**"
        pos = content.find(marker)

        if pos != -1:
            content = content[pos:]

    # 4. Trang đào tạo trực tuyến.
    elif "truc-tuyen-vua-hoc-vua-lam" in url:
        marker = "# Đào tạo Trực tuyến"
        pos = content.find(marker)

        if pos != -1:
            content = content[pos:]

        # Bỏ footer, giữ danh sách nội dung đào tạo phía trên.
        footer_marker = "\n#### Thông tin chung"
        pos = content.find(footer_marker)

        if pos != -1:
            content = content[:pos]

    # 5. Trang danh sách hoạt động sinh viên.
    elif "hoat-dong-sinh-vien" in url:
        marker = "## Hoạt động sinh viên"
        pos = content.find(marker)

        if pos != -1:
            content = content[pos:]

        
    
    # Loại menu đầu trang còn sót ở một số bài tin.
    # Chỉ áp dụng cho các trang bài viết tin tức đã xác định.
    article_markers = [
        "### Gần 1.000 sinh viên",
        "### Kết nối đào tạo với thực tiễn",
        "### Sinh viên quốc tế",
    ]

    if any(marker in content for marker in article_markers):
        positions = [
            content.find(marker)
            for marker in article_markers
            if content.find(marker) != -1
        ]
        if positions:
            content = content[min(positions):]

    # Cắt phần tin liên quan và footer của các bài viết tin tức.
    if any(marker in source_url.lower() for marker in [
        "gan-1-000-sinh-vien",
        "ket-noi-dao-tao-voi-thuc-tien",
        "sinh-vien-quoc-te",
    ]):
        for marker in ["\n### TIN LIÊN QUAN", "\n#### Thông tin chung"]:
            pos = content.find(marker)
            if pos != -1:
                content = content[:pos]

    # Bỏ ảnh Markdown.
    content = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", content)


    # 7. Chuẩn hóa khoảng trắng.
    content = re.sub(r"\n{3,}", "\n\n", content)
    content = re.sub(r"[ \t]+\n", "\n", content)

    return content.strip()



def split_oversized_unit(text: str) -> list[str]:
    """
    Chia đoạn quá dài theo câu.
    Chỉ chia theo từ nếu một câu đơn lẻ quá dài.
    """
    sentences = re.split(
        r"(?<!\d\.)(?<=[.!?;])\s+",
        text.strip()
    )

    result = []
    current = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        if len(sentence) > CHUNK_SIZE:
            if current:
                result.append(current)
                current = ""

            # Trường hợp hiếm: một câu dài hơn cả chunk.
            words = sentence.split()
            part = ""

            for word in words:
                candidate = f"{part} {word}".strip()

                if part and len(candidate) > CHUNK_SIZE:
                    result.append(part)
                    part = word
                else:
                    part = candidate

            if part:
                result.append(part)

            continue

        candidate = f"{current} {sentence}".strip()

        if current and len(candidate) > CHUNK_SIZE:
            result.append(current)
            current = sentence
        else:
            current = candidate

    if current:
        result.append(current)

    return result


def split_into_units(text: str) -> list[str]:
    """
    Tách các đơn vị nội dung:
    - Đoạn văn
    - Mục đánh số: 1. 2. 3.
    - Bullet: - hoặc *
    """
    units = []
    current = []

    def flush():
        if current:
            unit = "\n".join(current).strip()
            if unit:
                units.append(unit)
            current.clear()

    for line in text.splitlines():
        stripped = line.strip()

        if not stripped:
            flush()
            continue

        is_list_item = bool(
            re.match(r"^(?:\d+[.)]|[-*])\s+", stripped)
        )

        if is_list_item:
            flush()

        current.append(line)

    flush()

    return units


def split_long_text(text: str) -> list[str]:
    """
    Chia theo đơn vị nội dung hoàn chỉnh.
    Overlap theo nguyên đơn vị, không cắt ngang câu.
    """
    original_units = split_into_units(text)

    units = []

    for unit in original_units:
        if len(unit) <= CHUNK_SIZE:
            units.append(unit)
        else:
            units.extend(split_oversized_unit(unit))

    chunks = []
    current_units = []

    for unit in units:
        candidate = "\n\n".join(current_units + [unit])

        if len(candidate) <= CHUNK_SIZE:
            current_units.append(unit)
            continue

        if current_units:
            chunks.append("\n\n".join(current_units))

        # Giữ lại các đơn vị cuối làm overlap.
        overlap_units = []
        overlap_length = 0

        for previous in reversed(current_units):
            new_length = overlap_length + len(previous)

            if overlap_units:
                new_length += 2

            if new_length > CHUNK_OVERLAP:
                break

            overlap_units.insert(0, previous)
            overlap_length = new_length

        # Đảm bảo overlap + đơn vị mới không vượt kích thước.
        while overlap_units:
            combined = "\n\n".join(overlap_units + [unit])

            if len(combined) <= CHUNK_SIZE:
                break

            overlap_units.pop(0)

        current_units = overlap_units + [unit]

    if current_units:
        chunks.append("\n\n".join(current_units))

    return chunks



# =========================
# CHIA THEO TIÊU ĐỀ
# =========================

def split_by_headings(content: str) -> list[str]:
    """
    Chia nội dung theo tiêu đề Markdown từ cấp 1 đến cấp 4.
    Giữ tiêu đề trong section để cung cấp ngữ cảnh cho chunk.
    """

    lines = content.splitlines()
    sections = []
    current = []

    for line in lines:
        is_heading = bool(re.match(r"^#{1,4}\s+", line))

        if is_heading and current:
            section = "\n".join(current).strip()

            if section:
                sections.append(section)

            current = [line]
        else:
            current.append(line)

    section = "\n".join(current).strip()

    if section:
        sections.append(section)

    return sections


def make_chunks(content: str) -> list[str]:
    """Tách theo tiêu đề trước, chia nhỏ nếu section quá dài."""

    sections = split_by_headings(content)
    result = []

    for section in sections:
        if len(section) <= CHUNK_SIZE:
            result.append(section)
        else:
            result.extend(split_long_text(section))

    return result


# =========================
# CHƯƠNG TRÌNH CHÍNH
# =========================

def main():
    if not INPUT_DIR.exists():
        print(f"Không tìm thấy thư mục đầu vào: {INPUT_DIR}")
        return

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Chỉ lấy Markdown trực tiếp trong thư mục crawled
    # Không lấy trang chủ nằm ngoài thư mục này
    markdown_files = sorted(INPUT_DIR.glob("*.md"))

    if not markdown_files:
        print(f"Không tìm thấy file Markdown trong: {INPUT_DIR}")
        return

    all_chunks = []
    skipped_files = 0

    for file_path in markdown_files:
        try:
            original = read_markdown(file_path)

            title, source_url, category = extract_metadata(original)
            content = clean_content(original, source_url)

            if not content:
                print(f"BỎ QUA: {file_path.name} - nội dung rỗng")
                skipped_files += 1
                continue

            chunks = make_chunks(content)

            for index, chunk_text in enumerate(chunks):
                # ID ổn định nếu tên file, vị trí và nội dung không đổi
                chunk_id = hashlib.sha256(
                    f"{file_path.name}:{index}:{chunk_text}".encode("utf-8")
                ).hexdigest()[:16]

                all_chunks.append({
                    "id": chunk_id,
                    "text": chunk_text,
                    "source_file": file_path.name,
                    "source_url": source_url,
                    "title": title,
                    "category": category,
                    "chunk_index": index,
                })

            print(f"OK: {file_path.name} -> {len(chunks)} chunks")

        except (OSError, UnicodeError, ValueError) as error:
            skipped_files += 1
            print(f"LỖI: {file_path.name}: {error}")

    # Ghi JSON bằng UTF-8, giữ nguyên tiếng Việt
    OUTPUT_FILE.write_text(
        json.dumps(all_chunks, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n===== TỔNG KẾT CHUNKING =====")
    print(f"Số file Markdown: {len(markdown_files)}")
    print(f"Số file bị bỏ qua hoặc lỗi: {skipped_files}")
    print(f"Tổng số chunks: {len(all_chunks)}")
    print(f"File kết quả: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
    