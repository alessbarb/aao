# AAO — Decisión administrativa CEO: repositorio público

**ID:** CEO-DEC-REPO-PUBLIC-2026-10-21
**Autoridad:** CEO, como administrador de GitHub (D4). Decisión administrativa del 2026-10-21, comunicada en la conversación de gobierno.
**Estado:** **EJECUTADA por el CEO.** `alessbarb/aao` tiene `visibility: public`, verificado con GET `/repos/alessbarb/aao` el 2026-10-21.

## Cita literal del CEO

> «He cambiado la visibilidad de alessbarb/aao a pública. Esta es una decisión administrativa del CEO y debe registrarse como tal.»

> «La publicación del repositorio no autoriza automáticamente P1, P2, P5 ni la activación de R2.»

## Instrucciones asociadas del CEO

Son instrucciones del mismo mensaje, no decisiones nuevas:

- Revisar P2 y P3 con las capacidades de GitHub Free para repositorios públicos.
- Mantener los forks públicos para los implementadores si las pruebas confirman la separación de permisos.
- Evaluar la protección preventiva de `main` (protección de rama o rulesets) y su compatibilidad con la promoción atómica.
- Antes de crear forks, auditar la exposición pública y tratar cualquier credencial expuesta como comprometida.

## Lo que este registro NO hace

- No aprueba P1, P2, P3 ni P5, ni activa R2.
- No convalida las fusiones históricas.

## Evidencia relacionada

- `docs/PUBLIC_EXPOSURE_AUDIT_2026-10-21.md`: auditoría de exposición.
- `docs/proposals/P3_PUBLIC_REPOSITORY_MAIN_PROTECTION.md`: P3 revisada.

**Integración:** toca una ruta protegida (`docs/decisions/`). Se fusiona solo por la vía autorizada; no se fusiona por esta PR.
