# Procedimiento: GitHub Apps (P2) y rulesets (P3) en el repositorio de ensayo

**Autoridad:** P2 (#29) y P3 (#32), aprobados el 2026-10-23 con sus condiciones: sin gasto, sin transferencia y sin promoción de `main` hasta PASS. **Lo ejecuta el CEO:** crear Apps e instalarlas son acciones de su cuenta de GitHub, y `sudo` está reservado (P5 (a)). AAO solo prepara las herramientas.
**Cuántas Apps:** **9**, una por rol que necesita identidad en GitHub:
- `aao-integrator`, `aao-auditor`, `aao-auditor-alt`, `aao-supervisor`, `aao-notifier` y `aao-pm`;
- `aao-impl-codex`, `aao-impl-claude` y `aao-impl-ag`.

`aao-trust` no tiene identidad en GitHub. El «8» de la propuesta original contaba a los implementadores como una sola fila. Los permisos están en `docs/proposals/github-apps/*.json`.

## 0. Preparar (una vez, unos 2 minutos)

```bash
cd ~/workspace/repos/active/aao && git fetch origin && git checkout <SHA revisado de esta PR>
sudo install -d -o root -g root -m 0755 /opt/aao-p2
sudo install -o root -g root -m 0755 scripts/github_apps/exchange_manifest_code.py /opt/aao-p2/
sudo install -d -o root -g root -m 0755 /opt/aao-p2/github-apps
sudo install -o root -g root -m 0644 docs/proposals/github-apps/*.json /opt/aao-p2/github-apps/
gh repo create autoaiorg/aao-governance-trial --public --description "AAO P2/P3 trial (disposable)" --add-readme
```

## 1. Crear cada App y entregar su clave a su rol (unos 2 minutos por App)

Repite para cada uno de los 9 nombres. Ejemplo con `aao-integrator`:

```bash
python3 scripts/github_apps/create_app_form.py aao-integrator      # escribe /tmp/aao-create-aao-integrator.html
xdg-open /tmp/aao-create-aao-integrator.html                       # pulsa "Create GitHub App"
# GitHub redirige a http://127.0.0.1:9/?code=XXXX&state=YYYY (la página no carga; es normal).
# Comprueba que state coincide con el impreso y copia el valor de code:
sudo -u aao-integrator -H python3 /opt/aao-p2/exchange_manifest_code.py aao-integrator   # pega XXXX y pulsa Enter (stdin, no argv)
```

- La clave privada solo la recibe el uid del rol (`~/.config/aao/<app>.pem`, en `0600`). Nunca pasa por tu cuenta ni por otra.
- El código se puede usar una sola vez y caduca en una hora.
- El script rechaza ejecutarse como root o como un uid distinto del rol.

## 1-bis. Apps de la organización (segunda pasada)

Una App privada solo se puede instalar en la cuenta que es su propietaria. Las 3 de implementador se instalan solo en su fork, dentro de la organización, así que **se crean bajo la organización**. La App de sondeo de A-14 también.

**Primero** (antes de cualquier canje de esta pasada): El script de canje cambia en esta pasada: ahora rechaza guardar la clave si GitHub devuelve permisos distintos de los del manifiesto revisado. Instala la versión revisada y los manifiestos:

```bash
sudo install -o root -g root -m 0755 scripts/github_apps/exchange_manifest_code.py /opt/aao-p2/
sudo install -d -o root -g root -m 0755 /opt/aao-p2/github-apps
sudo install -o root -g root -m 0644 docs/proposals/github-apps/*.json /opt/aao-p2/github-apps/
```

```bash
# Crea la organización gratuita aao-agents en https://github.com/account/organizations/new (plan Free).
sudo useradd --system --create-home --shell /usr/sbin/nologin aao-probe-noworkflows   # uid solo para A-14; se borra al acabar
crear_org() {
  python3 scripts/github_apps/create_app_form.py "$1" --org aao-agents && xdg-open "/tmp/aao-create-$1.html"
  read -r -p "code: " code
  sudo -u "$1" -H python3 /opt/aao-p2/exchange_manifest_code.py "$1" <<<"$code"
}
for app in aao-impl-codex aao-impl-claude aao-impl-ag aao-probe-noworkflows; do crear_org "$app"; done
```

> **Registro (2026-10-24):** las nueve Apps ya están creadas e instaladas; sus identificadores no secretos están en `deploy/github-apps/aao-github-apps-registry.json`. La App de Antigravity se llama **`aao-impl-agy`** (manifiesto `docs/proposals/github-apps/aao-impl-agy.json`) y su clave la custodia el usuario Linux **`aao-impl-ag`**. La autenticación API de cada App se comprueba con `scripts/github_apps/verify_app_auth.py` (§1-ter).

Las Apps de la primera pasada se comprueban a posteriori con `scripts/github_apps/verify_app_permissions.sh <apps...>`; todas deben dar PASS.

## 1-ter. Verificar la autenticación API de las nueve Apps

**Quién:** el CEO (sudo, P5 (a)). Cada comprobación corre **como el uid que custodia la clave**; nadie más lee la clave.
**Qué hace:** con la clave de la App firma un JWT, comprueba `GET /app` (id, slug, permisos frente al manifiesto revisado), la instalación (`app_id`, cuenta, permisos, no suspendida), obtiene un token de instalación, lista los repositorios accesibles y revoca el token. Solo lectura en GitHub. No imprime clave, JWT ni token.
**Repos esperados:** integrador, auditores, supervisor, notifier y PM: `autoaiorg/aao` y, como único añadido, `autoaiorg/aao-governance-trial` (`selected`). Los implementadores: exactamente los forks indicados con `--fork` (de `autoaiorg/aao` o de su repo de ensayo), nunca el canónico (A-10/A-11).

```bash
REPO=$HOME/workspace/repos/active/aao
REV=<SHA de main que contiene este script>
git -C "$REPO" fetch -q origin && git -C "$REPO" cat-file -e "$REV^{commit}"
sudo install -d -o root -g root -m 0755 /opt/aao-p2 /opt/aao-p2/github-apps
git -C "$REPO" show "$REV:scripts/github_apps/verify_app_auth.py" | sudo install -o root -g root -m 0755 /dev/stdin /opt/aao-p2/verify_app_auth.py
git -C "$REPO" show "$REV:deploy/github-apps/aao-github-apps-registry.json" | sudo install -o root -g root -m 0644 /dev/stdin /opt/aao-p2/aao-github-apps-registry.json
for m in $(git -C "$REPO" ls-tree --name-only "$REV" docs/proposals/github-apps/ | grep '\.json$'); do
  git -C "$REPO" show "$REV:$m" | sudo install -o root -g root -m 0644 /dev/stdin "/opt/aao-p2/github-apps/$(basename "$m")"
done
out=~/aao-p2-app-auth-$(date +%Y%m%dT%H%M%S).jsonl
# Tercera columna: solo implementadores. Sustituye cada <forks-...> por TODOS los repos en los que está
# instalada esa App, separados por comas: su fork de producción (padre autoaiorg/aao) y, si ya existe,
# su fork de ensayo del paso 3 (padre autoaiorg/aao-governance-trial). Sus repos accesibles deben
# coincidir exactamente con esa lista. Si aún no hay fork, pon "-": la autenticación se registra igual,
# pero esa fila da FAIL (alcance no demostrado) y el total no llegará a 9.
set -o pipefail; rc=0
while read -r app uid forks; do
  extra=(); [[ $forks != - ]] && for f in ${forks//,/ }; do extra+=(--fork "$f"); done
  sudo -u "$uid" -H /usr/bin/python3 -I /opt/aao-p2/verify_app_auth.py "$app" "${extra[@]}" | tee -a "$out" || rc=1
done <<'APPS'
aao-integrator aao-integrator -
aao-auditor aao-auditor -
aao-auditor-alt aao-auditor-alt -
aao-supervisor aao-supervisor -
aao-notifier aao-notifier -
aao-pm aao-pm -
aao-impl-claude aao-impl-claude <forks-claude>
aao-impl-codex aao-impl-codex <forks-codex>
aao-impl-agy aao-impl-ag <forks-agy>
APPS
pass=$(grep -c '"result": "PASS"' "$out" || true)
# Hacen falta las dos cosas: nueve registros PASS y que ninguna ejecución (ni su tubería) haya fallado.
echo "PASS: $pass/9 rc=$rc"; if [[ $pass == 9 && $rc == 0 ]]; then echo "RESULT: PASS"; else echo "RESULT: FAIL"; false; fi
```

Pega el archivo `$out` completo en el issue de P2. No contiene secretos. Solo `RESULT: PASS` (9/9) demuestra la autenticación y el alcance de las nueve Apps; con forks en `-`, las filas de implementadores dan FAIL, y sus `checks` individuales (`jwt_app_id`, `installation_token_issued`, `token_revoked`…) muestran si la autenticación pasó, pero no demuestran el alcance. Nueve PASS **no** son el ensayo P2/P3: RA sigue en PENDING y el integrador no se activa.

## 2. Instalar las Apps (solo en el repo de ensayo, por ahora)

En la página de cada App, *Install App*, repo `aao-governance-trial` únicamente:

- Integrador, auditores, supervisor, notificador y PM: en el repo de ensayo.
- **Implementadores: no se instalan en el repo de ensayo con escritura.** Se instalan en su **fork** (paso 3). En el repo de ensayo, solo si GitHub permite limitar la instalación a «pull requests». Eso se comprueba en A-11.

## 3. Fork para los implementadores

En la **misma** organización `aao-agents` del §1-bis, haz un fork de `aao-governance-trial` en ella. Instala las 3 Apps de implementador solo en ese fork.

## 4. Rulesets en el repo de ensayo

```bash
INTEGRATOR_ID=$(sudo -u aao-integrator -H python3 -c 'import json,os;print(json.load(open(os.path.expanduser("~/.config/aao/aao-integrator.json")))["id"])')
AUDITOR_ID=$(sudo -u aao-auditor -H python3 -c 'import json,os;print(json.load(open(os.path.expanduser("~/.config/aao/aao-auditor.json")))["id"])')
scripts/github_apps/apply_rulesets.sh autoaiorg/aao-governance-trial "$INTEGRATOR_ID" "$AUDITOR_ID"          # simulación
scripts/github_apps/apply_rulesets.sh autoaiorg/aao-governance-trial "$INTEGRATOR_ID" "$AUDITOR_ID" --apply
```

**Si GitHub rechaza la App como excepción** en un repo de cuenta personal, el script falla y **se detiene**. Según P3, en ese caso se eleva la transferencia a una organización como decisión aparte. Nada se transfiere implícitamente.

## 5. Después

AAO ejecuta las pruebas A-01 a A-14 (P2) y P3-01 a P3-12 en el repo de ensayo. Cada rol actúa con su propia clave desde su uid; la herramienta de pruebas se prepara en la tarea siguiente del tablero (#36). La configuración se aplica al repo canónico **solo** con todas en PASS (P3 §6).

## Revocación (cualquier momento)

En la página de cada App, *Suspend* o *Uninstall* revoca de inmediato. Borrar la clave privada impide emitir tokens nuevos; los ya emitidos caducan en 1 h o menos.
