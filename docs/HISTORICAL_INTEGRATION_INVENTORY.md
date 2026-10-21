# Inventario de integraciones históricas sin dictamen válido

**Estado:** inventario preliminar de riesgo, previo al arranque (plan §6.1). **No convalida ninguna integración.**
**Fecha de corte:** 2026-10-21 · `main` `ddd520f`
**Fuente:** `gh pr view <n> --json mergeCommit,mergedBy,reviews,commits,files` ejecutado el 2026-10-21.

Las siete PR las fusionó a mano la cuenta propietaria (`alessbarb`), con **0 revisiones en GitHub** y sin un dictamen de auditoría independiente válido según GOV-REV-001. La clase de riesgo indicada es preliminar, según el modelo R0–R3 propuesto: es la clase que tendría el cambio hoy.

| PR | Merge SHA | Head SHA | Fusionada (UTC) | Commits | Rutas sensibles | Clase prelim. | Evaluación |
|---|---|---|---|---|---|---|---|
| #10 capability registry | `c08a64044c92ba501ad402f163814fbe2078c3f7` | `48a05f55a6b4` | 2026-10-20 06:05 | 6 | `.github/workflows/ci.yml`, migración `010_capability_registry.sql`, `work_management_api.py` | R2 (CI) | normal; revisar el cambio en CI |
| #11 checks vía cola | `8a4fca1cff98aa4c8b9a5cf3f46e9610a3b45b18` | `0ca311b7a787` | 2026-10-20 06:05 | 30 | `ci.yml`, migraciones 011 (reviews ligadas a SHA y veto) y 012, `review.py`, `pr_conformity.py`, `local_candidate_controller.py`, `sandboxed_repository_checks.py`, `scripts/rotate_local_ceo_token.py`, `scripts/bootstrap_self_dev_agent.py` | R2 (gate, veto, credenciales, sandbox) | **reforzada**; hallazgo abierto P11-4 (sin protección contra `TRUNCATE`) |
| #14 emisor de auditoría | `681f40c2d30037a8fff7eccedc66d78a3f0f159c` | `8e342c72d2d8` | 2026-10-20 06:07 | 7 | `src/aao/independent_audit.py` | R2/R3 (auditor, raíz de confianza) | **reforzada**; autor Claude, que está recusado |
| #15 Control Center UI | `83230f3c94ac66e5d999b8e825d442c567b6d5db` | `2b36c98d6285` | 2026-10-20 06:07 | 36 | ninguna en el backend | R1 | normal; hallazgos P1/P2 abiertos |
| #19 auditoría de manifiestos | `3a84ff501cd168420dd4fe6d55ea2f3ccae662e9` | `123d3ecd2305` | 2026-10-20 06:12 | 3 | `independent_audit.py`, `manifest_audit.py` | R2/R3 (auditor) | **reforzada**; autor Claude, que está recusado |
| #20 separación de HTML/CSS/JS | `5d8cc895783a2023016a6bfb108147dd8c60ce05` | `7d21b4afe927` | 2026-10-20 06:16 | 1 | `sqlite_api.py`, `work_management_api.py` (sirven estáticos) | R1 | normal |
| #21 excepción Clase A | `ddd520f58613564dbc6460949e2dea8e78b75517` | `78a76ceba4f3` | 2026-10-21 07:46 | 2 | `docs/decisions/` | R3 (decisión CEO) | contenido de autoridad CEO; integración sin vía válida |

## Riesgos pendientes

- **#14 y #19** forman la base del auditor. No pueden incluirse en `trusted_auditor_revisions` sin la revisión cruzada de arranque (Codex, como `aao-auditor-alt`). Hoy `trusted_auditor_revisions` está vacío (`docs/audit-runs/20261019-provisional/policy.json`).
- **#11** introduce el gate, el veto y la rotación de credenciales locales. Debe pasar la auditoría retroactiva antes de que el integrador dependa de él.
- **#10 y #11** modifican CI. Hay que revisar que ninguna comprobación quedara debilitada.
- Hallazgos abiertos que se trasladan al backlog: P11-4, P1/P2 de #15 y C-1 a C-6.

## Siguiente

La auditoría retroactiva completa corresponde a F6. Las PR marcadas como **reforzada** se auditan en F3b, antes del arranque.
