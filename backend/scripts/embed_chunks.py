
import json
import os
import time
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from google import genai
from google.genai import types, errors


ROOT_DIR = Path(__file__).resolve().parents[2]

load_dotenv(ROOT_DIR / ".env")

CHUNKS_FILE = ROOT_DIR / "data" / "processed" / "chunks.json"

CHROMA_DIR = Path(
    os.getenv("CHROMA_PERSIST_DIR", "data/chroma")
)
if not CHROMA_DIR.is_absolute():
    CHROMA_DIR = ROOT_DIR / CHROMA_DIR

MODEL = os.getenv(
    "GEMINI_EMBEDDING_MODEL",
    "gemini-embedding-001",
)

COLLECTION_NAME = os.getenv(
    "CHROMA_COLLECTION_NAME",
    "ou_documents_gemini",
)

BATCH_SIZE = 50
MAX_ATTEMPTS = 5


def load_chunks():
    if not CHUNKS_FILE.exists():
        raise FileNotFoundError(
            f"Không tìm thấy file: {CHUNKS_FILE}"
        )

    with CHUNKS_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, dict):
        data = data.get("chunks")

    if not isinstance(data, list):
        raise ValueError(
            "chunks.json phải là danh sách "
            "hoặc object chứa key 'chunks'."
        )

    return data


def get_text(chunk):
    for key in ("text", "content", "chunk_text"):
        value = chunk.get(key)

        if isinstance(value, str) and value.strip():
            return value.strip()

    return ""




def get_metadata(chunk, index):
    metadata = {}

    original = chunk.get("metadata", {})
    if isinstance(original, dict):
        metadata.update(original)

    for key in (
        "source",
        "url",
        "source_url",
        "title",
        "source_file",
        "heading",
        "category",
        "chunk_index",
    ):
        if key in chunk and key not in metadata:
            metadata[key] = chunk[key]

    # Chroma chỉ chấp nhận metadata dạng primitive.
    clean = {}

    for key, value in metadata.items():
        if isinstance(value, (str, int, float, bool)):
            clean[str(key)] = value
        elif value is not None:
            clean[str(key)] = json.dumps(
                value,
                ensure_ascii=False,
            )

    clean["chunk_index_fallback"] = index

    return clean




def get_chunk_id(chunk, index):
    for key in ("id", "chunk_id"):
        value = chunk.get(key)

        if value is not None and str(value).strip():
            return str(value)

    return f"ou_chunk_{index:05d}"


# =========================
# 3. GỌI GEMINI CÓ RETRY
# =========================

def embed_batch(client, texts):
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = client.models.embed_content(
                model=MODEL,
                contents=texts,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT",
                    output_dimensionality=768,
                ),
            )

            vectors = [
                item.values
                for item in response.embeddings
            ]

            if len(vectors) != len(texts):
                raise RuntimeError(
                    "Số vector không khớp số chunks."
                )

            return vectors

        except errors.APIError as error:
            if error.code != 429:
                raise

            if attempt == MAX_ATTEMPTS - 1:
                raise

            wait_seconds = 45 * (attempt + 1)

            print(
                f"Gemini giới hạn API. "
                f"Chờ {wait_seconds} giây "
                f"rồi thử lại..."
            )

            time.sleep(wait_seconds)


# =========================
# 4. CHẠY EMBEDDING
# =========================


def main():
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "Thiếu GEMINI_API_KEY trong file .env"
        )

    chunks = load_chunks()

    records = []
    seen_ids = set()

    # =========================
    # 1. CHUẨN BỊ CHUNKS
    # =========================

    for index, chunk in enumerate(chunks):
        if not isinstance(chunk, dict):
            continue

        text = get_text(chunk)

        if not text:
            continue

        chunk_id = get_chunk_id(chunk, index)

        if chunk_id in seen_ids:
            raise ValueError(
                f"ID chunk bị trùng: {chunk_id}"
            )

        seen_ids.add(chunk_id)

        records.append({
            "id": chunk_id,
            "text": text,
            "metadata": get_metadata(chunk, index),
        })

    if not records:
        raise ValueError(
            "Không có chunk hợp lệ để embedding."
        )

    print(f"Tổng chunks hợp lệ: {len(records)}")

    # =========================
    # 2. KẾT NỐI GEMINI + CHROMA
    # =========================

    client = genai.Client(api_key=api_key)

    CHROMA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    chroma_client = chromadb.PersistentClient(
        path=str(CHROMA_DIR)
    )

    collection = chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    # =========================
    # 3. SO SÁNH CHUNKS
    # =========================

    existing_ids = set(
        collection.get(include=[])["ids"]
    )

    new_ids = {
        record["id"]
        for record in records
    }

    pending = [
        record for record in records
        if record["id"] not in existing_ids
    ]

    existing_records = [
        record for record in records
        if record["id"] in existing_ids
    ]

    stale_ids = sorted(
        existing_ids - new_ids
    )

    print("\n=== CHROMA SYNC ===")
    print(f"Chunks trong JSON: {len(records)}")
    print(f"Chunks trong Chroma: {len(existing_ids)}")
    print(f"Cần embedding: {len(pending)}")
    print(f"Cần cập nhật metadata: {len(existing_records)}")
    print(f"Chunks cũ cần xóa: {len(stale_ids)}")

    # =========================
    # 4. EMBEDDING CHUNKS MỚI
    # =========================

    for start in range(0, len(pending), BATCH_SIZE):
        batch = pending[start:start + BATCH_SIZE]

        texts = [
            item["text"]
            for item in batch
        ]

        vectors = embed_batch(client, texts)

        # Kiểm tra dimension.
        if any(len(v) != 768 for v in vectors):
            raise ValueError(
                "Embedding dimension phải là 768."
            )

        # Lưu batch thành công.
        collection.upsert(
            ids=[
                item["id"]
                for item in batch
            ],
            documents=texts,
            embeddings=vectors,
            metadatas=[
                item["metadata"]
                for item in batch
            ],
        )

        completed = min(
            start + len(batch),
            len(pending),
        )

        print(
            f"Đã embedding {completed}/{len(pending)}"
        )

        if completed < len(pending):
            time.sleep(45)

    # =========================
    # 5. ĐỒNG BỘ METADATA
    # =========================

    print("\nĐang cập nhật metadata...")

    for start in range(
        0,
        len(existing_records),
        BATCH_SIZE,
    ):
        batch = existing_records[
            start:start + BATCH_SIZE
        ]

        collection.update(
            ids=[
                item["id"]
                for item in batch
            ],
            metadatas=[
                item["metadata"]
                for item in batch
            ],
        )

    # =========================
    # 6. XÓA CHUNKS CŨ
    # =========================

    if stale_ids:
        print(
            f"Đang xóa {len(stale_ids)} chunks cũ..."
        )

        for start in range(
            0,
            len(stale_ids),
            BATCH_SIZE,
        ):
            batch_ids = stale_ids[
                start:start + BATCH_SIZE
            ]

            collection.delete(ids=batch_ids)

    # =========================
    # 7. VALIDATION
    # =========================

    final_ids = set(
        collection.get(include=[])["ids"]
    )

    missing_ids = new_ids - final_ids
    remaining_stale_ids = final_ids - new_ids

    print("\n=== VALIDATION ===")
    print(f"Expected chunks: {len(new_ids)}")
    print(f"Actual chunks: {len(final_ids)}")
    print(f"Missing IDs: {len(missing_ids)}")
    print(f"Stale IDs: {len(remaining_stale_ids)}")

    if final_ids != new_ids:
        raise RuntimeError(
            "FAIL: Chroma chưa đồng bộ với chunks.json"
        )

    print("\nPASS: Chroma synchronized!")
    print("Embedding Gemini hoàn tất!")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Chroma lưu tại: {CHROMA_DIR}")


if __name__ == "__main__":
    main()
