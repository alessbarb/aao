# Vía de integración por PR bajo P5 (2026-10-23)

**Base normativa:** GOV-REV-002 v0.3, vigente desde P5 (#25, 2026-10-23; el arranque caduca el 2026-11-22).

- **§13.4:** entre P5 y la primera fusión R1 válida del integrador, **solo** se integran las operaciones del §12.3.
- **§13.5:** ningún cambio R2 se fusiona antes del §12.5, salvo el §12.3.
- **CEO-DEC-LOCAL-A:** terminada por P5. **D12** fija quién fusiona, pero no amplía qué se fusiona.

## 1. Lista cerrada del §12.3 y su estado

| Op. | Contenido | Estado |
|---|---|---|
| 1 | Instalar el registro de confianza (CEO con sudo, decisión (a)) | **no ejecutable**: no hay revisión del auditor válida para `trusted_auditor_revisions`; requiere cerrar F4-01, F4-02 y F4-02b, y una nueva segunda línea |
| 2 | Fusionar #22 en `432f7a8` | **consumida fuera de procedimiento** (fusión manual del CEO, `26434da`) |
| 3 | Fusionar GOV-REV-002 en `bafb74b` | **consumida fuera de procedimiento** (`ee65cda`) |
| 4 | Fusionar los componentes del §12.2.2 en sus SHA fijados (auditor, integrador, supervisor, notificador) | **cubre #30, #34 y #37** (correcciones de esos componentes) cuando sus SHA estén fijados y revisados, **y** se cumplan los PASS del §12.2.4, incluidos RA-02, RA-03 y RA-09 contra GitHub real (P2/P3) |

## 2. Clasificación de cada PR abierta

| PR | Contenido | Clase | ¿Vía actual? | Qué falta |
|---|---|---|---|---|
| #30, #34, #37 | F4-02, F4-02b, F4-01a (auditor, integrador y supervisor) | R2 | **op. 4 del §12.3** | dictámenes finales; PASS del §12.2.4 (RA-02/03/09 en GitHub tras los ensayos de P2/P3; RA-01/07; F2 en ejecución) |
| #35 | portabilidad de las pruebas F3a (restaura CI) | R1 (solo pruebas) | **ninguna** | §13.4: fuera de la lista; además, **circular** (ver §3) |
| #33 | endurecimiento del CI | **R2** (`.github/workflows/`) | **ninguna** | §13.5: R2 antes del §12.5 |
| #23 | script P1 (ya ejecutado) | R2 (identidad) | **ninguna** | §13.2 lo excluye; puede quedar como registro sin fusionar |
| #28 | documentación (P2/P3, F4, expediente, procedimientos, manifiestos) | R0, salvo `docs/decisions/` | **ninguna** | §13.4 no distingue R0 |

## 3. Bloqueo circular

- `main` está en rojo desde `45c8372`.
- El integrador exige CI en verde sobre el commit candidato (§6.2), y CI ejecuta la suite completa. Por tanto, **ningún candidato puede pasar CI mientras `main` no incluya #35**.
- Sin la primera fusión R1 válida del integrador, el §13.4 sigue en vigor y #35 no puede entrar.
- **Resultado:** la vía ordinaria no se puede abrir nunca.

## 4. Propuesta mínima (ampliación acotada del §12.3, decisión R3 del CEO)

Añadir **una única operación** al §12.3:

> **Op. 1-bis:** fusionar la PR #35 en su SHA exacto `a3e8e26` (o el que se fije tras la revisión), formado solo por `tests/test_governance_mechanisms.py`. Se exige APPROVE-TECHNICAL de un revisor no recusado (Codex) y CI en verde sobre ese SHA. La ejecuta el integrador designado de D12 con el token actual, mediante merge commit, y después se verifica `main` en verde. No cubre ningún otro archivo ni SHA.

**Por qué es acotada:**

- Son solo pruebas y no se toca producción.
- Se reprodujo en un contenedor: 16 fallos en `main` y 0 con #35.
- Es imprescindible para que cualquier integración posterior, incluidas las operaciones 1 y 4, pueda pasar CI.

**Alternativa:** esperar a que el integrador esté operativo (P2/P3 y F4) e integrar #35 como su **primera R1**. Tiene el mismo resultado, pero el CI de `main` queda en rojo durante semanas y la prueba piloto queda mezclada con la reparación.

**Recomendación:** aprobar la op. 1-bis.
- **#33** (R2) **no** se incluye: no es necesaria para abrir la vía y puede esperar al §12.5.
- **#28** (R0) puede añadirse por la misma vía si se quiere tener la documentación en `main`.
