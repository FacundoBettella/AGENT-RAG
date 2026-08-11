# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A multi-agent internal support system (HR / IT / Finance). An **Orchestrator** classifies an
employee's question by intent and conditionally routes it to a specialized **RAG agent**
(HR, Tech, or Finance). Built with LangChain (LCEL, 1.x — no `create_agent`), traced end-to-end
with Langfuse v4, gated by a pre-LLM moderation layer, and scored by an LLM-as-judge evaluator.

This started as a single-domain FAQ chatbot (hexagonal architecture) and was migrated into this
multi-agent system — a lot of the design only makes sense in light of that migration. **The "why"
behind every non-obvious technical choice is recorded as ADRs in `docs/DECISIONS.md`** (ADR-001
through ADR-012) — check it before assuming something is arbitrary or before revisiting a decision
that already has a documented rationale (e.g. why Chroma over FAISS, why LCEL over `create_agent`,
why moderation lives only in the Orchestrator).

`README.md` is deliberately kept short (tech stack, setup, endpoints only). The prose version of
the flows below — plus the directory tree and known limitations — lives in
`docs/ARCHITECTURE.md` (in Spanish); read it for more detail than this file gives.

## Commands

All development runs in Docker — there is no local venv in this repo (removed deliberately;
Docker is the only supported way to install/run this project now).

```bash
cp .env.example .env              # then fill in OPENAI_API_KEY at minimum
docker compose up --build         # API at http://localhost:8080, live reload via bind mounts
```

`docker-compose.yml` (project name `agent-rag`) bind-mounts `src/`, `data/`, `scripts/`,
`test_queries.json`, `.chroma/` and `logs/` into the container, so editing any of those on the
host takes effect without rebuilding the image — only changes to `requirements.txt` or the
`Dockerfile` itself require `--build` again. `.chroma/` and `logs/` are mounted (not just
copied) so the vector store and the moderation audit log survive `docker compose down`.

```bash
# One-off query through the full orchestrator, prints JSON
docker compose exec app python scripts/02_query.py "<question>"

# Same as 02_query, plus LLM-as-judge evaluation
docker compose exec app python scripts/03_evaluate.py "<question>"

# Force ingestion of the 3 knowledge bases into Chroma (no-op if already indexed)
docker compose exec app python scripts/01_ingest.py

# Run the full test suite (test_queries.json, 21 cases) against the orchestrator,
# with a per-category accuracy breakdown. This is the test runner for this repo —
# there is no pytest suite.
docker compose exec app python scripts/05_test_routing.py
```

`scripts/04_serve.py` (local `uvicorn` runner) is superseded by `docker compose up` — the
compose file starts `uvicorn` directly (see `Dockerfile`/`docker-compose.yml`'s `command:`).
The notebook (`multi_agent_system.ipynb`) is the one workflow Docker doesn't cover — it needs a
local Jupyter kernel with `pip install -r requirements.txt`, since the container only runs the
API, not Jupyter.

There is no linter or formatter configured in this repo (no pyproject.toml/ruff/flake8 config).

Scripts and the API both add `src/` to `sys.path` manually (see the `sys.path.insert(0, ...)` line
near the top of each `scripts/*.py`, and `--app-dir src` in the Dockerfile/compose `command:`) —
imports inside `src/` are written as absolute-from-`src` (e.g. `from agents import hr_agent`, not
`from src.agents import ...`).

**Path resolution**: all on-disk paths (`.chroma/`, `logs/`, `data/<domain>_docs/`) are resolved
against the project root via `src/factory.py::_resolve`, never against `cwd`. This is deliberate —
the server must produce the same files whether launched from the repo root or from `src/`. If you
add a new on-disk path anywhere, route it through `_resolve()` too.

## Architecture

Hexagonal: business logic never imports LangChain/Chroma/OpenAI directly, only through `ports/`
(Python `Protocol`s). `factory.py` is the **single place** that instantiates concrete adapters.

```text
domain/     DTOs (Chunk, RAGResponse), ModerationAction, exceptions
ports/      Protocols — Embedder, VectorStore, LLMClient, LogRepository
adapters/   concrete implementations — LangChain lives IN HERE
              chroma_store.py   → langchain_chroma
              faiss_store.py    → alternative VectorStore adapter, not used in the live flow
              openai_llm.py     → langchain_openai
              tracing.py        → Langfuse CallbackHandler
services/   Chunker, Indexer, Retriever, RAGPipeline (the LCEL chain), ModerationService, evaluator
agents/     DomainAgent (HR/Tech/Finance) + Orchestrator (classification + routing)
api/        FastAPI app exposing the Orchestrator over HTTP
factory.py  the only module that wires adapters together
```

Deliberate deviation from textbook hexagonal: `ports/llm.py` exposes LangChain's `BaseChatModel`
type on purpose, so callers can compose LCEL chains (`prompt | llm.model | parser`) without the
port reimplementing chain composition. LangChain's *types* leak through the port; the library
usage itself still lives only in adapters (see ADR-002).

### Request flow (`Orchestrator.handle()` — the one entry point)

```text
question
  → ① moderation gate (3 layers, see below) → BLOCK → ContentBlockedError, 0 tokens spent
  → ② intent classification (structured output, temperature=0) → hr | tech | finance | unknown
  → ③ routing
       unknown        → fixed "out of scope" response, no agent called
       hr/tech/finance → DomainAgent.ask() → Chroma top-k retrieve → LCEL chain (prompt | llm | parser)
  → OrchestratorResponse(question, intent, reasoning, rag_response, trace_id)
```

The 3 domain agents (`agents/hr_agent.py`, `tech_agent.py`, `finance_agent.py`) are all the same
`DomainAgent` class wrapping a `RAGPipeline`, parameterized by Chroma collection name, `data/`
folder, and system prompt (see `agents/base.py` / `DomainAgentConfig`). They are not meant to be
called directly in production — the Orchestrator is the only front door (ADR-007).

Moderation runs **only** inside `Orchestrator.handle()`, not inside `RAGPipeline` — it used to be
duplicated and was deliberately pulled out to a single gate (ADR-007). Don't re-add a moderation
check inside a domain agent or pipeline.

### Ingestion (lazy, per collection)

Each domain's `DomainAgent` builds its `FAQBundle` (indexer + pipeline) lazily on first `.ask()`.
If its Chroma collection is already non-empty, indexing is skipped — there is **no incremental
re-indexing**: editing a `.txt` under `data/<domain>_docs/` after first use requires deleting
`.chroma/` and re-ingesting, and re-running ingestion twice duplicates content (no idempotent
upsert). All 3 collections (`hr_docs`, `tech_docs`, `finance_docs`) share one Chroma
`persist_directory` (`.chroma/`) via multiple named collections (ADR-005).

### Tracing (Langfuse v4, OTel-based — API differs from v2)

`Orchestrator.handle()` is wrapped in `@observe`, opening one root span = one trace per question.
A single `CallbackHandler` is created per request and passed as `callbacks` to both the
classification chain and the routed agent's generation chain, so both nest under the same trace via
OTel context instead of producing two unrelated traces (ADR-011). If `LANGFUSE_PUBLIC_KEY`/
`LANGFUSE_SECRET_KEY` are unset, the client self-disables with a warning — tracing is best-effort,
never a hard dependency (ADR-010).

### Evaluation (LLM-as-judge)

`evaluate_response()` scores a completed `OrchestratorResponse` 0-10 on relevance/accuracy/
completeness, then `push_evaluation_score(trace_id, ...)` attaches that score to the same Langfuse
trace via the Score API. Wired into `POST /api/evaluate` and `scripts/03_evaluate.py`.

### Moderation — 3 pre-LLM layers (`services/moderation_service.py`)

Runs before any OpenAI call is made, inside `Orchestrator.handle()`:

| Layer | Detects | Technique | Action |
| --- | --- | --- | --- |
| 1 — Sensitive data | Credit cards (Visa/MC/Amex), CUIT/CUIL, SSN | Regex | BLOCK |
| 2 — Prompt injection | Adversarial framing (`roleplay`, `ignore instructions`, etc.) combined with a sensitive token | Keyword combination | BLOCK (framing alone → FLAG) |
| 3 — Abusive language | Hate speech, violence, self-harm, cyber abuse | Keywords | BLOCK |

`ModerationEvaluator` is a stateless, pure classifier (no I/O, easy to unit test in isolation);
`ModerationService` wraps it and writes every check (ALLOW/FLAG/BLOCK) to
`logs/moderation_events.jsonl` — the original text is never logged, only a salted SHA-256 hash
(`LOG_HASH_SALT`), with retention tag varying by severity. `BLOCK` raises `ContentBlockedError`,
which the API maps to HTTP 400 before classification or any OpenAI call happens. `FLAG` does not
block — the question is answered normally but the event is still audited.

## Testing conventions

There is no pytest suite. `test_queries.json` (21 cases: 12 domain-routing + 3 out-of-scope +
2 ambiguous + 4 moderation) is the fixture, and `scripts/05_test_routing.py` is the runner — it
drives every case through the real `Orchestrator.handle()` and compares the resulting `intent`
against `expected_intent` (a `ContentBlockedError` counts as `intent == "blocked"`). Cases with
`category: "moderation"` additionally assert against `ModerationService.check()` directly
(`expected_moderation` and `expected_risk`), so both the final intent *and* the specific
risk/action the moderation layer detected are covered. When adding a new domain/routing/moderation
case, add it to `test_queries.json` rather than writing an ad hoc script.

If you find a misclassification, the fix belongs in the classification prompt
(`agents/orchestrator.py::_CLASSIFICATION_USER_TEMPLATE`), not in the test fixture — see ADR-008,
where a real routing bug (a "tech" bucket that didn't cover design-tool questions) was fixed this
way rather than adjusting the expected answer.

## Known limitations (don't try to silently "fix" these — they're documented trade-offs)

- No incremental ingestion / no idempotent upsert (see Ingestion above).
- FAISS adapter (`adapters/faiss_store.py`) exists behind the same `VectorStore` port but isn't
  used by the live multi-agent flow (ADR-005) — don't assume it's dead code to delete, and don't
  assume it's wired in either.
- No conversational memory — each question is handled independently.
- Routing is single-hop: the Orchestrator picks exactly one domain per question; a genuinely
  compound cross-domain question is not split or fanned out to multiple agents (see `amb-01`/
  `amb-02` in `test_queries.json`).
