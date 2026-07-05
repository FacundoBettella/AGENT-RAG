from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from m2project.adapters.chroma_store import ChromaStore
from m2project.adapters.json_log import JsonLogRepository
from m2project.adapters.openai_embedder import OpenAIEmbedder
from m2project.adapters.openai_llm import OpenAILLMClient
from m2project.adapters.text_loader import TextLoader
from m2project.services.chunker import Chunker
from m2project.services.indexer import Indexer
from m2project.services.moderation_service import ModerationEvaluator, ModerationService
from m2project.services.pipeline import RAGPipeline
from m2project.services.retriever import Retriever


@dataclass
class FAQBundle:
    indexer: Indexer
    pipeline: RAGPipeline


def build_faq_bundle(
    vector_store: Literal["chroma", "faiss"] = "chroma",
    collection_name: str = "faq",
    persist_directory: str = ".chroma",
    chunk_size: int = 500,
    chunk_overlap: int = 100,
    top_k: int = 3,
    chat_model: str = "gpt-4o-mini",
    embedding_model: str = "text-embedding-3-small",
) -> FAQBundle:
    api_key = os.getenv("OPENAI_API_KEY")
    log_hash_salt = os.getenv("LOG_HASH_SALT", "m2-default-salt-change-me")
    logs_dir = os.getenv("LOGS_DIR", "logs")

    embedder = OpenAIEmbedder(model=embedding_model, api_key=api_key)

    if vector_store == "faiss":
        from m2project.adapters.faiss_store import FAISSStore
        store = FAISSStore(embedder=embedder, persist_path=".faiss")
    else:
        store = ChromaStore(
            embedder=embedder,
            collection_name=collection_name,
            persist_directory=persist_directory,
        )

    loader = TextLoader()
    chunker = Chunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    indexer = Indexer(loader=loader, chunker=chunker, store=store)

    llm = OpenAILLMClient(model=chat_model, api_key=api_key)
    retriever = Retriever(store=store, top_k=top_k)
    moderation = ModerationService(
        evaluator=ModerationEvaluator(salt=log_hash_salt),
        log_repository=JsonLogRepository(logs_dir=logs_dir),
    )
    pipeline = RAGPipeline(retriever=retriever, llm=llm, moderation=moderation)

    return FAQBundle(indexer=indexer, pipeline=pipeline)
