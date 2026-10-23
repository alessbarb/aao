# GOV-REV-002: política permanente de gobierno autónomo del repositorio AAO

**Versión:** 0.3 (borrador F1, revisado tras el `REJECT` de diseño de la ronda 2: GR-08; GR-02 y GR-03 parciales; GR-09)
**Estado:** BORRADOR. **No está vigente.** Solo entra en vigor si el CEO aprueba la propuesta P5 sobre el SHA exacto de este documento. El SHA se asignará cuando se abra la PR.
**Redacta:** agente PM provisional (estatuto provisional en `432f7a8:docs/PM_AGENT_CHARTER.md`; D10a, D10e). El PM no implementa, no audita, no fusiona y no modifica archivos del repositorio. Las propuestas y recomendaciones del PM no son decisiones del CEO ni autoridad vigente.
**Versiones anteriores:**
- 0.1, SHA-256 `92fd808aed3e113b2f124f4b74826ae11f0a3a1674b53bf06bb35a5706af2d9f`, dictamen `VETO` de Codex (`codex_design_gov_rev_002.md`);
- 0.2, SHA-256 `325d989de2c69317f702563f30fbc62a0d6e2382c4f0417c1fc0f086b3b601c3`, dictamen `REJECT` de Codex (`codex_design_gov_rev_002_r2.md`).

**Base de redacción:**
- `main` en `ddd520f58613564dbc6460949e2dea8e78b75517`;
- plan de gobierno v3.1 en `432f7a8:docs/AUTONOMOUS_GOVERNANCE_PLAN.md`;
- GOV-REV-001 v1.1;
- CEO-DEC-LOCAL-A-2026-10-20;
- **decisiones D1–D13** (incluidas D2-bis, D7-bis y D10a–D10e), adoptadas por el CEO el 2026-10-21. Su texto autoritativo es `432f7a8:docs/decisions/CEO-DEC-GOV-2026-10-21.md` (estado de registro en §0).

**Sustituye a:** CEO-DEC-LOCAL-A-2026-10-20, en los términos del §13.
**Complementa a:** GOV-REV-001 v1.1. No lo modifica ni lo debilita (§1.3).

---

## 0. Estado de las decisiones citadas

Este documento distingue cuatro categorías. Ninguna se presenta como otra.

| Categoría | Contenido | Estado |
|---|---|---|
| **Decisión CEO adoptada** | D1–D13 (D1, D2, D2-bis, D3–D7, D7-bis, D8, D9, D10a–D10e, D11, D12, D13) | Adoptadas por el CEO en la conversación de gobierno del 2026-10-21. Vinculan a los agentes desde su adopción. **Su texto autoritativo es la cita literal** del registro `CEO-DEC-GOV-2026-10-21.md`; este documento no las resume. Si este documento dice algo distinto de una cita, prevalece la cita. |
| **Registro en `main`** | Registro literal de D1–D13, inventario histórico y estatuto del PM | **Pendiente.** Están en la PR #22, en borrador y sin fusionar, con cabeza `432f7a8c96276c497e98eb8674ae732547d84a41`. Codex emitió en la ronda 5 un dictamen de fidelidad `APPROVE-TECHNICAL` sobre ese SHA, con el límite que el propio dictamen declara: «dictamen de fidelidad técnica documental, no una auditoría independiente ni aceptación de la PR». Su fusión figura en la lista cerrada del §12.3. |
| **Propuesta del PM** | Todo lo que este documento marca como *Propuesta del PM* o *Recomendación del PM*, las *lecturas del PM* sobre cómo encajan las decisiones, y el texto de esta política mientras no se apruebe P5 | No es decisión ni autoridad. |
| **Decisión CEO pendiente** | Dentro de P5: (a) custodia de `aao-trust` (§4.2) y (b) caducidad del arranque (§12.4.3). Fuera de P5: P1–P4 (§13.8, §12.2.5) | Pendientes. (a) y (b) se someten a aprobación expresa dentro de P5. P1–P4 se deciden aparte. |

**Evidencia primaria de D1–D13:** el registro bruto de la conversación de gobierno, `~/.claude/projects/-home-alessbarb-workspace-repos-active-aao/4119b041-a09a-4426-beca-9f143e6ead15.jsonl`. Se citan hashes por línea y no del archivo, porque el archivo sigue creciendo. El PM recalculó el 2026-10-21 los hashes de las líneas 191, 200, 206 y 562, y coinciden con los de v0.2.

| Línea | uuid | Marca de tiempo (UTC) | SHA-256 de la línea | Contenido |
|---|---|---|---|---|
| 176 | `59318250-e425-4233-8344-95ef4981ecfe` | 2026-10-21T07:57:08.894Z | `a2ee51c058e92058dfd2ae6fe8afa3983df58b23be7d50cd1c647fb692755063` | Correcciones del CEO al plan (base de D1, D3 y D4) |
| 191 | `a4c4c31a-015d-4a56-b8ae-4fb86549b74a` | 2026-10-21T08:00:43.591Z | `91b93df83c14091510d82e3b7a4966cd32e8507c1c69e6d96fd44defee67b448` | Respuestas del CEO (base de D2-bis, D5, D9 y **D11**) |
| 200 | `b0d55f39-13a6-41a6-8867-53f70e3344e0` | 2026-10-21T08:03:51.380Z | `afd13673fc3c9a238b12b757a744523e27573e6da9e18e9fbff284b7f73d11d3` | Respuestas del CEO (base de D7, D8 y **D13**) |
| 206 | `6ea52064-96a0-4c7a-8584-25d77d5c4e36` | 2026-10-21T08:09:27.827Z | `f3d6e30ba6519342ddb38aabf14fd314bfc042521c1d3fd6dce7a5eaec0e54f2` | Respuestas del CEO (base de D6, D7-bis, D10 y **D12**) |
| 216 | `f6cbc7b4-af25-41cc-a2ac-17588d2da014` | 2026-10-21T08:10:14.106Z | `6217a6ddbe89107c97e022cd7ba0dad65f92b598d612b6e9c5e50546223bcdce` | Respuestas del CEO (roles de PM, integrador y auditores; base de D10) |
| 562 | `c8f39888-e9bb-4031-bef9-dfb5acb5bf6b` | 2026-10-21T08:44:41.881Z | `2f9e14a9ce953a147ff4e4392c4574dbf44b0aedb9c56aa9f1999170b11f4bdb` | El CEO deja (a) y (b) pendientes de su aprobación expresa dentro de P5 |

*La correspondencia de cada D con cada línea es una lectura del PM, que localizó cada decisión buscando en el archivo la opción elegida. La fidelidad de la transcripción es objeto del dictamen de fidelidad de la PR #22.*

**Limitación de esa evidencia (se mantiene tras fusionar #22):**
1. El registro bruto es local, está bajo el mismo uid que usan los agentes y el CEO, y **no está firmado**. Un revisor puede reproducir las citas sobre ese archivo, pero no se puede acreditar ante terceros que no se haya alterado (registro CEO, sección «Límites»).
2. Fusionar la PR #22 **publica la transcripción** en `main`, en un SHA exacto. **No autentica técnicamente** las decisiones ni el registro bruto. Los mecanismos usan como referencia la transcripción en `main`, que no es una prueba criptográfica de que el autor sea el CEO.
3. D1–D13 vinculan a los agentes como decisiones del CEO desde su adopción.
4. **Ningún mecanismo técnico** (registro de confianza, integrador, supervisor) puede fundarse en D1–D13 ni en la custodia propuesta hasta que su registro conste en `main`. Ese registro debe estar vinculado a un SHA exacto y contener una referencia verificable a la resolución, a la identidad del aprobador, al alcance y al SHA aprobado. Esa referencia tiene la limitación del punto 2.

### 0.1 Coherencia con D11–D13

D11–D13 son disposiciones **provisionales** que regulan tres cosas:
- el control de `main`;
- quién fusiona mientras no existan las GitHub Apps;
- quién hace la segunda línea sobre el auditor.

Esta política las incorpora como sigue. La columna «Lectura del PM» es una propuesta; si contradice la cita, prevalece la cita.

| Decisión | Elemento de la cita literal | Dónde se aplica | Lectura del PM |
|---|---|---|---|
| **D11** | «Solo fusiona una identidad integradora (GitHub App).» | §4.2 (integrador), §6.3.9, §13.8 (P2) | La GitHub App integradora es administración de GitHub (D4) y se propone en P2. Mientras no exista, rige D12. |
| **D11** | «Un workflow revisa cada push a main y abre incidencia si falta el veredicto del auditor.» | §7.2, §7.4.5 | Es el control **detectivo** de `main`. El supervisor es una segunda capa. Ninguno de los dos es preventivo. |
| **D11** | «Se te propone una protección que lo impida: Pro, o repo público.» | §13.8 (P3) | La protección preventiva es una **propuesta** al CEO (P3) y no bloquea (D4). Esta política no elige entre Pro y repositorio público. |
| **D12** | «Un único agente designado fusiona solo si hay veredicto del auditor sobre el SHA exacto.» | §4.2, §6.2, §12.3 | El agente designado es el integrador (D10b: script determinista). D12 fija **quién** fusiona. **Qué** se fusiona lo fija el régimen vigente (§13). D12 no amplía la Clase A ni la lista cerrada del §12.3. |
| **D12** | «El control detectivo vigila main.» | §7 | Igual que D11. |
| **D12** | «Riesgo: el token tiene permisos de administrador, y queda registrado.» | §6.3.8, §13.8, §14 | Hasta P2, el integrador publica con el token actual. GitHub atribuye esas publicaciones a la cuenta del CEO, de modo que el principal de GitHub **no distingue** al integrador de otros usos del mismo token. La identidad publicadora autorizada se acredita con la autorización firmada del ledger y con el proceso del integrador, no con el principal de GitHub. El riesgo consta en el §14. |
| **D13** | «Codex u otro modelo con credenciales, usuario y evidencias separadas. Sin coste.» | §4.2 (auditor alterno), §9 | Codex, como `aao-auditor-alt`, hace la segunda línea sobre el código del auditor escrito por Claude. Hasta que F2 esté en PASS, ese usuario y esas credenciales separadas **no existen**, y el aislamiento no está demostrado. |
| **D13** | «Más débil que un revisor humano externo, y se registra como tal.» | §9.3, §14 | Se registra literalmente. |

---

## 1. Propósito y autoridad

### 1.1 Propósito

Esta política permite que AAO desarrolle, revise, integre y publique su propio código sin que el CEO intervenga en la operación (D1, D2). La autonomía es una delegación expresa de riesgo hasta un umbral escrito (D2-bis) y cubre las clases R0–R2. Las materias de D6, y todo lo que supere el umbral, se proponen al CEO.

**Principio rector:** no se declara autonomía ni independencia antes de probar el mecanismo que las hace efectivas. Mientras falte esa prueba, se aplica el régimen transitorio (§13). **Especificar un requisito no demuestra que se cumpla** (§16.0).

### 1.2 Autoridad

1. Esta política solo tiene autoridad si el CEO aprueba expresamente la propuesta P5 (R3).
   - P5 aprueba **solo** el texto y las operaciones expresamente enumeradas en su resolución.
   - No ratifica automáticamente decisiones separadas ni otorga permisos que no describa.
   - **P5 no certifica independencia ni satisface por sí sola ningún gate técnico** (§12.1).
2. D1–D13 son decisiones del CEO adoptadas el 2026-10-21 y la base de esta política (§0). Su registro en `main` está pendiente (PR #22 en `432f7a8c96276c497e98eb8674ae732547d84a41`). Hasta que conste, rigen las reglas del §0 sobre su uso por mecanismos técnicos.
3. `docs/CONSTITUTION.md` es una interpretación técnica en borrador que el CEO no ha confirmado. Esta política se alinea con ella, en especial con sus puntos 3, 6, 9 y 10, pero no la cita como mandato confirmado ni la confirma.
4. Ningún agente, componente o documento puede ampliar esta política, interpretarla a su favor ni suspenderla. Modificarla es R3 (§15).

### 1.3 Relación con GOV-REV-001 (cláusula de no debilitamiento)

1. **Acumulación.** Cada cambio recibe dos clasificaciones a la vez:
   - su clase de riesgo y autoridad R0–R3, según esta política;
   - su nivel de aseguramiento A–D, según GOV-REV-001.

   Se aplican los requisitos de ambas. Si discrepan, **prevalece el más estricto**.
2. Los niveles B, C y D de GOV-REV-001 siguen rigiéndose por GOV-REV-001 y por D6. Esta política no autoriza runtime controlado, despliegue operativo ni efectos externos.
3. Se mantienen íntegras estas reglas de GOV-REV-001:
   - congelar el SHA;
   - definir el comportamiento revisado, las amenazas y los límites antes de evaluar;
   - denegar ante hallazgos críticos;
   - verificar de nuevo tras corregir;
   - registrar el dictamen completo;
   - prohibir que nadie amplíe sus propios poderes.
4. **Nada de esto prueba por sí solo la independencia funcional:** el CI en verde, los prompts separados, los proveedores de modelo distintos, los hashes, una firma de informe o una aceptación de riesgo. La independencia solo se acredita con dos cosas:
   - uids, claves y evidencias que la otra parte no puede alterar;
   - pruebas de aislamiento en PASS (plan v3.1, §8.1).
5. Si una verificación humana es obligatoria por ley, por contrato o por una reserva específica, esta política no la dispensa.
6. Si una disposición de esta política admite una lectura que reduce una garantía de GOV-REV-001, se aplica la lectura que la conserva.

---

## 2. Tres niveles normativos

| Nivel | Contenido | Clase mínima de cualquier cambio | Custodia |
|---|---|---|---|
| **Política normativa** | Constitución, GOV-REV-001 y GOV-REV-002; competencias de los roles; garantías del gate; regla de recusación; **lista normativa de rutas protegidas y sus clases mínimas** (§3.4); clases y sus requisitos | **R3** | Repositorio (`docs/`) |
| **Configuración técnica delegada** | Implementación de las comprobaciones; parámetros operativos (plazos, intervalos, umbrales); protecciones técnicas adicionales que no alteran la clasificación (§3.4.4); código del auditor, el integrador, el supervisor y el notificador | **R2** | Repositorio y configuración del supervisor |
| **Raíz de confianza** | Claves públicas autorizadas, `trusted_auditor_revisions`, hash de la política vigente, **copia material de la lista normativa aprobada y su hash**, habilitaciones por clase | **R3** | Registro de confianza (uid `aao-trust`; custodia en el §4.2) |

**El registro de confianza no crea política.** Solo conserva copias materiales y hashes de lo aprobado como política normativa. No puede crear ni alterar la lista de rutas protegidas ni ninguna otra regla.

**Regla de reducción de garantías.** Un cambio de configuración técnica que, de hecho, reduce una garantía normativa pasa a **R3**, sea cual sea su forma. Ejemplos:
- menos comprobaciones;
- más plazo de vigencia para los dictámenes;
- una ventana de búsqueda de agregación más corta;
- menos rutas protegidas;
- una vigilancia menos frecuente;
- un umbral de latido más permisivo;
- tolerar skips.

En caso de duda, el auditor no recusado eleva la clase.

---

## 3. Clases de riesgo y autoridad R0–R3

### 3.1 Criterio

La clase la fija la **mayor** de estas dos dimensiones:
- el **impacto**: la consecuencia y la facilidad de recuperación;
- la **autoridad**: los controles, garantías o potestades que toca el cambio.

### 3.2 Clases

| Clase | Contenido | Quién autoriza | Requisitos mínimos |
|---|---|---|---|
| **R0** | Documentación y cambios inertes, sin código ejecutable en el gate ni en el runtime, que no tocan rutas protegidas | AAO | CI en verde y dictamen `APPROVE` de un auditor no recusado |
| **R1** | Cambios ordinarios y reversibles de producto o runtime, sin efectos externos | AAO | Lo de R0, más un dictamen firmado y pruebas reproducibles sobre el árbol resultante, vinculadas a los SHA exactos |
| **R2** | Seguridad, autenticación y autorización, identidad, secretos, auditoría, ledger, veto, gate, integrador, supervisor, notificador, configuración técnica delegada, CI y workflows | AAO, **solo** con la autonomía R2 activada (§12.5) | Lo de R1, más pruebas negativas, revisión de todo el árbol afectado (importadores incluidos) y dictamen de un auditor no recusado cuyo modelo sea distinto del modelo del autor |
| **R3** | Materias de D6 (efectos externos o producción, Constitución y políticas, datos sensibles reales, proveedores de modelo nuevos), política normativa, raíz de confianza, cambios que recusan a ambos auditores y arranque | **CEO** | Propuesta con recomendación por el canal D7/D7-bis, escalada una sola vez |

*Asignar materias concretas a R0–R2 es una propuesta del plan y del PM (registro CEO, «Lo que este registro NO hace»). Solo vincula si P5 la aprueba.*

### 3.3 Reglas de elevación

1. **Sentido único.** El PM propone la clase en la clasificación inicial.
   - El PM, el auditor o el supervisor pueden **subirla** en cualquier momento.
   - Para **bajarla** hace falta un dictamen motivado de un auditor no recusado. Ni el PM ni el implementador pueden bajarla.
2. **Cambio mixto.** Un cambio que mezcla clases toma la más alta. No se puede fragmentar para eludir controles.
3. **Duda.** Si la clasificación es dudosa, se aplica la clase superior.
4. **Falsa clasificación.** Clasificar a sabiendas un cambio por debajo de su clase es motivo de `VETO` y se registra como incidente en el ledger.

### 3.4 Rutas protegidas

1. **Naturaleza y ubicación.**
   - La lista canónica de rutas protegidas y sus clases mínimas son **política normativa R3** y están en este documento (§3.4.3).
   - Cualquier alta, baja, cambio de patrón, de clase mínima o de interpretación requiere **R3**.
   - El registro de confianza solo conserva una copia material de la lista aprobada y su hash. No puede crear ni alterar la política.
   - El supervisor y el integrador trabajan con una copia operativa. Antes de cada uso comprueban que la lista normativa, la copia del registro de confianza y la copia operativa coinciden por hash.
   - **Ante cualquier discrepancia, el gate falla cerrado:** el integrador no fusiona y el supervisor emite una alerta.
2. **Efecto.** Si una PR toca una ruta protegida, su clase sube automáticamente al mínimo de esa ruta.
3. **Lista inicial:**

| Clase mínima | Rutas | Origen |
|---|---|---|
| **R3** | `docs/CONSTITUTION.md`, `docs/AUTONOMOUS_AUDIT_POLICY.md`, el documento GOV-REV-002 y `docs/decisions/` | Plan v3.1, §3. Elevarlas a R3 es una **propuesta del PM**, coherente con el §2. Solo rige si P5 la aprueba expresamente |
| **R3** | Contenido del registro de confianza | Plan v3.1, §5.4 |
| **R2** | `src/aao/independent_audit.py`, `src/aao/manifest_audit.py`, el integrador, `.github/workflows/` y `policy*.json` | Plan v3.1, §3 |
| **R2** | `src/aao/policy.py` (los gates de operaciones reservadas que cita la Constitución) | **Propuesta del PM**. Solo rige si P5 la aprueba expresamente |
| **R2** | Código del supervisor, del notificador y de la herramienta del registro de confianza | **Propuesta del PM**. Solo rige si P5 la aprueba expresamente |
| **R2** | `AGENTS.md` y `docs/AGENT_OPERATING_RULES.md` | **Propuesta del PM**. Solo rige si P5 la aprueba expresamente |

4. **Protecciones técnicas adicionales (R2).** Un cambio de configuración R2 solo puede añadir una protección si se cumplen estas tres condiciones:
   - no cambia la lista normativa ni su copia en el registro de confianza;
   - no altera el resultado de clasificación de ninguna PR;
   - no crea un requisito de gate distinto.

   Cualquier otra cosa es R3. Ningún cambio R2 puede reducir protecciones ni cambiar la clasificación derivada.

### 3.5 Agregación causal

1. Una serie de PR se clasifica también **como conjunto**. Si varias PR de clase inferior producen juntas un efecto R2 o R3, el conjunto toma esa clase; por ejemplo, retirar un control repartiéndolo entre varias PR. En ese caso, la PR que completa el efecto necesita el dictamen de la clase del conjunto antes de integrarse.
2. Se consideran relacionadas las PR que cumplen alguna de estas condiciones:
   - tocan los mismos módulos, sus importadores o las mismas rutas protegidas;
   - comparten tarea u objetivo en el backlog del PM;
   - dependen unas de otras.
3. **No hay límite temporal.** La ventana de 7 días es solo la búsqueda automática mínima. El auditor puede buscar fuera de ella, y debe hacerlo si sospecha.

---

## 4. Roles, identidades y recusación

### 4.1 Distinciones

Hay que distinguir cuatro cosas:
- el **proceso**: el uid Unix y sus permisos;
- el **actor**: quien firma o publica;
- el **modelo**: quien razona;
- la **autoridad**: quien valida.

Cambiar de modelo no aporta independencia.

### 4.2 Roles

| Rol | uid | Credencial | Puede | No puede |
|---|---|---|---|---|
| PM (con funciones de COO, bajo registro; **propuesta no activa hasta P5**) | `aao-pm` | Lectura e issues | Con respaldo del CEO (D10a, D10e): priorizar, planificar y clasificar inicialmente. **Propuesto, activo solo tras P5:** subir la clase; congelar el SHA al pedir auditoría; asignar y reasignar auditores con efecto vinculante; redistribuir capacidad; escalar R3 una vez con recomendación | Implementar, auditar, fusionar, bajar la clase, levantar vetos, asumir gasto, ejecutar sudo, administrar GitHub |
| Implementadores (Codex, Claude, Antigravity; D10d) | `aao-impl-codex`, `aao-impl-claude`, `aao-impl-ag` | Token propio: ramas y PR | Escribir código y pruebas, preparar el plan de reversión, abrir PR | Aprobar; fusionar; leer claves, el ledger o el registro de confianza; modificar candidatos congelados ajenos |
| Auditor principal (Claude aislado; D10c) | `aao-auditor` | Clave ed25519 propia (permisos 0700). Solo puede **añadir** entradas firmadas al ledger | Dictaminar, firmar, subir la clase, bajarla de forma motivada, vetar | Auditar cambios de autoría Claude; editar candidatos; editar el registro de confianza; reescribir o truncar el ledger |
| Auditor alterno (Codex aislado; D10c, D13) | `aao-auditor-alt` | Clave propia distinta; usuario y evidencias separados (D13) | Lo mismo que el principal. Además audita los cambios de autoría Claude, sustituye al principal y hace la segunda línea sobre el código del auditor (§9) | Auditar cambios de autoría Codex |
| Integrador (script determinista; D10b; agente designado de D12) | `aao-integrator` | **Hasta P2:** el token actual, con permisos de administrador (D12; riesgo en el §14). **Tras P2:** GitHub App integradora con solo merge, sin el permiso Administration (D11) | Fusionar si se cumplen todas las comprobaciones del §6 | Decidir, interpretar o modificar políticas; usar el token para cualquier otra operación |
| Supervisor (script determinista) | `aao-supervisor` | Solo lectura en GitHub; canal local append-only y firmado | Vigilar y emitir eventos firmados (§7) | Escribir en el repositorio o en GitHub |
| Notificador | `aao-notifier` | Solo `issues: write` | Publicar los eventos del supervisor | Escribir código o leer algo distinto de los eventos |
| Custodio de la raíz | `aao-trust` | — | Contener el registro de confianza | Ser modificado sin una decisión R3 o de arranque |
| CEO | `alessbarb` | Administración de GitHub (D4) | R3, administración, suspensión y revocación de emergencia | — (D1: no hace tareas operativas) |

**Los uids de esta tabla aún no existen.** Los crea el script de separación de F2 (PR #23; §13.8, P1). Hasta que F2 esté en PASS, todos los agentes comparten uid y credenciales con el CEO.

**Custodia de `aao-trust` y ejecución de sus cambios. [DECISIÓN CEO PENDIENTE (a); se somete a aprobación expresa en P5]**
- *Texto propuesto:* «Solo el CEO ejecuta los cambios materiales del registro de confianza, mediante una operación sudo sobre un artefacto preparado y auditado. Ningún agente tiene credenciales de escritura sobre `aao-trust`.»
- *Coste:* una acción del CEO por cada cambio de la raíz. Esos cambios ya son R3 de todos modos.
- *Efecto de no decidir:* no se instala el registro de confianza (§12.3.1), no se activa el integrador y continúa el régimen transitorio (§13).
- *Alternativa:* otra forma de custodia, que requeriría una nueva propuesta R3.

### 4.3 Recusación

1. Un auditor queda recusado en cualquiera de estos casos:
   - su modelo o su uid coinciden con los del autor de **cualquier** commit del candidato;
   - el candidato modifica su propio código, su clave, su política efectiva o su habilitación;
   - participó en el diseño o la implementación del componente auditado.
2. **Fuentes de atribución (requisito).** La recusación se calcula con identidades obtenidas de fuentes autenticadas que el implementador no controla:
   1. El uid efectivo, comprobado por el proceso aislado y vinculado a una identidad de agente autorizada.
   2. El principal de push y los eventos de GitHub, obtenidos por API con una credencial de lectura independiente y vinculados a cada actualización de ref o de PR. **Mientras rija D12 y todos los agentes usen el token actual, el principal de GitHub es el mismo para todos y no distingue actores.** Esta fuente solo distingue actores tras P2.
   3. Atestaciones de commits, **solo** cuando la clave de firma está vinculada al principal en el registro de confianza y la firma se verifica.
   4. Los eventos de merge y los check runs obtenidos de GitHub, con `app_id`, identidad de la App, SHA del head y conclusión. Un check run prueba qué identidad o App publicó un resultado para qué SHA. **No** prueba que el contenido del check sea independiente.
3. **No son prueba suficiente:**
   - los metadatos `author` y `committer` de Git;
   - trailers como `Co-Authored-By`;
   - el campo `producer` de un manifiesto;
   - los nombres de usuario declarados por el cliente;
   - un `implementer_id` pasado por el llamador;
   - un ledger que el propio actor puede editar.

   Estos datos **solo pueden añadir** causas de recusación, nunca descartarlas.
4. **Si una atribución no puede resolverse, el resultado es `INCONCLUSIVE`, no `APPROVE`.**
5. **Estado actual del código.** Procede del dictamen de diseño GR-02 sobre `ddd520f`; el PM no lo ha verificado de forma independiente.
   - `independent_audit.py` recibe el implementador del llamador, y su ledger es una cadena hash sin clave.
   - `manifest_audit.py` deriva `implementer_ids` de `manifest["producer"]` y de los autores de los commits.
   - `pr_conformity.py` compara el `implementer_id` recibido sin verificar su origen.

   El código actual **no acredita técnicamente la identidad de cada actor**.
6. **Este apartado es un requisito de aceptación pendiente (RA-02, §16.0), no una garantía.** Mientras RA-02 no esté en PASS, ningún dictamen, integración ni activación puede apoyarse en que la atribución esté acreditada.
7. El dictamen de un auditor recusado es nulo.
8. Si los dos auditores están recusados, la materia es **R3**.
9. El PM no puede clasificar ni coordinar en solitario un cambio de su propio estatuto o de sus competencias. Ese cambio es política normativa (R3).

---

## 5. Ciclo de vida del dictamen

### 5.1 Precondiciones

Antes de evaluar resultados, se fija y se registra lo siguiente:
- `target_ref`, `candidate_sha`, `base_sha` y el árbol resultante;
- la clase y el nivel de aseguramiento;
- el comportamiento revisado, las amenazas y los límites de operación (GOV-REV-001, paso 2).

Sin estas precondiciones no se emite dictamen.

### 5.2 Estados

| Resultado | Efecto | Resolución |
|---|---|---|
| `APPROVE` | Habilita la integración si se cumple el §6 | — |
| `REJECT` | Devuelve el candidato al implementador | Se corrige, se congela un SHA nuevo y se vuelve a auditar lo cambiado y los contratos afectados |
| `VETO` | Bloquea (§5.2.1) | Solo se levanta por recurso (§5.4). **Ni el implementador, ni el integrador, ni el PM** pueden levantarlo |
| `INCONCLUSIVE` | No autoriza | Nueva auditoría o elevación de clase |
| `EXPIRED` | Dictamen caducado: han pasado 72 h desde `issued_at`, o han cambiado el árbol resultante, `base_sha`, el head de la PR o la política, o se han revocado la clave, el auditor o su revisión | Hay que renovarlo |

#### 5.2.1 Requisitos del `VETO`

1. Un `VETO` debe identificar:
   - el requisito o límite normativo o arquitectónico incumplido;
   - la afirmación falsable;
   - el alcance afectado;
   - la evidencia mínima verificable;
   - un procedimiento reproducible para confirmarlo o refutarlo.
2. La evidencia puede ser una línea de código, una secuencia de estados, una traza, una configuración efectiva, un modelo de amenazas, una prueba negativa o una demostración de flujo de autoridad. **Si la propiedad es sistémica, no se exige una línea.**
3. El auditor debe explicar por qué la evidencia acredita el incumplimiento. Una preferencia de diseño sin un defecto reproducible no es motivo de veto.
4. Un veto sin evidencia suficiente puede convertirse en `INCONCLUSIVE` al resolver el recurso. Nunca habilita la promoción.

### 5.3 Contenido mínimo del dictamen

El dictamen es un documento JSON canónico y firmado. Incluye los campos del §6.1 y, además, los que exige el paso 7 de GOV-REV-001:
- `scope`;
- `known_limitations`;
- `residual_risks`;
- `permitted_operations` y `prohibited_operations`;
- `assurance_level`;
- `findings[]`, con la disposición de cada hallazgo;
- `expediente_sha256`.

Un dictamen al que le falte cualquiera de estos campos no es válido.

### 5.4 Recurso

1. **Contra un `VETO`.** Lo evalúa un revisor no recusado: el otro auditor, o el CEO por D7/D7-bis si la materia es R3 o no queda otro auditor no recusado. El revisor reproduce o refuta el procedimiento del veto y emite una disposición motivada.
   - **El veto se mantiene hasta que se resuelva el recurso.**
   - El ledger conserva el veto original, la evidencia, la reproducción y el resultado.
2. **Contra la clasificación.** El implementador o el PM pueden pedir que se baje la clase. Solo la baja un dictamen motivado de un auditor no recusado. Si la discrepancia es entre R2 y R3, decide el CEO por D7/D7-bis.
3. **Contra un `REJECT`.** No hay recurso: se corrige y se vuelve a auditar. Si el implementador cree que el rechazo es erróneo, puede pedir una vez una nueva auditoría al otro auditor no recusado. El primer dictamen se conserva en el ledger.
4. Que venza un plazo nunca convierte un recurso en `APPROVE`.

### 5.5 Continuidad

1. Si un auditor no responde en 24 h, el PM reasigna la PR al otro auditor, siempre que no esté recusado.
2. Si no queda ningún auditor disponible y no recusado, la PR **queda bloqueada** y el PM dedica la capacidad a otras tareas.
3. **El vencimiento de un plazo nunca aprueba nada**: ni en el dictamen, ni en el recurso, ni en la escalada al CEO.

---

## 6. Autorización de integración

### 6.1 Documento firmado

```
repo, pr_number, target_ref, candidate_sha, base_sha, merge_result_tree_sha,
merge_method, expected_parents[], git_version,
risk_class, assurance_level, policy_id, policy_sha256, protected_paths_sha256,
auditor_id, auditor_key_id, auditor_code_revision,
attribution[{sha, principal, source, evidence_sha256}],
checks_executed[{name, cmd, result, evidence_sha256}],
scope, known_limitations, residual_risks,
permitted_operations, prohibited_operations,
findings[{id, severity, disposition}], expediente_sha256,
verdict, issued_at, expires_at
```

`merge_method` es `merge-commit`, `squash` o `fast-forward`. La configuración técnica (R2) admite uno solo de esos métodos y fija también la versión de Git y el tratamiento de conflictos: un conflicto aborta la operación y no hay resolución automática.

### 6.2 Comprobaciones del integrador

El integrador solo fusiona si se cumplen todas estas comprobaciones:

1. La firma corresponde a una clave del registro de confianza, y esa clave no está revocada.
2. `repo`, `pr_number` y `target_ref` coinciden con la PR, y `candidate_sha` es su cabeza actual según una instantánea autenticada de GitHub.
3. `base_sha` es el valor actual de `target_ref`. Si ha cambiado, el integrador aborta y el dictamen pasa a `EXPIRED`.
4. El árbol resultante, calculado localmente por el integrador con la versión de Git fijada en `git_version`, es igual a `merge_result_tree_sha`.
5. `policy_sha256` corresponde a la política vigente según el registro de confianza.
6. El auditor está habilitado para `risk_class` y no está recusado según las fuentes del §4.3.2, que el integrador consulta por sí mismo.
   - En R2, además, el modelo del auditor es distinto del modelo del autor.
   - Una atribución no resuelta impide fusionar.
7. `auditor_code_revision` figura en `trusted_auditor_revisions`.
8. `checks_executed` incluye los controles obligatorios de la clase, y la evidencia de cada uno existe con su digest. El expediente existe y su digest es `expediente_sha256`.
9. No hay veto en el ledger ni suspensión, y el dictamen no ha caducado. La política, la clave, el auditor y la revisión del auditor siguen vigentes **en el momento de fusionar**, no solo en `issued_at`.
10. El CI está en verde sobre `candidate_sha`, según check runs publicados para ese SHA por una identidad o App autorizada (§4.3.2.4).
11. La lista normativa de rutas protegidas, su copia en el registro de confianza y la copia operativa coinciden por hash con `protected_paths_sha256` (§3.4.1). La clase cubre la agregación causal (§3.5).
12. El último latido del supervisor es válido según el §7.4.
13. **Hay evidencia PASS de RA-03 y RA-09 (§16.0) para la configuración efectiva:** el servidor, el repositorio, la protección de rama y la credencial con la que va a publicar. Si esa evidencia no existe o no corresponde a la configuración actual, el integrador no fusiona.

### 6.3 Promoción: contrato de política fail-closed

**Naturaleza de este apartado.** El §6.3 es un **contrato de política**: fija lo que debe cumplir la promoción y dispone que, si no puede cumplirse o demostrarse, no se publica.
- **No afirma que la promoción atómica esté garantizada.**
- La atomicidad solo podrá afirmarse con evidencia del comportamiento del servidor y de la configuración reales (RA-09, §16.0), obtenida en F3a y repetida en F4.
- No bastan una simulación del integrador ni una prueba contra otro servidor Git.

1. **Instantánea.** El integrador obtiene una instantánea autenticada de la PR y de `target_ref`, y ejecuta las comprobaciones del §6.2.
2. **Construcción.** Crea localmente el commit de promoción según `merge_method`:
   - con padres exactamente iguales a `expected_parents[]` (por ejemplo, `[base_sha, candidate_sha]` en `merge-commit`);
   - con árbol `merge_result_tree_sha`. Si el árbol no coincide, rechaza.
3. **Revalidación.** Inmediatamente antes de publicar, vuelve a comprobar que el head de la PR es `candidate_sha` y que `target_ref` es `base_sha`.
4. **Publicación condicionada (requisito).** `refs/heads/main` **en GitHub** solo se actualiza mediante una operación que **el servidor** rechace si `main` ya no es `base_sha`.
   - *Mecanismo candidato, no verificado:* `git push --atomic --force-with-lease=refs/heads/main:<base_sha>`. **No está demostrado** que el servidor de GitHub aplique esa comprobación del valor anterior con la credencial efectiva (el token actual bajo D12, o la App tras P2) y con la protección de rama vigente. Es objeto de RA-09.
   - Un `git update-ref` local no publica nada y no sustituye a esta operación.
   - No se asume que un endpoint o una opción de GitHub llamados «merge» ofrezcan esta atomicidad si no se ha demostrado.
   - **Fail-closed.** El integrador **no publica** en cualquiera de estos casos:
     - no hay evidencia PASS de RA-09 para la configuración efectiva;
     - la configuración ha cambiado después de obtener esa evidencia;
     - el servidor devuelve un resultado ambiguo.

     No hay mecanismo alternativo ni fallback.
5. **Si cualquiera de los refs ha cambiado,** el integrador aborta sin tocar `main`, recalcula y exige una autorización vigente para el nuevo estado. **No se permite fallback manual.**
6. **Ventana residual del head de la PR.**
   - En la vía de publicación por push condicionado no hay CAS sobre el head de la PR.
   - El parámetro `sha` del endpoint de merge de GitHub (y `gh pr merge --match-head-commit`) sí lo ofrece. Pero ese endpoint no fija `base_sha` ni el árbol resultante, por lo que no se usa para promocionar.
   - El contenido promovido queda fijado por `candidate_sha` en los padres del commit. Si el head cambia entre la revalidación y la publicación, el árbol promovido no varía, pero la PR no queda cerrada correctamente.
   - Esa divergencia se detecta en la verificación posterior y es un incidente. **Es una divergencia residual conocida y se acepta solo como riesgo detectivo** (§14).
7. **Verificación posterior.** Tras publicar, el integrador comprueba el SHA promovido, su árbol, sus padres y el estado de la PR. Una discrepancia es un **incidente, no una integración válida**, y tiene estos efectos:
   1. se congelan todas las integraciones;
   2. se abre una PR de reversión;
   3. se registra el incidente en el ledger.

   La reversión es R1 con prioridad y la audita un auditor no recusado. La congelación solo se levanta con un dictamen sobre la causa.
8. **Validez de la promoción.** No se acepta como promoción ningún commit con un árbol distinto, ni ningún commit con el árbol autorizado pero con padres, método o identidad publicadora no autorizados.
   - **Mientras rija D12**, la identidad publicadora en GitHub es la del token actual, que también se usa para otras cosas (§0.1).
   - Por eso la validez se comprueba contra la autorización firmada en el ledger y contra el registro del integrador. Esa limitación consta en el §14.
9. Una fusión hecha por cualquier actor distinto del integrador es una violación de gobierno (§7.2), aunque el contenido sea correcto. **No se convalida a posteriori.**
10. **Dependencia de P2/P3.** Si una protección de rama futura impide la publicación condicionada por parte del integrador, el integrador no fusiona. La configuración se propone al CEO (D4) y no se busca otra vía. Cualquier cambio de credencial o de protección invalida la evidencia RA-09 anterior y obliga a repetirla.
11. **Este apartado es un requisito de aceptación pendiente (RA-03 y RA-09, §16.0), no una garantía.**

---

## 7. Supervisor y notificador

### 7.1 Ubicación

El supervisor se ejecuta como `aao-supervisor`, **fuera del repositorio**:
- su código está en un checkout congelado, con la revisión registrada;
- su configuración y sus credenciales no están en `main`;
- en GitHub solo tiene permiso de lectura.

### 7.2 Vigilancia

Cada 10 minutos, el supervisor contrasta cada commit de `main` con el ledger de autorizaciones. Emite un evento firmado en estos casos:
- un commit sin autorización válida;
- una fusión hecha por un actor distinto del integrador;
- un cambio en `.github/workflows/`;
- un workflow detectivo desactivado o que lleva más de 1 h sin ejecutarse;
- una discrepancia entre los hashes de la lista de rutas (§3.4.1);
- un fallo de su propio latido.

El control detectivo de D11 es el workflow del repositorio, que revisa cada push a `main` y abre una incidencia si falta el veredicto del auditor (§7.4.5). El supervisor es una segunda capa, fuera del repositorio. **Ninguno de los dos impide un push; solo lo detectan.**

### 7.3 Publicación

1. El supervisor escribe los eventos firmados en su canal local append-only.
2. El notificador (`aao-notifier`, solo `issues: write`) los publica como Issue `governance-violation` y en Control Center.
3. Si el notificador cae, los eventos se conservan en el canal y se publican cuando vuelva.

### 7.4 Latidos y vigilancia cruzada

1. **Los latidos acreditan disponibilidad, no la integridad de la vigilancia.** Un latido firmado acredita que una clave lo emitió, no que el supervisor haya observado todas las fusiones.
2. Cada latido incluye:
   - la autenticación del emisor (firma con una clave registrada en el registro de confianza);
   - un contador de secuencia monótono, contra la repetición;
   - una marca de tiempo de emisión y una expiración.
3. **Quién verifica.** El integrador verifica cada latido por sí mismo antes de fusionar (§6.2.12), con su propia lectura de la fuente y su propio reloj, sin depender de lo que muestre Control Center. La configuración técnica (R2) fija la fuente de tiempo y de recepción. Mientras no se demuestre que es independiente de los actores supervisados, se registra como limitación.
4. **Bloquean la integración:** la falta de latido, una antigüedad superior a 1 h, una secuencia repetida o una firma inválida.
5. Los vigilantes se controlan entre sí:
   - el workflow del repositorio (control detectivo de D11) detecta si falta el latido del supervisor;
   - el supervisor detecta si el workflow deja de ejecutarse.

   El workflow está en el repositorio que vigila: es una capa detectiva, no una garantía preventiva.
6. Control Center muestra la antigüedad del último latido de cada vigilante. **Es una interfaz sin autoridad**, no una observación independiente.
7. **La independencia de la vigilancia no se declara demostrada** hasta probar que la credencial y el proceso que verifican al supervisor no están bajo el control de los actores supervisados (F2 en PASS y pruebas del §16).

### 7.5 Respuesta a una alerta

Ante una alerta `governance-violation`:
1. el integrador congela las integraciones;
2. el PM abre la contención con una PR de reversión R1 con prioridad;
3. un auditor no recusado dictamina la causa.

Si la causa es una acción del CEO o de su credencial de administración, se informa al CEO por D7/D7-bis y no se revierte nada sin su decisión. **Mientras rija D12**, el integrador y el CEO usan el mismo token. El supervisor no puede distinguirlos por el principal de GitHub, así que clasifica la causa según haya o no en el ledger una autorización firmada para el integrador.

---

## 8. Fuentes de verdad

| Fuente | Contenido | Custodia |
|---|---|---|
| GitHub (maestro; D3) | Código, PR, issues, eventos de push y merge, check runs, estado de integración | CEO (administración; D4) |
| Ledger de auditoría | Dictámenes, vetos, recursos, autorizaciones e incidentes, en modo append-only, encadenados por hash y **con cada entrada firmada por su emisor** | Custodia efectivamente independiente de los auditores, el integrador y los implementadores. Los auditores solo pueden añadir; nadie puede reescribir ni truncar. El supervisor y el integrador leen y verifican la cadena y las firmas |
| Registro de confianza | Claves públicas, `trusted_auditor_revisions`, hash de la política vigente, copia de la lista normativa de rutas y su hash, habilitaciones | `aao-trust`. Solo cambia por R3 o en el arranque (§4.2) |
| Control Center | Interfaz | Sin autoridad propia |

1. «Append-only» solo es una garantía si quien escribe no puede reescribir ni truncar. Un tercero dentro del sistema debe poder verificar la integridad y la autenticidad del ledger. No basta una cadena hash sin clave custodiada por quien escribe. **Requisito de aceptación pendiente** (parte de RA-02, §16.0).
2. Los eventos de GitHub relevantes para la atribución (§4.3.2) se conservan o se consultan en la fuente autenticada.
3. Si GitHub y el ledger no coinciden, ninguno prevalece: el ledger no legitima lo que muestra GitHub, y GitHub no prueba la autorización. La discrepancia es un incidente.

---

## 9. Segunda línea sobre el auditor

1. Conforme a GOV-REV-001 (Gobierno), D10c y D13, el código y la política efectiva del auditor pasan una revisión de segunda línea:
   - la del código del auditor escrito por Claude la hace **otro proveedor aislado** (hoy Codex, como `aao-auditor-alt`), «con credenciales, usuario y evidencias separadas. Sin coste.» (D13);
   - nunca la hacen el propio componente revisado ni su autor;
   - se hace en cada cambio R2 sobre el auditor y, como mínimo, cada 90 días. *El plazo es una propuesta del PM y un parámetro R2; alargarlo es R3.*
2. Un cambio que afecta a los dos auditores es R3 (§4.3.8).
3. **Registro literal (D13):** esta segunda línea es «Más débil que un revisor humano externo, y se registra como tal.» No sustituye a P4 ni a ninguna verificación humana obligatoria (§1.3.5).
4. Mientras F2 no esté en PASS, no existen el «usuario y evidencias separadas» que exige D13: Codex comparte uid y credenciales con el autor. Todo dictamen de segunda línea anterior a F2 lleva la mención «Independencia de auditoría no demostrada; revisor y autor comparten uid y credenciales.»

---

## 10. Escalada al CEO

1. Al CEO solo se le escalan materias R3, una sola vez, con recomendación y por Control Center (D7). Mientras esa vista no exista, se usa un Issue de GitHub con la etiqueta `ceo-proposal` (D7-bis).
2. **No se escalan** las tareas ordinarias, las revisiones de PR, la publicación de PR (D1), la planificación ni los bloqueos técnicos que tengan una alternativa autorizada.
3. Las necesidades de administración de GitHub (D4) y de gasto (D5) se proponen al CEO y no bloquean el resto del trabajo.
4. La suspensión y la revocación de emergencia por parte del CEO no dependen de los agentes y prevalecen sobre cualquier estado del gate (Constitución, punto 10; GOV-REV-001).

---

## 11. Continuidad

1. **Auditor caído:** se aplica el §5.5. El trabajo que no depende de esa PR continúa.
2. **Integrador caído:** no se integra nada y **ninguna fusión manual lo sustituye**. El PM dedica la capacidad a otras tareas. Reparar el integrador es R2.
3. **Supervisor caído:** se aplica el §7.4. El integrador se detiene cuando el latido deja de ser válido.
4. **Ledger o registro de confianza no disponibles, o con la cadena de hashes o las firmas rotas:** no se integra nada y se abre un incidente. Reparar el ledger es R2; reparar la raíz es R3.
5. **Pérdida de la clave de un auditor:** se revoca la clave en el registro de confianza (R3). Mientras tanto se integra con el otro auditor, dentro de su habilitación.
6. Un bloqueo nunca da autoridad para eludir la identidad, la auditoría, el veto, el aislamiento ni el gate (AGENTS.md, regla 6).

---

## 12. Arranque único

### 12.1 Naturaleza y alcance

1. Ningún sistema puede certificar su propia creación. Por eso el arranque es una aceptación de riesgo **R3** por parte del CEO:
   - se concede una sola vez, dentro de la aprobación de P5;
   - después se extingue;
   - **no es una excepción genérica.**
2. **La aprobación de P5 solo autoriza las operaciones de arranque enumeradas en el §12.3. No certifica independencia ni satisface por sí sola los gates técnicos.**
3. Cada operación del §12.3 se ejecuta solo cuando su evidencia exigida en el §12.2 está en PASS. Si falta, la operación no se ejecuta y continúa el régimen transitorio (§13).
4. Toda aceptación de riesgo residual se limita a riesgos delegables. **No dispensa** requisitos constitucionales, el veto ni la evidencia obligatoria de GOV-REV-001, ni permite promover con defectos críticos.

### 12.2 Requisitos previos

1. **Inventario histórico.** Cada PR integrada sin una auditoría válida tiene una ficha de riesgo (`432f7a8:docs/HISTORICAL_INTEGRATION_INVENTORY.md`):
   - #10 `c08a640`;
   - #11 `8a4fca1`;
   - #14 `681f40c`: código del auditor, con evaluación reforzada;
   - #15 `83230f3`;
   - #19 `3a84ff5`: código del auditor, con evaluación reforzada;
   - #20 `5d8cc89`;
   - #21 `ddd520f`.

   **Ninguna se convalida.**
2. **Componentes de arranque, con sus SHA fijados:** auditor, integrador, supervisor, notificador, registro de confianza y GOV-REV-002.
3. **Revisión cruzada.** El auditor alterno (Codex) revisa lo que escribió Claude, y a la inversa. Claude queda recusado respecto del auditor que escribió (D10c, D13).
4. **Pruebas en PASS, con evidencia vinculada a SHA:**
   - la matriz de aislamiento de F2 (plan v3.1, §8.1), ejecutada en la máquina objetivo con el verificador de la PR #23 después de P1;
   - las pruebas de integridad del gate (plan v3.1, §8.2);
   - los requisitos de aceptación RA-01, RA-02, RA-03, RA-07 y RA-09 (§16.0) y sus pruebas negativas (§16.1 a §16.5), en F3a y otra vez en F4.
5. **Control externo. [DECISIÓN CEO PENDIENTE: P4, con gasto (D5), fuera de P5]**
   - *Recomendación del PM:* no condicionar el arranque a P4.
   - Sin P4, el arranque se registra con esta mención literal: «independencia de la raíz no demostrada por un tercero». Esa mención **no** sustituye ninguna de las pruebas del §12.2.4.

### 12.3 Lista cerrada de operaciones autorizadas

La autorización de arranque cubre **solo** las operaciones siguientes, en este orden y cada una condicionada a sus requisitos del §12.2. La lista coincide con el plan v3.1, §6.6.

1. **Instalar el registro de confianza** con su contenido inicial auditado, conforme a la custodia aprobada en P5 (§4.2, decisión (a)).
2. **Fusionar la PR #22 de F0 en su SHA exacto `432f7a8c96276c497e98eb8674ae732547d84a41`, y solo con ese contenido.**
   - *Contenido autorizado:* el diff `ddd520f58613564dbc6460949e2dea8e78b75517..432f7a8c96276c497e98eb8674ae732547d84a41`, formado por cinco archivos:
     - `docs/decisions/CEO-DEC-GOV-2026-10-21.md` (registro literal de D1–D13);
     - `docs/HISTORICAL_INTEGRATION_INVENTORY.md`;
     - `…/20261021-historical-inventory/gh_pr_view.json` (evidencia del inventario);
     - `docs/PM_AGENT_CHARTER.md`;
     - `docs/AUTONOMOUS_GOVERNANCE_PLAN.md`.
   - *Base de fidelidad:* el dictamen `APPROVE-TECHNICAL` de Codex en la ronda 5 sobre ese SHA. Es un dictamen de fidelidad documental. **No es un dictamen de integración del §6.1** ni una auditoría independiente. La fusión exige además una autorización de integración firmada para ese SHA, conforme al §6.
   - *Fuera de la autorización:*
     - cualquier otro SHA de la rama;
     - cualquier rebase, amend o squash que cambie el contenido;
     - cualquier archivo distinto de esos cinco.

     Si la rama avanza, la operación 2 no cubre el nuevo SHA y hace falta una nueva propuesta.
   - *Límite que se mantiene:* la fusión publica la transcripción, pero no autentica el registro bruto (§0).
3. **Fusionar GOV-REV-002** en el SHA aprobado en P5.
4. **Fusionar los componentes del §12.2.2** en sus SHA fijados.

**Ejecutor.** Las operaciones 2 a 4 las ejecuta el integrador, que es el agente designado de D12, con estas condiciones:
- trabaja desde un checkout congelado y auditado de su SHA fijado, fuera del repositorio (como el supervisor, §7.1);
- el supervisor está en marcha desde su propio checkout congelado;
- hasta P2 publica con el token actual (D12; riesgo en el §14);
- cada operación cumple íntegramente el §6.2 y el §6.3 contra el registro de confianza instalado en la operación 1, incluida la evidencia RA-09 de la configuración efectiva.

No hay fusión manual ni excepción al §6.3.9. Si alguna condición no puede cumplirse, la operación no se ejecuta.

**Nada más.** Cualquier SHA distinto del aprobado queda fuera de la autorización y necesita una nueva propuesta. En particular, **la fusión de la PR #23 (script de F2) no está en esta lista**: sigue el régimen ordinario (§13.5).

### 12.4 Extinción

1. La autorización de arranque se extingue cuando se cumplen las dos condiciones siguientes:
   - el registro de confianza contiene su primera revisión de confianza;
   - el integrador ha hecho su primera fusión R1 válida.
2. La autorización no puede reutilizarse. Cualquier cambio posterior en la raíz es R3.
3. **Caducidad sin uso. [DECISIÓN CEO PENDIENTE (b); se somete a aprobación expresa en P5]**
   - *Texto propuesto:* «Si F4 no se completa en 30 días naturales desde la aprobación de P5, la autorización de arranque caduca, sin prórroga automática, y hace falta una nueva P5.»
   - *Efecto de no decidir:* P5 no puede aprobarse completa. Sin un plazo fijado no hay autorización de arranque.

### 12.5 Activación de la autonomía R2

1. La autonomía R2 **no** se activa con P5 ni con la extinción del arranque.
2. Solo se activa con evidencia PASS, vinculada a SHA, de todo lo siguiente:
   - aislamiento (F2; plan v3.1, §8.1);
   - atribución de actores y ledger independiente (RA-02);
   - promoción con árbol autorizado (RA-03) y comportamiento del servidor en la configuración real (RA-09);
   - pruebas del integrador (plan v3.1, §8.2);
   - las demás precondiciones aplicables de GOV-REV-001.
3. Si falta cualquiera de ellas, solo se puede continuar bajo el régimen que ya tenga autoridad (§13) y no se fusiona nada R2.

---

## 13. Régimen transitorio

1. **La Clase A no se amplía.** Hasta que se apruebe P5, CEO-DEC-LOCAL-A-2026-10-20 cubre solo lo que ya cubría: cambios de Clase A, reversibles e inertes.
   - Siguen vigentes todas sus condiciones, sus exclusiones absolutas y su mención literal.
   - Por D3, la integración se hace en GitHub, con las mismas condiciones.
   - **R0 y R1 no equivalen a la Clase A.**
   - D12 fija quién fusiona, pero no amplía qué se fusiona.
2. **Lo que queda fuera de la excepción** puede desarrollarse en PR, pero **no se fusiona**, salvo lo incluido en la lista cerrada del §12.3 y en sus condiciones. Queda fuera, en particular:
   - auditoría, gate, integrador y supervisor;
   - identidad y seguridad (incluido el script de F2 de la PR #23);
   - registro de confianza;
   - `docs/decisions/`.
3. **Fin de la Clase A.** La excepción termina en la primera de estas dos fechas: el 2026-11-19 a las 00:00 (Europe/Madrid) o la aprobación de P5 (D8).
4. **Entre P5 y F4.** Desde la aprobación de P5 hasta la primera fusión R1 válida del integrador, **solo** se integran las operaciones del §12.3.
5. **R2 antes de su activación.** Mientras no se cumpla el §12.5, no se fusiona ningún cambio R2, aunque P5 ya esté aprobada. La única excepción es el §12.3.
6. **Escalada por plazo.** Si GOV-REV-002 no está aprobada el 2026-11-12, el PM escala una sola vez, con recomendación.
7. **Vacío.** Si la Clase A caduca sin que se haya aprobado P5, no se integra nada. **Nunca se vuelve a la fusión manual silenciosa.**
8. **Decisiones CEO pendientes P1–P3 (fuera de P5) y riesgos mientras no se tomen:**
   - **P1 [DECISIÓN CEO PENDIENTE]:** ejecutar con sudo el script de separación de F2. D9 fija el medio: «Script único que ejecutas tú».
     - *Artefacto:* la PR #23, en borrador y sin fusionar, con cabeza `68bfa715a8931cf86a4cc25a1259f431fd6313ae` («script de separación de identidades y verificador de aislamiento (F2 / P1)»). Ha recibido dos `REJECT` de Codex, corregidos en `0dc67e3` y `68bfa71`. El PM no tiene registrado ningún dictamen posterior.
     - *Estado:* **F2 no está en PASS.** El script no se ha ejecutado en la máquina objetivo. La matriz de aislamiento solo puede pasar a PASS después de ejecutar P1 y de ejecutar el verificador bajo cada uid.
     - *Condición propuesta:* P1 se ejecuta sobre un SHA exacto de la PR #23 que haya superado la revisión cruzada sin ningún `REJECT` ni `VETO` pendiente.
     - Sin P1 no hay independencia demostrada y, por tanto, no hay R2.
   - **P2 [DECISIÓN CEO PENDIENTE]:** configurar las GitHub Apps y los tokens (D4, D11).
     - GitHub App integradora con solo merge (D11), supervisor con solo lectura y notificador con `issues: write`.
     - Tokens fine-grained para cada implementador, sin el permiso Administration.
     - Hasta P2 rige D12: el integrador fusiona con el token actual. «Riesgo: el token tiene permisos de administrador, y queda registrado» (§14). Cualquier cambio de credencial obliga a repetir RA-09.
   - **P3 [DECISIÓN CEO PENDIENTE]:** proteger `main` de forma preventiva.
     - D11 ya prevé que se proponga «una protección que lo impida: Pro, o repo público».
     - Las alternativas se evalúan en F1, sin dar la elección por resuelta.
     - Hasta P3, el control de `main` es solo detectivo (D11).

   *Recomendación del PM:* aprobar P1 antes de F3b. P2 y P3 se tratan por separado, como propuestas que no bloquean (D4).

---

## 14. Riesgos residuales

| Riesgo | Hasta | Quién lo acepta |
|---|---|---|
| Los agentes comparten el uid y `docker` con el CEO; la independencia no está demostrada | F2 en PASS (P1, PR #23) | AAO, solo dentro de la Clase A transitoria. Lo R2 no se fusiona |
| El código actual no acredita la identidad de cada actor (§4.3.5) | RA-02 en PASS (F3a, F4) | Nadie: bloquea R2 y la instalación del integrador |
| El ledger no tiene custodia independiente ni firma por entrada | RA-02 en PASS y F2 | Nadie: bloquea R2 |
| La atomicidad de la promoción no está demostrada en el servidor y la configuración reales (§6.3.4) | RA-09 en PASS en F4 | Nadie: sin esa evidencia, el integrador no publica (fail-closed) |
| Sin CAS sobre el head de la PR en la vía de push condicionado; ventana residual detectiva (§6.3.6) | Mientras el método de promoción sea el push condicionado | AAO, con detección e incidente |
| No está demostrado que la fuente de tiempo de los latidos sea independiente (§7.4.3) | F2 y §16 | AAO, registrado como limitación; no sustituye al §12.5 |
| **D12:** el integrador fusiona con el token actual. «Riesgo: el token tiene permisos de administrador, y queda registrado.» El principal de GitHub no distingue al integrador del CEO ni de otros agentes | P2 | **CEO**, por D12 (decisión adoptada) |
| **D11:** el control de `main` es solo detectivo; un push no autorizado no se impide, solo se detecta | P3 | **CEO**, por D11 (decisión adoptada) |
| **D13:** la segunda línea sobre el auditor la hace otro proveedor aislado y es «Más débil que un revisor humano externo, y se registra como tal.» | P4, o de forma permanente | **CEO**, por D13 (decisión adoptada) |
| La raíz de confianza no tiene un tercero humano | P4, o de forma permanente | CEO, en el arranque (R3), sin dispensar el §12.2.4 |
| Solo hay auditores de dos modelos; si ambos están recusados, decide el CEO | Hasta que haya un tercer auditor | CEO (R3), en P5 |
| Si nadie mira Control Center, la caída de los vigilantes solo se nota porque las integraciones se detienen | Permanente | AAO |
| El PM ejerce las funciones de COO (propuesta no activa hasta P5) | Hasta que haya un segundo proyecto | AAO, si P5 lo aprueba |
| D1–D13 solo constan en un registro bruto local **no firmado**. La fusión de #22 publica la transcripción pero no la autentica | Permanente para el registro bruto. La transcripción consta en `main` tras el §12.3.2 | Nadie. Ningún mecanismo técnico se funda en D1–D13 antes del §12.3.2; después se fundan en la transcripción, con esta limitación (§0) |
| Integraciones históricas #10–#21 sin auditoría válida | Auditoría histórica (F6) | Nadie: quedan inventariadas, sin convalidar |

---

## 15. Vigencia y modificación

1. **Entrada en vigor.** Cuando el CEO apruebe la propuesta P5 sobre el SHA exacto de este documento. La operación plena depende además de F4 (§13.4) y, para R2, del §12.5.
2. **Duración.** Indefinida, hasta que el CEO la modifique o la revoque.
3. **Modificación.** Es R3 cualquier cambio en este documento, en la política normativa (incluida la lista de rutas protegidas) o en la raíz de confianza. Los parámetros técnicos son R2, siempre que no reduzcan ninguna garantía (§2).
4. **Revocación.** El CEO puede suspender o revocar esta política en cualquier momento. La suspensión congela el integrador de inmediato.
5. **Interpretación.** En caso de conflicto, el orden de prevalencia es este:
   1. la Constitución, en lo que el CEO haya confirmado;
   2. las decisiones del CEO, en su cita literal (D1–D13);
   3. GOV-REV-001;
   4. GOV-REV-002;
   5. la configuración técnica.

   Siempre se elige la lectura que conserva la garantía más estricta.

---

## 16. Requisitos de aceptación pendientes y pruebas negativas (F3a y F4)

### 16.0 Requisitos de aceptación pendientes

**Estado de todos: PENDIENTE.** Que esta política especifique un requisito **no** demuestra que exista un mecanismo que lo cumpla. Ningún requisito de esta tabla se presenta como garantía. El PM los fija, pero no los ejecuta ni los certifica.

| ID | Requisito | Origen | Se cierra con | Fase | Mientras esté pendiente |
|---|---|---|---|---|---|
| RA-01 | Rutas protegidas: la lista es R3 y cualquier discrepancia falla cerrado | GR-01, §3.4 | §16.1 en PASS | F3a, F4 | El integrador no se instala |
| **RA-02** | Atribución autenticada de cada actor (§4.3.2 a §4.3.4) y ledger con firma por entrada y custodia independiente (§8) | GR-02 | Implementación en el auditor, el integrador y el ledger; §16.2 en PASS; F2 en PASS | F3a, F4 | Toda atribución se trata como no resuelta (`INCONCLUSIVE`). No hay R2 ni integrador |
| **RA-03** | Promoción con método, padres, árbol e identidad autorizados; revalidación; verificación posterior; ventana residual del head solo detectiva (§6.3) | GR-03 | §16.3 en PASS | F3a, F4 | El integrador no publica |
| RA-07 | Latidos autenticados, con anti-repetición y expiración, verificados por el integrador | GR-07, §7.4 | §16.4 en PASS | F3a, F4 | El integrador no publica |
| **RA-09** | El servidor de GitHub rechaza la actualización de `main` si su valor no es `base_sha`, **con la credencial, el repositorio y la protección de rama efectivos** | GR-09, §6.3.4 | §16.5 en PASS, con evidencia del servidor real y lectura registrada de la configuración efectiva | F3a: repositorio desechable **alojado en GitHub**, con plan y configuración equivalentes. F4: repositorio real con la configuración instalada | El integrador no publica (fail-closed) |

Cada evidencia se vincula al SHA del componente probado y a la configuración en que se obtuvo. Un cambio posterior de credencial, de protección o de versión del integrador invalida la evidencia y obliga a repetirla.

### Pruebas negativas (§16.1 a §16.5)

**Estado: no ejecutadas.** Deben pasar en F3a, con los SHA fijados, y repetirse en F4 sobre la configuración instalada antes de la primera fusión R1. Se suman al plan v3.1, §8.2. **Cada caso debe fallar cerrado** (rechazo, `INCONCLUSIVE` o recusación) **sin modificar `main`**, y dejar evidencia con digest.

#### 16.1 Rutas protegidas (RA-01)

| ID | Caso |
|---|---|
| NT-01-1 | Con una autorización R2 válida, se añade una ruta al registro de confianza y se modifica su copia: el integrador rechaza porque la política o el hash R3 no coinciden |
| NT-01-2 | Igual, eliminando una ruta |
| NT-01-3 | Igual, cambiando la clase mínima de una ruta |
| NT-01-4 | Igual, con un patrón solapado que cambia la clasificación |
| NT-01-5 | Divergencia entre la lista normativa, la copia del registro de confianza y la copia operativa, en todas las combinaciones: ninguna habilita una integración |

#### 16.2 Atribución de actores (RA-02)

| ID | Caso |
|---|---|
| NT-02-1 | Manifiesto con `producer` falsificado |
| NT-02-2 | `author` y `committer` de Git falsificados |
| NT-02-3 | `implementer_id` arbitrario pasado al gate |
| NT-02-4 | Check run de otro SHA |
| NT-02-5 | Check run de una identidad o App no autorizada |
| NT-02-6 | Ledger alterado |
| NT-02-7 | Ledger truncado |
| NT-02-8 | Auditor que coincide con el principal real de push aunque los metadatos Git digan lo contrario: debe quedar recusado |
| NT-02-9 | Atribución no resoluble: el resultado es `INCONCLUSIVE`, nunca `APPROVE` |
| NT-02-10 | Bajo D12 (token compartido), dos actores distintos publican con el mismo principal de GitHub: la atribución no se da por resuelta solo con el principal |

#### 16.3 Promoción y árbol autorizado (RA-03)

| ID | Caso |
|---|---|
| NT-03-1 | Se pausa tras calcular y autorizar el árbol, se mueve `main` con una integración competidora y se reanuda: la publicación condicionada falla sin cambiar `main` |
| NT-03-2 | El head de la PR cambia entre la validación y la publicación: la revalidación aborta. Si el cambio cae en la ventana del §6.3.6, la verificación posterior abre un incidente |
| NT-03-3 | Commit con el árbol autorizado pero con padres no autorizados: no se acepta como promoción |
| NT-03-4 | Commit con el árbol autorizado pero con método o identidad publicadora no autorizados: no se acepta |
| NT-03-5 | Commit con un árbol distinto: no se acepta |
| NT-03-6 | `main` se fuerza hacia atrás, a un ancestro de `base_sha`, antes de publicar: la publicación condicionada falla |
| NT-03-7 | Conflicto de fusión: el integrador aborta sin resolución automática |

#### 16.4 Latidos (RA-07)

| ID | Caso |
|---|---|
| NT-07-1 | Latido ausente, con más de 1 h, con secuencia repetida o con firma inválida: el integrador no fusiona |

#### 16.5 Comportamiento del servidor en la configuración real (RA-09)

| ID | Caso |
|---|---|
| NT-09-1 | Con la credencial efectiva del integrador, se publica con un valor esperado obsoleto contra un ref de prueba del mismo repositorio y con la misma protección: el servidor rechaza y el ref no cambia |
| NT-09-2 | Igual, contra `main` en el repositorio desechable de F3a: el servidor rechaza y `main` no cambia |
| NT-09-3 | No hay evidencia RA-09 registrada, o la evidencia corresponde a otra credencial o protección: el integrador no publica |
| NT-09-4 | Respuesta ambigua o error de red del servidor durante la publicación: el integrador no reintenta por otra vía, verifica el estado y, si hay discrepancia, abre un incidente |

*La forma concreta de NT-09-1 en el repositorio real es una propuesta del PM. La decide en F3b el auditor no recusado, sin tocar `main`.*

---

## Anexo A: trazabilidad de la redacción

- **Alcance:** borrador F1 de GOV-REV-002, versión 0.3. No se ha modificado ningún archivo del repositorio.
- **Revisiones consultadas:**
  - `main` en `ddd520f58613564dbc6460949e2dea8e78b75517`;
  - PR #22 en `432f7a8c96276c497e98eb8674ae732547d84a41` (registro de D1–D13, plan v3.1, estatuto del PM, inventario);
  - PR #23 en `68bfa715a8931cf86a4cc25a1259f431fd6313ae`. Solo se comprobaron su existencia, su título y su estado de borrador; el PM no ha auditado su contenido.
- **Fuentes leídas:**
  - GOV-REV-002 v0.2 y el dictamen de diseño de Codex en la ronda 2 (`REJECT`, GR-01 a GR-09);
  - `432f7a8:docs/decisions/CEO-DEC-GOV-2026-10-21.md`, `432f7a8:docs/AUTONOMOUS_GOVERNANCE_PLAN.md` (§6.6 y §7) y `432f7a8:docs/PM_AGENT_CHARTER.md`;
  - el dictamen de fidelidad de Codex en la ronda 5 sobre la PR #22 (`APPROVE-TECHNICAL`);
  - el registro bruto de la conversación de gobierno (hashes de las líneas 191, 200, 206 y 562 recalculados; coinciden).
- **Comprobado por el PM:**
  - `432f7a8` y `68bfa71` resuelven a los SHA completos citados;
  - el diff `ddd520f..432f7a8` contiene exactamente cinco archivos;
  - las PR #22 y #23 están abiertas, en borrador y con esas cabezas (consulta `gh pr view` del 2026-10-21).
- **Registro literal exigido por los dictámenes de Codex:** «Independencia de auditoría no demostrada; revisor y autor comparten uid y credenciales.»
- **No verificado por el PM:**
  - el estado del código descrito en GR-02 (`independent_audit.py`, `manifest_audit.py`, `pr_conformity.py`), que se cita como hallazgo de Codex;
  - que `git push --force-with-lease` o la API de GitHub ofrezcan en este repositorio, con la credencial actual, la semántica requerida (RA-09);
  - los detalles de los planes de GitHub (solo consta un error 403 al proteger una rama en el plan privado gratuito);
  - que las CLI de los agentes funcionen bajo otros uids;
  - el contenido y el resultado de la PR #23 (F2 no está en PASS);
  - la integridad del registro de la conversación (archivo bajo un uid compartido y no firmado).
- **Pendiente:**
  - una nueva revisión adversarial de Codex sobre esta versión 0.3 (Claude no puede sustituirla);
  - la evaluación de P3;
  - la asignación del SHA definitivo.
- **Autoridad usada:** estatuto provisional del PM (D10a, D10e), limitado a redactar y proponer. Ninguna decisión, aprobación ni fusión.
- **Siguientes pasos y responsables:**
  1. el auditor de diseño (Codex) revisa la versión 0.3;
  2. si no hay `REJECT` ni `VETO`, el PM fija el SHA y abre el Issue `ceo-proposal` (D7-bis) con P5, el dictamen y la evidencia.

## Anexo B: disposición de los hallazgos GR-01 a GR-09

| ID | Severidad | Estado en la ronda 2 | Disposición en v0.3 | Cambio en v0.3 |
|---|---|---|---|---|
| GR-01 | ALTO | RESUELTO | Sin cambios de fondo | Pasa a ser el requisito de aceptación RA-01 (§16.0). Pruebas en §16.1 |
| GR-02 | CRÍTICO | PARCIAL | **ACEPTADO como requisito pendiente** | El §4.3.6 y el §8.1 lo declaran requisito, no garantía. RA-02 (§16.0) fija la condición de cierre y el efecto mientras esté pendiente. Se añade la limitación del principal compartido bajo D12 (§4.3.2.2) y la prueba NT-02-10 |
| GR-03 | CRÍTICO | PARCIAL | **ACEPTADO como requisito pendiente** | Nuevo §6.3.11 y RA-03 (§16.0). La ventana residual del head se declara divergencia conocida, aceptada solo como riesgo detectivo (§6.3.6, §14). Pruebas del §16.3 sin cambios de fondo |
| GR-04 | ALTO | RESUELTO | Sin cambios | — |
| GR-05 | ALTO | RESUELTO | Sin cambios de fondo | El §12.5 remite a RA-02, RA-03 y RA-09 |
| GR-06 | ALTO | PARCIAL | **ACEPTADO** (absorbido por GR-08) | Base de decisiones ampliada a D1–D13 en el encabezado, el §0, el §1.2.2, el §12.3, el §14 y el §15.5 |
| GR-07 | MEDIO | RESUELTO | Sin cambios de fondo | Pasa a ser RA-07. Prueba en §16.4 |
| GR-08 | ALTO | NUEVO | **ACEPTADO** | D1–D13 en todas las referencias. El §0.1 contrasta la política con D11 (control detectivo y propuesta de protección), D12 (integrador con el token actual y riesgo registrado) y D13 (segunda línea más débil que un revisor humano, registrada como tal). El §12.3.2 autoriza fusionar la PR #22 solo en `432f7a8c96276c497e98eb8674ae732547d84a41` y solo su diff de cinco archivos, sobre la base del `APPROVE-TECHNICAL` de la ronda 5. Se mantiene que el registro bruto no está firmado y que la fusión no lo autentica (§0, §14) |
| GR-09 | MEDIO | NUEVO | **ACEPTADO** | El §6.3 pasa a ser un contrato de política fail-closed y no afirma la atomicidad. RA-09 exige evidencia del servidor y de la configuración reales en F3a (en GitHub) y en F4. Nuevo §6.2.13 y pruebas del §16.5 |

---

## Propuesta P5 al CEO

**Al aprobar P5, el CEO aprueba exactamente esto (R3, una sola vez):**
1. GOV-REV-002 v0.3 en el SHA `<por asignar>`, basada en D1–D13 y acumulativa con GOV-REV-001. Prevalece el requisito más estricto.
2. La extinción de CEO-DEC-LOCAL-A al aprobar P5. Hasta la primera fusión R1 válida, solo se integra lo del §12.3.
3. Un arranque limitado a las cuatro operaciones del §12.3, cada una condicionada a su evidencia PASS. Entre ellas, fusionar la PR #22 **solo** en `432f7a8c96276c497e98eb8674ae732547d84a41`. P5 no certifica independencia ni activa R2.
4. Las rutas protegidas del §3.4.3, incluidas las propuestas del PM: R3 para `docs/CONSTITUTION.md`, `docs/AUTONOMOUS_AUDIT_POLICY.md`, GOV-REV-002 y `docs/decisions/`; R2 para `src/aao/policy.py`, el supervisor, el notificador, la herramienta del registro, `AGENTS.md` y `docs/AGENT_OPERATING_RULES.md`.
5. Una raíz sin tercero humano (salvo que se apruebe P4), registrada como «independencia de la raíz no demostrada por un tercero».

**Decisiones CEO pendientes que se someten a aprobación expresa en P5:**
- (a) **Custodia de `aao-trust`:** solo el CEO ejecuta los cambios materiales de la raíz, con sudo sobre un artefacto preparado y auditado.
- (b) **Caducidad del arranque:** 30 días naturales desde la aprobación de P5, sin prórroga.

**Fuera de P5:** P1 (sudo de F2 sobre la PR #23; F2 no está en PASS), P2 y P3 (GitHub; D11, D12) y P4 (gasto).

**Riesgos residuales:** RA-02, RA-03 y RA-09 pendientes (bloquean R2 y la publicación, no P5); token de administrador en uso (D12); `main` solo con control detectivo (D11); segunda línea más débil que un revisor humano (D13); registro bruto no firmado; #10–#21 sin convalidar.

**Recomendación del PM:** aprobar P5 con (a) y (b) **solo** cuando Codex haya revisado la v0.3 sin `REJECT` ni `VETO` y se haya fijado su SHA. La aprobación no habilita ninguna operación sin su evidencia PASS.
