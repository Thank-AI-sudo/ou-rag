
import json
import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")

CHUNKS_FILE = ROOT_DIR / "data" / "processed" / "chunks.json"

CHROMA_DIR = Path(
    os.getenv("CHROMA_PERSIST_DIR", "data/chroma")
)
if not CHROMA_DIR.is_absolute():
    CHROMA_DIR = ROOT_DIR / CHROMA_DIR

COLLECTION_NAME = os.getenv(
    "CHROMA_COLLECTION_NAME",
    "ou_documents_gemini",
)

with CHUNKS_FILE.open("r", encoding="utf-8") as f:
    chunks = json.load(f)

json_ids = {
    str(chunk.get("id"))
    for chunk in chunks
    if isinstance(chunk, dict)
    and chunk.get("id")
    and isinstance(
        chunk.get("text", chunk.get("content", chunk.get("chunk_text"))),
        str,
    )
    and chunk.get("text", chunk.get("content", chunk.get("chunk_text"))).strip()
}

client = chromadb.PersistentClient(path=str(CHROMA_DIR))
collection = client.get_collection(name=COLLECTION_NAME)

chroma_ids = set(collection.get(include=[])["ids"])

print(f"Chunks hợp lệ trong JSON: {len(json_ids)}")
print(f"Bản ghi trong ChromaDB: {len(chroma_ids)}")
print(f"ID có trong JSON nhưng chưa có trong ChromaDB: {len(json_ids - chroma_ids)}")
print(f"ID có trong ChromaDB nhưng không còn trong JSON: {len(chroma_ids - json_ids)}")
