from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from adapters.chroma_store import ChromaStore
from adapters.json_log import JsonLogRepository
from adapters.openai_embedder import OpenAIEmbedder
from adapters.openai_llm import OpenAILLMClient
from adapters.text_loader import TextLoader
from services.chunker import Chunker
from services.indexer import Indexer
from services.moderation_service import ModerationEvaluator, ModerationService
from services.pipeline import DEFAULT_SYSTEM_PROMPT, RAGPipeline
from services.retriever import Retriever


@dataclass
class FAQBundle:
    indexer: Indexer
    pipeline: RAGPipeline


def build_faq_bundle(
    collection_name: str = "faq",
    data_dir: str | None = None,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    vector_store: Literal["chroma", "faiss"] = "chroma",
    persist_directory: str = ".chroma",
    chunk_size: int = 500,
    chunk_overlap: int = 100,
    top_k: int = 3,
    chat_model: str = "gpt-4o-mini",
    embedding_model: str = "text-embedding-3-small",
) -> FAQBundle:
    """Wire up one domain's RAG bundle (indexer + pipeline).

    `collection_name` and `data_dir` are what make this multi-domain: each
    of the 3 specialized agents (src/agents/*) calls this with its own
    collection name and knowledge base directory, sharing one Chroma
    PersistentClient/persist_directory — ChromaDB supports multiple named
    collections in a single client, which is why it was chosen over FAISS
    (which has no native collection concept) for this multi-agent system.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    log_hash_salt = os.getenv("LOG_HASH_SALT", "m2-default-salt-change-me")
    logs_dir = os.getenv("LOGS_DIR", "logs")

    embedder = OpenAIEmbedder(model=embedding_model, api_key=api_key)

    if vector_store == "faiss":
        from adapters.faiss_store import FAISSStore
        store = FAISSStore(embedder=embedder, persist_path=f".faiss/{collection_name}")
    else:
        store = ChromaStore(
            embedder=embedder,
            collection_name=collection_name,
            persist_directory=persist_directory,
        )

    loader = TextLoader()
    chunker = Chunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    indexer = Indexer(loader=loader, chunker=chunker, store=store)

    if data_dir is not None and store.count() == 0:
        indexer.index(data_dir)

    llm = OpenAILLMClient(model=chat_model, api_key=api_key)
    retriever = Retriever(store=store, top_k=top_k)
    moderation = ModerationService(
        evaluator=ModerationEvaluator(salt=log_hash_salt),
        log_repository=JsonLogRepository(logs_dir=logs_dir),
    )
    pipeline = RAGPipeline(retriever=retriever, llm=llm, moderation=moderation, system_prompt=system_prompt)

    return FAQBundle(indexer=indexer, pipeline=pipeline)
