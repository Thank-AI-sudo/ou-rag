import re
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


from fastapi import HTTPException
from pydantic import BaseModel, Field

# Điều chỉnh đường dẫn này theo file thực tế
# đang chứa hàm hybrid_search() của bạn.
from backend.app.services.retrieval import hybrid_search
from backend.app.services.reranker import rerank_chunks
from backend.app.services.generator import generate_answer
import traceback

from backend.app.request_schemas import (
    SearchRequest,
    SearchResponse,
    SourceItem,
)

from backend.app.services.citation_validator import (
    validate_citations
)

app = FastAPI(
    title="OU RAG Chatbot API",
    version="0.1.0",
    description="Backend API cho hệ thống OU RAG Chatbot"
)
# Cho phép frontend gọi API trong môi trường phát triển

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Welcome to OU RAG Chatbot API"}

@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "ou-rag-chatbot",
        "version": "0.1.0",
    }   


@app.post("/api/search", response_model=SearchResponse)
def search(request: SearchRequest):
    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=422,
            detail="Câu hỏi không được để trống",
        )

    try:
        results = hybrid_search(
            question=question,
            top_k=request.top_k,
        )

        return SearchResponse(
            question=question,
            results=[
                SourceItem(**item) for item in results
            ],
            total=len(results),
        )


    except Exception as exc:
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"{type(exc).__name__}: {exc}",
        )


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    top_k: int = Field(default=10, ge=1, le=30)
    top_n: int = Field(default=3, ge=1, le=10)


def get_source(chunk: dict, number: int) -> dict:
    """Tạo thông tin nguồn từ chunk đã rerank."""

    metadata = chunk.get("metadata") or {}
    content = chunk.get("content", "")

    url = (
        metadata.get("source_url")
        or metadata.get("url")
        or ""
    )

    # Nếu metadata chưa có URL, thử lấy từ Markdown
    if not str(url).startswith(("http://", "https://")):
        match = re.search(
            r"https?://[^\s)>\]]+",
            content
        )
        url = match.group(0) if match else None

    return {
        "number": number,
        "chunk_id": chunk.get("chunk_id"),
        "title": metadata.get("title", "Không có tiêu đề"),
        "url": url,
        "source_file": metadata.get("source_file"),
        "rerank_score": chunk.get("rerank_score"),
    }


@app.post("/api/chat")
def chat(request: ChatRequest):

    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=422,
            detail="Câu hỏi không được để trống"
        )

    # 1. Hybrid Retrieval + RRF
    try:
        chunks = hybrid_search(
            question=question,
            top_k=request.top_k,
        )
    except Exception:
        traceback.print_exc()
        raise HTTPException(
            status_code=503,
            detail="Không thể truy xuất tài liệu"
        )

    if not chunks:
        return {
            "question": question,
            "answer": "Không tìm thấy tài liệu phù hợp.",
            "sources": [],
            "retrieved_count": 0,
            "reranking_used": False,
        }

    # 2. Cohere Reranking
    reranking_used = True

    try:
        ranked_chunks = rerank_chunks(
            question=question,
            chunks=chunks,
            top_n=request.top_n,
        )

        if not ranked_chunks:
            raise RuntimeError("Reranker trả về rỗng")

    except Exception:
        traceback.print_exc()
        reranking_used = False

        # Nếu Cohere lỗi, dùng Top N từ RRF
        ranked_chunks = chunks[:request.top_n]

    # 3. Gemini Generation
    try:
        answer = generate_answer(
            question=question,
            chunks=ranked_chunks,
        )
    except Exception:
        traceback.print_exc()
        raise HTTPException(
            status_code=503,
            detail="Không thể sinh câu trả lời"
        )

    
    # 4. Tạo danh sách nguồn ban đầu
    sources = [
        get_source(chunk, index)
        for index, chunk in enumerate(ranked_chunks, start=1)
    ]

    # 5. Citation Validation
    answer, validated_sources = validate_citations(
        answer=answer,
        sources=sources
    )

    # 6. API Response
    return {
        "question": question,
        "answer": answer,
        "sources": validated_sources,
        "retrieved_count": len(chunks),
        "reranking_used": reranking_used,
    }