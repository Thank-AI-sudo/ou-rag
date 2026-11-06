import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from google import genai
from google.genai import types


# 1. Xác định thư mục gốc của dự án
ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")

# 2. Cấu hình
CHROMA_DIR = Path(
    os.getenv("CHROMA_PERSIST_DIR", "data/chroma")
)
if not CHROMA_DIR.is_absolute():
    CHROMA_DIR = ROOT_DIR / CHROMA_DIR

COLLECTION_NAME = os.getenv(
    "CHROMA_COLLECTION_NAME",
    "ou_documents_gemini",
)

EMBEDDING_MODEL = os.getenv(
    "GEMINI_EMBEDDING_MODEL",
    "gemini-embedding-001",
)

TOP_K = 10


def embed_query(client, question: str) -> list[float]:
    """Chuyển câu hỏi thành vector dùng cho retrieval."""

    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=question,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=768,
        ),
    )

    if not response.embeddings:
        raise RuntimeError("Gemini không trả về embedding.")

    return list(response.embeddings[0].values)


def retrieve(question: str) -> None:
    # Kết nối Gemini
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Không tìm thấy GEMINI_API_KEY trong file .env"
        )

    gemini_client = genai.Client(api_key=api_key)

    # Kết nối ChromaDB đã lưu trên ổ đĩa
    chroma_client = chromadb.PersistentClient(
        path=str(CHROMA_DIR)
    )

    collection = chroma_client.get_collection(
        name=COLLECTION_NAME
    )

    print(f"\nCollection: {COLLECTION_NAME}")
    print(f"Tổng số chunks: {collection.count()}")
    print(f"Câu hỏi: {question}")

    # Vector của câu hỏi
    query_vector = embed_query(gemini_client, question)

    # Tìm Top K chunks gần nhất
    results = collection.query(
        query_embeddings=[query_vector],
        n_results=min(TOP_K, collection.count()),
        include=[
            "documents",
            "metadatas",
            "distances",
        ],
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]
    ids = results["ids"][0]

    print("\n" + "=" * 70)
    print(f"KẾT QUẢ RETRIEVAL: {len(documents)} CHUNKS")
    print("=" * 70)

    for rank, (chunk_id, document, metadata, distance) in enumerate(
        zip(ids, documents, metadatas, distances),
        start=1,
    ):
        print(f"\n[{rank}] Chunk ID: {chunk_id}")
        print(f"Distance: {distance:.4f}")
        print(f"Metadata: {metadata}")
        print("-" * 70)
        print(document)

    print("\n" + "=" * 70)
    print("Hoàn tất retrieval.")


if __name__ == "__main__":
    question = input(
        "Nhập câu hỏi của sinh viên OU: "
    ).strip()

    if not question:
        print("Vui lòng nhập câu hỏi.")
    else:
        try:
            retrieve(question)
        except Exception as error:
            print(f"Lỗi retrieval: {error}")
            raise
