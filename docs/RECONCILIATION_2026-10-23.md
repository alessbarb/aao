# Reconciliación del repositorio tras las fusiones del CEO (2026-10-23)

**Estado:** registro verificado. **No** convalida nada ni aprueba P1, P2, P3 o P5, ni demuestra independencia operativa (orden del CEO del 2026-10-23).

## 1. Fusiones registradas

| PR | Fusionada por | Fecha (UTC) | Merge commit | Cabeza integrada | ¿Coincide con el SHA del expediente? | ¿Árbol = fusión limpia de sus padres? |
|---|---|---|---|---|---|---|
| #22 registro D1–D13 | CEO (`alessbarb`) | 2026-10-23 09:30:49 | `26434da` | `432f7a8c96276c497e98eb8674ae732547d84a41` | **sí** | **sí** |
| #24 GOV-REV-002 v0.3 | CEO | 2026-10-23 09:31:03 | `ee65cda` | `bafb74b56c4f1355512b48c8112cbac3b064d2b4` | **sí** | **sí** |
| #26 mecanismos F3a | CEO | 2026-10-23 09:31:32 | `45c8372` | `8d06feb2ff1ebad8e8857de79177571ec011de00` | **sí** | **sí** |
| #27 auditor (SL-01..SL-08) | CEO | 2026-10-23 09:31:44 | `12b25fb` | `1e5c0c8c81001dae1edf20f746da17b8f7ae7d28` | **sí** | **sí** |
| #31 repo público, exposición y P3 | CEO | 2026-10-23 09:32:13 | `e24d269` | `0d1ab59673fa09f25ada0a0a90505206c3892b4f` | **sí** | **sí** |

**Método:** para cada merge commit `M` se comprobó lo siguiente. El resultado es **sin discrepancias de contenido**.

- `M^2` es exactamente el SHA del expediente.
- `tree(M)` es igual a `git merge-tree --write-tree M^1 M^2`, es decir, sin contenido añadido durante la fusión.
- La cadena de primer padre `ddd520f → 26434da → ee65cda → 45c8372 → 12b25fb → e24d269` no contiene ningún otro commit.

## 2. Naturaleza de las fusiones

- Las hizo el CEO **a mano**, con su token de administrador. **No** las hizo el integrador, **no** hubo autorización de integración firmada (§6.1) y **no** se usó la vía de arranque del §12.3.
- Con ellas, P5 no queda aprobado. GOV-REV-002 está en `main` como texto, pero **sigue sin estar vigente**.
- Se añaden al inventario de integraciones sin dictamen válido, junto a #10–#21. **Ninguna se convalida.**
- #27 estaba apilada sobre #26. GitHub la reapuntó a `main` al fusionar #26.

## 3. Discrepancias y riesgos que deja `main`

| ID | Discrepancia | Estado |
|---|---|---|
| R-01 | **CI de `main` en rojo** desde `45c8372`: 16 pruebas de F3a no son portables al runner (versión de git fija y `git init` sin rama `main`) | corregido en la **PR #35**, con CI en verde; pendiente de fusión |
| R-02 | `main` contiene el auditor `1e5c0c8` **con el hueco F4-02**: un veto sin custodia tras una aprobación registrada no bloqueaba el gate | corregido en las **PR #30** (gate) y **#34** (integrador), no fusionadas. Hoy no hay riesgo operativo porque nada está activado |
| R-03 | `trusted_auditor_revisions` sigue **sin valor de confianza**. `1e5c0c8` no es candidata válida (F4-02 y A-2) | depende de #30, #34, F4-01 y una nueva revisión de segunda línea |
| R-04 | GOV-REV-002 cita como pendiente la fusión de #22 por la vía de arranque, pero #22 ya está fusionada fuera de esa vía | operación 2 del §12.3 **consumida fuera de procedimiento**; queda registrada aquí |

## 4. P1 ejecutado (2026-10-23)

El CEO ejecutó P1. Los **9 roles pasan en PASS** en el host, con las huellas de los scripts verificadas. La evidencia está en el Issue #25 (sha256 de `run.log`: `76b56d47…09b6`).

Con eso queda cerrada la matriz de identidades estáticas de F2. Siguen pendientes:

- el aislamiento en ejecución entre auditores;
- que los agentes usen sus propias cuentas;
- F4-01.
