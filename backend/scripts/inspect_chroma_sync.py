
import json
import os
from collections import Counter
from pathlib import Path

import chromadb
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")

CHUNKS_FILE = ROOT_DIR / "data" / "processed" / "chunks.json"
CHROMA_DIR = Path(os.getenv("CHROMA_PERSIST_DIR", "data/chroma"))
if not CHROMA_DIR.is_absolute():
    CHROMA_DIR = ROOT_DIR / CHROMA_DIR

COLLECTION_NAME = os.getenv(
    "CHROMA_COLLECTION_NAME", "ou_documents_gemini"
)

with CHUNKS_FILE.open("r", encoding="utf-8") as f:
    chunks = json.load(f)

json_by_id = {
    str(c["id"]): c
    for c in chunks
    if isinstance(c, dict) and c.get("id") and c.get("text")
}

client = chromadb.PersistentClient(path=str(CHROMA_DIR))
collection = client.get_collection(name=COLLECTION_NAME)
stored = collection.get(include=["metadatas"])

chroma_by_id = {
    chunk_id: metadata or {}
    for chunk_id, metadata in zip(stored["ids"], stored["metadatas"])
}

missing_ids = set(json_by_id) - set(chroma_by_id)
stale_ids = set(chroma_by_id) - set(json_by_id)

print("\n=== ID CÓ TRONG JSON NHƯNG CHƯA CÓ TRONG CHROMA ===")
print("Tổng:", len(missing_ids))
print("Theo file:")
print(Counter(
    json_by_id[i].get("source_file", "(không rõ)")
    for i in missing_ids
))
print("\nChunks học bổng còn thiếu:")
for i in sorted(missing_ids):
    c = json_by_id[i]
    if c.get("source_file") == "hoc-bong-vuot-kho-quy-dinh-164.md":
        print(f"ID={i} | chunk_index={c.get('chunk_index')}")

print("\n=== ID CÓ TRONG CHROMA NHƯNG KHÔNG CÒN TRONG JSON ===")
print("Tổng:", len(stale_ids))
print("Theo file:")
print(Counter(
    chroma_by_id[i].get("source_file", "(không rõ)")
    for i in stale_ids
))
