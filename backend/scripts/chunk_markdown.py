
import json
import re
import hashlib
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]

INPUT_DIR = ROOT_DIR / "data" / "raw" / "web" / "crawled"
OUTPUT_FILE = ROOT_DIR / "data" / "processed" / "chunks.json"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150


def read_markdown(path: Path) -> str:
    """Đọc file Markdown với encoding UTF-8."""
    return path.read_text(encoding="utf-8")


def extract_metadata(content: str) -> tuple[str, str, str]:
    """Lấy tiêu đề, URL và nhóm dữ liệu từ đầu file."""
    lines = content.splitlines()

    title = path_title = lines[0].lstrip("# ").strip() if lines else ""

    url_match = re.search(
        r"^- URL nguồn:\s*(.+)$", content, re.MULTILINE
    )
    category_match = re.search(
        r"^- Nhóm:\s*(.+)$", content, re.MULTILINE
    )

    source_url = url_match.group(1).strip() if url_match else ""
    category = category_match.group(1).strip() if category_match else "khac"

    return path_title, source_url, category


def clean_content(content: str) -> str:
    """Bỏ metadata đầu file và một số thành phần giao diện phổ biến."""
    content = re.sub(
        r"\A.*?^---\s*$",
        "",
        content,
        count=1,
        flags=re.DOTALL | re.MULTILINE,
    )

    # Riêng trang quy chế: bắt đầu từ khu vực nội dung chính.
    markers = [
        "## CHUYÊN TRANG THÔNG TIN TỪ PHÒNG CÔNG TÁC SINH VIÊN",
        "# CÁC QUY CHẾ QUY ĐỊNH HIỆN HÀNH",
    ]

    positions = [
        content.find(marker)
        for marker in markers
        if content.find(marker) >= 0
    ]

    if "quyche-quydinh" in content.lower() and positions:
        content = content[min(positions):]

    # Bỏ ảnh Markdown.
    content = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", content)

    # Bỏ các dòng chỉ chứa liên kết rỗng.
    content = re.sub(r"(?m)^\s*\[\s*\]\([^)]*\)\s*$", "", content)

    # Chuẩn hóa dòng trống, không xóa nội dung văn bản.
    content = re.sub(r"\n[ \t]+\n", "\n\n", content)
    content = re.sub(r"\n{3,}", "\n\n", content)

    return content.strip()


def split_long_text(text: str) -> list[str]:
    """Chia một mục dài thành các chunks có overlap."""
    chunks = []
    start = 0

    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))

        if end < len(text):
            # Ưu tiên cắt tại cuối câu hoặc dòng.
            candidates = [
                text.rfind("\n", start, end),
                text.rfind(". ", start, end),
                text.rfind("; ", start, end),
                text.rfind(" ", start, end),
            ]
            best = max(candidates)

            if best > start + CHUNK_SIZE // 2:
                end = best + 1

        piece = text[start:end].strip()

        if piece:
            chunks.append(piece)

        if end >= len(text):
            break

        next_start = max(start + 1, end - CHUNK_OVERLAP)

        # Tránh bắt đầu giữa một từ.
        space = text.find(" ", next_start, min(next_start + 80, len(text)))
        if space != -1:
            next_start = space + 1

        start = next_start

    return chunks


def split_by_headings(content: str) -> list[str]:
    """
    Tách theo tiêu đề Markdown.
    Các tiêu đề ### thường là những mục quy chế riêng.
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
    """Tách theo mục trước, chỉ chia nhỏ mục quá dài."""
    sections = split_by_headings(content)
    result = []

    for section in sections:
        if len(section) <= CHUNK_SIZE:
            result.append(section)
        else:
            result.extend(split_long_text(section))

    return result


def main():
    if not INPUT_DIR.exists():
        print(f"Không tìm thấy thư mục đầu vào: {INPUT_DIR}")
        return

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    all_chunks = []
    markdown_files = sorted(INPUT_DIR.glob("*.md"))
    skipped_files = 0

    for file_path in markdown_files:
        try:
            original = read_markdown(file_path)
            title, source_url, category = extract_metadata(original)
            content = clean_content(original)

            chunks = make_chunks(content)

            for index, text in enumerate(chunks):
                chunk_id = hashlib.sha256(
                    f"{file_path.name}:{index}:{text}".encode("utf-8")
                ).hexdigest()[:16]

                all_chunks.append({
                    "id": chunk_id,
                    "text": text,
                    "source_file": file_path.name,
                    "source_url": source_url,
                    "title": title,
                    "category": category,
                    "chunk_index": index,
                })

            print(f"OK: {file_path.name} -> {len(chunks)} chunks")

        except Exception as error:
            skipped_files += 1
            print(f"LỖI: {file_path.name}: {error}")

    OUTPUT_FILE.write_text(
        json.dumps(all_chunks, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\nHoàn thành chunking!")
    print(f"Số file Markdown: {len(markdown_files)}")
    print(f"Số file bị lỗi: {skipped_files}")
    print(f"Tổng số chunks: {len(all_chunks)}")
    print(f"File kết quả: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
