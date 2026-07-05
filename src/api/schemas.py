from __future__ import annotations

from pydantic import BaseModel


class QuestionRequest(BaseModel):
    question: str


class ErrorResponse(BaseModel):
    error: str


class ChunkOut(BaseModel):
    content: str
    source: str
    similarity: float


class QueryResult(BaseModel):
    user_question: str
    system_answer: str
    chunks_related: list[ChunkOut]


class QueryResponse(BaseModel):
    query_result: QueryResult


class HealthResponse(BaseModel):
    status: str
    chunks_indexed: int


class IngestRequest(BaseModel):
    documents: list[str]


class IngestResult(BaseModel):
    documents_received: int
    chunks_indexed: int
    total_in_store: int


class IngestResponse(BaseModel):
    ingest_result: IngestResult


class EvaluationScore(BaseModel):
    score: int
    relevancia: int
    precision: int
    completitud: int
    justificacion: str


class EvaluateResult(BaseModel):
    user_question: str
    system_answer: str
    chunks_related: list[ChunkOut]
    evaluation: EvaluationScore | dict


class EvaluateResponse(BaseModel):
    evaluate_result: EvaluateResult
