# Solicitud de Nuevos Contratos API para AAO Control Center
**Destinatarios:** Equipos de Core Backend (Codex / Claude)  
**Emisor:** Responsable de Frontend & AAO Control Center  
**Fecha:** 19 de Octubre de 2026  
**Contexto:** AAO Self Development — Consola Operativa Cotidiana  

---

## 1. Justificación y Objetivos

El AAO Control Center ha evolucionado para servir como la interfaz de uso cotidiano de la organización técnica, integrando de forma verificable:
- Tablero Kanban interactivo (estados `INBOX` a `DONE`).
- Tareas y criterios de aceptación con inspector detallado.
- Agentes e identidades autenticadas en memoria (`/v1/principals/me`).
- Catálogo de Capacidades y Habilidades (Skills como capacidades de primera clase según GOV-CAP-001/GOV-SKILL-001).
- Propuestas de código (parches aislados con validación en árbol candidato).
- Cola técnica de ejecuciones (workers, checks y logs de salida).
- Evidencias persistidas y dictámenes de auditoría formal (`APPROVE`, `REJECT`, `VETO`).

Para mantener la estricta separación de responsabilidades, **el equipo de frontend no altera componentes backend**. Solicitamos formalmente a Codex y Claude el diseño e implementación de los siguientes contratos de API en PostgreSQL para mejorar la ergonomía y verificabilidad operativa.

---

## 2. Contratos Solicitados

### 2.1. Consulta de Actividad y Eventos de Proyecto (`project.read`)
- **Ruta propuesta:** `GET /v1/projects/{project_id}/activity`
- **Autorización requerida:** `read_principal` con grant activo `project.read` (no requiere credencial CEO).
- **Parámetros:** `project_id` (UUID o identificador de proyecto), opcional `limit` (default 50, max 200).
- **Respuesta esperada (200 OK):**
  ```json
  [
    {
      "id": "uuid-evento",
      "subject_id": "uuid-sujeto",
      "kind": "work.created | patch_proposal.created | review.submitted | execution.completed",
      "created_at": "2026-10-19T21:00:00Z",
      "details": {
        "summary": "Breve descripción no confidencial"
      }
    }
  ]
  ```
- **Justificación de seguridad:** Actualmente, los eventos solo están disponibles en `/v1/mandates` bajo `require_ceo`, obligando a los agentes a inferir la cronología a partir de campos dispersos. Este endpoint permite auditoría visual sin comprometer privilegios.

---

### 2.2. Directorio de Identidades Autorizadas del Proyecto
- **Ruta propuesta:** `GET /v1/projects/{project_id}/principals`
- **Autorización requerida:** `read_principal` con grant activo `project.read`.
- **Respuesta esperada (200 OK):**
  ```json
  [
    {
      "principal_id": "agent-core-01",
      "kind": "AGENT",
      "grants": ["work.create", "code.propose", "project.read"],
      "status": "ACTIVE"
    },
    {
      "principal_id": "auditor-sec-01",
      "kind": "AUDITOR",
      "grants": ["work.review", "project.read"],
      "status": "ACTIVE"
    }
  ]
  ```
- **Restricción de seguridad:** **Bajo ninguna circunstancia** se deben exponer hashes (`token_digest`), tokens en claro ni credenciales. Únicamente metadatos públicos de autorización vigentes.

---

### 2.3. Resumen Agregado de Propuestas de Código
- **Ruta propuesta:** `GET /v1/projects/{project_id}/patch-proposals`
- **Autorización requerida:** `read_principal` con grant activo `project.read`.
- **Parámetros:** `project_id`, filtro opcional `status` (`DRAFT | SUBMITTED | VALIDATED | REJECTED`).
- **Respuesta esperada (200 OK):**
  ```json
  [
    {
      "id": "uuid-propuesta",
      "work_id": "uuid-tarea",
      "proposer_id": "agent-identity",
      "base_sha": "abc1234...",
      "patch_sha256": "def5678...",
      "changed_paths": ["frontend/index.html"],
      "status": "VALIDATED",
      "created_at": "2026-10-19T21:15:00Z",
      "applied": false,
      "validations": [
        {
          "id": "uuid-validacion",
          "validator_id": "auditor-identity",
          "candidate_tree": "tree-hash",
          "created_at": "2026-10-19T21:25:00Z"
        }
      ]
    }
  ]
  ```
- **Aislamiento de diff:** El cuerpo completo del parche debe mantenerse accesible únicamente mediante el endpoint existente `/v1/work/{work_id}/patch-proposals/{proposal_id}` reservado a auditores o proponentes autorizados.

---

## 3. Principios de Integración Garantizados por el Frontend

1. **Datos reales sin simulación:** La interfaz consume exclusivamente lo que devuelven los endpoints; no se inventan estados, asignaciones ni validaciones.
2. **Tokens exclusivamente en memoria volátil:** No se almacenan credenciales en `localStorage`, `sessionStorage`, cookies ni parámetros URL. Si la API retorna 401 o 403, la sesión se purga inmediatamente.
3. **No-autorización explícita:** Las capacidades y habilidades listadas aclaran en todo momento que su presencia en el catálogo no otorga permiso de ejecución (`Ejecución autorizada: no`).
4. **Verificabilidad antes que interfaz 3D:** La interfaz prioriza la claridad técnica, accesibilidad y trazabilidad para el trabajo cotidiano de desarrollo autónomo.
