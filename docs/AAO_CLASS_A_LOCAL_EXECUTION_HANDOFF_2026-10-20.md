# AAO — Orden operativa PM: ejecución de la excepción Clase A

**Decisión aplicable:** [CEO-DEC-LOCAL-A-2026-10-20](decisions/CEO-DEC-LOCAL-A-2026-10-20.md)  
**Objetivo:** habilitar una vía de integración Git local, transitoria y estrictamente Clase A, sin presentar la revisión adversarial cruzada como auditoría independiente.

## 1. PM / planificador — P0

- Registrar la decisión en el repositorio canónico local y distinguir su adopción documental de la habilitación técnica.
- Mantener **dos colas**: `Clase A transitoria` y `Cambios excluidos`. Las etiquetas del autor no acreditan la clasificación.
- Abrir expediente histórico separado para merges #10, #11, #14, #15, #19 y #20; documentar SHA y carencias, sin convalidación retroactiva.
- Inventario único de solicitudes con base/candidato/árbol resultante SHA completos, autor, revisor, clasificación, vigencia, riesgos y autoridad.
- Congelar candidato antes de revisión; cualquier cambio exige otra revisión. Bloqueos externos se escalan una sola vez, con alternativas.

## 2. Codex — controlador runtime, P0

- Implementar verificación estricta de elegibilidad Clase A, caducidad y revocación como candidato local. **No activar promoción canónica anticipadamente**.
- Ejecutar pruebas negativas: cambios excluidos, SHA mutado, revisor ausente o igual al autor, veto/rechazo, árbol divergente, excepción vencida y carrera CAS.
- Conservar manifiestos y evidencias de solo lectura, con digests; acordar esquema con Claude y contrato de lectura con Antigravity.
- No modificar credenciales, permisos ni políticas protegidas sin autorización específica.
- Entregar SHA, comandos, pruebas reproducibles y límites al PM.

## 3. Claude — auditoría, P0

- Diferenciar `APPROVE-TECHNICAL` provisional de un dictamen GOV-REV-001; documentar qué controles técnicos se exigen siempre y cuáles no acreditan independencia.
- Revisar adversarialmente el candidato de Codex y su clasificación sin autoaprobar cambios en auditoría, gate o seguridad.
- Probar falso Clase A, veto, cambio de SHA, manipulación de evidencias y mismo autor/revisor.
- Mantener bloqueadas las promociones de clases excluidas. Informar del aislamiento real no demostrado (usuarios compartidos, grupo docker, clave y ledger).

## 4. Antigravity — Control Center, P1

- Mostrar por separado: candidato, chequeos, revisión adversarial, auditoría independiente, gate, promoción efectiva, vencimiento y revocación.
- No mostrar referencias históricas como promociones realizadas ni habilitar el botón de promoción por la sola existencia de la excepción.
- Usar exclusivamente endpoints de lectura autorizados; si no existe fuente, mostrar datos no disponibles.

## 5. Prueba conjunta LINT-002 — P0

- Ejecutar T01–T10 definidos en la decisión en repositorio desechable. No modificar `main` real.
- Matriz `PASS / FAIL / NOT RUN / NOT DEMONSTRABLE` con evidencia por SHA, resultados, revisor y hallazgos.
- Cualquier prueba de seguridad fallida impide activar promoción. La revisión local sin separación resistente nunca se denomina auditoría independiente.
- Registrar autoridad efectiva del integrador o bloqueo explícito; no conferirla automáticamente por software.
- Separar backlog de regularización histórica y trabajo nuevo.

## Política de coordinación

- Trabajo y fusiones **100 % locales**. GitHub es únicamente copia online de `main` publicada cuando lo disponga el CEO.
- Ni este documento ni su incorporación a GitHub hacen avanzar `main` local automáticamente.
- PM coordina por expediente local y comunicaciones con CEO; no usar Issues/PR GitHub como sistema canónico.
- No reabrir rondas sobre SHA obsoletos ni solicitar al CEO revisiones técnicas ordinarias.

## Criterio de cierre

1. Contrato Clase A estable y revisado por los dominios.
2. Evidencia reproducible de T01–T10.
3. Registro de autoridad efectiva o bloqueo justificado.
4. Control Center representa estados reales sin aprobación ficticia.
5. El controlador impide promociones excluidas, caducadas o vetadas.

**Estado inicial:** aprobado documentalmente, no habilitado técnicamente. La independencia GOV-REV-001 continúa sin demostrarse.
