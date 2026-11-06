
import re
from pathlib import Path

# Xác định thư mục gốc dự án
ROOT_DIR = Path(__file__).resolve().parents[2]

INPUT_DIR = ROOT_DIR / "data" / "raw" / "web"
OUTPUT_DIR = ROOT_DIR / "data" / "processed"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ERROR_PATTERNS = [
    r"502 Bad Gateway",
    r"502 Server Error",
    r"404 Not Found",
    r"403 Forbidden",
    r"500 Internal Server Error",
]


def is_error_page(text: str) -> bool:
    """Kiểm tra nội dung có phải trang báo lỗi hay không."""
    sample = text[:3000].lower()

    for pattern in ERROR_PATTERNS:
        if re.search(pattern.lower(), sample):
            return True

    return False


def clean_markdown(text: str) -> str:
    """Chuẩn hóa khoảng trắng, giữ nguyên nội dung chính."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in text.split("\n")]

    cleaned_lines = []
    previous_blank = False

    for line in lines:
        if not line:
            if not previous_blank:
                cleaned_lines.append("")
            previous_blank = True
        else:
            cleaned_lines.append(line)
            previous_blank = False

    return "\n".join(cleaned_lines).strip() + "\n"


def main():
    if not INPUT_DIR.exists():
        print(f"Không tìm thấy thư mục: {INPUT_DIR}")
        return

    # Lấy Markdown ở thư mục gốc và thư mục crawled.
    files = list(INPUT_DIR.glob("*.md"))

    crawled_dir = INPUT_DIR / "crawled"
    if crawled_dir.exists():
        files.extend(crawled_dir.glob("*.md"))

    files = sorted(set(files))

    if not files:
        print(f"Không tìm thấy file Markdown trong: {INPUT_DIR}")
        return

    cleaned_count = 0
    skipped_count = 0

    for input_file in files:
        print(f"\nĐang xử lý: {input_file.name}")

        try:
            text = input_file.read_text(encoding="utf-8")

            if not text.strip():
                print("Bỏ qua: file rỗng.")
                skipped_count += 1
                continue

            if is_error_page(text):
                print("Bỏ qua: có dấu hiệu là trang báo lỗi.")
                skipped_count += 1
                continue

            cleaned_text = clean_markdown(text)

            if not cleaned_text.strip():
                print("Bỏ qua: không còn nội dung.")
                skipped_count += 1
                continue

            # Giữ riêng tên file để tránh ghi đè giữa các nguồn.
            if input_file.parent == crawled_dir:
                output_file = OUTPUT_DIR / "crawled" / input_file.name
            else:
                output_file = OUTPUT_DIR / input_file.name

            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(cleaned_text, encoding="utf-8")

            print(f"Đã lưu: {output_file}")
            print(f"Số ký tự: {len(cleaned_text)}")
            cleaned_count += 1

        except (OSError, UnicodeError) as error:
            print(f"Lỗi đọc/ghi file: {error}")
            skipped_count += 1

    print("\n===== TỔNG KẾT =====")
    print(f"Số file đã làm sạch: {cleaned_count}")
    print(f"Số file bị bỏ qua: {skipped_count}")
    print(f"Thư mục kết quả: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
