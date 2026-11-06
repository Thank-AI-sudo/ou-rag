import json
import re
from pathlib import Path
from urllib.parse import urlparse

# Thư mục gốc dự án
ROOT_DIR = Path(__file__).resolve().parents[2]

# File Markdown đã crawl
INPUT_FILE = ROOT_DIR / "data" / "raw" / "web" / "ou.edu.vn_home.md"

# Nơi lưu kết quả phân loại
OUTPUT_DIR = ROOT_DIR / "data" / "processed"
OUTPUT_JSON = OUTPUT_DIR / "urls_by_category.json"
OUTPUT_MD = OUTPUT_DIR / "urls_by_category.md"

# Từ khóa dùng để phân loại tiêu đề và URL

CATEGORIES = {
    "dao_tao": [
        "quy chế đào tạo", "quản lý đào tạo",
        "đăng ký học phần", "đăng ký môn học",
        "học phần", "lịch thi", "điểm thi",
        "điểm học tập", "học vụ", "tốt nghiệp",
        "khảo thí", "phòng khảo thí",
        "thi kết thúc", "kế hoạch học tập",
    ],

    "cong_tac_sinh_vien": [
        "quy chế sinh viên", "quy chế - quy định ctsv",
        "công tác sinh viên", "công tác sv",
        "sổ tay sinh viên", "hỗ trợ sinh viên",
        "khen thưởng sinh viên", "kỷ luật sinh viên",
        "cố vấn học tập", "hoạt động sinh viên",
        "sinh hoạt công dân", "thông báo cho sinh viên",
        "tín dụng sinh viên",
    ],

    "hoc_phi_hoc_bong": [
        "học phí", "học bổng", "miễn giảm học phí",
        "đóng học phí", "vay vốn sinh viên",
        "tín dụng sinh viên",
    ],

    "thong_bao": [
        "thông báo đổi phòng thi",
        "thông báo điều chỉnh lịch thi",
        "thông báo lịch thi",
        "thông báo đăng ký học phần",
        "thông báo sinh viên",
        "hạn đăng ký",
    ],

    "dich_vu_sinh_vien": [
        "hệ thống thông tin sinh viên",
        "đăng ký môn học trực tuyến",
        "cổng thông tin sinh viên",
        "dịch vụ sinh viên",
        "tra cứu điểm",
        "thời khóa biểu",
        "hệ thống hỗ trợ học tập",
        "trung tâm học liệu",
    ],

    "tin_tuc_tuyen_sinh": [
        "tuyển sinh", "xét tuyển",
        "thông tin tuyển sinh", "tin tức",
        "sự kiện", "hoạt động ngoại khóa",
        "giới thiệu ngành",
    ],

    "khoa_trung_tam": [
        "khoa công nghệ sinh học",
        "khoa công nghệ thông tin",
        "khoa kế toán kiểm toán",
        "khoa luật",
        "khoa kinh tế và quản lý công",
        "khoa ngoại ngữ",
        "khoa quản trị kinh doanh",
        "khoa tài chính",
        "khoa xây dựng",
        "khoa khoa học xã hội",
        "khoa khoa học cơ bản",
        "khoa đào tạo sau đại học",
        "khoa đào tạo đặc biệt",
        "trung tâm đào tạo",
        "trung tâm học liệu",
    ],

    "don_vi_chuc_nang": [
        "phòng quản lý đào tạo",
        "phòng khảo thí",
        "phòng công tác sv",
        "phòng công tác sinh viên",
        "phòng hành chính",
        "phòng hợp tác quản lý khoa học",
        "phòng tổ chức",
        "phòng tài chính",
        "phòng pháp chế",
        "phòng bảo đảm chất lượng",
        "phòng đầu tư",
        "trạm y tế",
    ],

    "gioi_thieu_truong": [
        "giới thiệu chung", "sứ mạng và tầm nhìn",
        "sơ đồ cơ cấu tổ chức", "lịch sử và phát triển",
        "lịch sử hình thành", "thông tin liên hệ",
        "các cơ sở đào tạo", "cơ sở 1",
        "cơ sở 2", "cơ sở 4", "cơ sở 5",
        "cơ sở 6", "cơ sở 7", "cơ sở 8",
    ],

    "khac": [],
}



def classify_link(title: str, url: str) -> str:
    title_lower = title.lower().strip()
    url_lower = url.lower()
    text = f"{title_lower} {url_lower}"

    # Loại bỏ các URL chỉ trỏ đến ảnh hoặc tài nguyên tĩnh.
    path = url_lower.split("?", 1)[0].split("#", 1)[0]
    if path.endswith((
        ".jpg", ".jpeg", ".png", ".gif",
        ".webp", ".svg", ".ico"
    )):
        return "bo_qua"

    # Phân loại theo nội dung cụ thể trước.
    if "quy chế" in text and (
        "ctsv" in text or "sinh viên" in text
    ):
        return "cong_tac_sinh_vien"

    if any(keyword in text for keyword in [
        "điều chỉnh lịch thi",
        "đổi phòng thi",
        "điều chỉnh hình thức thi",
        "lịch thi",
    ]):
        return "dao_tao"

    if any(keyword in text for keyword in [
        "đóng học phí",
        "miễn giảm học phí",
        "học bổng",
        "tín dụng sinh viên",
    ]):
        return "hoc_phi_hoc_bong"

    # Phân loại trang đơn vị theo tiêu đề.
    if title_lower.startswith(("khoa ", "trung tâm ")):
        return "khoa_trung_tam"

    if title_lower.startswith(("phòng ", "trạm y tế")):
        return "don_vi_chuc_nang"

    # Các chủ đề còn lại.
    rules = [
        ("cong_tac_sinh_vien", [
            "sổ tay sinh viên",
            "công tác sinh viên",
            "thông báo sinh viên",
            "sinh hoạt công dân",
            "hỗ trợ sinh viên",
            "cố vấn học tập",
        ]),
        ("dich_vu_sinh_vien", [
            "hệ thống thông tin sinh viên",
            "đăng ký môn học trực tuyến",
            "dịch vụ sinh viên",
            "tra cứu điểm",
            "hệ thống hỗ trợ học tập",
        ]),
        ("dao_tao", [
            "quy chế đào tạo",
            "quản lý đào tạo",
            "đăng ký học phần",
            "điểm học tập",
            "học vụ",
            "tốt nghiệp",
        ]),
        ("thong_bao", [
            "thông báo",
            "hạn đăng ký",
        ]),
        ("hoc_phi_hoc_bong", [
            "học phí",
            "học bổng",
        ]),
        ("tin_tuc_tuyen_sinh", [
            "tuyển sinh",
            "tin tức",
            "sự kiện",
        ]),
        ("gioi_thieu_truong", [
            "giới thiệu chung",
            "sứ mạng và tầm nhìn",
            "sơ đồ cơ cấu tổ chức",
            "chức năng, nhiệm vụ các đơn vị",
            "lịch sử và phát triển",
            "thông tin liên hệ",
        ]),
    ]

    for category, keywords in rules:
        if any(keyword in text for keyword in keywords):
            return category

    return "khac"




def main():
    if not INPUT_FILE.exists():
        print(f"Khong tim thay file: {INPUT_FILE}")
        print("Hay kiem tra lai duong dan file Markdown.")
        return

    markdown = INPUT_FILE.read_text(encoding="utf-8")

    # Chỉ lấy liên kết Markdown thông thường, bỏ cú pháp ảnh
    pattern = re.compile(
        r'(?<!!)\[([^\]]+)\]\((https?://[^)\s]+)(?:\s+"[^"]*")?\)'
    )

    results = {}
    seen_urls = set()

    for title, url in pattern.findall(markdown):
        title = title.strip()
        url = url.strip().rstrip(".,;")

        # Loại URL trùng lặp
        if url in seen_urls:
            continue
        seen_urls.add(url)

        # Chỉ lấy các liên kết thuộc OU
        host = (urlparse(url).hostname or "").lower()
        if not (host == "ou.edu.vn" or host.endswith(".ou.edu.vn")):
            continue

        category = classify_link(title, url)
        if category == "bo_qua":
            continue

        results.setdefault(category, []).append({
            "title": title,
            "url": url,
            "category": category,
        })

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Lưu kết quả dạng JSON để Python xử lý ở các bước sau
    OUTPUT_JSON.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Lưu thêm Markdown để dễ đọc và kiểm tra bằng mắt
    lines = ["# Danh sách đường dẫn OU đã phân loại", ""]

    for category, links in results.items():
        lines.append(f"## {category} ({len(links)} đường dẫn)")
        lines.append("")

        for item in links:
            lines.append(f"- [{item['title']}]({item['url']})")

        lines.append("")

    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print("Phan loai hoan tat!")
    print(f"Tong so URL: {sum(len(v) for v in results.values())}")

    for category, links in results.items():
        print(f"- {category}: {len(links)} URL")

    print(f"\nFile JSON: {OUTPUT_JSON}")
    print(f"File Markdown: {OUTPUT_MD}")
    print("\nLuu y: Hay kiem tra nhom chua_phan_loai va cac ket qua truoc khi crawl tiep.")


if __name__ == "__main__":
    main()
