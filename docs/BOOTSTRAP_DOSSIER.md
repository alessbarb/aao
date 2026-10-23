# Expediente cerrado de arranque (GOV-REV-002 §12.2) — 2026-10-21

Estado: **preparación técnica completa; arranque NO ejecutable todavía**, por los requisitos pendientes de la sección 3. No se ha fusionado, activado ni ejecutado nada con `sudo`. **Independencia de auditoría no demostrada:** todos los agentes comparten hoy uid y credenciales.

## 1. Componentes con SHA fijado y dictamen

| Componente | PR | SHA exacto | Revisor (≠ autor) | Dictamen |
|---|---|---|---|---|
| Registro de decisiones D1–D13, inventario histórico, estatuto del PM y plan v3.1 | #22 | `432f7a8c96276c497e98eb8674ae732547d84a41` | Codex (fidelidad) | APPROVE-TECHNICAL, ronda 5 |
| GOV-REV-002 v0.3 (texto de P5) | #24 | `bafb74b56c4f1355512b48c8112cbac3b064d2b4` | Codex (diseño) | APPROVE-TECHNICAL, ronda 3 |
| Script de separación de identidades (P1) | #23 | `38f40e5c35d3a5745b36491ff9c33168ad1743ed` | Codex (auditor alterno) | APPROVE-TECHNICAL, ronda 5, apto para proponer P1 |
| Mecanismos F3a: autorización, ledger, integrador, supervisor y notificador | #26 | `8d06feb2ff1ebad8e8857de79177571ec011de00` | Claude aislado (auditor principal; autor Codex) | APPROVE-TECHNICAL, ronda 4: construcción, **no activación** |
| Código del auditor corregido, candidato a raíz de confianza (incluye F3a) | #27 | `1e5c0c8c81001dae1edf20f746da17b8f7ae7d28` | Codex (segunda línea D13; autor Claude, recusado) | APPROVE-TECHNICAL, ronda 4: apto como revisión inicial de `trusted_auditor_revisions` |

Huellas sha256 de los scripts P1 en `38f40e5`, las mismas que comprueba `~/run_p1_identity_separation.sh`:

- `identity_separation.sh`: `5115cbc6452b40f8f5e6fe8e41a462291cc96bfc9f5415e0d9fd96f7f2ab2b09`
- `verify_identity_separation.sh`: `d1259211e27d48b58d982ab658d77ca9c9db6c92f7b4400c2513e7d6e5041c6f`

**Hallazgo posterior al dictamen (2026-10-21):** al preparar F4-02 se comprobó que en `1e5c0c8` un veto emitido sin custodia, después de una aprobación registrada, no bloquea el gate (`verify_promotion` → conforme). Ver `docs/F4_PENDING_WORK.md`, F4-02. **Debe corregirse antes del arranque**, y por tanto el SHA de la raíz cambiará otra vez y necesitará una nueva revisión de segunda línea.

**Valor inicial propuesto para `trusted_auditor_revisions` (provisional, pendiente de F4-02):** `1e5c0c8c81001dae1edf20f746da17b8f7ae7d28`. No `681f40c`/`3a84ff5`: la segunda línea los rechazó por SL-01..SL-03.

## 2. Fidelidad de D11–D13

Codex las evaluó **FIEL** contra el registro bruto de la conversación en la ronda 3 (`da3123a`). Hasta `432f7a8`, el diff de `docs/decisions/` solo añade la línea de historial de revisión, sin cambios en las filas D1–D13. La ronda 5 aprobó `432f7a8` entero.

**Límite:** el registro bruto es local y no está firmado.

## 3. Requisitos del §12.2 todavía pendientes

| Requisito | Estado | Qué falta | Responsable |
|---|---|---|---|
| §12.2.4 Matriz de aislamiento F2 en el host | **PENDIENTE** | ejecutar P1 (`~/run_p1_identity_separation.sh`) y que los 9 roles den PASS | CEO (sudo) |
| RA-02 Atribución de identidad real (GitHub) | **PENDIENTE** | proveedor de identidad de GitHub; requiere P2 (GitHub Apps/tokens) | CEO (administración de GitHub, D4) → AAO |
| RA-09 / RA-03 CAS en el servidor real | **PENDIENTE** | prueba del integrador contra GitHub con la configuración efectiva; depende de P2/P3 | AAO tras P2 |
| RA-01 / RA-07 | **PENDIENTE** | lista normativa de rutas en sus tres copias y evidencia del supervisor en el host | AAO tras P1 |
| Registro de confianza con su contenido inicial | **PENDIENTE** | se genera tras P1, cuando existen las claves de los auditores; incluirá el SHA de raíz de arriba | AAO prepara → CEO lo instala con sudo, decisión (a) |
| P5 (texto de GOV-REV-002 y decisiones (a) y (b)) | **PENDIENTE** | tu aprobación en el Issue #25 | CEO |
| P4 (revisor humano externo) | opcional | sin P4 se registra: «independencia de la raíz no demostrada por un tercero» | CEO |

## 4. Limitaciones B declaradas (aceptables, no ocultas)

1. Mientras no se ejecute P1, todos los roles comparten uid. Hasta P2 se usa el token de administrador (D12).
2. Quien pueda escribir el ledger (uid del auditor o root) puede truncar las entradas posteriores al último anclaje. Cerrarlo requiere que otro rol avance el ancla.
3. Las pruebas de F3a usan repos bare locales. No demuestran la atomicidad ni la identidad de GitHub.
4. La segunda línea es un modelo de otro proveedor, más débil que un revisor humano (D13).
5. El sandbox del auditor (bwrap) solo tiene pruebas parciales.
6. Las fusiones históricas #10–#21 siguen sin convalidar.

## 5. Siguiente paso

1. **Tú:** aprobar P5 y ejecutar P1.
2. **AAO:** generar el registro de confianza, verificar F2 en el host y preparar P2.
3. Ninguna operación del §12.3 se ejecuta hasta que todos sus requisitos estén en PASS.

🤖 Generated with [Claude Code](https://claude.com/claude-code)


## Actualización 2026-10-23: nuevo candidato a raíz de confianza

**Candidato:** `97ad4f13655aae2b736c7ba6b3d8d666e51d4680`, punta de la pila F4. Sustituye al valor provisional `1e5c0c8`.

**Pila:**

| PR | SHA | Contenido |
|---|---|---|
| #30 | `1fc2d6c` | F4-02 |
| #34 | `47072de` | F4-02b |
| #37 | `3666c92` | F4-01a |
| #39 | `ec47d76` | F4-01b |
| #40 | `97ad4f1` | F4-03 |

**Dictámenes:**

- **Revisiones individuales:** todas con APPROVE-TECHNICAL en su última ronda.
  - #34 y #37: auditor aislado (Claude); autor Codex.
  - #39 y #40: segunda línea Codex; autor Claude, recusado.
- **Revisión de conjunto (Codex):** primero REJECT por la ventana de A-2 previa al latido. F4-03 la cerró y la ronda 2 dio **APPROVE-TECHNICAL**: «apta técnicamente como valor inicial de `trusted_auditor_revisions`, condicionada a verificar en el host».

**Condiciones previas a la instalación** (operación 1 del §12.3):

1. Exclusividad en ejecución del uid `aao-auditor`, es decir, solo el servicio auditor corre con ese uid.
2. Custodia de la ruta del socket de admisión del supervisor y de su directorio padre.

Ambas se verifican en el host con los servicios por rol y su verificador.

**Estado:** **revisado, no instalado.** La instalación del registro de confianza la ejecuta el CEO con sudo (P5 (a)) sobre el artefacto que se prepara y audita.
