
import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from google import genai
from google.genai import types
ROOT_DIR = Path(__file__).resolve().parents[3]
load_dotenv(ROOT_DIR / ".env")

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

chroma_client = chromadb.PersistentClient(
    path=str(CHROMA_DIR)
)
collection = chroma_client.get_collection(
    name=COLLECTION_NAME
)

gemini_client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


def search_chunks(question: str, top_k: int = 5) -> list[dict]:
    
    response = gemini_client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=question,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=768,
        ),
    )

    query_embedding = response.embeddings[0].values


    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    documents = results["documents"][0]
    ids = results["ids"][0]
    metadatas = results["metadatas"][0]
    # Lấy thêm distance
    distances = results["distances"][0]
    return [
        {
            "chunk_id": ids[i],
            "content": documents[i] or "",
            "metadata": metadatas[i] or {},
            "distance": distances[i],
        }
        for i in range(len(ids))
    ]


def hybrid_search(question: str, top_k: int = 5):

    from backend.app.services.hybrid_search import (
        keyword_search,
        reciprocal_rank_fusion,
    )

    candidate_k = max(top_k * 2, 10)

    # 1. Vector Search
    vector_results = search_chunks(
        question=question,
        top_k=candidate_k,
    )

    # 2. Keyword Search
    keyword_results = keyword_search(
        question=question,
        top_k=candidate_k,
    )

    # 3. Fusion
    return reciprocal_rank_fusion(
        vector_results=vector_results,
        keyword_results=keyword_results,
        top_k=top_k,
    )