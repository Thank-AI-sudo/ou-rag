
import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")

chroma_dir = Path(
    os.getenv("CHROMA_PERSIST_DIR", "data/chroma")
)
if not chroma_dir.is_absolute():
    chroma_dir = ROOT_DIR / chroma_dir

collection_name = os.getenv(
    "CHROMA_COLLECTION_NAME",
    "ou_documents_gemini",
)

client = chromadb.PersistentClient(path=str(chroma_dir))
collection = client.get_collection(name=collection_name)

results = collection.get(
    where={"source_file": "quy-che-quy-dinh-ctsv-2f08105a.md"},
    include=["documents", "metadatas"],
)

keyword = "tiếp nhận lại sinh viên"

print(f"Tổng chunks trong collection: {collection.count()}")
print(f"Số chunks thuộc tài liệu: {len(results['ids'])}")

found = False

for chunk_id, document, metadata in zip(
    results["ids"],
    results["documents"],
    results["metadatas"],
):
    if keyword.casefold() in (document or "").casefold():
        found = True
        print("\n=== TÌM THẤY ĐOẠN LIÊN QUAN ===")
        print("Chunk ID:", chunk_id)
        print("Metadata:", metadata)
        print("Nội dung:\n", document)

if not found:
    print("\nKhông tìm thấy cụm từ trong các chunks của tài liệu.")
