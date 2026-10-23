# P2: autenticación API de las nueve GitHub Apps (2026-10-24)

**Estado: autenticación DEMOSTRADA para las nueve Apps (2026-10-23 23:08–23:09 UTC). Resultado global 5/9 PASS:** los cuatro FAIL no son de autenticación (ver «Resultados»).

## Hechos verificados por el PM (2026-10-24)

- El repositorio se transfirió: `alessbarb/aao` redirige a `autoaiorg/aao`. Las referencias de la documentación las actualizó el CEO en `45d494a` (push directo a `main`, sin PR). Esta rama completa el código: la guarda canónica de `github_trial` usa `CANONICAL_REPO`.
- El registro no secreto aportado por el CEO se incorpora sin cambios en `deploy/github-apps/aao-github-apps-registry.json`. Su `verification_status` sigue siendo el del CEO.
- La App de Antigravity se llama `aao-impl-agy`; su clave la custodia el usuario Linux `aao-impl-ag`. El código mapea los dos nombres (`aao.github_app_auth.linux_user`).
- Las nueve claves están en homes `0700` de sus uid. El PM (`alessbarb` sin sudo en esta sesión) **no** puede leerlas, que es lo correcto. Por eso el PM no ha ejecutado ninguna autenticación.
- `GET /apps/<slug>` sin credenciales da 404 para las nueve: son Apps privadas. No es evidencia ni a favor ni en contra.
- El repo de ensayo `aao-governance-trial` no existe ni en `alessbarb` ni en `autoaiorg`.

## Desviación que se registra

Las Apps tienen `installation_id` en `autoaiorg/aao` antes de existir el repo de ensayo. El diseño P2 prevé instalar primero en el ensayo. Además, los implementadores (`aao-impl-*`) **no** deben alcanzar el repo canónico (A-10). El verificador lo comprueba; si alguno lo alcanza, es un hallazgo para el CEO (desinstalar es administración de GitHub, reservada).

## Cómo se demuestra

`docs/procedures/P2_P3_TRIAL_SETUP.md` §1-ter: el CEO ejecuta `scripts/github_apps/verify_app_auth.py` una vez por App, como su uid. Comprueba:

| Comprobación | Esperado |
|---|---|
| `GET /app` con JWT | `id` = `app_id` del registro; `slug` = nombre; permisos = manifiesto revisado |
| `GET /app/installations/<id>` | pertenece a la App, no suspendida, permisos = manifiesto |
| token de instalación | se emite y se revoca (`DELETE /installation/token` → 204) |
| repos accesibles | integrador, auditores, supervisor, notifier, PM: solo `autoaiorg/aao` (`selected`). Implementadores: exactamente los forks indicados (`--fork`), de `autoaiorg/aao` o de su repo de ensayo; nunca el canónico |

## Resultados

Ejecución del CEO, §1-ter, `REV=c24a269`, salida íntegra en [`app-auth-20261024T010852.jsonl`](app-auth-20261024T010852.jsonl), sha256 `5b86c2715f0322c8e1801e2ff2233efba2be020d55a2007ec2e917cb23c154d1`, sin secretos (comprobado: no hay clave, JWT ni token). La generó el CEO en su terminal con el verificador instalado como root en `/opt/aao-p2`; el PM la copió al expediente sin modificarla. En las nueve filas pasan `jwt_app_id`, `slug_equals_name`, `installation_belongs_to_app`, `installation_not_suspended`, `installation_token_issued` y `token_revoked`: **las nueve Apps autentican**, y todas son de `autoaiorg`, con instalación `selected`.

| App | uid | Repos accesibles | Resultado | Motivo del FAIL |
|---|---|---|---|---|
| aao-integrator | aao-integrator | `autoaiorg/aao` | FAIL | La App no tiene `workflows: write` y el manifiesto lo pedía. Por política, `.github/workflows/` es R2, así que se corrige el manifiesto (mínimo privilegio) y no la App |
| aao-auditor | aao-auditor | `autoaiorg/aao` | PASS | — |
| aao-auditor-alt | aao-auditor-alt | `autoaiorg/aao` | PASS | — |
| aao-supervisor | aao-supervisor | `autoaiorg/aao` | PASS | — |
| aao-notifier | aao-notifier | `autoaiorg/aao` | PASS | — |
| aao-pm | aao-pm | `autoaiorg/aao` | PASS | — |
| aao-impl-claude | aao-impl-claude | `autoaiorg/aao-claude` | FAIL | Se ejecutó sin `--fork`, así que el alcance no quedó demostrado. Según la API pública, el repo es un fork de `autoaiorg/aao` |
| aao-impl-codex | aao-impl-codex | `autoaiorg/aao-codex` | FAIL | Igual (fork de `autoaiorg/aao`) |
| aao-impl-agy | aao-impl-ag | `autoaiorg/aao-agy` | FAIL | Igual (fork de `autoaiorg/aao`) |

No se observó acceso de ningún implementador al repo canónico (`implementer_cannot_reach_canonical: true`). El alcance exacto a su fork **no** está demostrado, porque se ejecutó sin `--fork` (`implementer_only_its_forks: false`). Pendiente: repetir las cuatro filas FAIL con el manifiesto corregido y `--fork`.

Las nueve Apps autenticaron; cuatro filas fallaron comprobaciones adicionales (permisos del integrador y alcance de los forks). Ni la autenticación ni un futuro 9/9 son el ensayo P2/P3 (A-01..A-14, P3-01..P3-12): RA sigue en PENDING, `enabled_risk_classes` sigue en `["R1"]`, el integrador no se activa y R2 sigue bloqueado.
