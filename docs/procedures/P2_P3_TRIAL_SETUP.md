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
gh repo create alessbarb/aao-governance-trial --public --description "AAO P2/P3 trial (disposable)" --add-readme
```

## 1. Crear cada App y entregar su clave a su rol (unos 2 minutos por App)

Repite para cada uno de los 9 nombres. Ejemplo con `aao-integrator`:

```bash
python3 scripts/github_apps/create_app_form.py aao-integrator      # escribe /tmp/aao-create-aao-integrator.html
xdg-open /tmp/aao-create-aao-integrator.html                       # pulsa "Create GitHub App"
# GitHub redirige a http://127.0.0.1:9/?code=XXXX&state=YYYY (la página no carga; es normal).
# Comprueba que state coincide con el impreso y copia el valor de code:
sudo -u aao-integrator -H python3 /opt/aao-p2/exchange_manifest_code.py aao-integrator XXXX
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
  sudo -u "$1" -H python3 /opt/aao-p2/exchange_manifest_code.py "$1" "$code"
}
for app in aao-impl-codex aao-impl-claude aao-impl-ag aao-probe-noworkflows; do crear_org "$app"; done
```

Las Apps de la primera pasada se comprueban a posteriori con `scripts/github_apps/verify_app_permissions.sh <apps...>`; todas deben dar PASS.

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
scripts/github_apps/apply_rulesets.sh alessbarb/aao-governance-trial "$INTEGRATOR_ID" "$AUDITOR_ID"          # simulación
scripts/github_apps/apply_rulesets.sh alessbarb/aao-governance-trial "$INTEGRATOR_ID" "$AUDITOR_ID" --apply
```

**Si GitHub rechaza la App como excepción** en un repo de cuenta personal, el script falla y **se detiene**. Según P3, en ese caso se eleva la transferencia a una organización como decisión aparte. Nada se transfiere implícitamente.

## 5. Después

AAO ejecuta las pruebas A-01 a A-14 (P2) y P3-01 a P3-12 en el repo de ensayo. Cada rol actúa con su propia clave desde su uid; la herramienta de pruebas se prepara en la tarea siguiente del tablero (#36). La configuración se aplica al repo canónico **solo** con todas en PASS (P3 §6).

## Revocación (cualquier momento)

En la página de cada App, *Suspend* o *Uninstall* revoca de inmediato. Borrar la clave privada impide emitir tokens nuevos; los ya emitidos caducan en 1 h o menos.
