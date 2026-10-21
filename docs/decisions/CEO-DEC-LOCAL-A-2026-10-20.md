# AAO — Decisión CEO: excepción transitoria de integración local Clase A

**ID:** CEO-DEC-LOCAL-A-2026-10-20  
**Autoridad:** CEO; aprobación expresa el 20 de octubre de 2026.  
**Estado:** aprobada, pendiente de habilitación técnica.  
**Inicio:** 2026-10-20 (Europe/Madrid). **Caducidad exclusiva:** 2026-11-19 00:00 (Europe/Madrid).  
**Ámbito:** AAO Self Development; desarrollo e integración Git locales. GitHub es registro remoto publicado por el CEO.

## Decisión vinculante

Durante 30 días se autoriza excepcionalmente la integración **local** de cambios de **Clase A, reversibles e inertes**, sin acreditar independencia institucional plena GOV-REV-001, SOLO cuando concurran todas estas condiciones:

1. Congelación de SHA completo del candidato, base y árbol resultante; cualquier cambio invalida la revisión.
2. Pruebas reproducibles sobre el árbol resultante, con evidencia vinculada a los SHA exactos.
3. Revisión adversarial de un **agente distinto del autor**, con hallazgos y disposiciones. Registrar obligatoriamente que la independencia organizativa no está demostrada.
4. Expediente trazable de autor, revisor, clasificación, cambios, verificaciones, riesgos, decisión y resultado.
5. Promoción solo si hay clasificación Clase A documentada, controles satisfactorios, ausencia de veto y autoridad operativa preexistente. Esta decisión **no concede nuevos permisos**.

## Exclusiones absolutas

Quedan FUERA: seguridad, autenticación/autorización, identidad, secretos, roles/grants, infraestructura o aislamiento, auditoría, políticas protegidas, evidencias/ledger/veto, controlador/gate de integración, autoridad de promoción, capacidades privilegiadas, efectos externos y asuntos constitucionales o estratégicos reservados al CEO. Un cambio mixto asume la clase de mayor riesgo; no puede fragmentarse para eludir controles.

Esta decisión **no reforma permanentemente GOV-REV-001**, no sustituye una auditoría independiente, no ratifica retrospectivamente las fusiones anteriores, no autoriza instalar cuentas, modificar permisos/secretos, activar el promotor canónico ni cambiar la visibilidad de GitHub.

## Vencimiento y revocación

Expira automáticamente el **19 de noviembre de 2026 a las 00:00 Europe/Madrid**, incluso para revisiones iniciadas previamente. Revocable inmediatamente por CEO, sin renovación automática. Si el mecanismo no puede imponer los límites, **promoción bloqueada**.

## Riesgo residual aceptado

Únicamente en Clase A se acepta que la revisión adversarial cruzada no pruebe independencia institucional ante agentes que comparten cuenta y privilegios elevados. No se acepta omitir pruebas, ignorar vetos ni ampliar la excepción a cambios sensibles. Cada expediente debe incluir literalmente:

> Independencia de auditoría no demostrada; excepción CEO-DEC-LOCAL-A-2026-10-20 aplicada.

## Evidencia mínima por candidato

- ID, autor, revisor distinto, clase y justificación de reversibilidad e inercia.
- SHA completos de base, candidato, árbol candidato, árbol resultante y commit promovido (si existe).
- Rutas/diffs, impactos, permisos, datos y reversión.
- Entorno, versiones, comandos, tests, skips, resultados y digests de evidencia.
- Hallazgos y disposición individual; cero vetos o defectos bloqueantes.
- Aceptación explícita del riesgo residual, autoridad operativa, fecha y resultado de compare-and-swap (CAS), o denegación motivada.

## Responsabilidades

**PM/planificador:** clasifica independientemente del autor, crea solicitud, congela SHA, asigna revisor y evita escaladas circulares.  
**Implementador:** prepara candidato, pruebas y reversión; no revisa ni promueve su cambio.  
**Revisor adversarial:** reproduce la evidencia y emite `APPROVE-TECHNICAL`, `REJECT` o `VETO`; nunca lo denomina auditoría independiente.  
**Integrador habilitado:** verifica vigencia, clase, SHA, evidencias, veto y autoridad antes de operar CAS. El permiso de integración no deriva de esta decisión.  
**Claude:** mantiene auditoría e identidad fuera de Clase A.  
**CEO:** retiene excepciones estratégicas, revocación y publicación voluntaria del `main` local como registro online.

## Pruebas obligatorias en Git desechable

| ID | Caso | Resultado esperado |
| --- | --- | --- |
| T01 | Clase A con todos los controles | Integración de ensayo válida |
| T02 | Revisión cruzada ausente | Bloqueo |
| T03 | Autor = revisor | Bloqueo |
| T04 | SHA/base/árbol modificado | Bloqueo |
| T05 | VETO, REJECT o hallazgo bloqueante | Bloqueo |
| T06 | Seguridad/auditoría/integración falsamente clasificada A | Rechazo |
| T07 | Excepción caducada o revocada | Bloqueo |
| T08 | Evidencia ausente/manipulada o skips injustificados | Bloqueo |
| T09 | Referencia objetivo modificada concurrentemente | CAS falla |
| T10 | Ensayo de trazabilidad y reversión | Evidencia y main real intacto |

**Gate de puesta en marcha:** solo se declarará «procedimiento preparado» tras estas pruebas. No puede declararse «promoción autorizada» sin controles obligatorios y una identidad integradora efectivamente habilitada.

## Regularización histórica — expediente distinto

Documentar integraciones manuales #10, #11, #14, #15, #19 y #20, SHA finales, falta de auditoría independiente y riesgos pendientes. Ninguna queda convalidada retroactivamente.
