# P2: identidades, permisos mínimos y custodia en GitHub

**Estado:** PROPUESTA al CEO (D4: la administración de GitHub la gestiona el CEO; la propuesta no bloquea el trabajo). No vigente. No concede permisos.
**Base:** GOV-REV-002 v0.3 (#24), RA-02, RA-03 y RA-09; mecanismos F3a (#26, `8d06feb`); auditor corregido (#27, `1e5c0c8`); D11 y D12.
**Gasto:** ninguno. GitHub Apps y organización gratuita (D5).

## 1. Qué resuelve

Hoy todos los agentes usan el token del propietario, que tiene permisos de administrador. Cualquiera puede empujar a `main`, fusionar o cambiar la configuración, y GitHub atribuye todo al CEO. P2 tiene tres objetivos:

1. Una **identidad distinta por rol**, atribuible en GitHub (RA-02).
2. **Permisos mínimos.** Ningún rol tiene Administration, y solo el integrador puede escribir en `main` del repositorio canónico.
3. **Promoción por actualización condicionada** del ref. Su prueba contra el servidor real es la evidencia de RA-03 y RA-09.

## 2. Capacidades de GitHub: qué garantiza cada una

| Mecanismo | Qué garantiza | Qué NO garantiza | Uso en AAO |
|---|---|---|---|
| **GitHub App** (token de instalación) | identidad propia (`<app>[bot]`, `app_id`), permisos por recurso, token de 1 h | no impide por sí sola que un token con `contents: write` empuje a `main` en un repo privado gratuito sin protección | identidad de cada rol |
| **REST `PUT /pulls/{n}/merge`** | con `sha`, que la cabeza de la PR coincide (si no, 409) | **no fija el árbol resultante, los padres ni la base**: los calcula GitHub | **no se usa** para promover |
| **REST `PATCH /git/refs/{ref}`** | con `force=false`, solo avance rápido | **no tiene valor esperado** (no es CAS) | **no se usa** |
| **GraphQL `updateRefs`** | `beforeOid` es una precondición sobre el valor actual del ref; las actualizaciones son atómicas | requiere que el commit ya exista en GitHub | **promoción preferida**: subir el commit a un ref temporal y después `updateRefs(main: beforeOid=base_sha → afterOid=merge_commit)` |
| **`git push --atomic --force-with-lease=main:<base>`** | `receive-pack` aplica la actualización solo si el valor actual es el esperado | depende de que el servidor respete el valor antiguo enviado; hay que probarlo en GitHub | **alternativa equivalente**; F3a ya la implementa y prueba en local |
| **Check runs** (`checks: write`) | quién publicó el resultado (`app_id`) y para qué SHA | no prueba que el contenido del check sea independiente | publicación atribuible del dictamen del auditor |

**Implicación:** el merge-commit lo construye el integrador, con el árbol y los padres autorizados (§6.1), y se publica por CAS. GitHub marca la PR como fusionada cuando su cabeza pasa a ser alcanzable desde `main`.

## 3. Identidades propuestas (8 GitHub Apps privadas, propiedad del CEO)

| App | Rol | uid que custodia la clave (P1) | Instalada en |
|---|---|---|---|
| `aao-integrator` | integrador determinista | `aao-integrator` | repo canónico |
| `aao-auditor` | auditor principal | `aao-auditor` | repo canónico |
| `aao-auditor-alt` | auditor alterno / segunda línea | `aao-auditor-alt` | repo canónico |
| `aao-supervisor` | supervisor | `aao-supervisor` | repo canónico |
| `aao-notifier` | notificador | `aao-notifier` | repo canónico |
| `aao-pm` | PM | `aao-pm` | repo canónico |
| `aao-impl` (una por implementador: `-codex`, `-claude`, `-ag`) | implementadores | `aao-impl-*` | **fork** (§5) y canónico, solo PR |

Cada implementador tiene **su propia App**. Así la atribución distingue a Codex, Claude y Antigravity. Un PAT del CEO lo atribuiría todo al CEO.

## 4. Permisos mínimos

`metadata: read` es obligatorio en todas las Apps. Ninguna tiene **Administration**, **Secrets**, **Actions: write** ni **Workflows: write**, salvo donde se indica.

| App | Repo canónico | Fork de implementación |
|---|---|---|
| `aao-integrator` | `contents: write` (CAS de `main` y refs temporales), `pull_requests: write` (comentar o cerrar tras promover), `checks: read`, `statuses: read`, **`workflows: write`** (solo para poder promover árboles autorizados que toquen `.github/workflows/`; la clase R2 y la autorización firmada lo controlan) | — |
| `aao-auditor`, `aao-auditor-alt` | `contents: read`, `pull_requests: read`, `checks: write` (dictamen como check run) | `contents: read` |
| `aao-supervisor` | `contents: read`, `pull_requests: read`, `checks: read`, `actions: read` (latido del workflow detectivo) | — |
| `aao-notifier` | `issues: write` | — |
| `aao-pm` | `issues: write` (etiquetas, propuestas), `pull_requests: read`, `contents: read` | — |
| `aao-impl-*` | `pull_requests: write` (abrir y actualizar sus PR), `contents: read` | `contents: write` (ramas), `workflows: write` (para proponer cambios de CI, que serán R2) |

**Punto crítico (P3).** En un repositorio privado del plan gratuito no hay protección de rama. Cualquier App con `contents: write` en el canónico podría empujar a `main`. Por eso **solo el integrador tiene `contents: write` en el canónico**. Los implementadores escriben únicamente en el fork.


## 4-bis. Corrección de la especificación (auditoría del harness, A6-05 y A6-06, 2026-10-23)

**Hecho de GitHub:** los permisos se definen **por App**, no por instalación. Una App instalada en dos repositorios tiene los mismos permisos en ambos. Por tanto, la tabla del §4 con columnas por repositorio **no es realizable** para los implementadores.

**Regla corregida:**

- **Apps de implementador (`aao-impl-*`):** se instalan **solo en su fork**, nunca en el canónico. Permisos: `contents: write`, `workflows: write` y `metadata: read`. Sin `pull_requests`.
- **Apertura de PR hacia el canónico:** la hace **`aao-pm`**, con `pull_requests: write`, `contents: read` e `issues: write` en el canónico. Abre la PR desde la rama del fork indicada por el implementador.
  - La **autoría** sigue siendo verificable: los commits y los eventos de push del fork los hace la App del implementador, y el supervisor la atribuye con RA-02.
  - El PM **no** puede escribir código en el canónico.
- **Auditores:** `checks: write` **y `statuses: write`**. P3 §4 prevalece, porque el ruleset exige que la App fuente del check obligatorio tenga `statuses: write`. P3-04 comprueba que un status de otra App no satisface el check.
- **A-14 (`workflows`)** se prueba **en el fork**, con la App del implementador, y en el canónico con `aao-integrator`. Ninguna otra App puede probarlo.
- **A-10** compara los permisos de cada instalación con esta tabla corregida, según el repositorio en el que esté instalada la App.

## 5. Modelo de fork (prevención sin plan de pago)

- **Propuesta:** crear una **organización gratuita** (p. ej. `aao-agents`) con un fork privado del repositorio. Las Apps de implementación se instalan con escritura solo en el fork. Las PR se abren desde `aao-agents:<rama>` hacia el canónico.
- **Efecto:** los implementadores **no pueden** escribir en el canónico por permisos. Es una prevención real para ellos, sin GitHub Pro. El control detectivo (D11) sigue cubriendo al integrador y al CEO.
- **A verificar en la prueba A-11:** que GitHub permita el fork privado hacia esa organización y que una App con solo `pull_requests: write` en el canónico pueda abrir una PR desde el fork.
- **Si no fuera posible:** los implementadores tendrían `contents: write` en el canónico. La prevención pasaría a depender de P3 (Pro o reglas), y mientras tanto sería solo detectiva.

## 6. Custodia de claves y tokens

| Elemento | Dónde | Quién lo genera | Modo |
|---|---|---|---|
| Clave privada de cada App (`.pem`) | `/home/<uid-del-rol>/.config/aao/<app>.pem` | el CEO la descarga y la instala con sudo en el uid del rol, sin pasar por otros uids | `0600`, propietario el uid del rol |
| Token de instalación | solo en memoria del proceso del rol | lo pide el propio rol con un JWT firmado con su clave | caduca en 1 h y no se escribe en disco |
| Token del CEO (`~/.config/gh`) | cuenta del CEO | — | **los agentes dejan de usarlo** tras P2; el verificador F2 comprueba que no lo leen |

Nadie más que el uid del rol puede leer su clave; lo comprueba el verificador F2. El CEO conserva la propiedad de las Apps como administrador de GitHub.

## 7. Revocación y rotación

| Acción | Cómo | Efecto | Tiempo |
|---|---|---|---|
| Revocar una App | suspender o desinstalar la instalación | tokens nuevos y existentes inválidos | inmediato |
| Revocar una clave | borrar la clave en la configuración de la App | no se pueden emitir tokens nuevos; los emitidos caducan | ≤ 1 h |
| Revocar un token | `DELETE /installation/token` desde el rol | token inválido | inmediato |
| Rotar | generar una clave nueva, instalarla en el uid, borrar la antigua | sin interrupción | — |
| Emergencia | el CEO suspende `aao-integrator` | ninguna promoción posible | inmediato |

Cada revocación o rotación deja una entrada en el ledger de gobierno.

## 8. Pruebas de aceptación (repo de ensayo privado desechable, antes de usarlo en el canónico)

| ID | Prueba | Resultado esperado | Cubre |
|---|---|---|---|
| A-01 | token de `aao-impl-codex` → `git push` a `main` del canónico | 403 o rechazo; `main` intacto | prevención |
| A-02 | token de `aao-impl-codex` → `PUT /pulls/{n}/merge` | 403 | prevención |
| A-03 | integrador: `updateRefs` con `beforeOid` antiguo, tras mover `main` | rechazo; `main` intacto | **RA-03 / RA-09** |
| A-04 | integrador: `git push --force-with-lease` con lease antiguo | rechazo del servidor; `main` intacto | **RA-09** |
| A-05 | integrador: promoción válida | `main` == commit con árbol y padres autorizados; PR marcada como fusionada | RA-03 |
| A-06 | auditor: check run sobre el SHA; la puerta comprueba `app_id` | check aceptado solo del `app_id` del auditor; un implementador sin `checks: write` recibe 403 | atribución del dictamen |
| A-07 | supervisor: push al canónico por una identidad que no es el integrador (en el ensayo, con el token del CEO) | evento `governance-violation` con el actor real | **RA-02**, D11 |
| A-08 | atribución: el integrador escribe `attribution.json` a partir de los eventos de push y de autor de la PR (actor, `app_id`) | identidades = Apps de implementación reales; sin evento → provisional | **RA-02**, SL-02 |
| A-09 | notificador: crea un Issue; intento de push | Issue creado; push 403 | mínimo privilegio |
| A-10 | ninguna instalación tiene `administration`; `GET /installation` lo comprueba | lista de permisos == tabla del §4 | mínimo privilegio |
| A-11 | fork en la organización y PR desde el fork con App solo-PR en el canónico | PR abierta; la App no puede empujar al canónico | §5 |
| A-12 | revocación: clave borrada o instalación suspendida | emisión de token falla; las operaciones fallan | §7 |
| A-13 | token de instalación pasada su caducidad | 401 | §6 |
| A-14 | push de un cambio en `.github/workflows/` desde una App sin `workflows: write` | rechazado | §4 |

Cada prueba guarda la evidencia con el SHA, la petición, la respuesta y el `app_id`.

**Aceptación:** A-01 a A-14 en PASS → RA-02, RA-03 y RA-09 pasan a PASS en el registro de confianza (`ra_status`).

## 9. Lo que el CEO tendría que hacer (unos 30 minutos, una vez)

1. Crear la organización gratuita y el fork (si se acepta §5).
2. Crear las Apps desde los manifiestos que AAO preparará (`docs/proposals/github-apps/*.json`) e instalarlas con los permisos de la tabla del §4.
3. Descargar cada clave e instalarla con sudo en su uid. AAO preparará el comando exacto, que requiere P1 ejecutado.
4. Crear el repo de ensayo privado para las pruebas A-01 a A-14.

## 10. Riesgos residuales tras P2

- El integrador tiene `contents: write` y `workflows: write` en el canónico. Una vulneración del uid `aao-integrator` permitiría escribir en `main`. Lo detecta el supervisor (D11) y lo frena la custodia de su uid.
- El CEO sigue siendo administrador, que es su papel (D4). Sus pushes manuales los detecta el supervisor.
- Sin P3, la prevención para el integrador y el CEO es solo detectiva.

## 11. Decisión que se pide

- Aprobar las identidades del §3, los permisos del §4 y el modelo de fork del §5, o indicar si se descarta el fork.
- Autorizar a AAO a preparar los manifiestos de las Apps y el repo de ensayo.

**Recomendación:** aprobar.

---
Fuentes: documentación de GitHub, comprobada el 2026-10-21:
- [Merge a pull request](https://docs.github.com/en/rest/pulls/pulls#merge-a-pull-request)
- [Update a reference](https://docs.github.com/en/rest/git/refs#update-a-reference)
- [GraphQL `updateRefs` / `RefUpdate`](https://docs.github.com/en/graphql/reference/git)
- [Permiso `workflows` de GitHub Apps](https://github.blog/changelog/2020-04-07-github-apps-workflow-permission)
