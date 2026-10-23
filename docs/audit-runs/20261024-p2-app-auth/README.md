# P2: autenticación API de las nueve GitHub Apps (2026-10-24)

**Estado: NO DEMOSTRADA.** Las claves están instaladas (lo declara el CEO); ninguna App ha autenticado todavía contra la API en un registro de este expediente.

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
| repos accesibles | integrador, auditores, supervisor, notifier, PM: solo `autoaiorg/aao` (`selected`). Implementadores: exactamente su fork (`--fork`), que es fork de `autoaiorg/aao`; nunca el canónico |

## Resultados

| App | uid | Resultado |
|---|---|---|
| aao-integrator | aao-integrator | PENDIENTE |
| aao-auditor | aao-auditor | PENDIENTE |
| aao-auditor-alt | aao-auditor-alt | PENDIENTE |
| aao-supervisor | aao-supervisor | PENDIENTE |
| aao-notifier | aao-notifier | PENDIENTE |
| aao-pm | aao-pm | PENDIENTE |
| aao-impl-claude | aao-impl-claude | PENDIENTE |
| aao-impl-codex | aao-impl-codex | PENDIENTE |
| aao-impl-agy | aao-impl-ag | PENDIENTE |

Nueve PASS demostrarían la autenticación. **No** son el ensayo P2/P3 (A-01..A-14, P3-01..P3-12): RA sigue en PENDING, `enabled_risk_classes` sigue en `["R1"]`, el integrador no se activa y R2 sigue bloqueado.
