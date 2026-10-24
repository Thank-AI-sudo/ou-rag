from aiohttp import client_middleware_digest_auth
import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from crawl4ai import AsyncWebCrawler

# Xác định thư mục gốc dự án
ROOT_DIR = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT_DIR / "data" / "raw" / "web"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Crawl thử một trang trước
URLS = [
    "https://ou.edu.vn/",
]


def make_filename(url: str) -> str:
    parsed = urlparse(url)
    name = re.sub(r"[^a-zA-Z0-9_-]", "_", parsed.path).strip("_")
    return f"{parsed.netloc}_{name or 'home'}.json"


async def main():
    async with AsyncWebCrawler() as crawler:
        for url in URLS:
            print(f"Dang crawl: {url}")
            try:
                result = await crawler.arun(url=url)

                if not result.success:
                    print(f"Crawl that bai: {result.error_message}")
                    continue

                markdown = result.markdown
                if not isinstance(markdown, str):
                    markdown = getattr(markdown, "raw_markdown", "") or ""

                if not markdown.strip():
                    print("Khong tim thay noi dung.")
                    continue

                data = {
                    "url": url,
                    "crawled_at": datetime.now(timezone.utc).isoformat(),
                    "markdown": markdown,
                }

                output_file = OUTPUT_DIR / make_filename(url)
                # Chuẩn hóa xuống dòng trong nội dung Markdown
                data["markdown"] = re.sub(r"\n{3,}", "\n\n", data["markdown"])
                data["markdown"] = data["markdown"].replace("\r\n", "\n")

                
                # Lưu dữ liệu JSON
                output_file.write_text(
                    json.dumps(data, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

                # Lưu dữ liệu Markdown
                markdown_file = OUTPUT_DIR / f"{output_file.stem}.md"
                markdown_file.write_text(data["markdown"], encoding="utf-8")

                print(f"Da luu JSON: {output_file}")
                print(f"Da luu Markdown: {markdown_file}")
                print(f"So ky tu: {len(data['markdown'])}")


            except Exception as error:
                print(f"Loi: {error}")


if __name__ == "__main__":
    asyncio.run(main())
