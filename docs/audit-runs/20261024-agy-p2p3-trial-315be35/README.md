# Auditoría independiente de Antigravity: arnés y procedimientos del ensayo P2/P3 (2026-10-24 10:26 UTC)

**Veredicto: REJECT.** Hay 2 hallazgos A, 4 B y 2 C. **El ensayo no se ejecuta** hasta que se corrijan los A y una nueva auditoría lo apruebe.

| Campo | Valor |
|---|---|
| Auditor | Antigravity CLI 1.4.4, uid `aao-auditor-alt`, resolución delegada en #25 |
| Rango | `ef1913799fa5c04534f7f2204ff9d5f7de4eb1d4..315be35e6742504fea7fed0d0c858c6803352dba` (#60 a #70), más los archivos completos `github_trial.py` y `run_trial.sh` |
| Prompt | `docs/audit-prompts/p2p3-trial.md`, sha256 `6272f216…` |
| Informe | [`report.md`](report.md), sha256 `35a74631fa98d555911662d64000b8423221714cd8b17300ee71c2a092323e77` |
| Atestación | [`attestation.json`](attestation.json), sha256 `21037457182506f6b85de2e06e2414f01de99bd687445b0a20fc6b7de973c094` |

**Procedencia.** El CEO ejecutó el auditor como `aao-auditor-alt`. El PM copió el informe y la atestación sin modificarlos.

## Hallazgos A (bloqueantes)
- **A-01:** `run_trial.sh` crea `/var/tmp/aao-trial`, dentro de un directorio con modo 1777, sin comprobar su propietario ni si es un enlace simbólico. Además, ejecuta `git` en los clones de cada rol sin aislarlos de la configuración local. Un agente que cree antes ese directorio puede plantar enlaces simbólicos o un `.git/config` malicioso, y ejecutar código como el CEO, el integrador o el auditor.
- **A-02:** el modo de equivalencia pide un token limitado a un único repositorio. Así, `GET /installation/repositories` no muestra el alcance real de la instalación, y podría registrar «canónico excluido» aunque la App tuviera acceso a él.

## Hallazgos B y C
- **B-01:** la comprobación de rulesets usa el listado, que no incluye `rules` ni `bypass_actors`. Falla en cerrado.
- **B-02:** a `updateRefs` le falta `repositoryId`.
- **B-03:** el rechazo de A-04 ocurre en el cliente, no en el servidor.
- **B-04:** root lee y copia evidencias desde los homes de los roles, lo que abre una ventana TOCTOU, y no comprueba `extra_rc`.
- **C-01:** el registro se lee del árbol de trabajo y no de los objetos git.
- **C-02:** la atribución de P3-12 no es coherente con la de P3-07, y los tests del ejecutor son solo estáticos.

Se corrigen en una rama aparte. Después, nueva auditoría.
