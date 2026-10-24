
import asyncio
import json
import re
import hashlib
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig


# Thư mục gốc của dự án: E:\project\RAG chatbot
ROOT_DIR = Path(__file__).resolve().parents[2]

INPUT_FILE = ROOT_DIR / "data" / "processed" / "urls_by_category.json"
OUTPUT_DIR = ROOT_DIR / "data" / "raw" / "web" / "crawled"

# Lần chạy đầu chỉ crawl tối đa 10 trang
MAX_PAGES = 10
# Những trang cần crawl trước
TARGET_URLS = [
    "http://ou.edu.vn/cong-tac-sinh-vien/quyche-quydinh/",
]

# Các nhóm ưu tiên cho chatbot hỗ trợ sinh viên
PRIORITY_CATEGORIES = {
    "cong_tac_sinh_vien",
    "hoc_phi_hoc_bong",
    "dao_tao",
    "thong_bao",
    "dich_vu_sinh_vien",
}

# Từ khóa để nhận diện một số trang hữu ích
PRIORITY_KEYWORDS = [
    "quy che",
    "quy-che",
    "quy dinh",
    "quy-dinh",
    "so tay sinh vien",
    "sinh-vien",
    "hoc phi",
    "hoc-phi",
    "hoc bong",
    "hoc-bong",
    "lich thi",
    "lich-thi",
    "thong bao",
    "thong-bao",
    "dao tao",
    "dao-tao",
    "cong tac sinh vien",
    "cong-tac-sinh-vien",
    "dich vu sinh vien",
    "dich-vu-sinh-vien",
]


def normalize_text(text: str) -> str:
    """Chuyển chữ về dạng đơn giản để so khớp từ khóa."""
    import unicodedata

    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(
        char for char in text
        if unicodedata.category(char) != "Mn"
    )
    return text.replace("đ", "d")


def select_urls(data: dict) -> list[dict]:
    """Chọn URL từ các nhóm ưu tiên và một số trang quy chế bị phân loại nhầm."""

    selected = []
    seen_urls = set()

    for category, items in data.items():
        for item in items:
            title = item.get("title", "").strip()
            url = item.get("url", "").strip()

            if not url.startswith(("http://", "https://")):
                continue

            parsed = urlparse(url)

            # Chỉ lấy trang thuộc OU và các tên miền con của OU
            if not (
                parsed.hostname == "ou.edu.vn"
                or (
                    parsed.hostname
                    and parsed.hostname.endswith(".ou.edu.vn")
                )
            ):
                continue

            # Không crawl URL trỏ thẳng tới ảnh
            if Path(parsed.path).suffix.lower() in {
                ".png", ".jpg", ".jpeg", ".gif",
                ".webp", ".svg", ".ico", ".pdf"
            }:
                continue

            text = normalize_text(f"{title} {url}")

            is_priority_category = category in PRIORITY_CATEGORIES
            has_priority_keyword = any(
                normalize_text(keyword) in text
                for keyword in PRIORITY_KEYWORDS
            )

            # Lấy nhóm ưu tiên hoặc trang hữu ích bị xếp nhầm vào "khac"
            if not (is_priority_category or has_priority_keyword):
                continue

            # Bỏ trang chủ và các liên kết chỉ dùng để chuyển vị trí trên trang
            if not parsed.path.strip("/") and parsed.fragment:
                continue

            if url in seen_urls:
                continue

            seen_urls.add(url)
            selected.append({
                "title": title or "Trang OU",
                "url": url,
                "category": category,
            })

    # Ưu tiên các URL quan trọng lên đầu danh sách
    target_urls = {
        url.rstrip("/")
        for url in TARGET_URLS
    }

    selected.sort(
        key=lambda item: (
            0 if item["url"].rstrip("/") in target_urls else 1
        )
    )

    return selected[:MAX_PAGES]

def safe_filename(title: str, url: str) -> str:
    """Tạo tên file an toàn, tránh trùng tên."""
    slug = normalize_text(title)
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    slug = slug[:60] or "ou-page"

    url_hash = hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]
    return f"{slug}-{url_hash}.md"


def get_markdown(result) -> str:
    """Lấy nội dung Markdown tương thích với các dạng kết quả Crawl4AI."""

    markdown = result.markdown

    if hasattr(markdown, "fit_markdown") and markdown.fit_markdown:
        return markdown.fit_markdown

    if hasattr(markdown, "raw_markdown") and markdown.raw_markdown:
        return markdown.raw_markdown

    return str(markdown or "")


async def main():
    if not INPUT_FILE.exists():
        print(f"Không tìm thấy file đầu vào: {INPUT_FILE}")
        return

    data = json.loads(INPUT_FILE.read_text(encoding="utf-8"))
    urls = select_urls(data)

    if not urls:
        print("Không tìm thấy URL phù hợp để crawl.")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Tìm thấy {len(urls)} URL để thử crawl.")
    print(f"Nơi lưu file: {OUTPUT_DIR}")

    # Lưu danh sách URL thử nghiệm để dễ kiểm tra
    selected_file = OUTPUT_DIR / "selected_urls.json"
    selected_file.write_text(
        json.dumps(urls, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    success_count = 0
    errors = []

    browser_config = BrowserConfig(headless=True)
    run_config = CrawlerRunConfig(
        page_timeout=60000,
        word_count_threshold=5,
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        for index, item in enumerate(urls, start=1):
            title = item["title"]
            url = item["url"]

            print(f"\n[{index}/{len(urls)}] {title}")
            print(f"URL: {url}")

            try:
                result = await crawler.arun(url=url, config=run_config)

                if not result.success:
                    message = getattr(
                        result, "error_message", "Lỗi không xác định"
                    )
                    print(f"  THẤT BẠI: {message}")
                    errors.append({
                        "title": title,
                        "url": url,
                        "error": str(message),
                    })
                    continue

                content = get_markdown(result).strip()

                if not content:
                    print("  Cảnh báo: trang không có nội dung Markdown.")
                    errors.append({
                        "title": title,
                        "url": url,
                        "error": "Không có nội dung Markdown",
                    })
                    continue

                # Lưu nguồn gốc để chatbot có thể trích dẫn sau này
                document = (
                    f"# {title}\n\n"
                    f"- URL nguồn: {url}\n"
                    f"- Nhóm: {item['category']}\n"
                    f"- Thời điểm crawl: "
                    f"{datetime.now().isoformat(timespec='seconds')}\n\n"
                    f"---\n\n"
                    f"{content}\n"
                )

                output_file = OUTPUT_DIR / safe_filename(title, url)
                output_file.write_text(document, encoding="utf-8")

                success_count += 1
                print(f"  OK: đã lưu {output_file.name}")
                print(f"  Số ký tự: {len(content)}")

            except Exception as exc:
                print(f"  LỖI: {exc}")
                errors.append({
                    "title": title,
                    "url": url,
                    "error": str(exc),
                })

            # Tránh gửi yêu cầu liên tục quá nhanh
            await asyncio.sleep(1)

    report = {
        "total_selected": len(urls),
        "success": success_count,
        "failed": len(errors),
        "errors": errors,
    }

    report_file = OUTPUT_DIR / "crawl_report.json"
    report_file.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n========== KẾT QUẢ ==========")
    print(f"Tổng URL được chọn: {len(urls)}")
    print(f"Crawl thành công: {success_count}")
    print(f"Crawl thất bại: {len(errors)}")
    print(f"Báo cáo: {report_file}")


if __name__ == "__main__":
    asyncio.run(main())
