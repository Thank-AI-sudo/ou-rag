import re
from functools import lru_cache

from rank_bm25 import BM25Okapi


def tokenize(text: str) -> list[str]:
    """
    Tách tiếng Việt thành các tiếng và cặp tiếng liên tiếp.
    Bản đơn giản phục vụ thử nghiệm BM25.
    """
    words = re.findall(
        r"[^\W_]+",
        text.lower(),
        flags=re.UNICODE,
    )

    bigrams = [
        words[i] + "_" + words[i + 1]
        for i in range(len(words) - 1)
    ]

    return words + bigrams


@lru_cache(maxsize=1)
def build_bm25_index():
    from backend.app.services.retrieval import collection

    data = collection.get(
        include=["documents", "metadatas"]
    )

    ids = data["ids"]
    documents = data["documents"]
    metadatas = data["metadatas"]

    tokenized_corpus = [
        tokenize(doc or "")
        for doc in documents
    ]

    bm25 = BM25Okapi(tokenized_corpus)

    return bm25, ids, documents, metadatas


def keyword_search(question: str, top_k: int = 10):
    bm25, ids, documents, metadatas = build_bm25_index()

    query_tokens = tokenize(question)
    scores = bm25.get_scores(query_tokens)

    ranked_indices = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True,
    )

    results = []

    for i in ranked_indices:
        if scores[i] <= 0:
            continue

        results.append({
            "chunk_id": ids[i],
            "content": documents[i] or "",
            "metadata": metadatas[i] or {},
            "distance": None,
        })

        if len(results) >= top_k:
            break

    return results


def reciprocal_rank_fusion(
    vector_results: list[dict],
    keyword_results: list[dict],
    top_k: int = 5,
    k: int = 60,
):
    fused = {}

    for result_list in [vector_results, keyword_results]:
        for rank, item in enumerate(result_list, start=1):
            chunk_id = item["chunk_id"]

            if chunk_id not in fused:
                fused[chunk_id] = {
                    **item,
                    "rrf_score": 0.0,
                }

            fused[chunk_id]["rrf_score"] += 1 / (k + rank)

            # Giữ distance của Vector Search nếu có.
            if item.get("distance") is not None:
                fused[chunk_id]["distance"] = item["distance"]

    ranked = sorted(
        fused.values(),
        key=lambda x: x["rrf_score"],
        reverse=True,
    )
    
    return ranked[:top_k]