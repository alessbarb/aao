# Propuesta: datos de confianza para RA-01 y RA-02 (decisión del CEO)

**Estado: APROBADA POR EL CEO (R3), 2026-10-24 12:38 CEST.** El CEO aprobó todas las filas del §1, `aao-audit` solo desde `aao-auditor` (5448107) y la correspondencia entre principales e implementadores del §2. La lista normativa es [`docs/protected-routes.json`](../protected-routes.json). Su aprobación no pone ningún RA en PASS: después hay que implementar, probar (NT-01, NT-02), auditar y regenerar la raíz de confianza.

**Por qué hace falta.** Codex se detuvo en el límite que le correspondía (#73). Lo que falta no es código, sino datos R3 que solo puede fijar el CEO:
- **RA-01.** El §3.4.3 de la política no es una lista ejecutable. Mezcla conceptos («el integrador», «código del supervisor») con rutas, e incluye filas condicionadas a P5. Además, las dos copias que existen no coinciden con él:
  - la operativa, `policy.json`, tiene 19 prefijos y le faltan `manifest_audit.py`, el integrador, el supervisor y `policy*.json`;
  - la del registro de confianza las clasifica todas como R2.
- **RA-02.** No hay una lista de publicadores de checks autorizados en el camino R1 de producción (NT-02-5), ni una correspondencia fiable entre actores y principales de GitHub (NT-02-3 y NT-02-10).

## 1. RA-01: lista normativa de rutas protegidas

**Semántica propuesta.**
- Una entrada que termina en `/` cubre todo lo que hay debajo de ese directorio. Cualquier otra entrada es una ruta exacta, salvo que contenga `*`, que equivale a cualquier secuencia sin `/`.
- Se comparan las rutas de todos los archivos que la PR añade, modifica, borra o renombra; en los renombrados, el origen y el destino.
- Si una ruta coincide con varias entradas, rige la **clase más alta**. Los solapamientos nunca rebajan la clase.
- La lista normativa queda en `docs/protected-routes.json`, que es R3. El registro de confianza guarda una copia y su sha256, y la copia operativa también. El integrador y el supervisor comprueban que los tres hashes coinciden antes de cada uso; si no coinciden, fallan en cerrado (NT-01-1 a NT-01-5).

**Lista propuesta.** La columna «Decisión» es la que tienes que fijar:

| Clase | Ruta | Origen | Decisión |
|---|---|---|---|
| R3 | `docs/CONSTITUTION.md` | §3.4.3, fila condicionada a P5 | ¿aprobar como R3? |
| R3 | `docs/AUTONOMOUS_AUDIT_POLICY.md` | §3.4.3, fila condicionada a P5 | ¿aprobar como R3? |
| R3 | `docs/AUTONOMOUS_GOVERNANCE_POLICY.md` | contiene el propio §3.4 (si no fuera R3, la lista podría cambiarse por R2) | **propuesta nueva** |
| R3 | `docs/GOV-REV-002*` | §3.4.3, fila condicionada a P5 | ¿aprobar como R3? |
| R3 | `docs/decisions/` y `docs/CEO-DEC-*` | §3.4.3, fila condicionada a P5 (en el repo las decisiones están en `docs/CEO-DEC-*`) | ¿aprobar como R3? |
| R3 | `docs/protected-routes.json` | la propia lista normativa | **propuesta nueva** |
| R3 | `scripts/make_trust_root_files.py`, `deploy/github-apps/aao-github-apps-registry.json` | «contenido del registro de confianza» (§3.4.3): generador y registro de identidades | ¿aprobar? |
| R2 | `src/aao/independent_audit.py`, `src/aao/manifest_audit.py`, `src/aao/auditor_dispatch.py` | §3.4.3 (fila vigente) | vigente |
| R2 | `src/aao/integrator.py`, `src/aao/integration_authorization.py`, `src/aao/r1_pipeline.py` | «el integrador» (§3.4.3, fila vigente) | vigente |
| R2 | `.github/workflows/` | §3.4.3 (fila vigente) | vigente |
| R2 | `policy*.json` (en cualquier directorio) | §3.4.3 (fila vigente) | vigente |
| R2 | `src/aao/policy.py` | §3.4.3, fila condicionada a P5 | ¿aprobar? |
| R2 | `src/aao/supervisor.py`, `src/aao/supervisor_service.py`, `src/aao/notifier.py` | §3.4.3, fila condicionada a P5 | ¿aprobar? |
| R2 | `AGENTS.md`, `docs/AGENT_OPERATING_RULES.md` | §3.4.3, fila condicionada a P5 | ¿aprobar? |
| R2 | `src/aao/pr_conformity.py`, `src/aao/review.py`, `src/aao/governance_ledger.py`, `src/aao/github_app_auth.py` | ya figuran en la copia operativa (salvo ledger y App auth, que se proponen nuevas) | ¿aprobar? |
| R2 | `deploy/systemd/`, `deploy/tmpfiles.d/`, `scripts/bootstrap/`, `scripts/identity_separation.sh`, `scripts/verify_trust_root_host.py`, `scripts/audit/`, `docs/audit-prompts/` | unidades, arranque y auditor de la raíz de confianza | **propuesta nueva** |
| R2 | `pyproject.toml`, `setup.cfg`, `tox.ini`, `pytest.ini`, `ruff.toml`, `.ruff.toml`, `conftest.py`, `tests/conftest.py`, `db/postgres/011_sha_bound_reviews_and_veto.sql` | ya figuran en la copia operativa (configuración de pruebas y del lint) | vigente en la copia operativa |

**Recomendación del PM:** aprobar todas las filas. Una lista más estricta solo hace que más PR caigan en R2 o R3, y por tanto fuera de la autonomía R1; nunca concede nada.

## 2. RA-02: publicadores de checks y principales

**Publicadores autorizados de checks requeridos** (NT-02-5). El camino R1 de producción solo acepta un check si la App que lo publicó es esta:

| Check | App autorizada (id) |
|---|---|
| `aao-audit` | `aao-auditor` (5448107) únicamente (decisión del CEO) |
| `test` | GitHub Actions (15368) |

**Correspondencia entre principal de GitHub e implementador** (NT-02-3 y NT-02-10). La atribución solo se resuelve si el principal que empujó es exactamente uno de estos:

| Principal (push) | Implementador |
|---|---|
| `aao-impl-claude[bot]` | `claude` |
| `aao-impl-codex[bot]` | `codex` |
| `aao-impl-agy[bot]` | `antigravity` |

Cualquier otro principal deja la atribución sin resolver (`INCONCLUSIVE`), y la PR no pasa por R1. Esto incluye la cuenta humana del CEO, el PM y el integrador. Así, dos actores que compartan un principal nunca quedan resueltos.

## 3. Consecuencias

1. **Raíz de confianza.** Hay que regenerarla con los nuevos campos (lista normativa con su hash, publicadores y principales). Es una operación del CEO con sudo, y la rotación es otro procedimiento. Después hay que reverificar el host.
2. **Implementación (Codex):**
   - la comparación de los tres hashes en el integrador y el supervisor;
   - la clasificación por la lista normativa;
   - la lista de publicadores en el camino R1;
   - la correspondencia de principales en la atribución;
   - los tests NT-01 y NT-02.
   Todo ello pasa por auditoría independiente.
3. **R1.** Ninguna PR que toque una ruta de esta lista se integra sin el CEO. Esto incluye todas las del propio sistema de gobierno.
