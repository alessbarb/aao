# Coordinación y Solicitud de Contratos API para AAO Control Center

**Destinatarios:** Agentes de Core Backend y Gobernanza (Codex / Claude)
**Emisor:** Responsable de AAO Control Center (Frontend & Pruebas)
**Fecha:** 19 de Octubre de 2026
**Rama:** `feat/control-center-daily-ui`
**Base:** `feat/capability-backed-repository-checks`

---

## 1. Estado de Reconciliación de Endpoints Existentes

Tras auditar las ramas activas del repositorio (`feat/capability-backed-repository-checks`, `fix/control-center-auth-session`, `feat/explicit-work-assignment`), se ha verificado el estado real de los contratos para **evitar duplicidades**:

| Endpoint | Estado Actual | Ubicación / Rama | Acción Coordinada Solicitada |
|---|---|---|---|
| `GET /v1/projects` | **Existe** | Base activa | Ninguna. Consumido con autenticación `X-Agent-Token`. |
| `GET /v1/principals/me` | **Existe** | Base activa | Ninguna. Valida identidad `AGENT` activa sin revelar secretos. |
| `GET /v1/projects/{id}/board` | **Existe** | Base activa | Ninguna. Retorna tareas con criterios, evidencias, ejecuciones, revisiones y propuestas. |
| `GET /v1/projects/{id}/capabilities` | **Existe** | Base activa | Ninguna. Consumido con filtro por tipo (`agent_skill`, `agent`, etc.). |
| `GET /v1/projects/{id}/capability-evaluations` | **Existe** | Base activa | Ninguna. Muestra comparativa multicriterio sin otorgar ejecución. |
| `GET /v1/work/{id}/patch-proposals/{p_id}` | **Existe** | Base activa | Ninguna. Inspección de parche para auditor/proponente. |
| `GET /v1/projects/{id}/activity` | **Pre-existente en rama paralela** | `fix/control-center-auth-session` | **Reconciliar a la base activa**: Promover o rebasear este endpoint para habilitar journal de eventos a lectores autorizados. |
| `GET /v1/projects/{id}/assignable-agents` | **Pre-existente en rama paralela** | `feat/explicit-work-assignment` | **Reconciliar a la base activa**: Habilitar listado de agentes asignables con grant `execution.claim`. |
| `GET /v1/projects/{id}/patch-proposals` | **Pendiente / Opcional** | Propuesta nueva | Opcional para optimización de paginación. Actualmente el Control Center consume `patch_proposals` directamente de `/board`. |

---

## 2. Coordinación entre Dominios (Frontend <-> Codex / Claude)

1. **Sin invasión de dominios:** El frontend trabaja exclusivamente en `frontend/` y `tests/test_control_center_ui.py`. No alteramos `src/aao/` ni aplicamos migraciones de base de datos.
2. **Tolerancia a fallos y degradación elegante:** Si endpoints como `/activity` o `/assignable-agents` devuelven 404 (porque aún no están fusionados en la base), la interfaz no falla ni se bloquea: muestra de forma honesta que la funcionalidad no está disponible en este entorno o que no hay registros persistidos.
3. **No simulación:** No se generan registros ficticios ni se simulan aprobaciones.

---

## 3. Garantías de Gobernanza Verificadas

- **Evaluaciones ≠ Ejecuciones:** Las evaluaciones de capacidades (`capability-evaluations`) se muestran estrictamente con la leyenda `Evaluación no autoriza ejecución.` y `Ejecución autorizada: no`.
- **Dictámenes ≠ Auditoría Independiente:** Todo dictamen (`APPROVE`, `REJECT`, `VETO`) se rotula como registro persistido de auditor local. Se incluye advertencia explícita de que los registros no constituyen una certificación independiente externa.
- **`IN_REVIEW` ≠ Aprobada:** Las tareas en estado `IN_REVIEW` permanecen clasificadas en la columna "Revisión" y jamás son catalogadas como aprobadas o completadas.
