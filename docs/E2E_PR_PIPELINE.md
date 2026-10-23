# Cadena R1 de extremo a extremo sin el CEO (especificación)

**Estado:** PROPUESTA técnica de AAO, dentro de P2, P3 y P5, que ya están decididas. No cambia la política.
**Régimen:** ordinario R1, tras el arranque (§12.3, §13.4). R2 sigue bloqueado hasta el §12.5.

## Actores (uid → App)

| Paso | uid | App | Qué hace |
|---|---|---|---|
| 1 | `aao-impl-*` | `aao-impl-*` (solo su fork) | empuja la rama al fork |
| 2 | `aao-pm` | `aao-pm` | abre la PR fork → canónico (`pull_requests: write`) |
| 3 | `aao-integrator` (timer) | `aao-integrator` | sondea las PR abiertas. Por cada cabeza nueva: fetch al espejo `/srv/aao/mirror` (suyo, de lectura pública), `merge-tree`, y escribe el manifiesto y la petición `{repo, pr_number}` en `/var/lib/aao-audit-inbox/<id>.json` |
| 4 | `aao-auditor` (path unit → `aao-auditor-dispatch.service`) | `aao-auditor` | `audit_manifest` sobre el espejo y, si sale APPROVE, el emisor escribe `authorization.json/.sig` en `reports/<id>/`. El veto pasa por F4-03 |
| 5 | `aao-integrator` | `aao-integrator` | `promote` paso a paso: valida la autorización y el latido, construye M = merge(base, cand) y lo empuja a `aao-staging/<pr>-<sha>` |
| 6 | `aao-auditor` (dispatch, petición «gate») | `aao-auditor` | `verify_promotion(M)` y, si da conforme, publica el check `aao-audit` sobre M (`checks: write`, `statuses: write`) |
| 7 | GitHub Actions | — | `test` sobre M |
| 8 | `aao-integrator` | `aao-integrator` | con `test` y `aao-audit` en verde sobre M: `updateRefs(main, beforeOid = base → M)`. El ruleset A solo lo permite a esta App y el ruleset B exige los dos checks. Si `main` se ha movido, se rechaza: vuelve al paso 3 con la nueva base |
| 9 | `aao-supervisor` | `aao-supervisor` | latido firmado; detecta pushes no atribuidos (RA-02) |

**Ninguna acción del CEO** desde el paso 1 hasta el 9.

## Invariantes

- Cada clave de App la custodia su uid (manifest flow). No se reutiliza nunca el token del CEO.
- La única vía de ejecución como `aao-auditor` es el dispatch (E7). El dispatch valida el `<id>` con una regex y trata el contenido del inbox como datos no confiables.
- Un R2 detectado por el emisor no se emite: la PR queda en espera de §12.5 y el PM la etiqueta.
- Cualquier fallo deja `main` intacto y produce evidencia. No hay reintento con menos controles.

## Lo que sí requiere al CEO, una vez

1. **P2/P3:** crear las Apps y aplicar los rulesets (administración de GitHub).
2. **Op. 1 del §12.3:** sudo para instalar la raíz de confianza, las unidades y el verificador.

## Detalles de implementación (etapa runtime)

- **M es único.** El integrador construye M una sola vez y lo empuja a staging. Los checks corren sobre ese M, y a `main` se promueve el mismo M: `promote` acepta `staged_commit` y verifica `tree(M) == merge_result_tree_sha` y que los padres sean `[base, candidato]`. Si M se recalculara, `commit-tree` daría otro SHA, porque incluye la fecha.
- **The trust registry is static; no per-PR data is stored in it.** CI evidence is derived from the SHA verified by the pipeline, and attribution is derived from the auditor-signed authorization.
- **Inbox del auditor.** `/var/lib/aao-audit-inbox/<id>.json`, escrito solo por el integrador (`<id>` = `[0-9a-f]{64}`). Hay dos tipos de petición:
  - `audit`: `{repo, pr_number, manifest}`;
  - `gate`: `{id, promoted_sha}`.

  El dispatch del auditor lo trata como datos no confiables.
- **Salidas del auditor.** Van en `/var/lib/aao-auditor/reports/<id>/`: `report.json`, `report.sig`, `authorization.json`, `authorization.sig` y `gate.json`, de lectura para `aao-ledger-read`.
- **Estado del integrador.** Una máquina de estados por `(pr, head_sha)`, persistida en su `state_dir`, con escritura atómica: `queued → audited → staged → gated → promoted | failed(reason)`. Cada tick es idempotente.
- **GitHub.** Todo pasa por `GitHubAppClient`, con la App de cada rol. Las pruebas usan un cliente falso y remotos bare locales.
