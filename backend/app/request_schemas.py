
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        description="Câu hỏi cần tìm kiếm trong tài liệu OU",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Số lượng chunks liên quan cần trả về",
    )


class SourceItem(BaseModel):
    chunk_id: str
    content: str
    metadata: dict
    distance: float | None = None
    rrf_score: float | None = None


class SearchResponse(BaseModel):
    question: str
    results: list[SourceItem]
    total: int
