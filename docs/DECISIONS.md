# Decisiones técnicas — Architecture Decision Records (ADR)

Registro de decisiones tomadas durante la migración de M2 (RAG single-domain
custom) a M3 (sistema multi-agente con LangChain + Langfuse). Cada entrada
sigue el formato: **Contexto → Decisión → Alternativas consideradas →
Consecuencias**.

---

## ADR-001: Formato del entregable — archivos .py + notebook demo

**Contexto:** M3 acepta un notebook único (`multi_agent_system.ipynb`) o
múltiples archivos `.py`. El repo M2 ya tiene una arquitectura hexagonal en
`src/` (domain/ports/adapters/services).

**Decisión:** La lógica vive en `src/agents/*.py` (código real, testeable,
importable). Un notebook delgado importa esos módulos y muestra el flujo
completo por secciones (setup, vector stores, agentes, orquestador, tests,
Langfuse) como pide la consigna.

**Alternativas consideradas:**
- *Solo notebook*: todo el código dentro de celdas. Más simple de corregir,
  pero mezcla lógica de negocio con exploración, no es testeable, y
  desaprovecha la estructura `src/` que ya existe.
- *Solo .py + scripts CLI*: sin notebook. Más "producción", pero pierde la
  narrativa ejecutable paso a paso que la consigna espera para mostrar el
  razonamiento.

**Consecuencias:** hay que mantener el notebook sincronizado con los módulos
(no duplicar lógica en celdas). El notebook es una capa de presentación, no
de implementación.

---

## ADR-002: Arquitectura — hexagonal envolviendo LangChain

**Contexto:** M2 tiene `ports/` (Protocols) y `adapters/` (implementaciones
concretas de OpenAI, Chroma, FAISS) para poder intercambiar proveedores sin
tocar la lógica de negocio. M3 exige usar LangChain, que ya trae sus propias
abstracciones (`Runnable`, `VectorStore`, `BaseRetriever`, chains con LCEL).

**Decisión:** Se conserva la arquitectura hexagonal. LangChain se integra
**como implementación dentro de los adapters existentes** (p. ej.
`adapters/chroma_store.py` pasa a usar `langchain_chroma.Chroma` por dentro,
en vez de el cliente crudo de ChromaDB). Los `ports/` definen el contrato;
LangChain resuelve el contrato.

**Alternativas consideradas:**
- *LangChain idiomático sin capa propia*: usar los componentes de LangChain
  directamente en los agentes, sin ports/adapters intermedios. Es más
  "estándar de mercado" y lo que un corrector esperaría ver de forma directa,
  pero tira la arquitectura hexagonal que ya tenías y con la que la venías
  demostrando en M2.

**Consecuencias:** hay doble capa de abstracción (ports propios sobre
abstracciones de LangChain). Es más código que la opción idiomática pura,
pero mantiene la propiedad de "cambiar de vector store o LLM sin tocar
servicios" que ya tenía M2, y deja claro en el código *dónde* entra LangChain
sin que se disuelva en todo el proyecto.

---

## ADR-003: Alcance — migrar moderación y API FastAPI en paralelo

**Contexto:** M2 tiene una capa de moderación (3 filtros: datos sensibles,
lenguaje abusivo, prompt injection) y una API FastAPI con rutas de
ingest/query/evaluate. M3 no las pide explícitamente; solo pide el sistema
multi-agente con LangChain y Langfuse.

**Decisión:** Se migran ambas en paralelo a cada fase del roadmap, en lugar
de dejarlas para el final o descartarlas.

**Alternativas consideradas:**
- *Moderación sí, API después*: integrar solo el filtro de moderación ahora
  (barato, alto valor) y dejar FastAPI como extra opcional si sobra tiempo.
- *Ninguna de las dos*: enfocarse 100% en lo obligatorio de M3, dejando
  moderación y API intactas y desconectadas del nuevo flujo.

**Consecuencias:** más superficie de trabajo por fase (cada cambio en el
core RAG debe reflejarse también en moderación y en las rutas de API), pero
el resultado final es un sistema end-to-end coherente: API HTTP real,
protegida por moderación, sirviendo al sistema multi-agente completo.

---
