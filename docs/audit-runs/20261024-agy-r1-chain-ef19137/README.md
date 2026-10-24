# Auditoría independiente de Antigravity: correcciones B y arranque de host (2026-10-24 08:58 UTC)

**Veredicto: APPROVE-TECHNICAL, sin hallazgos A.** Hay 4 hallazgos B, todos fallan en cerrado, y 2 C.

| Campo | Valor |
|---|---|
| Auditor | Antigravity CLI 1.4.4 (sha256 `337dcde6…`), uid `aao-auditor-alt` (1006), resolución delegada en #25 |
| Rango | `26f7df8a7b3942fc25258965b161a419b3dd982f..ef1913799fa5c04534f7f2204ff9d5f7de4eb1d4` (`src tests scripts deploy docs/procedures`; commits `67b79b6` = #57 y `ef19137` = #58) |
| Prompt | plantilla `docs/audit-prompts/r1-chain.md`, sha256 `3ddba537…` (fijada en el ejecutor); prompt final `e0bff6ab…` |
| Informe | [`report.md`](report.md), sha256 `6af12e23f20a7b0df84d658b488a612750ced0c5ecae554a8307be421b1f9667` |
| Atestación | [`attestation.json`](attestation.json), sha256 `1025b81d4d1f608a43c664305fa74923c19206dcebbf1490992680b602079abe` |

**Procedencia.** El CEO ejecutó `/opt/aao-audit/run_agy_audit.sh` como `aao-auditor-alt`, con el ejecutor y la plantilla instalados desde `ef19137`. El PM copió `report.md` y `attestation.json` sin modificarlos; los hashes de esta carpeta coinciden con los que imprimió el ejecutor.

**Independencia.** Los autores (Codex en `src/` y `tests/`; Claude en `scripts/`, `deploy/` y `docs/procedures/`) quedan recusados. El mismo rol auditor emitió el dictamen anterior (`7d025f2`) que motivó estas correcciones, pero no participó en ellas.

**Limitaciones.** No se ejecutaron pruebas: `pytest` no está permitido en el entorno del auditor. El análisis es estático y no cubre el host instalado ni la configuración en vivo de GitHub.

## Hallazgos B pendientes

- **B-1:** ni `host_bootstrap.sh` ni `TRUST_ROOT_HOST_INSTALL.md` habilitan `aao-supervisor-attribution.timer`. Sin ese timer, la atribución no se refresca y las auditorías quedan en `provisional`. Mientras no se corrija, el CEO lo habilita a mano tras instalar la raíz de confianza.
- **B-2:** la fase `app-keys` instala `<app>.pem`, pero no crea `~/.config/aao/<app>.json` con el `app_id`, que `GitHubAppClient` necesita. Afecta a un host nuevo.
- **B-3:** la atribución solo consulta el repo destino. Si el implementador empuja a su fork y `aao-pm` abre la PR, el commit se atribuye a `aao-pm[bot]`. En R1 falla en cerrado; antes de R2 hay que corregirlo.
- **B-4:** es el B-5 residual de la auditoría anterior. Ante un incidente posterior al push, el integrador queda congelado pero no puede escribir en el ledger del auditor.

**C-1:** `git ls-remote` sin token (solo afecta a repos privados). **C-2:** quedan `aao-auditor@.service` y `/var/lib/aao-auditor/inbox` de la vía manual.

Ninguno bloquea instalar la raíz de confianza en `ef19137`. B-1 y B-2 se corrigen antes del próximo traslado de host, y B-3 antes de R2.
