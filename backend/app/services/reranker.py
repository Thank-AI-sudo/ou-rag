
import os

import cohere


def rerank_chunks(
    question: str,
    chunks: list[dict],
    top_n: int = 3
) -> list[dict]:
    """
    Nhận chunks từ Vector Search.
    Sử dụng Cohere để xếp hạng lại.
    Giữ nguyên metadata và nguồn.
    """

    if not chunks:
        return []

    if top_n < 1:
        raise ValueError("top_n phải >= 1")

    api_key = os.getenv("COHERE_API_KEY")

    if not api_key:
        raise RuntimeError("Thiếu COHERE_API_KEY")

    # Loại bỏ chunk không có nội dung
    valid_chunks = [
        chunk
        for chunk in chunks
        if isinstance(chunk.get("content"), str)
        and chunk["content"].strip()
    ]

    if not valid_chunks:
        return []

    # Chỉ gửi content sang Cohere
    documents = [
        chunk["content"]
        for chunk in valid_chunks
    ]

    client = cohere.ClientV2(api_key=api_key)

    response = client.rerank(
        model=os.getenv(
            "COHERE_RERANK_MODEL",
            "rerank-v5.0-fast"
        ),
        query=question,
        documents=documents,
        top_n=min(top_n, len(documents))
    )

    ranked_chunks = []

    for result in response.results:
        # Tìm lại chunk gốc qua index
        chunk = valid_chunks[result.index].copy()

        # Lưu điểm rerank
        chunk["rerank_score"] = result.relevance_score

        ranked_chunks.append(chunk)

    return ranked_chunks
