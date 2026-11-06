
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
import chromadb


# 1. Đọc cấu hình từ file .env
ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")

MODEL = os.getenv(
    "GEMINI_EMBEDDING_MODEL",
    "gemini-embedding-001"
)

CHROMA_DIR = Path(
    os.getenv("CHROMA_PERSIST_DIR", "data/chroma")
)
if not CHROMA_DIR.is_absolute():
    CHROMA_DIR = ROOT_DIR / CHROMA_DIR

COLLECTION_NAME = os.getenv(
    "CHROMA_COLLECTION_NAME",
    "ou_documents_gemini"
)


def main():
    # 2. Kết nối Gemini
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "Không tìm thấy GEMINI_API_KEY trong file .env"
        )

    gemini_client = genai.Client(api_key=api_key)

    # 3. Kết nối ChromaDB
    chroma_client = chromadb.PersistentClient(
        path=str(CHROMA_DIR)
    )

    collection = chroma_client.get_collection(
        name=COLLECTION_NAME
    )

    print("Collection:", COLLECTION_NAME)
    print("Tổng số chunks:", collection.count())

    # 4. Nhập câu hỏi từ người dùng
    question = input("\nNhập câu hỏi (hoặc q để thoát): ").strip()

    if not question or question.lower() == "q":
        print("Đã thoát.")
        return

    # 5. Chuyển câu hỏi thành vector
    response = gemini_client.models.embed_content(
        model=MODEL,
        contents=question,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=768,
        ),
    )

    query_embedding = response.embeddings[0].values

    # 6. Tìm 5 chunks gần nhất trong ChromaDB
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(5, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    # 7. In kết quả
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    if not documents:
        print("Không tìm thấy tài liệu phù hợp.")
        return

    print(f"\nTìm thấy {len(documents)} chunks:\n")

    for i, (document, metadata, distance) in enumerate(
        zip(documents, metadatas, distances),
        start=1,
    ):
        print("=" * 70)
        print(f"KẾT QUẢ {i}")
        print(f"Khoảng cách: {distance:.4f}")
        print("\nNội dung:")
        print(document)

        print("\nMetadata / nguồn:")
        print(metadata)

    print("=" * 70)


if __name__ == "__main__":
    main()
