# P3 (revisada tras la publicación): protección preventiva de `main` y forks públicos

**Estado:** PROPUESTA administrativa al CEO (D4). No vigente. No autoriza P1, P2, P5 ni la activación de R2.
**Contexto:** el CEO cambió `alessbarb/aao` a **público** el 2026-10-21 (`docs/decisions/CEO-DEC-REPO-PUBLIC-2026-10-21.md`). Con GitHub Free, un repositorio público dispone de protección de ramas y rulesets, lo que cambia P2 y P3. La auditoría de exposición previa está en `docs/PUBLIC_EXPOSURE_AUDIT_2026-10-21.md`.
**Complementa:** P2 (`docs/proposals/P2_GITHUB_IDENTITIES_AND_PERMISSIONS.md`). Las identidades y la custodia de P2 se mantienen; este documento sustituye la parte de prevención de P2 (el modelo de fork «para evitar el plan de pago») por reglas preventivas en el propio repo, y mantiene los forks como capa adicional.

## 1. Qué cambia respecto a P2

| Tema | P2 (repo privado, gratuito) | Ahora (repo público, gratuito) |
|---|---|---|
| Prevención de pushes a `main` | ninguna; solo control detectivo (D11) | **ruleset «Restrict updates»**: solo la App `aao-integrator` puede actualizar `main` |
| Implementadores | fork en una organización gratuita para no tener escritura en el canónico | **forks públicos** en la organización, sin escritura en el canónico; sigue siendo la recomendación |
| Dictamen del auditor | check run atribuible, verificado por el integrador | además, **status check obligatorio cuya fuente es la App `aao-auditor`**, aplicado por GitHub |
| CI | verificado por el integrador | además, **check obligatorio aplicado por GitHub** sobre el commit exacto que se promueve |

## 2. Compatibilidad con la promoción atómica del integrador

El integrador **no** usa el merge de la API (`PUT /pulls/{n}/merge`), porque solo protege la cabeza de la PR. Construye él mismo el merge-commit con el árbol y los padres autorizados (GOV-REV-002 §6.1).

**Flujo propuesto, compatible con las reglas:**

1. El integrador crea el merge-commit `M` con los padres `[base_sha, candidate_sha]` y el árbol `merge_result_tree_sha`.
2. Empuja `M` a una rama de staging, `aao-staging/<pr>-<sha>`. No está protegida por la regla de `main`, pero sí la cubren «Block force pushes» y «Restrict deletions» del ruleset B.
3. CI corre sobre `M`. El auditor verifica que `tree(M) == merge_result_tree_sha` y publica en `M` el check `aao-audit`, con fuente `aao-auditor`.
4. El integrador ejecuta `updateRefs(main: beforeOid = base_sha → afterOid = M)` por GraphQL, o un push con lease. Es un avance rápido, porque `M` es hijo de `base_sha`.
5. **GitHub hace cumplir** que solo `aao-integrator` puede actualizar `main` (ruleset A), y que `M` tiene en verde los checks obligatorios de la App esperada (ruleset B).

**Ventaja:** si se compromete el integrador, aun así no puede promover un commit sin el check `aao-audit` de la App del auditor. GitHub lo impide, no solo el código del integrador.

## 3. Reglas concretas

**Ruleset A: «main: solo integrador»**

- Objetivo: `refs/heads/main`.
- Estado: Active.
- Reglas: **Restrict updates**, **Require a pull request before merging** (0 aprobaciones; la PR existe por trazabilidad).
- **Bypass:** solo la GitHub App `aao-integrator`. **Ni el CEO ni los administradores** están en la lista de exclusión. La emergencia del CEO consiste en desactivar el ruleset, y eso queda en el historial de rulesets.

**Ruleset B: «main y staging: integridad», sin lista de exclusión**

- Objetivo: `refs/heads/main`, `refs/heads/aao-staging/**`.
- Reglas:
  - **Block force pushes**;
  - **Restrict deletions** (en `main`);
  - **Require status checks to pass**, con `aao-audit` (fuente: App `aao-auditor`) y el job de CI `test` (fuente: GitHub Actions), y con «require branches to be up to date» desactivado, porque el CAS ya cubre la base;
  - **Require linear history: NO**, porque bloquearía el merge-commit autorizado.

**Ruleset C: «etiquetas»**

- Objetivo: todas las etiquetas.
- Reglas: Restrict creations, updates y deletions.
- Bypass: `aao-integrator`, si en el futuro hay publicaciones.

**Configuración del repo**

- Actions:
  - pedir aprobación para workflows de **todos** los colaboradores externos;
  - `GITHUB_TOKEN` con permisos por defecto de solo lectura;
  - no permitir que Actions cree ni apruebe PR.
- `ci.yml`: añadir `permissions: contents: read` explícito. Hoy no declara permisos.
- Se mantiene la prohibición de `pull_request_target`; hoy no se usa.
- Merge de PR por la interfaz:
  - permitido solo como «merge commit»;
  - auto-merge desactivado;
  - de todos modos, Restrict updates impide que nadie salvo el integrador lo complete.
- **Límites de interacción:** limitar Issues y PR a colaboradores mientras no exista el filtro de contenido externo. Es contenido no confiable que podría intentar instruir a los agentes (AGENTS.md, regla 4).

## 4. Identidades y permisos (actualiza el §4 de P2)

Sin cambios respecto a P2, salvo:

- `aao-auditor` y `aao-auditor-alt`: añadir **`statuses: write`** a `checks: write`, porque el ruleset exige que la App fuente tenga `statuses: write`.
- `aao-integrator`: además, `contents: write` sobre las ramas `aao-staging/**`, que ya cubre su permiso `contents: write`.
- Implementadores: siguen **sin** escritura en el canónico. Trabajan en **forks públicos** de la organización `aao-agents` y abren las PR hacia el canónico. Con el repo público, el fork ya no depende de la configuración de forks privados.
- **El ruleset se hereda en la red de forks:** las exclusiones de las reglas de push solo las tiene quien puede saltárselas en el repo raíz. Esto refuerza la separación.

## 5. Pruebas negativas obligatorias (en un repo público de ensayo, antes del canónico)

| ID | Prueba | Resultado esperado |
|---|---|---|
| P3-01 | el CEO, con permisos de administrador, intenta `git push` a `main` | **rechazado** por Restrict updates (el CEO no tiene exclusión) |
| P3-02 | la App de un implementador intenta push a `main` del canónico | rechazado (sin `contents: write`, y además Restrict updates) |
| P3-03 | `aao-integrator` intenta actualizar `main` a un commit **sin** el check `aao-audit` | **rechazado por GitHub** (ruleset B) |
| P3-04 | `aao-integrator` intenta actualizar `main` a un commit cuyo `aao-audit` lo publicó otra App, o un status manual | rechazado (la fuente debe ser `aao-auditor`) |
| P3-05 | `aao-integrator`, con todo en verde, `updateRefs` con `beforeOid` antiguo (`main` movido) | rechazado; `main` intacto (RA-09) |
| P3-06 | `aao-integrator` con todo en verde y `beforeOid` correcto | `main == M`; la PR se marca como fusionada |
| P3-07 | force push a `main` o a staging por cualquier actor, incluido el integrador | rechazado (ruleset B sin exclusiones) |
| P3-08 | borrar `main` | rechazado |
| P3-09 | fusionar la PR desde la interfaz o la API con el token del CEO | rechazado (Restrict updates) |
| P3-10 | una PR desde un fork que modifica `.github/workflows/` ejecuta Actions sin aprobación | no se ejecuta sin aprobación; `GITHUB_TOKEN` de solo lectura |
| P3-11 | desactivar el ruleset A (emergencia del CEO) | posible para el CEO; queda registrado; el supervisor lo detecta y alerta |
| P3-12 | push del integrador a `main` que no es avance rápido | rechazado (ruleset B; no hace falta forzar) |

Toda la evidencia queda vinculada al SHA y a la respuesta de la API. P3-01 a P3-12 en PASS, junto con A-01 a A-14 de P2, cierran RA-02, RA-03 y RA-09.

**A verificar en el ensayo**, porque la documentación no lo deja claro para repos de **cuenta personal**:
- (a) que una GitHub App pueda figurar en la lista de exclusión;
- (b) que «Restrict updates» esté disponible.

Si alguna falla, la recomendación es **transferir el repo a la organización gratuita `aao-agents`**, donde ambas funciones están documentadas. Es una decisión R3 del CEO, porque cambia la propiedad.

## 6. Lo que tendría que hacer el CEO (unos 20 minutos, además de P2)

1. Crear el repo público de ensayo y aplicar en él los rulesets A, B y C.
2. Tras P3-01 a P3-12 en PASS, aplicar los mismos rulesets en `alessbarb/aao`.
3. Configurar Actions y los límites de interacción del §3.

## 7. Riesgos residuales

- El CEO puede desactivar los rulesets: es su papel. El supervisor lo detecta (P3-11).
- Un compromiso conjunto de `aao-integrator` y `aao-auditor` permitiría promover. Mitigación: uids separados (P1) y revisión cruzada.
- La publicación expone el código y la documentación de gobierno. Ver la auditoría de exposición.

## 8. Decisión que se pide

- Aprobar los rulesets A, B y C y la configuración del §3.
- Mantener los forks públicos de la organización para los implementadores.
- Autorizar el repo de ensayo.

**Recomendación:** aprobar. No requiere gasto. La parte que depende de P1 (custodia de claves) sigue requiriendo P1.

---
Fuentes (documentación de GitHub, consultada el 2026-10-21):
- [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
- [Creating rulesets for a repository](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository)
- [GraphQL `updateRefs`](https://docs.github.com/en/graphql/reference/git)
