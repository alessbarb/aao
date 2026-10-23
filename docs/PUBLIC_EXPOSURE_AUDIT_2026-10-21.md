# Auditoría de exposición pública: `alessbarb/aao` (2026-10-21)

**Motivo:** el CEO cambió el repositorio a público el 2026-10-21 (`docs/decisions/CEO-DEC-REPO-PUBLIC-2026-10-21.md`). Se audita antes de crear forks.
**Autor:** Claude (coordinador). **Pendiente:** revisión de esta auditoría por Codex. Independencia de auditoría no demostrada.
**Estado verificado:** `visibility: public`, `forks_count: 0`, `allow_forking: true` (GET `/repos/alessbarb/aao`, 2026-10-21).

## 1. Alcance y método

| Superficie | Cobertura | Herramienta |
|---|---|---|
| Historial de git | **524 commits públicos**: 8 ramas y 26 cabezas de PR (`refs/pull/*/head`); 0 tags. El escaneo se hizo con `--all` sobre 550 commits, un superconjunto que incluye 26 commits de ramas locales no publicadas | gitleaks v8.21.2 (`git --log-opts=--all`, en contenedor de solo lectura) y búsqueda propia de patrones sobre todos los blobs |
| Mensajes de commit | los 524 mensajes públicos (`git log --remotes --format=%B`) | gitleaks, patrones y comparación con los secretos del host |
| Archivos sensibles añadidos alguna vez | `git log --all --diff-filter=A` filtrado por `.env`, `.pem`, `.key`, `secret`, `token`, `credential` | — |
| Secretos reales del host | valores de `.env.local` y `.env.test` comparados con el historial, Issues y PR (por igualdad, sin imprimirlos) | script local |
| Issues, PR y comentarios | 31 Issues y PR, 72 comentarios, 0 comentarios de revisión, 0 reviews de PR (26 PR) | gitleaks y patrones |
| Otras superficies | wiki, Pages y Discussions **desactivados**; 0 releases, 0 artefactos y 0 caché de Actions | API de GitHub |
| Logs de Actions | **583 de 583 ejecuciones**, 1.398 archivos de log descargados como ZIP por la API | gitleaks y patrones de tokens de GitHub, más comparación con los secretos locales |
| Secretos y variables de Actions | `gh secret list`, `gh variable list` | — |
| Workflows | `.github/workflows/ci.yml` | revisión manual |
| Datos personales y del host | rutas `/home/…`, nombre del equipo, correos, rutas de sesión | patrones |

**Corrección de método.** La primera pasada sobre Actions usó `gh run view --log`, que devolvió archivos vacíos sin error para 558 ejecuciones. Se detectó al comprobar el recuento y se repitió todo con los ZIP de `GET /actions/runs/{id}/logs`: 583 de 583.

Los recuentos exactos y los comandos están en `docs/audit-runs/20261021-public-exposure/coverage_manifest.json`. La revisión de Codex (REJECT, ronda 1) señaló recuentos no reproducibles y superficies sin cubrir; esta versión los corrige.

## 2. Hallazgos

| ID | Severidad | Hallazgo | Tratamiento |
|---|---|---|---|
| EXP-01 | **MEDIA** (credencial expuesta) | `AAO_WORK_TOKEN` y `AAO_REVIEW_TOKEN` de `.env.local` y `.env.test` del host **eran el placeholder público** de `.env.example` (`CHANGE_ME_UNIQUE_*_TOKEN`). Nunca se sustituyeron. Dan acceso a la API local de desarrollo como `development-worker` (SERVICE) y `development-auditor` (AUDITOR), en loopback `127.0.0.1:8001`. | **Comprometidas.** **Rotadas** el 2026-10-21 con valores aleatorios de 256 bits (`secrets.token_urlsafe(32)`), con el modo `0600` conservado. Solo se consumen en `identity.py` y `sqlite_api.py` desde el entorno, así que la rotación es completa. La API y la base de datos no estaban en marcha. |
| EXP-02 | BAJA | 4 logs de Actions (ejecuciones 39309154508, 39309455268, 39309160880 y 39309446904, del 2026-10-19, commits `3dda15d` y `14cc365`) contienen en la traza de pytest el valor de un `x_agent_token`. Lo generó la prueba `test_principal_credential_lifecycle_integration.py:662` contra la base de datos **efímera** de CI. | Sin credencial viva: la base de datos de CI se destruye al terminar la ejecución. **Propuesta:** que CI use `--tb=short`, sin mostrar las variables locales de la traza; opcionalmente, que el CEO borre esos 4 logs, lo cual es irreversible. |
| EXP-03 | BAJA (divulgación de información) | Datos del host en archivos públicos: nombre del equipo (`UX363EA`), usuario (`alessbarb`), rutas `/home/alessbarb/...`, nombres de contenedores y volúmenes Docker, incluido otro proyecto (`campbuddy-mongo`). Están en `docs/audit-runs/20261021-identity-separation/host_inventory.log` (#23), en informes `docs/audit-runs/20261019-provisional/*/report.json`, en `docs/GOVERNANCE_MECHANISMS.md`, en el registro de decisiones y en GOV-REV-002 (ruta del registro de la conversación). | No son secretos. **No se reescribe el historial**: cambiaría los SHA fijados en el expediente. Propuesta: no publicar nuevos inventarios del host sin redactar. |
| EXP-04 | INFORMATIVA | El correo del CEO (`alessbarb@gmail.com`) figura como autor de **508 commits públicos** (`git log --remotes --format=%ae`). | Es inherente a git. Opcional: usar el correo `noreply` de GitHub en commits futuros. |
| EXP-05 | BAJA (configuración) | `ci.yml` no declara `permissions:`; usa los permisos por defecto de `GITHUB_TOKEN`. No usa secretos ni `pull_request_target`. | Propuesta P3, §3: `permissions: contents: read`, aprobación obligatoria de workflows para colaboradores externos y token de solo lectura por defecto. |
| EXP-06 | MEDIA (nueva superficie) | Con el repo público, cualquiera puede abrir Issues y PR. Los agentes que los lean reciben **contenido externo no confiable** que podría intentar instruirlos (AGENTS.md, regla 4). | Propuesta P3, §3: límite de interacción a colaboradores. El PM solo trata como propuestas del CEO los Issues `ceo-proposal` **escritos por el CEO**. |

**Sin hallazgos:**

- **Historial de git:** gitleaks no detectó fugas. Los patrones propios solo encontraron placeholders (`CHANGE_ME_*`, `local-dev-only-change-me`, `locally-generated-secret`) y valores de prueba (`old-secret`, `from-file`).
- **Secretos reales del host:** ningún valor real, ni la contraseña de Postgres ni `AAO_CEO_TOKEN`, aparece en git, Issues, PR ni logs.
- **Issues y PR:** sin secretos.
- **Actions:** sin secretos ni variables configurados.
- **Claves privadas:** ningún archivo `.pem` ni `.key` versionado. Las claves de prueba se generan en tiempo de ejecución.
- **Token de GitHub del CEO** (`~/.config/gh/hosts.yml`): no aparece en ninguna superficie.

## 3. Limitaciones

- La auditoría no cubre lo que pudo copiarse mientras el repo era público (desde el cambio de visibilidad hasta esta auditoría). Los hallazgos se tratan como ya expuestos.
- Los detectores pueden no reconocer formatos propios. Por eso se compararon además los secretos reales del host por igualdad.
- Revisión independiente pendiente (Codex).

## 4. Acciones pendientes

| Acción | Responsable |
|---|---|
| Revisión de esta auditoría por Codex | AAO |
| `--tb=short` en CI y `permissions: contents: read` en `ci.yml` (cambio de CI, R2) | AAO, por PR |
| Decidir si se borran los 4 logs de EXP-02 (irreversible) | CEO |
| Rulesets y configuración de Actions de P3 | CEO (administración, D4) |
