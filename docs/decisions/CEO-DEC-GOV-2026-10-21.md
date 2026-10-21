# AAO — Decisiones CEO de gobierno autónomo

**ID:** CEO-DEC-GOV-2026-10-21
**Autoridad:** CEO, con decisiones expresas del 2026-10-21 en la conversación de gobierno con Claude (09:50–10:28 CEST).
**Naturaleza de este registro:** cada decisión reproduce **literalmente**:

- el mensaje del CEO; o
- la pregunta que se le planteó, la opción que eligió y la descripción de esa opción tal como se le mostró.

La columna «Registro» no añade alcance. Solo nombra la decisión para referenciarla. **Prevalece siempre la cita literal.**
**Evidencia primaria:** el registro bruto de la conversación (`~/.claude/projects/-home-alessbarb-workspace-repos-active-aao/4119b041-a09a-4426-beca-9f143e6ead15.jsonl`), que es local y no se publica. Los bloques pegados en esa conversación son revisiones de terceros y **no** son decisiones del CEO.
**Integración:** esta PR toca una ruta protegida. Su fusión figura en la lista cerrada de la autorización única de arranque (`docs/AUTONOMOUS_GOVERNANCE_PLAN.md` §6.6) y no se fusiona antes.

## Decisiones expresadas en mensajes del CEO

| # | Registro | Cita literal del CEO |
|---|---|---|
| D1 | Publicar PR no es tarea del CEO | «El CEO no debe molestarse en tareas genericas como la publicacion de una PR, eso es responsabilidad del agente correspondiente» |
| D2 | Autonomía de AAO | «AAO debe ser absolutamente autónomo, el CEO solo define la estrategia y propone proyectos» |
| D3 | GitHub, maestro | «github vuelve a convertirse en maestro» |
| D4 | Administración de GitHub | «la administracion del github, por ahora, lo gestiona el CEO y cualquier necesidad sobre la administración de github se debe proponer al CEO pero no debe resultar bloqueante para continuar los trabajos» |

## Decisiones expresadas como selección en preguntas estructuradas

| # | Registro | Pregunta planteada | Opción elegida | Descripción de la opción mostrada al CEO |
|---|---|---|---|---|
| D2-bis | Umbral de riesgo | «Si el CEO solo define estrategia, ¿quién acepta riesgos residuales no estratégicos? Ejemplo: dar por buena la versión inicial del auditor sin revisión externa.» | «AAO con umbral escrito (Recommended)» | «AAO acepta riesgos hasta un límite fijado en una política. Por encima del límite, propuesta al CEO, sin bloquear el resto del trabajo.» |
| D5 | Gasto | «¿Puede AAO gastar dinero sin preguntarte, por ejemplo en GitHub Pro o en un revisor externo puntual?» | «Cero, todo se propone» | — |
| D6 | Materias por encima del umbral | «¿Qué queda POR ENCIMA del umbral de AAO y se te propone como decisión estratégica? Marca todo lo que aplique.» | «Efectos externos / producción, Cambios a Constitución/política, Datos sensibles reales, Nuevos proveedores de modelo» | Nota añadida por el CEO: «Si la actividad de los agentes lo requiere se puede proponer al CEO todos los cambios anteriores» |
| D7 | Canal de propuestas | «¿Por dónde te llegan las propuestas no bloqueantes, como gasto o administración de GitHub?» | «Control Center» | «Vista de decisiones reservadas en la app. Depende de que la app esté operativa.» |
| D7-bis | Canal provisional | «Las propuestas te llegarán por Control Center, pero hoy no tiene vista de propuestas al CEO. ¿Qué uso mientras tanto?» | «GitHub Issue hasta que exista (Recommended)» | «Issue con la etiqueta ceo-proposal. Cuando Control Center tenga la vista, se migra y se cierra esta vía.» |
| D8 | Excepción Clase A | «La excepción Clase A (caduca el 19-nov) partía de que el main local era el maestro. Con GitHub otra vez de maestro y AAO autónomo, ¿qué hago con ella?» | «Sustituir por política permanente (Recommended)» | «Redacto GOV-REV-002 […] La apruebas una sola vez y después no intervienes en fusiones» |
| D9 | Separación en la máquina | «Separar agentes y auditor en esta máquina (usuarios distintos, sin docker para agentes) necesita permisos de root una sola vez. ¿Cómo lo hago?» | «Script único que ejecutas tú (Recommended)» | — |
| D10a | PM | «Con tres proveedores, ¿quién hace de agente PM? Prioriza, clasifica el riesgo, asigna tareas y escala propuestas.» | «Claude, instancia separada (Recommended)» | «Otra instancia de Claude con identidad y credenciales propias, distintas del auditor. Puede planificar y clasificar, pero no audita ni fusiona.» |
| D10b | Integrador | «¿Quién es el "agente integrador" que fusiona en GitHub?» | «Script determinista (Recommended)» | «No es un modelo: un programa que fusiona solo si el veredicto firmado coincide con el SHA y no hay veto. Su ejecución es reproducible y nunca es el autor del cambio.» |
| D10c | Auditor | «¿Quién audita las PR de los demás?» | «Claude aislado + Codex en 2ª línea (Recommended)» | «Claude audita como usuario aao-auditor y nunca audita sus propias PR, que audita Codex. Codex revisa también el código del auditor.» |
| D10d | Agentes disponibles | «¿Qué agentes forman AAO hoy? Determina quién puede ser auditor, distinto del implementador.» | «Claude, Codex, Antigravity» | Nota del CEO: «Hoy tengo disponibilidad de Claude, Codex, Antigravity. La idea es que en el futuro se tengan también modelos locales que podrían apoyar a los principales e incluso sustituirles, pero es el futuro de AAO.» |
| D10e | Prioridad tras la gobernanza | «¿Qué debe hacer AAO al terminar de resolver la gobernanza?» | Respuesta libre | «Lo decide AAO, se debe crear el agente PM que lo priorice» |
| D11 | Control de `main` provisional | «En el plan privado gratuito, main en GitHub no tiene protección: cualquier token con escritura puede empujar a main. Mientras decides la administración de GitHub, ¿qué control aplico?» | «Detectivo + propuesta (Recommended)» | «Solo fusiona una identidad integradora (GitHub App). Un workflow revisa cada push a main y abre incidencia si falta el veredicto del auditor. Se te propone una protección que lo impida: Pro, o repo público.» |
| D12 | Fusión provisional | «Crear la GitHub App integradora y la del auditor es administración de GitHub (tuya) y no debe bloquear. Mientras no existan, ¿quién fusiona las PR que pasen el gate?» | «Agente integrador, token actual (Recommended)» | «Un único agente designado fusiona solo si hay veredicto del auditor sobre el SHA exacto. El control detectivo vigila main. Riesgo: el token tiene permisos de administrador, y queda registrado.» |
| D13 | Segunda línea del auditor | «¿Quién hace la revisión de segunda línea del código del auditor? Tiene que ser alguien distinto de su autor (Claude). Ojo: has elegido gasto cero sin propuesta previa.» | «Otro proveedor aislado (Recommended)» | «Codex u otro modelo con credenciales, usuario y evidencias separadas. Sin coste. Más débil que un revisor humano externo, y se registra como tal.» |

D11–D13 son decisiones del mismo día que faltaban en la primera versión del registro. Se añaden sin modificar D1–D10.

## Lo que este registro NO hace

- **Las propuestas no son decisiones.** No son decisiones del CEO las clases R0–R3, los uids, el gate, el supervisor, el estatuto detallado del PM ni las fases. Son **propuestas** del plan y del PM, y solo vinculan si se aprueban dentro de P5 (GOV-REV-002).
- No aprueba GOV-REV-002 ni el arranque.
- No amplía CEO-DEC-LOCAL-A-2026-10-20, que sigue vigente con sus condiciones y exclusiones originales hasta el 2026-11-19 o hasta que la sustituya GOV-REV-002.
- No convalida las fusiones históricas (`docs/HISTORICAL_INTEGRATION_INVENTORY.md`).
- No concede credenciales, permisos ni gasto.

## Límites

El registro bruto de la conversación es local y no está firmado. Un revisor puede reproducir las citas sobre ese archivo, pero no se puede acreditar ante terceros que no se haya alterado.

Historial de revisión de fidelidad por Codex:

- REJECT sobre `d902f7e`;
- REJECT sobre `59c42cb`;
- REJECT sobre `da3123a`, en el que D1–D13 quedaron evaluadas como FIEL y los hallazgos restantes estaban en el plan y en el estatuto del PM.

Las disposiciones de cada ronda constan en la PR #22.
