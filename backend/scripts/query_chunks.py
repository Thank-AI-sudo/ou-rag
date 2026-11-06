
import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from google import genai
from google.genai import types


# 1. Xác định thư mục gốc của project
ROOT_DIR = Path(__file__).resolve().parents[2]

# 2. Đọc cấu hình từ .env
load_dotenv(ROOT_DIR / ".env")

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv(
    "GEMINI_EMBEDDING_MODEL",
    "gemini-embedding-001",
)
CHROMA_DIR = Path(
    os.getenv("CHROMA_PERSIST_DIR", "data/chroma")
)
COLLECTION_NAME = os.getenv(
    "CHROMA_COLLECTION_NAME",
    "ou_documents_gemini",
)

if not CHROMA_DIR.is_absolute():
    CHROMA_DIR = ROOT_DIR / CHROMA_DIR

if not API_KEY:
    raise ValueError("Chưa cấu hình GEMINI_API_KEY trong .env")

# 3. Khởi tạo Gemini và ChromaDB
client = genai.Client(api_key=API_KEY)

chroma_client = chromadb.PersistentClient(
    path=str(CHROMA_DIR)
)

collection = chroma_client.get_collection(
    name=COLLECTION_NAME
)

# 4. Nhập câu hỏi
question = input("Nhập câu hỏi: ").strip()

if not question:
    raise ValueError("Câu hỏi không được để trống.")

# 5. Tạo embedding cho câu hỏi
embedding_response = client.models.embed_content(
    model=MODEL,
    contents=question,
    config=types.EmbedContentConfig(
        task_type="RETRIEVAL_QUERY",
        output_dimensionality=768,
    ),
)

query_embedding = embedding_response.embeddings[0].values

# 6. Tìm kiếm các chunks liên quan trong ChromaDB
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=5,
    include=["documents", "metadatas", "distances"],
)

# 7. Hiển thị kết quả
documents = results["documents"][0]
metadatas = results["metadatas"][0]
distances = results["distances"][0]

print(f"\nSố chunks tìm được: {len(documents)}")

for i, (document, metadata, distance) in enumerate(
    zip(documents, metadatas, distances),
    start=1,
):
    print(f"\n{'=' * 70}")
    print(f"CHUNK {i}")
    print(f"Distance: {distance}")

    print("\nMetadata:")
    for key, value in (metadata or {}).items():
        print(f"  {key}: {value}")

    print("\nNội dung:")
    print(document)
