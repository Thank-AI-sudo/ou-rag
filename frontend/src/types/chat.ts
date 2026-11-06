export interface ChatSource {
    number: number;
    chunk_id: string | null;
    title: string;
    url: string | null;
    source_file: string | null;
    rerank_score: number | null;
}

export interface ChatRequest {
    question: string;
    top_k?: number;
    top_n?: number;
}

export interface ChatResponse {
    question: string;
    answer: string;
    sources: ChatSource[];
    retrieved_count: number;
    reranking_used: boolean;
}

export interface ChatMessageData {
    id: string;
    role: "user" | "assistant";
    content: string;
    sources?: ChatSource[];
}
