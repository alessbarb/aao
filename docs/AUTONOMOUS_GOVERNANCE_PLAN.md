# Plan v3.1: gobierno autónomo del repositorio AAO

**Fecha:** 2026-10-21 · **Base:** `main` `ddd520f` · **Estado:** PROPUESTA, no vigente. Entra en vigor solo con la aprobación de GOV-REV-002 y del arranque (P5).
**Cambios respecto a v2:** incorpora los hallazgos H-01 a H-12 de la auditoría del v2 (§10).
**Cambios en v3.1:** consolida los hallazgos V3-01 a V3-09 de la revisión del v3 (§11), sin cambiar D1–D10.
Las versiones anteriores (v1 a v3) están en el historial de la conversación de gobierno del 2026-10-21 y no se publican.

**Principio rector:** no se declara autonomía ni independencia antes de probar el mecanismo que las hace efectivas. Mientras tanto se trabaja en todo lo que no dependa de esa garantía.

---

## 1. Decisiones del CEO (2026-10-21)

El **texto autoritativo** de las decisiones está en `docs/decisions/CEO-DEC-GOV-2026-10-21.md` (D1–D13). Ahí cada una figura como cita literal del CEO o como la pregunta, la opción elegida y la descripción que se le mostró. Este plan **no las resume**: las cita por número. Si este plan dice algo distinto de una cita, prevalece la cita, y el contenido del plan que no proceda de una cita es **propuesta**.

**Las decisiones D1–D13 no autorizan desplegar los mecanismos.** Esa autorización llega con la aprobación única de GOV-REV-002, que incluye el arranque (§6).

### 1.1 Corrección del alcance transitorio (H-05)

- **CEO-DEC-LOCAL-A no se amplía.** Hasta que se apruebe GOV-REV-002 cubre solo lo que ya cubría: Clase A reversible e inerte. Con D3, la integración pasa a hacerse en GitHub con las mismas condiciones y las mismas exclusiones.
- **Auditoría, gate, integrador, identidad y seguridad quedan fuera de la excepción.** Se desarrollan en PR, pero **no se fusionan** hasta el arranque del §6.
- **Caducidad:** la excepción termina el 2026-11-19 o al aprobarse GOV-REV-002, lo que ocurra antes.

---

## 2. Roles e identidades (H-02, H-07)

Hay cuatro cosas distintas que **no deben confundirse**:

1. el **proceso**, con su uid Unix y sus permisos;
2. el **actor** que firma o publica;
3. el **modelo** que razona;
4. la **autoridad** que valida.

Cambiar de modelo no aporta independencia. La independencia la aportan uids, claves y evidencias que el otro no puede tocar.

| Rol | Modelo | uid | Credencial | Puede | No puede |
|---|---|---|---|---|---|
| PM | Claude, instancia propia | `aao-pm` | token de solo lectura e issues | priorizar, hacer la clasificación **inicial**, asignar, redistribuir | **bajar** una clasificación, levantar vetos, fusionar, implementar |
| COO (funciones) | sin agente propio por ahora; las ejerce el PM bajo registro | — | — | recursos, cuotas, inventario de identidades | lo mismo que el PM |
| Implementador Codex | Codex | `aao-impl-codex` | token propio: ramas y PR | código, pruebas, PR | aprobar o fusionar; leer claves, ledger o política del auditor |
| Implementador Claude | Claude | `aao-impl-claude` | idem | idem | idem |
| Implementador Antigravity | Antigravity | `aao-impl-ag` | idem | idem | idem |
| Auditor principal | Claude aislado | `aao-auditor` | clave ed25519 en 0700 y ledger | dictamen firmado; **subir** la clasificación; vetar | auditar cambios de autoría Claude; editar candidatos |
| Auditor alterno | Codex aislado | `aao-auditor-alt` | **clave propia** | lo mismo; audita lo de autoría Claude y sustituye al principal | auditar cambios de autoría Codex |
| Integrador | script determinista | `aao-integrator` | solo merge, sin Administration (P2) | fusionar si se cumple el §5 | decidir; modificar políticas |
| Supervisor externo | script determinista | `aao-supervisor` | token de solo lectura | vigilar GitHub y el ledger y alertar (§5.3) | escribir en el repo |
| CEO | — | `alessbarb` | administración | R3, administración de GitHub, suspensión de emergencia | tareas operativas |

**Recusación:** un auditor queda recusado si su modelo o su uid coincide con el autor de cualquier commit del candidato, o si el candidato modifica su propio código, su clave o su política. En ese caso actúa el otro auditor. Si los dos están recusados (por ejemplo, un cambio que toca a ambos auditores), es R3.

Las funciones de COO no justifican hoy un agente propio, pero quedan nombradas para separarlas cuando haya un segundo proyecto.

---

## 3. Clases de riesgo y autoridad (H-01)

La clase se fija por la **dimensión más alta** de dos: el **impacto** (consecuencia y facilidad de recuperación) y la **autoridad** (qué controles o garantías toca).

| Clase | Contenido | Quién autoriza | Requisitos |
|---|---|---|---|
| R0 | Documentación y cambios inertes (sin código ejecutable en el gate o el runtime) | AAO | CI y un dictamen de cualquier auditor no recusado |
| R1 | Cambios ordinarios reversibles de producto o runtime | AAO | CI, dictamen firmado y pruebas sobre el árbol resultante |
| R2 | Seguridad, autenticación, identidad, auditoría, gate, integrador, supervisor, políticas efectivas del auditor, CI y workflows | AAO **solo** con independencia demostrada (tras F2) y un auditor no recusado | R1 más pruebas negativas, revisión del árbol completo afectado y dictamen del auditor que no sea del modelo autor |
| R3 | D6, Constitución, GOV-REV, raíz de confianza, cambios que recusan a ambos auditores | CEO | propuesta con recomendación, por D7 |

**Tres niveles normativos (V3-04):**

| Nivel | Ejemplos | Clase |
|---|---|---|
| Política normativa | Constitución, GOV-REV-002, competencias, garantías, lista de rutas R2, regla de recusación | R3 |
| Configuración técnica delegada | implementación de comprobaciones, parámetros operativos, umbrales que **no reducen** ninguna garantía normativa | R2 |
| Raíz de confianza | claves autorizadas, `trusted_auditor_revisions`, potestades y custodia | R3 |

Cuando un cambio de configuración técnica reduce de hecho una garantía normativa (menos comprobaciones, más tiempo de vigencia de los dictámenes, menos rutas protegidas), pasa a R3. En la duda, el auditor lo eleva.

**Reglas:**

- **Agregación causal (V3-08):** una serie de PR se clasifica también como conjunto. Si varias R1 dan en conjunto un efecto R2 o R3 (por ejemplo, retirar un control en varias PR), el conjunto toma esa clase. Se consideran relacionadas:
  - las PR que tocan los mismos módulos, sus importadores o las mismas rutas R2;
  - las que comparten tarea u objetivo en el PM;
  - las que dependen unas de otras.

  No hay límite temporal. Los 7 días son solo la ventana mínima de búsqueda automática.
- **Rutas R2 fijas:** una lista protegida, en la configuración del supervisor (no en el repo), eleva automáticamente la clase de cualquier PR que las toque. Rutas: `src/aao/independent_audit.py`, `manifest_audit.py`, el integrador, `.github/workflows/`, `policy*.json`, `docs/AUTONOMOUS_AUDIT_POLICY.md`, `docs/CONSTITUTION.md` y `docs/decisions/`.
- **Sentido único:** la clasificación sube sola. Para **bajarla** hace falta un dictamen del auditor no recusado.

---

## 4. Ciclo de vida del dictamen (H-09, H-10)

| Resultado | Efecto | Quién lo resuelve |
|---|---|---|
| `APPROVE` | Permite integrar si se cumple el §5 | — |
| `REJECT` | Devuelve el candidato al implementador | El implementador corrige y se audita de nuevo |
| `VETO` | Bloquea con motivo verificable (ruta, línea y prueba que lo reproduce) | Recurso ante el otro auditor no recusado; si es R3 o no hay otro, ante el CEO. **Ni el implementador, ni el integrador, ni el PM** pueden levantarlo |
| `INCONCLUSIVE` | No autoriza | Se audita de nuevo o se escala de clase |
| `EXPIRED` | Dictamen caducado (72 h, cambio de base o de política, auditor revocado) | Hay que renovarlo |

**Continuidad:**

- Si un auditor no responde en 24 h, el PM pasa la PR al auditor alterno, si no está recusado.
- Si no queda ninguno, la PR **se queda bloqueada** y el PM reasigna capacidad a otras tareas.
- **El vencimiento de un plazo nunca aprueba nada.**

---

## 5. Gate de integración (H-03, H-08, H-11)

### 5.1 Autorización de integración (sustituye al «veredicto»)

El auditor firma un documento JSON canónico con estos campos:

```
repo, pr_number, candidate_sha, base_sha, merge_result_tree_sha,
risk_class, policy_id, policy_sha256, auditor_id, auditor_key_id,
auditor_code_revision, checks_executed[{name, cmd, result, evidence_sha256}],
verdict, issued_at, expires_at
```

### 5.2 Lo que verifica el integrador (todo se cumple, o no fusiona)

1. La firma corresponde a una clave del **registro de confianza** (§5.4) y no está revocada.
2. `repo` y `pr_number` coinciden. `candidate_sha` es la cabeza actual de la PR.
3. `base_sha` es el `main` actual. Si `main` ha avanzado, se recalcula el árbol de fusión y, si el `tree_sha` cambia, el dictamen queda en `EXPIRED`.
4. El integrador calcula el árbol resultante localmente y comprueba que es igual a `merge_result_tree_sha`.
5. `policy_sha256` es la política vigente en el registro de confianza en la fecha `issued_at`.
6. El auditor está habilitado para `risk_class` y no está recusado según los autores de los commits.
7. `auditor_code_revision` figura en `trusted_auditor_revisions`.
8. Los `checks_executed` incluyen los controles obligatorios de la clase y sus evidencias existen con ese digest.
9. No hay veto en el ledger, ni suspensión, ni el dictamen ha caducado. Política, clave, auditor y revisión del auditor siguen vigentes **en el instante de fusionar**, no solo en `issued_at` (V3-06).
10. CI está en verde sobre `candidate_sha`.

**La fusión:**

- se hace con `--match-head-commit`;
- después se comprueba que el commit de fusión resultante tiene `tree == merge_result_tree_sha`.

**Prevención y contención (V3-07):**

- La fusión se hace con el árbol que el integrador ha **calculado y comprobado de antemano**. Dentro del rango de fusión solo se admite fast-forward o el commit de fusión que generó el propio integrador, así que no puede aparecer un árbol nuevo después.
- Si aun así el resultado diverge, el integrador:
  1. **congela** todas las integraciones;
  2. abre una PR de reversión;
  3. registra el incidente en el ledger.

  La reversión es R1 con prioridad y la audita el auditor no recusado. La congelación solo se levanta con un dictamen sobre la causa.

### 5.3 Supervisor externo

- Corre como `aao-supervisor`, por cron o systemd, **fuera del repo**: su código está en un checkout congelado y su configuración y credenciales no están en `main`.
- Cada 10 minutos lee la API de GitHub y contrasta cada commit de `main` con el ledger de autorizaciones.
- Alerta (Issue `governance-violation` y Control Center) en estos casos:
  - commit sin autorización válida;
  - fusión hecha por un actor distinto del integrador;
  - cambios en `.github/workflows/`;
  - `workflow` detectivo desactivado o sin ejecución en más de 1 h;
  - fallo del propio supervisor: si el supervisor no escribe su latido, el workflow en GitHub lo detecta. Se vigilan mutuamente, de forma cruzada.
- El workflow en el repo se mantiene como segunda capa, no como la única.
- **Publicación de alertas (V3-03).** El supervisor conserva el **solo lectura** en GitHub. Escribe eventos firmados en su canal append-only local. Un **notificador** separado (uid `aao-notifier`, token con solo `issues: write`) los publica como Issues y en Control Center. Si el notificador cae, los eventos quedan en el canal y se publican al volver.
- **Caída simultánea.** Si caen el supervisor y el workflow a la vez:
  - Control Center muestra en rojo la **antigüedad del último latido** de cada vigilante, una tercera observación que no depende de ninguno de los dos;
  - el integrador **se niega a fusionar** si el último latido del supervisor tiene más de 1 h. Sin vigilancia no hay integraciones.

  Riesgo residual registrado: si nadie mira Control Center, la caída solo se nota porque las integraciones se paran.

### 5.4 Fuentes de verdad (H-11)

| Fuente | Contiene | Custodia |
|---|---|---|
| GitHub | código, PR, issues, estado de integración | CEO (administración) |
| Ledger de auditoría | dictámenes, vetos, autorizaciones de integración, append-only, encadenados por hash | `aao-auditor` y `aao-auditor-alt` (solo añaden); el supervisor lee |
| Registro de confianza | claves públicas, `trusted_auditor_revisions`, política vigente con su hash, lista de rutas R2 y recusaciones | uid `aao-trust`, editable solo con decisión R3 o del arranque; los agentes solo leen |
| Control Center | interfaz | sin autoridad propia |

---

## 6. Arranque (bootstrap) único (H-04, H-12)

**Hecho:** ningún sistema puede certificar su propia creación. El arranque es necesariamente una aceptación de riesgo **R3** por parte del CEO, una sola vez, dentro de la aprobación de GOV-REV-002. Después se extingue.

1. **Inventario previo (antes del arranque).** Ficha de riesgo por cada PR histórica:
   - #10 `c08a640`
   - #11 `8a4fca1`
   - #14 `681f40c` (auditor)
   - #15 `83230f3`
   - #19 `3a84ff5` (auditor)
   - #20 `5d8cc89`
   - #21 `ddd520f`

   Ninguna se convalida. #14 y #19 reciben evaluación reforzada.
2. **Componentes de arranque, con SHAs fijados:** auditor, integrador, supervisor, registro de confianza y GOV-REV-002.
3. **Revisión:**
   - el auditor alterno (Codex, `aao-auditor-alt`) revisa lo escrito por Claude, y viceversa;
   - pruebas negativas completas (§8) en un repo desechable;
   - Claude queda recusado sobre el auditor que escribió.
4. **Control externo disponible:** solo P4 (revisor humano externo, con gasto). Si el CEO no lo aprueba, el arranque se registra con «independencia de la raíz no demostrada por un tercero».
5. **Autoriza:** el CEO, en la aprobación de GOV-REV-002 (R3).
6. **Operaciones expresamente incluidas en la autorización de arranque (V3-02):**
   - fusionar la PR de F0 (registro literal de D1–D13, inventario y estatuto del PM);
   - fusionar GOV-REV-002;
   - fusionar los componentes del punto 2, con sus SHAs;
   - instalar el registro de confianza.

   Nada más. No es una excepción genérica.
7. **Extinción:** la excepción de arranque termina en el momento en que el registro de confianza contiene la primera revisión de confianza y el integrador hace su primera fusión R1 válida. No es reutilizable. Cualquier cambio posterior a la raíz es R3.

---

## 7. Fases ejecutables

| Fase | Contenido | Depende de | Responsable | Salida verificable | ¿Bloquea al resto? |
|---|---|---|---|---|---|
| **F0** | Una PR con tres partes: el registro literal de D1–D13, el inventario de riesgo histórico (§6.1) y el estatuto del PM provisional. **Se abre, pero no se fusiona** (V3-02): toca `docs/decisions/`, una ruta R2/R3, y queda pendiente hasta la autorización de arranque (§6.6). El PM provisional coordina desde F0. | — | Claude-impl (PR) y PM | PR abierta, con un dictamen de fidelidad de Codex | No |
| **F1** | Redactar GOV-REV-002: §2–§6, §8 y los tres niveles normativos del §3. Evaluar alternativas de GitHub para P3 (permisos efectivos, coste, mantenimiento, privacidad; preferencia por mantenerlo privado). | F0 abierta | PM y auditor de diseño (Codex) | Issue `ceo-proposal` con la política, el arranque y la recomendación | No |
| **F2** | Script de separación: uids del §2, claves, `aao-trust`, sockets, directorios, `$HOME`, SSH y tokens, unidades systemd de lanzamiento. Pruebas de aislamiento. | F0 | Claude-impl escribe; el auditor alterno revisa; **CEO ejecuta sudo** (P1) | Matriz de aislamiento en PASS (§8.1) | Solo R2 |
| **F3a** | **Construcción** (V3-01): autorización de integración, integrador, supervisor, notificador y ledger encadenado. Se prueban en un repo desechable con §8.2. Las PR se abren pero no se fusionan. | F1 (contrato) | Codex implementa; revisa el auditor no recusado | §8.2 en PASS en el entorno desechable, con SHAs fijados | Solo R2 |
| **F3b** | Auditoría de arranque de los componentes de F3a, en sus revisiones exactas, y propuesta P5 al CEO | F2 en PASS y F3a | auditores, cruzados | expediente de arranque | Solo R2 |
| **F4** | **Activación:** con P5 aprobada, se fusionan las operaciones del §6.6, se instala la raíz y se hace la primera integración R1 por el integrador. La excepción de arranque se extingue. | P5 aprobada por el CEO | integrador y PM | raíz registrada, primera fusión válida, excepción extinguida | — |
| **F5** | Piloto: 3 PR R1 reales sin el CEO, **más 1 PR R2 controlada** (V3-09), reversible, sin efectos externos y sin tocar la raíz ni nada R3, con revisión reforzada. Más los simulacros del §8.3. | F4 | PM | §8.3 | — |
| **F6** | Operación: auditoría histórica completa, deuda (P11-4, P1/P2 de #15, C-1 a C-6), vista de propuestas en Control Center, métricas | F5 | PM y COO; Antigravity | métricas publicadas | — |

**Durante F0–F3 sigue el trabajo** que cumpla las **condiciones originales** de CEO-DEC-LOCAL-A, que caduca el 19-nov. R0/R1 **no equivalen** a Clase A: solo se fusiona lo que cumple la Clase A al pie de la letra, con sus exclusiones. Si GOV-REV-002 no está aprobada el **2026-11-12**, el PM escala una sola vez con una recomendación. Nunca se vuelve a la fusión manual silenciosa.

**Propuestas al CEO (no bloqueantes):**

| ID | Propuesta |
|---|---|
| P1 | Ejecutar el script de F2 |
| P2 | GitHub Apps: integrador (solo merge) y supervisor (solo lectura); tokens fine-grained por implementador, sin Administration |
| P3 | Protección preventiva de `main`, con una evaluación de alternativas, no una elección ya resuelta |
| P4 | Revisor humano externo para la raíz (gasto) |
| P5 | Aprobar GOV-REV-002, incluido el arranque |

---

## 8. Criterios de aceptación

### 8.1 Aislamiento (F2)

Se ejecuta desde la ruta real de lanzamiento de cada agente.

- Un implementador **no** puede:
  - leer las claves del auditor;
  - escribir en el ledger o en `aao-trust`;
  - usar `docker` o `sudo -n`;
  - leer el `$HOME` de otro uid;
  - usar el token del integrador.
- El integrador no tiene el permiso Administration en GitHub (tras P2; antes, riesgo registrado).
- **Aislamiento entre auditores (V3-05):** el auditor principal y el alterno no comparten `$HOME`, venv, caché de dependencias, directorio temporal, socket ni clave. Ninguno de los dos puede escribir en el checkout congelado del otro.
- El supervisor y el notificador no pueden escribir en el repo, y el notificador no puede leer el canal de firma del supervisor más allá de los eventos.

### 8.2 Integridad del gate (F4)

Cada caso debe ser **rechazado**:

- firma válida pero con otra política;
- auditor recusado;
- `base_sha` antigua con árbol distinto;
- `tree` distinto;
- PR o repo distinto;
- dictamen caducado o con veto;
- controles obligatorios ausentes;
- clave revocada;
- serie de R1 que en conjunto es R2 sin dictamen R2.

### 8.3 Operación (F5)

- **Autonomía:** 3 ciclos completos sin ninguna acción operativa del CEO.
- **Evasión:**
  - un push directo genera una alerta en menos de 15 min;
  - desactivar el workflow genera una alerta del supervisor;
  - detener el supervisor genera una alerta del workflow.
- **Continuidad:** con el auditor principal caído, una PR R1 se integra con el alterno y otra queda bloqueada sin parar el resto del trabajo.
- **Recuperación:** una integración irregular simulada se identifica, se contiene y se revierte sin perder evidencia.

---

## 9. Riesgos residuales hasta completar cada fase

| Riesgo | Hasta | Aceptado por |
|---|---|---|
| Agentes con el uid y el `docker` del CEO; independencia no demostrada | F2 | AAO, solo para R0/R1. Lo R2 no se fusiona |
| Token de administrador en uso; control de `main` solo detectivo | P2 y P3 | AAO (R1) |
| Raíz de confianza sin tercero humano | P4 o permanente | CEO en el arranque (R3) |
| Funciones de COO ejercidas por el PM | segundo proyecto | AAO |

---

## 10. Trazabilidad de los hallazgos de la auditoría del v2

| Hallazgo | Tratamiento |
|---|---|
| H-01 | §3: R0–R3, dos dimensiones, regla de agregación, rutas R2 fijas |
| H-02 | §2: separación de proceso, actor, modelo y autoridad; un uid por implementador; claves distintas por auditor |
| H-03 | §5.1–5.2: autorización de integración con 10 comprobaciones y verificación del árbol tras la fusión |
| H-04 | §6: arranque R3 único, extinción definida |
| H-05 | §1.1: la Clase A no se amplía; R2 no se fusiona hasta F3 |
| H-06 | §2, F2, §8.1 |
| H-07 | §2: el PM solo sube la clasificación, no levanta vetos; funciones de COO nombradas |
| H-08 | §5.3: supervisor externo con vigilancia cruzada |
| H-09 | §4: cinco estados, motivo verificable y vía de recurso |
| H-10 | §4: auditor alterno; el vencimiento nunca aprueba |
| H-11 | §5.4: cuatro fuentes de verdad |
| H-12 | §6.1: inventario previo al arranque |
| P3 | F1: evaluación de alternativas; no hacer público por defecto |

**Matices respecto a la auditoría:**

1. **COO.** No creo un agente COO ahora. Con un solo proyecto sería otro agente que mantener sin uso. Nombro sus funciones para separarlas cuando haya un segundo proyecto.
2. **Arranque.** La auditoría pide un «auditor independiente habilitado» para el arranque, pero no puede existir antes de la raíz de confianza. Lo honesto es declararlo **R3 del CEO una sola vez**, con P4 como única vía para que lo valide un tercero.
3. **Hecho no verificado.** He comprobado que en el plan privado gratuito no hay protección de rama (en las sesiones anteriores hubo un 403). Los detalles de planes que cita la auditoría no los he comprobado. F1 los evalúa.

## 11. Trazabilidad de la revisión del v3

| Hallazgo | Tratamiento |
|---|---|
| V3-01 | F3a (construcción en entorno desechable) separada de F4 (activación tras P5) |
| V3-02 | La PR de F0 se abre sin fusionar; su fusión figura en la lista cerrada del §6.6 |
| V3-03 | §5.3: supervisor de solo lectura, eventos firmados y notificador con `issues: write`; caída simultánea cubierta por latidos e integrador que se niega a fusionar |
| V3-04 | §3: tres niveles (política normativa R3, configuración técnica R2, raíz de confianza R3) |
| V3-05 | §8.1: aislamiento entre auditores |
| V3-06 | §5.2.9: vigencia comprobada también al fusionar |
| V3-07 | §5.2: árbol fijado antes de fusionar; congelación y reversión ante divergencia |
| V3-08 | §3: agregación causal, no solo temporal |
| V3-09 | F5: piloto R2 controlado |
| §7 | R0/R1 no equivalen a Clase A |

## Informe (AGENTS.md)

- **Alcance:** plan v3; sin cambios en el repo.
- **Revisión:** `ddd520f`.
- **Acciones:** redacción del plan a partir del v2 y de la auditoría.
- **Evidencia y límites:**
  - no he verificado los planes de GitHub;
  - no he probado que las CLI de los agentes funcionen bajo otros uids.
- **Bloqueos:** ninguno para F0 y F1.
- **Autoridad:** D1–D13.
- **Siguiente:** F0. Claude-impl abre la PR con D1–D13 y el inventario; el PM provisional arranca F1.
