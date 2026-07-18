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

## ADR-004: LangChain 1.x — LCEL en vez de chains clásicas o `create_agent`

**Contexto:** Al instalar dependencias, `langchain` resolvió a la versión
**1.3**, no a la serie 0.3.x que es la más común en tutoriales y en el
conocimiento previo del asistente. Al inspeccionar el paquete instalado
(en vez de asumir por memoria) se confirmó que LangChain 1.0 reestructuró
la librería:

- El paquete `langchain` de primer nivel ahora expone principalmente
  `langchain.agents.create_agent` — un constructor de agentes autónomos
  (el LLM decide qué tool usar en un loop).
- Las chains clásicas (`RetrievalQA`, `create_retrieval_chain`, etc.) se
  movieron a un paquete separado, `langchain-classic`, mantenido por
  compatibilidad.
- Las primitivas LCEL (`Runnable`, `ChatPromptTemplate`, `StrOutputParser`,
  el operador `|` para componer) siguen viviendo en `langchain-core` y no
  cambiaron — son la base estable de todo lo demás.

**Decisión:** El core RAG (`services/pipeline.py`) se implementó con **LCEL
puro**: `ChatPromptTemplate | chat_model | StrOutputParser()`. El
orquestador (ADR pendiente, fase de routing) también se construirá con LCEL
explícito (clasificar → `RunnableBranch`/`RunnableLambda` según intención),
no con `create_agent`.

**Alternativas consideradas:**
- *`langchain-classic` (`create_retrieval_chain` + `RetrievalQA`)*: es la
  API "clásica" que más aparece en documentación y cursos. Se descartó
  porque es explícitamente la ruta de compatibilidad hacia atrás en 1.x, no
  la recomendada para código nuevo, y agrega una dependencia extra sin
  ganar nada que LCEL no dé ya de forma más simple y explícita.
- *`langchain.agents.create_agent` (agente autónomo con tools)*: cada
  agente de dominio se expondría como una `tool`, y el orquestador sería un
  único agente que decide con tool-calling a cuál delegar. Es el patrón
  "más nuevo" y más autónomo, pero la consigna de M3 describe
  explícitamente "clasifique la intención... enrutamiento condicional" —
  es decir, un paso de clasificación explícito seguido de un branch
  determinístico, no una decisión libre del LLM vía tool-calling. LCEL con
  branching explícito matchea esa descripción de forma más directa, es más
  fácil de trazar en Langfuse (cada paso es un span nombrado, no una
  decisión opaca dentro del loop del agente), y es más fácil de testear
  (test_queries.json puede verificar el paso de clasificación de forma
  aislada).

**Consecuencias:** el proyecto no usa la primitiva "más nueva y destacada"
de LangChain 1.x (`create_agent`), lo cual vale la pena aclarar en el README
como decisión consciente, no como desconocimiento de la API. Si en el futuro
se quisiera un orquestador más autónomo (que además decida *combinar*
información de varios dominios en una sola respuesta), `create_agent` con
los 3 RAG agents como tools sería el camino natural de evolución.

---

## ADR-005: ChromaDB como vector store primario (FAISS queda como adapter alternativo sin migrar)

**Contexto:** El sistema necesita 3 colecciones de vectores independientes
(HR/Tech/Finance). `ports/vector_store.py` ya definía un Protocol
(`add`/`query`/`count`) con dos adapters intercambiables desde M2:
`ChromaStore` y `FAISSStore`.

**Decisión:** `ChromaStore` se reescribió para envolver
`langchain_chroma.Chroma` (ver ADR-002) y es el vector store usado por los
3 agentes, cada uno con su propio `collection_name` dentro de un mismo
`persist_directory` — ChromaDB soporta múltiples colecciones nombradas en
un solo cliente persistente, que es exactamente lo que hace falta acá.
`FAISSStore` (FAISS + `IndexHNSWFlat` explícito, documentado en el README
de M2) **no se migró a LangChain** y queda tal cual estaba: una
implementación alternativa del mismo port, no usada por el flujo
multi-agente de M3.

**Alternativas consideradas:**
- *Migrar también FAISS a `langchain_community.vectorstores.FAISS`*: dado
  que FAISS no tiene concepto nativo de colecciones, cada dominio
  necesitaría su propio índice `.faiss` serializado por separado
  (`save_local`/`load_local`), sin ninguna ventaja sobre Chroma para este
  caso de uso. Se descartó por ser trabajo extra sin beneficio: el punto de
  tener ports/adapters (ADR-002) es poder no tocar el adapter que no se usa.

**Consecuencias:** el repo mantiene la comparación educativa Chroma vs
FAISS documentada en el README de M2 (HNSW, IVF, PQ, Flat), pero hay que
aclarar en el README de M3 que solo el path de Chroma está integrado con
LangChain y activo en el sistema multi-agente; FAISS queda como referencia
de la arquitectura swappable, no como opción funcional del flujo actual.

---

## ADR-006: Clasificación de intención con structured output (no texto libre, no embeddings, no keywords)

**Contexto:** El orquestador necesita clasificar cada consulta en uno de 3
dominios (o "fuera de alcance") antes de rutear al agente correcto.

**Decisión:** Se usa `llm.with_structured_output(IntentClassification)`
con un schema Pydantic (`intent: Literal["hr","tech","finance","unknown"]`
+ `reasoning: str`), compuesto en una chain LCEL
(`prompt | structured_llm`).

**Alternativas consideradas:**
- *LLM con texto libre + parseo*: pedirle al LLM que responda "HR" o
  "Finanzas" como string y parsear la respuesta. Se descartó porque el LLM
  puede variar el formato (mayúsculas, sinónimos, texto extra) y no hay
  garantía de que el valor esté dentro del enum esperado — cada variación
  requeriría lógica de parseo defensiva ad-hoc.
- *Similitud de embeddings*: embeber la pregunta y compararla contra
  embeddings de ejemplos por dominio (o contra los propios chunks de cada
  colección, quedándose con la de mayor similitud máxima). Es más barato
  (sin llamada a LLM) pero le cuesta más a preguntas ambiguas o compuestas
  ("¿cuál es el límite de gasto de mi tarjeta de la empresa para
  capacitación?" toca Finance y HR a la vez), y no da una señal de "fuera
  de alcance" tan limpia como un label explícito.
- *Keywords/regex*: más simple y predecible, pero no generaliza a
  parafraseos y requiere mantenimiento manual de listas de palabras por
  dominio, igual que la Capa 3 de moderación — aceptable ahí porque es una
  lista cerrada de riesgos, pero no para clasificar lenguaje natural
  abierto.

**Consecuencias:** agrega la dependencia de que el modelo soporte tool
calling / structured output (los modelos de OpenAI usados sí lo soportan).
El campo `reasoning` no se usa para tomar la decisión de ruteo, pero se
guarda y se traza en Langfuse — es precisamente lo que permite depurar
misclassifications sin adivinar por qué el LLM eligió un dominio.

---

## ADR-007: Moderación como gate único del orquestador (se saca de RAGPipeline)

**Contexto:** El ADR-003 ya estableció que la moderación se integra "antes
del orquestador". Con el orquestador como único punto de entrada del
sistema (los agentes de dominio no se llaman directamente), mantener el
chequeo de moderación *también* dentro de cada `RAGPipeline` generaría dos
entradas de auditoría por pregunta (una en el orquestador, otra en el
agente ruteado) para el mismo texto evaluado por el mismo evaluador
determinístico — pura duplicación sin valor.

**Decisión:** El chequeo de moderación se movió al `Orchestrator.handle()`,
como el primer paso antes de clasificar. `RAGPipeline` ya no depende de
`ModerationService` ni de `ContentBlockedError`.

**Alternativas consideradas:**
- *Dejar la moderación en RAGPipeline y agregar otra en el orquestador*:
  "defensa en profundidad", pero con doble log por pregunta y un chequeo
  redundante (mismo evaluador, mismo texto, mismo resultado determinístico)
  que no agrega seguridad real, solo ruido en el log de auditoría.

**Consecuencias:** cualquier código que instancie un `DomainAgent` o
`RAGPipeline` fuera del orquestador (por ejemplo, en un test unitario o un
script puntual) queda sin protección de moderación — es una decisión
consciente: en este sistema el orquestador es la única puerta de entrada.
La API FastAPI (próxima fase) debe rutear a través del orquestador, no
llamar a un agente de dominio directamente, para no perder esta protección.

---
