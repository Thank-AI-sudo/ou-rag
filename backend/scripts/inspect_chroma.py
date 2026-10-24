
from pathlib import Path
import chromadb
from dotenv import load_dotenv
import os

# Xác định thư mục gốc dự án
ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")

# Kết nối ChromaDB đã lưu trên máy
chroma_dir = ROOT_DIR / os.getenv(
    "CHROMA_PERSIST_DIR", "data/chroma"
)

client = chromadb.PersistentClient(
    path=str(chroma_dir)
)

# Mở collection đã embedding
collection = client.get_collection(
    name="ou_documents_gemini"
)

print("Tên collection:", collection.name)
print("Tổng số bản ghi:", collection.count())

# Lấy thử 3 bản ghi đầu tiên
results = collection.get(
    limit=3,
    include=["documents", "metadatas", "embeddings"]
)

for i, chunk_id in enumerate(results["ids"]):
    print(f"\n{'=' * 50}")
    print("ID:", chunk_id)
    print("Nội dung:", results["documents"][i])
    print("Metadata:", results["metadatas"][i])

    embedding = results["embeddings"][i]
    print("Số chiều embedding:", len(embedding))
    print("5 giá trị vector đầu:", embedding[:5])
