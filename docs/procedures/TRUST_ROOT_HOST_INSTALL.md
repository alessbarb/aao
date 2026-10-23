# Instalación de la raíz de confianza en el host (op. 1 del §12.3)

**Estado:** BORRADOR. No ejecutar hasta que:
- el SHA final de la cadena R1 tenga APPROVE de un revisor no recusado;
- esta página fije ese SHA en `REV`.

**Quién:** el CEO, con sudo (P5 (a)). Ningún agente ejecuta estos pasos.
**Tiempo:** unos 15 minutos. Se hace **una sola vez**. Después, las integraciones R1 no requieren al CEO.
**Deshacer:** `sudo systemctl disable --now aao-supervisor-intake aao-supervisor-heartbeat.timer` y borrar `/etc/aao-audit/trust-anchor.json`. Así el auditor y el integrador fallan cerrados. Los datos no se borran.

```bash
REV=<SHA final auditado>          # sustituye a 97ad4f1
REPO=$HOME/workspace/repos/active/aao
git -C "$REPO" fetch -q origin && git -C "$REPO" cat-file -e "$REV^{commit}"
```

## 1. Árboles congelados y entornos

El árbol del auditor tiene que ser **propiedad de `aao-auditor`**. `auditor_revision()` ejecuta `git rev-parse` en él, y git 2.43 rechaza los repos de otro propietario («dubious ownership»). Nadie más puede escribir en él: E10 lo comprueba.

La venv es de root. El python del sistema no trae pytest ni ruff, que las comprobaciones de la política necesitan.

```bash
for role in aao-auditor aao-supervisor; do
  sudo install -d -o aao-trust -g aao-trust -m 0755 /srv/aao/frozen/$role
  sudo git clone -q --no-hardlinks "$REPO" /srv/aao/frozen/$role/tree
  sudo git -C /srv/aao/frozen/$role/tree -c advice.detachedHead=false checkout -q "$REV"
  sudo git -C /srv/aao/frozen/$role/tree remote remove origin
  sudo python3 -m venv /srv/aao/frozen/$role/venv
  sudo /srv/aao/frozen/$role/venv/bin/pip install -q -r /srv/aao/frozen/$role/tree/deploy/auditor-venv-constraints.txt
done
sudo chown -R aao-auditor:aao-auditor /srv/aao/frozen/aao-auditor/tree
sudo chmod -R go-w /srv/aao/frozen
```

## 2. Unidades, directorios y clave del supervisor

```bash
T=/srv/aao/frozen/aao-supervisor/tree/deploy
sudo install -o root -g root -m 0644 $T/systemd/*.service $T/systemd/*.timer /etc/systemd/system/
sudo install -o root -g root -m 0644 $T/tmpfiles.d/aao-trust-root.conf /etc/tmpfiles.d/
sudo systemd-tmpfiles --create /etc/tmpfiles.d/aao-trust-root.conf
sudo -u aao-supervisor openssl genpkey -algorithm ed25519 -out /var/lib/aao-supervisor/keys/supervisor-ed25519.pem
sudo -u aao-supervisor chmod 0600 /var/lib/aao-supervisor/keys/supervisor-ed25519.pem
sudo -u aao-supervisor openssl pkey -in /var/lib/aao-supervisor/keys/supervisor-ed25519.pem -pubout \
  | sudo install -o aao-trust -g aao-trust -m 0644 /dev/stdin /srv/aao/trust/keys/aao-supervisor-ed25519.pub
```

## 3. Ancla, política, configuración del supervisor y registro

Se generan con el script revisado de la misma revisión: `scripts/make_trust_root_files.py`. **[PENDIENTE: se escribe cuando la prueba E2E fije el formato del registro.]** Los archivos son estos:

| Archivo | Propietario | Modo |
|---|---|---|
| `/etc/aao-audit/trust-anchor.json` | root | 0644 |
| `/etc/aao-supervisor/config.json` | root | 0644 |
| `/srv/aao/trust/registry.json` | aao-trust | 0644 |
| la política en `policy_path` | aao-auditor | 0644 |

`trusted_auditor_revisions = ["$REV"]`.

## 4. Arranque y verificación

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now aao-supervisor-intake.service aao-supervisor-heartbeat.timer
sudo /usr/bin/python3 -I /srv/aao/frozen/aao-supervisor/tree/scripts/verify_trust_root_host.py --expected-revision "$REV" \
  | tee ~/aao-trust-root-verify-$(date +%Y%m%dT%H%M%S).log
```

Hace falta `RESULT: PASS`. Pega el log completo en el issue del arranque.

Si alguna comprobación da FAIL, la raíz de confianza **no** se considera instalada. El auditor y el integrador siguen fallando cerrados, que es el estado seguro.
