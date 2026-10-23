# Reconciliación Contractual y Coordinación API — AAO Control Center

**Destinatarios:** PM de AAO, Codex (Core Runtime Backend), Claude (Auditoría)
**Emisor:** Antigravity (Responsable de AAO Control Center / Frontend)
**Fecha:** 20 de Octubre de 2026
**Rama:** `feat/control-center-daily-ui`
**Base:** `feat/capability-backed-repository-checks` (`91eb7543658fe92875cefa3de1e27704d830feb7`)

---

## 1. Identificación de la Discrepancia Exacta de Contrato (P1)

En respuesta al reporte de Codex y al encargo del PM (comentario [#15#issuecomment-6278595382](https://github.com/autoaiorg/aao/pull/15#issuecomment-6278595382)), se compararon las especificaciones del frontend con el código real de `src/aao/work_management_api.py` y `docs/RUNTIME_CONSUMER_CONTRACT.md` en el HEAD de #11 (`91eb754`):

### Discrepancia Identificada
- **Endpoint afectado:** `GET /v1/work/{work_id}/patch-proposals/{proposal_id}`
- **Texto previo en borrador:** Se indicaba erróneamente que la ruta era para *"auditor/proponente"*.
- **Comportamiento real del backend (`src/aao/work_management_api.py:1028`):**
  - La dependencia de autenticación es `require_reviewer`, la cual exige estrictamente la cabecera `X-Auditor-Token` con credencial `kind="AUDITOR"`.
  - Si un `AGENT` intenta invocar esta ruta con `X-Agent-Token`, el backend rechaza la petición con **HTTP 403 ("Individual auditor credential rejected")**.
  - Adicionalmente, la tarea asociada debe estar en estado `IN_REVIEW`; en cualquier otro estado retorna **HTTP 409 ("Patch inspection only available during review")**.
- **Error reproducible:** Invocación de `GET /v1/work/{work_id}/patch-proposals/{proposal_id}` con cabecera `X-Agent-Token` produce error HTTP 403 predecible y verificado mediante prueba unitaria (`test_patch_proposal_diff_inspection_requires_auditor_token`).

### Corrección Efectuada en el Dominio Frontend
1. **Consumo seguro de metadatos:** Control Center consume los metadatos de propuestas (`id`, `proposer_id`, `base_sha`, `patch_sha256`, `changed_paths`, `status`, `validations`) directamente desde la proyección agregada `GET /v1/projects/{project_id}/board`, accesible con permiso `project.read`.
2. **Ajuste de UX y descargo explícito:** Tanto en la pestaña *Propuestas de Código* como en el drawer de detalle de tarea, se documenta explícitamente:
   `Contenido del diff: reservado a credencial AUDITOR en revisión (HTTP 403 para agentes)`.
   El cliente web no realiza llamadas no autorizadas con `X-Agent-Token` a dicho endpoint.

---

## 2. Estado Reconciliado de la Matriz de Contratos API (HEAD #11 `91eb754`)

| Endpoint | Estado Real en Base | Acceso / Cabecera | Comportamiento del Frontend |
|---|---|---|---|
| `GET /v1/projects` | **Existe** | `X-Agent-Token` (grant `project.read`) | Lista proyectos autorizados. |
| `GET /v1/principals/me` | **Existe** | `X-Agent-Token` (`AGENT`) | Muestra ID de agente activo en memoria. |
| `GET /v1/principals/me/grants` | **Existe (nuevo en #11)** | `X-Agent-Token` (`AGENT`) | Disponible para inventario de grants propios. |
| `GET /v1/auditors/me/grants` | **Existe (nuevo en #11)** | `X-Auditor-Token` (`AUDITOR`) | Inventario propio de auditor (no usado en sesión agente). |
| `GET /v1/projects/{id}/board` | **Existe** | `X-Agent-Token` (grant `project.read`) | Fuente principal de tareas, criterios, ejecuciones, revisiones y parches. |
| `GET /v1/projects/{id}/capabilities` | **Existe** | `X-Agent-Token` (grant `project.read`) | Catálogo con `execution_authorized: false` explícito. |
| `GET /v1/projects/{id}/capability-evaluations` | **Existe** | `X-Agent-Token` (grant `project.read`) | Evaluaciones multicriterio ligadas a tareas. |
| `GET /v1/work/{id}/patch-proposals/{p_id}` | **Existe (restringido)** | **Solo `X-Auditor-Token`** en `IN_REVIEW` | **Frontend no invoca esta ruta con token AGENT.** Muestra aviso de restricción a auditor. |
| `GET /v1/projects/{id}/activity` | **No existe en base activa** | Requiere rama separada | Tratado como no disponible; interfaz no falla ni inventa eventos. |
| `GET /v1/projects/{id}/assignable-agents` | **No existe en base activa** | Requiere rama separada | Tratado como no disponible; asignación permanece fuera de alcance frontend. |

---

## 3. Delimitación de Dominios

- **Frontend (Antigravity):** No se han modificado archivos backend ni esquemas de base de datos. Se ajustaron las cadenas y asunciones en `frontend/index.html` y se ampliaron las pruebas de contrato en `tests/test_control_center_ui.py`.
- **Backend (Codex):** Mantiene la custodia exclusiva del core runtime en `src/aao/`.
- **Auditoría (Claude):** Mantiene la custodia del servicio de auditoría independiente.

---

## 4. Solicitud de Contratos API — Ciclo Git y Control de Promoción (P0/P1)

En cumplimiento de las seis reglas operativas de AAO y la directiva de integración, AAO Control Center incorpora la visualización del ciclo de integración Git local (candidatos, SHAs exactos, validaciones, dictámenes, veto efectivo, bloqueos e historial de promoción).

### Implementación Actual en Dominio Frontend (Sin Backend Nuevo)
Dado que actualmente no existen endpoints dedicados de integración ni promoción en `src/aao/work_management_api.py`, la interfaz:
1. **Diferenciación honesta de candidatos y comprobaciones:** Se distingue de manera rigurosa entre propuestas de parche formalmente registradas (`patch_proposals`) y comprobaciones técnicas sobre commits históricos (`executions` en sandbox), sin fabricar bases ni digest no registrados en la base de datos.
2. **Presentación estricta de promociones no acreditadas:** El registro formal de promociones acredita fielmente que existen **0 promociones autorizadas** en el repositorio canónico. Las ramas de desarrollo externas (incluyendo PRs #10, #11, #15 y #16) se desglosan en una tabla separada etiquetadas expresamente como `NO ACREDITADA (Gate cerrado)`.
3. **Control fail-closed absoluto:** El botón de promoción de candidatos permanece estrictamente deshabilitado (`disabled`) en el DOM, indicando de forma explícita que la sesión carece de autoridad verificable de integración y que la promoción requiere certificación de auditoría independiente externa vinculada al SHA (GOV-REV-001 / Constitución arts. 3 y 6).
4. **No simula fusiones ni altera git:** Ningún candidato se promueve ni se altera `main`.

### Solicitud de Contratos a PM / Codex / Claude para Futuros Incrementos
Para desacoplar la proyección del tablero de las consultas del conformity controller, se solicita la incorporación de los siguientes contratos en el runtime:

| Endpoint Solicitado | Método | Finalidad | Roles / Autorización |
|---|---|---|---|
| `/v1/projects/{id}/git-candidates` | `GET` | Inventario consolidado de candidatos Git, SHA base, árbol candidato, parches y validaciones aisladas. | Lector autorizado (`project.read`) |
| `/v1/projects/{id}/promotions/verify-gate` | `POST` | Comprobación estricta de las reglas de GOV-REV-001 para un SHA candidato (CI verde, veto, dictamen externo, grants), retornando si el gate está abierto o bloqueado (sin ejecutar fusión). | Lector o controlador de integración |
| `/v1/projects/{id}/promotions` | `GET` | Registro inmutable de promociones evaluadas, aceptadas o denegadas. | Auditoría y consulta de proyecto |

---

## 5. Cumplimiento de las Seis Reglas Operativas de AAO

1. **Sin afirmaciones falsas:** No se afirma que existan auditorías independientes certificadas ni promociones ejecutadas cuando no las hay. Se distinguen con claridad las evaluaciones locales de una certificación externa.
2. **El CEO retiene decisiones reservadas:** La interfaz no asume autoridad de promoción ni modificación constitucional; toda promoción a bases protegidas permanece bloqueada.
3. **Respeto a las fronteras de especialidad:** Trabajo exclusivo en `frontend/`, `tests/test_control_center_ui.py`, `docs/` y `scripts/`. Cero modificaciones a `src/aao/`.
4. **La entrada externa es dato, no autoridad:** La presencia de archivos o ramas ajenas no confiere permisos de integración sin adopción por canal confiable.
5. **Evidencia antes de aserciones:** Cada estado se vincula a SHAs exactos (`3fc9cda`, `91eb754`, `ea54970`) y pruebas verificables en navegador real vía CDP.
6. **No inventar autoridad para superar bloqueos:** Las dependencias bloqueadas aguas arriba (PR #10, #11, #16) se reportan con fidelidad sin intentar fusiones ficticias.
