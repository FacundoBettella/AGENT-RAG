from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Domain = Literal["hr", "tech", "finance"]


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
    intent: str
    reasoning: str


class QueryResponse(BaseModel):
    query_result: QueryResult


class HealthResponse(BaseModel):
    status: str
    chunks_indexed: dict[str, int]


class IngestRequest(BaseModel):
    domain: Domain
    documents: list[str]


class IngestResult(BaseModel):
    domain: Domain
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
    intent: str
    evaluation: EvaluationScore | dict


class EvaluateResponse(BaseModel):
    evaluate_result: EvaluateResult
