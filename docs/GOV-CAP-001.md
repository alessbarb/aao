# GOV-CAP-001 — Gestión y evolución de capacidades

**Versión:** 1.1
**Estado:** v1.0 ratificada expresamente por el CEO el 2026-10-19; v1.1 incorpora precisión explícita sobre skills de agentes
**Ámbito:** AAO y sus proyectos, agentes, herramientas y servicios
**Jerarquía:** Subordinada a CONST-CAP-001 y a la Constitución. Se aplica junto a GOV-REV-001 v1.1.

## 1. Objeto
AAO descubrirá, evaluará, desarrollará, adquirirá, registrará, compartirá, ejecutará, mantendrá, mejorará y retirará capacidades para alcanzar mandatos aprobados, reducir duplicidades y optimizar coste total respetando autoridad y segregación.

## 2. Definición y categorías
Una capacidad es un recurso identificado, versionado y gobernado para realizar una función. Incluye CLI/scripts, bibliotecas, API/servicios, aplicaciones/plataformas, agentes, skills de agentes, conocimiento y workflows. Cada categoría tendrá contrato apropiado.

## 3. Descubrimiento
Antes de construir se consulta el catálogo interno. Se investiga externamente si falta una solución adecuada, hay insuficiencia, riesgos, oportunidades justificadas o información obsoleta. La profundidad y presupuesto de búsqueda serán proporcionales y estarán sujetos a reglas de parada.

## 4. Selección y benchmark
Comparar reutilizar, adaptar, adquirir y construir considerando requisitos, coste inicial/recurrente, tokens/modelos, rendimiento, recursos, fiabilidad, seguridad, procedencia, licencias, dependencias, mantenimiento, reutilización y riesgo residual. Benchmarks reproducibles solo cuando justificados. Detener la investigación cuando la ganancia esperada no compense el esfuerzo.

## 5. Origen y responsabilidad
Cada nueva capacidad se inicia en el proyecto/unidad responsable, con ID, versión, responsables funcional y técnico, contrato, dependencias, permisos, riesgo, pruebas y condiciones de soporte. Mantener aislamiento de datos y recursos de proyecto.

## 6. Catálogo
El catálogo diferencia capacidades locales y corporativas sin romper controles de visibilidad. Estados: descubierta, evaluada, registrada localmente, candidata a promoción, aprobada compartida, obsoleta, suspendida y retirada. Disponibilidad en el catálogo NO implica autorización de uso.

## 7. Promoción corporativa
Exigir evaluación proporcional de utilidad, contratos, pruebas, permisos, seguridad, cadena de suministro, licencias, procedencia, mantenimiento, compatibilidad, costes, auditoría independiente y reversión. La autoridad aprobadora depende de una delegación verificable; fuera de ella permanece bloqueada.

## 8. Ejecución
Exigir autorización específica por agente, proyecto, operación y entorno. Privilegio mínimo, límites temporales, de efectos y recursos, aislamiento proporcional al riesgo; controles reforzados para código externo o desconocido. Se prohíbe elusión de seguridad y autoampliación de facultades.

## 9. Adquisición externa
El descubrimiento no concede permisos para descargar, instalar o ejecutar. Utilizar mecanismos de adquisición previamente autorizados, comprobando procedencia, versiones, integridad, licencias, vulnerabilidades y compatibilidad cuando corresponda.

## 10. Evolución compartida
Mejoras en versión candidata aislada; mantener estable la anterior hasta verificación de compatibilidad, auditoría y promoción. Para componentes críticos: recuperación y control independiente del componente sustituido. Prohibida la modificación unilateral de reglas de autopromoción.

## 11. Mantenimiento y retirada
Cada capacidad compartida tiene responsabilidades asignadas y suplencia; AAO puede reasignarlas dentro de su delegación. Retirada ordinaria con análisis de consumidores, migración y reversión. Riesgo crítico: suspensión inmediata, investigación y recuperación.

## 12. Medición y aprendizaje
Medir proporcionalmente tokens, coste monetario, tiempo, CPU/recursos, éxito, fallos, calidad, mantenimiento y reutilización. Optimizar coste total y valor, no solo tokens. Compartir decisiones, alternativas, pruebas, costes y limitaciones sin exponer datos o secretos privados de otros proyectos por defecto; reevaluar la vigencia.

## 13. Auditoría y autoridad
Aplicar GOV-REV-001 para independencia y veto. El creador no autoriza unilateralmente la promoción crítica. CEO decide solo materias reservadas; operación fuera de autoridad falla de forma cerrada.

## 14. Implantación gradual
AAO Self Development comienza con catálogo mínimo: consulta, evaluación sencilla y registro local. Ampliar descubrimiento, benchmarking, promoción y optimización conforme a casos reales. La falta de funcionalidades futuras no impide usos ya autorizados ni suspende controles obligatorios.

## 15. Reforma
La autoridad corporativa competente podrá aprobar ajustes ordinarios auditados dentro de su delegación; cualquier cambio constitucional, ampliación reservada o reducción de garantías protegidas exige autorización CEO.

## Control de alcance
Esta ratificación crea una norma de gobierno, no evidencia de implementación. No autoriza automáticamente herramientas, descargas, instalación, red, shell, modelos, efectos externos, producción, merge ni modificación de permisos. Todos los controles previos siguen vigentes.

## 16. Skills de agentes
Los skills son capacidades especializadas versionadas que aportan instrucciones, procedimientos, referencias, configuraciones y, opcionalmente, scripts o recursos a uno o varios agentes. Deben registrarse, descubrirse, evaluarse, actualizarse, compartirse y retirarse bajo las mismas reglas de procedencia, aislamiento, auditoría y autoridad aplicables a otras capacidades.

Un skill no es por sí mismo una identidad de agente ni una concesión de permisos. Su aplicación no puede ampliar capacidades ejecutables, privilegios, acceso a datos, presupuesto o herramientas del principal que lo utiliza. Las instrucciones del skill tienen menor autoridad que la Constitución, las políticas, los mandatos y las autorizaciones del runtime.

El contrato de un skill incluye identidad y versión inmutable, propósito, agentes o roles compatibles, entradas y salidas esperadas, dependencias, recursos incluidos, origen y licencia, límites de uso, evaluación de calidad, pruebas, riesgos y responsables. Los scripts incluidos también requieren autorizaciones operativas separadas.

Los skills nuevos se desarrollan inicialmente en el proyecto de origen. Su promoción al catálogo común y las nuevas versiones siguen la evaluación independiente y las reglas de compatibilidad y recuperación de las secciones 7 y 10. Se examinan específicamente inyección de instrucciones, exfiltración, dependencias y escalada de privilegios.

## Historial normativo
- 2026-10-19 — v1.0 ratificada por el CEO.
- 2026-10-19 — v1.1: precisión de skills como categoría explícita, sin nueva autoridad de ejecución ni modificación constitucional.
