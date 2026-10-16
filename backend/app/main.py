from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="OU RAG Chatbot API",
    version="0.1.0",
    description="Backend API cho hệ thống OU RAG Chatbot"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to OU RAG Chatbot API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
