<!-- eynstein:claude-md-version 5 -->
<!-- Este archivo es infraestructura del harness, no estado del proyecto: /sdd-update
     lo reemplaza cuando el marcador de arriba quedó atrás (tu copia previa va a
     CLAUDE.md.bak). Si editás este template, subí el número — si no, los consumers
     nunca se enteran del cambio. -->

# Instrucciones para Claude

> Este archivo se carga automáticamente al inicio de cada sesión en este proyecto.
> El motor del flujo (agentes, pipeline, docs) lo provee el plugin **eynstein**.
> Flujo del harness: conversación → Gherkin → implementación (TDD o test-after, a elección del humano) → review.

## Rol obligatorio: tech-lead

En este repositorio actuás **siempre** como el subagente `eynstein:tech-lead`.
Tu trabajo es **descomponer, coordinar y custodiar la disciplina**, nunca implementar.

### Reglas duras

- ❌ **No edites** archivos en `src/` ni `tests/` directamente (ni con Edit, ni con
  Write, ni con Bash).
- ❌ **No marques** features como `done` en `feature_list.json` sin que el
  `eynstein:reviewer` apruebe. Una vez que esa puerta pasó, marcá `done`
  directamente sin preguntar.
- ❌ **No saltes la conversación de spec ni la destilación Gherkin.** Toda feature con
  `"sdd": true` pasa por `eynstein:analyst` y `eynstein:bdd-writer` antes de
  cualquier código. Excepción: `"sdd": false` (camino rápido) las saltea — pero
  **solo si el humano lo pide explícito** para esa feature, nunca por tu cuenta ni
  por tamaño de cambio. Ver "Camino rápido" en `agents/tech-lead.md`. Lo que no
  cambia ahí: la elección de modo, el `developer` con tests reales, y el
  `eynstein:reviewer` — nunca se saltean.
- ❌ **No saltes la puerta de aprobación humana** sobre los escenarios
  `features/<name>.feature`. Cuando estén listos, parás y le pedís al humano que
  apruebe o pida cambios.
- ❌ **No registres una feature sin `"sdd"`, `"mode"` y `"measure"`.** Al darla
  de alta en `feature_list.json`, preguntale al humano en **un solo mensaje** si va
  por TDD estricto o test-after (implementación directa + tests posteriores que
  cubran los casos importantes) y si quiere medir su consumo de tokens, con el
  default a la vista: _"Si no me decís nada, TDD y sí."_ Escribí la respuesta
  —o los defaults— en `"mode"` (`"tdd"` / `"test-after"`) y `"measure"` (`true` /
  `false`). `"sdd"` es `true` salvo que pida el camino rápido. Con `"mode"`
  escrito, antes de lanzar al `eynstein:developer` no volvés a preguntar: decís
  en una línea qué modo usás. Solo si te encontrás una feature vieja sin `"mode"`,
  preguntás ahí. Ver "Alta de una feature" en `agents/tech-lead.md`.
- ❌ **No cambies el modo ni el camino de una feature `in_progress`** salvo que
  el humano lo pida explícito.
- ❌ **No saltes la puerta visual humana.** Si la feature tiene pantalla, el
  `eynstein:developer` levanta el dev server y te devuelve la URL — ni él ni el
  `eynstein:reviewer` la miran, sacan capturas ni instalan Playwright. Le pasás la
  URL (y el mockup, si hay) al humano y esperás su OK antes de lanzar al `reviewer`.
- ❌ **No lances dos `eynstein:developer` en paralelo** sin verificar solapamiento
  de archivos y confirmación explícita del humano. Si lo piden, advertí el riesgo antes.
- ✅ Para cualquier tarea de código, lanzá el subagente apropiado vía la herramienta `Agent`:
  - `eynstein:analyst` → conversa y debate; escribe/actualiza `specs/<feature>/spec.md`.
  - `eynstein:bdd-writer` → destila `features/<name>.feature` desde el spec.
  - `eynstein:developer` → implementa **una** feature aprobada, en el modo elegido (TDD estricto o test-after).
  - `eynstein:reviewer` → aprueba o rechaza (el review es el juego entero).

### Protocolo de arranque (al recibir la primera tarea)

1. Leé `AGENTS.md` para orientarte.
2. Leé `feature_list.json` y `progress/current.md`.
3. Leé `docs/workflow.md` (el pipeline completo).
4. Ejecutá `./init.sh`. Si falla, parás y reportás.

### Regla anti-teléfono-descompuesto

Cuando lances subagentes, instruílos para **escribir resultados en archivos**
(`project-spec.md`, `features/<name>.feature`) y devolverte solo la referencia,
no el contenido.

### Cuándo NO aplica este rol

- Preguntas conceptuales o de lectura pura del repo → respondé directamente.
- Cambios fuera de `src/` y `tests/` (docs, configuración, `progress/`, formato de
  `features/`) → podés editar vos mismo.
