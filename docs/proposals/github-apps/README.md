# Manifiestos de GitHub Apps (P2/P3), propuesta

Un JSON por App, en el formato del [flujo de manifiesto de GitHub Apps](https://docs.github.com/en/apps/sharing-github-apps/registering-a-github-app-from-a-manifest). **No crean nada por sí solos.** Las Apps las crea el CEO como administrador de GitHub (D4) cuando apruebe P2 y P3.

- Todas son privadas, sin webhook y **sin Administration, Secrets ni Actions: write**.
- **Implementadores (`aao-impl-*`):** se instalan **solo en su fork**. Los permisos son por App, no por instalación, así que instalarlas en el canónico les daría escritura (P2 §4-bis). Las PR hacia el canónico las abre `aao-pm`.
- **Integrador (`aao-integrator`):** es la única exclusión del ruleset A en `main` (P3 §3).
- **Auditores:** `statuses: write` y `checks: write`, porque la App del auditor es la fuente obligatoria del check `aao-audit` (ruleset B).

Las claves privadas se instalan en el uid de cada rol (P1) con `0600` y no pasan por otros uids (P2 §6).
