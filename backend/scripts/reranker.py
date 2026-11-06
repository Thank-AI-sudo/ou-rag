
import os
import cohere


def rerank_chunks(question: str, chunks: list, top_n: int = 3):
    if not chunks:
        return []

    api_key = os.getenv("COHERE_API_KEY")
    if not api_key:
        raise RuntimeError("Thiếu COHERE_API_KEY")

    client = cohere.ClientV2(api_key=api_key)

    documents = [
        chunk["content"]
        for chunk in chunks
    ]

    response = client.rerank(
        model=os.getenv(
            "COHERE_RERANK_MODEL",
            "rerank-v5.0-fast"
        ),
        query=question,
        documents=documents,
        top_n=min(top_n, len(chunks)),
    )

    ranked = []

    for result in response.results:
        original_chunk = chunks[result.index].copy()

        original_chunk["rerank_score"] = (
            result.relevance_score
        )

        ranked.append(original_chunk)

    return ranked
