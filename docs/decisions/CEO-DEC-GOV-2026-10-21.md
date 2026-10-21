# AAO — Decisiones CEO de gobierno autónomo

**ID:** CEO-DEC-GOV-2026-10-21
**Autoridad:** CEO, con decisiones expresas del 2026-10-21 en la conversación de gobierno con Claude (09:50–10:28 CEST).
**Naturaleza de este registro:** **resumen fiel con citas literales.** Cada decisión D se resume en una frase y va acompañada de la fuente literal: mensaje del CEO u opción elegida por el CEO en una pregunta estructurada. El resumen no añade contenido. Si hay discrepancia, prevalece la cita literal.
**Evidencia primaria:** el registro bruto de la conversación (`~/.claude/projects/-home-alessbarb-workspace-repos-active-aao/4119b041-a09a-4426-beca-9f143e6ead15.jsonl`), que es local y no se publica. Los bloques pegados en esa conversación son revisiones de terceros y **no** son decisiones del CEO.
**Integración:** esta PR toca una ruta protegida. Su fusión figura en la lista cerrada de la autorización única de arranque (`docs/AUTONOMOUS_GOVERNANCE_PLAN.md` §6.6) y no se fusiona antes.

## Decisiones

| # | Resumen | Fuente literal del CEO |
|---|---|---|
| D1 | El CEO no realiza tareas operativas. PR, revisiones y fusiones corresponden a los agentes. | «El CEO no debe molestarse en tareas genericas como la publicacion de una PR, eso es responsabilidad del agente correspondiente» |
| D2 | AAO es autónomo. El CEO define la estrategia y propone proyectos. AAO acepta los riesgos residuales hasta un umbral escrito. | «AAO debe ser absolutamente autónomo, el CEO solo define la estrategia y propone proyectos». Ante la pregunta sobre quién acepta los riesgos residuales no estratégicos, eligió la opción «AAO con umbral escrito (Recommended)». |
| D3 | GitHub vuelve a ser el maestro. | «github vuelve a convertirse en maestro» |
| D4 | El CEO gestiona la administración de GitHub. Las necesidades se le proponen y no bloquean el trabajo. | «la administracion del github, por ahora, lo gestiona el CEO y cualquier necesidad sobre la administración de github se debe proponer al CEO pero no debe resultar bloqueante para continuar los trabajos» |
| D5 | Gasto cero sin propuesta previa. | Opción elegida: «Cero, todo se propone» |
| D6 | Materias que se proponen al CEO: efectos externos o producción, cambios a la Constitución o a las políticas, datos sensibles reales, nuevos proveedores de modelo. | Opciones elegidas: «Efectos externos / producción, Cambios a Constitución/política, Datos sensibles reales, Nuevos proveedores de modelo». Nota del CEO: «Si la actividad de los agentes lo requiere se puede proponer al CEO todos los cambios anteriores». Sobre los modelos locales: «La idea es que en el futuro se tengan también modelos locales […] pero es el futuro de AAO». |
| D7 | Canal de propuestas: Control Center. Mientras no exista esa vista, GitHub Issue. | Opciones elegidas: «Control Center» y «GitHub Issue hasta que exista (Recommended)» |
| D8 | La excepción Clase A se sustituirá por una política permanente, que el CEO aprueba una sola vez. | Opción elegida: «Sustituir por política permanente (Recommended)», cuya descripción, presentada al CEO al elegir, decía: «Redacto GOV-REV-002 […] La apruebas una sola vez y después no intervienes en fusiones». |
| D9 | La separación de usuarios en la máquina se hará con un script que el CEO ejecuta una vez con sudo. | Opción elegida: «Script único que ejecutas tú (Recommended)» |
| D10 | Roles. PM: instancia separada de Claude. Integrador: script determinista. Auditor: Claude aislado, con Codex en segunda línea. Agentes disponibles: Claude, Codex y Antigravity. Hay que crear el agente PM, que prioriza. | Opciones elegidas: «Claude, instancia separada (Recommended)», «Script determinista (Recommended)», «Claude aislado + Codex en 2ª línea (Recommended)». Sobre los agentes: «Hoy tengo disponibilidad de Claude, Codex, Antigravity». Sobre la prioridad: «Lo decide AAO, se debe crear el agente PM que lo priorice». |

## Lo que este registro NO hace

- **Las propuestas no son decisiones.** No son decisiones del CEO las clases R0–R3, los uids, el gate, el supervisor, el estatuto del PM ni las fases. Son **propuestas** del plan y del PM, y solo vinculan si se aprueban dentro de P5 (GOV-REV-002).
- No aprueba GOV-REV-002 ni el arranque.
- No amplía CEO-DEC-LOCAL-A-2026-10-20, que sigue vigente con sus condiciones y exclusiones originales hasta el 2026-11-19 o hasta que la sustituya GOV-REV-002.
- No convalida las fusiones históricas (`docs/HISTORICAL_INTEGRATION_INVENTORY.md`).
- No concede credenciales, permisos ni gasto.

## Límites

El registro bruto de la conversación es local y no está firmado. Un revisor puede reproducir las citas sobre ese archivo, pero no se puede acreditar ante terceros que no se haya alterado. Fidelidad revisada por Codex (REJECT FD-01..FD-10, 2026-10-21), con las correcciones de esta versión.
