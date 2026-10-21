# Trabajo pendiente de F4 (activación) y requisitos abiertos

**Estado:** registro de trabajo pendiente; nada de esto está implementado ni activado. Mantiene los SHA y dictámenes del expediente (`docs/BOOTSTRAP_DOSSIER.md`).
**Origen:** expediente de arranque del 2026-10-21; instrucción del CEO del 2026-10-21 (preparación de P2 y dos requisitos nuevos de F4).

## F4-01: custodia independiente del ancla del ledger (requisito del CEO)

**Problema (limitación B declarada en #27).** El ledger está firmado por entrada y el gate exige que el ancla externa siga en la cadena. Pero quien puede escribir el archivo (el uid del auditor o root) puede truncar las entradas añadidas después del último anclaje. Hoy el ancla no la avanza nadie: se queda en el origen.

**Requisito.** El ancla la avanza un rol distinto del escritor del ledger, tras cada entrada y antes de que el integrador pueda usarla.

**Diseño propuesto (mínimo):**
1. El **supervisor** (uid `aao-supervisor`, sin escritura en el ledger) lee el ledger, verifica firmas y cadena, y escribe el hash terminal verificado en el archivo de ancla de `aao-trust`. Lo hace con una operación delegada, porque el supervisor no escribe en `aao-trust` directamente. Lo emite como evento firmado con secuencia, y el latido incluye `ledger_head`.
2. El **integrador** exige que el hash terminal del ledger que lee sea **exactamente** el último `ledger_head` del latido firmado vigente. Ya no basta con que esté contenido en la cadena. Si alguien trunca, el terminal deja de coincidir y no se integra. Si alguien añade una entrada todavía no anclada, la integración espera al siguiente latido.
3. Ningún rol puede escribir a la vez el ledger y el ancla.
4. **Cubre también las marcas de veto pendiente (hallazgo A-2 de #30):** el supervisor registra el conjunto de digests de las marcas de cada candidato. El gate y el integrador deniegan si una marca registrada desaparece sin una resolución firmada. Así se cierra el borrado de marcas por otro proceso del uid del auditor. Requiere P1, para que el uid del auditor sea exclusivo.

**Pruebas de aceptación:**
- truncar la cola tras un veto anclado → el integrador rechaza;
- entrada nueva no anclada todavía → el integrador espera y no integra;
- un supervisor que intenta escribir el ledger → denegado;
- el auditor que intenta escribir el ancla → denegado (verificador F2).

## F4-02: un veto no registrado por falta de custodia nunca permite una integración indebida (requisito del CEO)

**Riesgo detectado al preparar este requisito.**
- Con el comportamiento actual (#27, SL-07), un `--veto` emitido sin custodia válida escribe un informe sin firmar y **no** se registra.
- Si antes existía una aprobación registrada para el mismo candidato, esa aprobación sigue siendo la última decisión.
- Resultado: **el gate de manifiestos la aceptaría**. **Comprobado empíricamente el 2026-10-21 sobre `1e5c0c8`:** aprobación registrada → veto con clave no anclada → `verify_promotion` devuelve `(True, ())`. Es una integración indebida potencial, aunque el veto fuera legítimo y solo fallara la custodia; por ejemplo, una clave temporalmente inaccesible.

**Requisito (fail-closed: cualquier señal de veto bloquea).**
1. Todo `--veto`, con o sin custodia, deja una **marca de veto pendiente** en un sitio que el integrador lee obligatoriamente: un evento del supervisor o un archivo de bloqueo propiedad del auditor, protegido como el ledger.
2. El integrador **rechaza** cualquier candidato que tenga una marca de veto pendiente, aunque exista una aprobación firmada posterior o anterior.
3. La marca solo se levanta con un dictamen **custodia-válido** del auditor sobre el mismo candidato: un veto registrado o una aprobación nueva que la referencie expresamente. El implementador, el integrador y el PM no pueden levantarla.
4. El riesgo opuesto es aceptable: si alguien crea marcas falsas, el resultado es un bloqueo. Es una denegación de servicio, que va en la dirección segura y que el supervisor detecta y notifica.

**Prueba negativa obligatoria** (nombre fijo, validada por mutación):
`test_custodyless_veto_after_recorded_approval_blocks_integration`
- se registra la aprobación de un candidato con custodia válida;
- se emite un veto sin custodia sobre el mismo candidato;
- **el integrador rechaza**, el gate de manifiestos rechaza y `main` queda intacto;
- **mutación:** si se ignora la marca de veto pendiente, la prueba debe fallar.

Pruebas complementarias:
- marca pendiente y aprobación posterior firmada que no la referencia → sigue bloqueado;
- veto registrado con custodia que referencia la marca → la marca se convierte en veto registrado y sigue bloqueado;
- aprobación posterior que referencia y resuelve la marca → se integra, solo si el resto de comprobaciones pasa.

## F4-02b: el integrador de F3a también debe consultar las marcas de veto pendiente

La PR #30 cierra F4-02 en el gate de manifiestos. El integrador de F3a (#26) lee los vetos del ledger de gobierno, pero **no** las marcas de veto pendiente. Antes de activarlo, el integrador debe tratar como bloqueante cualquier marca sin resolver del candidato, con la misma prueba negativa y validación por mutación.

## F4-03: P2 (identidades y permisos de GitHub)

Ver `docs/proposals/P2_GITHUB_IDENTITIES_AND_PERMISSIONS.md`. Las pruebas A-01 a A-14 son las que llevan RA-02, RA-03 y RA-09 a PASS.

## F4-04: requisitos del arranque (§12.2) pendientes

| Requisito | Depende de |
|---|---|
| Matriz F2 en el host (9 roles en PASS) | P1 (CEO, sudo) |
| Registro de confianza con su contenido inicial (`trusted_auditor_revisions = [1e5c0c8c81001dae1edf20f746da17b8f7ae7d28]`, claves y lista normativa de rutas) | P1 (claves) → AAO lo prepara → CEO lo instala (decisión (a)) |
| RA-01 (tres copias de la lista de rutas protegidas) y RA-07 | P1 |
| RA-02, RA-03 y RA-09 (GitHub real) | P2 |
| P5 (texto de GOV-REV-002 y decisiones (a) y (b)) | CEO |

## F4-05: deuda técnica y hallazgos menores que se arrastran

- NF-13 (prueba vacía de `ls-remote` con ref exacto), NF3-02 (severidad sin normalizar, por ejemplo `"CRITICAL "`), redacción «nothing is recorded» → «no decision is recorded in the ledger». Son de clase B o baja.
- Hallazgos previos: P11-4 (sin protección contra `TRUNCATE`), P1/P2 de #15 y C-1 a C-6.
- Auditoría retroactiva completa de `main` (F6) y fusiones históricas #10–#21 sin convalidar.

## Orden recomendado

1. F4-02: el gate está en la PR #30. A-1 está resuelto. A-2 sigue abierto hasta F4-01 y P1. Falta F4-02b, el integrador.
2. F4-01 (custodia del ancla).
3. Pruebas de P2 en el repo de ensayo, tras la decisión del CEO.
4. Requisitos del §12.2 tras P1 y P5.

Cada uno va en su propia PR, con la auditoría del rol no recusado y regresiones validadas por mutación.
