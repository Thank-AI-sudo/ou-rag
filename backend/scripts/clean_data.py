
import re
from pathlib import Path

# Xác định thư mục gốc dự án
ROOT_DIR = Path(__file__).resolve().parents[2]

INPUT_DIR = ROOT_DIR / "data" / "raw" / "web"
OUTPUT_DIR = ROOT_DIR / "data" / "processed"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Nhận diện một số trang báo lỗi phổ biến
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
    # Chuẩn hóa kiểu xuống dòng
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Xóa khoảng trắng thừa ở đầu và cuối mỗi dòng
    lines = [line.strip() for line in text.split("\n")]

    # Xóa các dòng trống liên tiếp, không xóa nội dung
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
        print(f"Khong tim thay thu muc: {INPUT_DIR}")
        return

    files = list(INPUT_DIR.glob("*.md"))

    if not files:
        print(f"Khong tim thay file Markdown trong: {INPUT_DIR}")
        return

    cleaned_count = 0
    skipped_count = 0

    for input_file in files:
        print(f"\nDang xu ly: {input_file.name}")

        try:
            text = input_file.read_text(encoding="utf-8")

            if not text.strip():
                print("Bo qua: file rong.")
                skipped_count += 1
                continue

            if is_error_page(text):
                print("Bo qua: co dau hieu la trang bao loi.")
                skipped_count += 1
                continue

            cleaned_text = clean_markdown(text)

            if not cleaned_text.strip():
                print("Bo qua: khong con noi dung.")
                skipped_count += 1
                continue

            output_file = OUTPUT_DIR / input_file.name
            output_file.write_text(cleaned_text, encoding="utf-8")

            print(f"Da luu: {output_file}")
            print(f"So ky tu: {len(cleaned_text)}")
            cleaned_count += 1

        except (OSError, UnicodeError) as error:
            print(f"Loi doc/ghi file: {error}")
            skipped_count += 1

    print("\n===== TONG KET =====")
    print(f"So file da lam sach: {cleaned_count}")
    print(f"So file bi bo qua: {skipped_count}")
    print(f"Thu muc ket qua: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
