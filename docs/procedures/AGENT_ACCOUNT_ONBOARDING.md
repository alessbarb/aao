# Procedimiento: cada agente con su propia cuenta (tras P1)

**Estado:** procedimiento preparado. **Lo ejecuta el CEO**, porque requiere `sudo` y el inicio de sesión interactivo en los proveedores. No concede permisos de GitHub, que corresponden a P2.
**Requisito previo:** P1 ejecutado (2026-10-23, 9/9 PASS, Issue #25).

## Por qué

Tras P1 existen las cuentas `aao-*`, pero **los agentes siguen ejecutándose como `alessbarb`**, con tu token de GitHub, `sudo` y `docker`. La separación solo es efectiva cuando cada CLI corre en su cuenta y con sus propias credenciales.

## Reglas

- **Nunca copies** `~/.config/gh`, `~/.claude/.credentials.json`, `~/.codex/` ni `~/.antigravity/` de tu cuenta a una cuenta de agente. Cada cuenta inicia su propia sesión.
- Los agentes **no reciben ningún token de GitHub** hasta P2. Mientras tanto trabajan solo en local; las PR las sigue publicando el coordinador con el token actual (D12, riesgo registrado).
- La cuenta del auditor no tiene shell (`nologin`). Sus procesos se lanzarán como servicios systemd (F4), no por sesión interactiva.

## Pasos (unos 10 minutos)

```bash
# 1. Implementadores y PM: iniciar sesión de cada CLI en su propia cuenta
sudo -u aao-impl-codex  -i codex login           # Codex
sudo -u aao-impl-claude -i claude                # Claude Code: /login dentro de la sesión
sudo -u aao-pm          -i claude                # PM (instancia separada de Claude)
# Antigravity: se decide aparte, porque es una aplicación de escritorio (ver más abajo)

# 2. Clon propio del repositorio en cada cuenta (público, sin credenciales)
for u in aao-pm aao-impl-codex aao-impl-claude aao-impl-ag; do
  sudo -u "$u" -i git clone https://github.com/alessbarb/aao.git
done

# 3. Verificación, desde la ruta real de lanzamiento
for u in aao-pm aao-impl-codex aao-impl-claude aao-impl-ag; do
  sudo -u "$u" -i bash /opt/aao-p1/verify_identity_separation.sh
done
```

**Aceptación:** los 4 roles en PASS, ejecutados desde su ruta de lanzamiento real (`sudo -u <rol> -i`).

## Pendiente de decisión

- **Antigravity** es una aplicación de escritorio (`/usr/bin/antigravity`). Ejecutarla como otra cuenta requiere sesión gráfica propia. Alternativas:
  - (a) usarla solo para la interfaz, sin acceso de escritura al repositorio canónico;
  - (b) un usuario de escritorio separado.

  **Recomendación:** (a) hasta P2.
- **Postgres de desarrollo:** sigue corriendo bajo tu cuenta en `127.0.0.1:54329`. Los agentes lo usan por TCP, sin el socket de `docker`.

## Antigravity como auditor alternativo (resolución delegada en #25)

Para el paquete de la cadena R1 y la raíz inicial, Antigravity actúa como auditor no recusado bajo el uid **`aao-auditor-alt`**. Nunca bajo `aao-impl-ag`, nunca bajo tu cuenta, y sin copiar `~/.antigravity`, `~/.gemini` ni ninguna sesión.

```bash
# 0. Copia root del CLI (el de ~/.local/bin es tuyo y otra cuenta podría modificarlo):
sudo install -o root -g root -m 0755 ~/.local/bin/agy /usr/local/bin/agy
# 1. Una vez: inicia sesión de agy COMO el auditor alternativo. `sudo -u ... -H agy` lanza agy directamente,
#    sin shell de login (la cuenta sigue con nologin). El navegador o el código de dispositivo los completas tú;
#    las credenciales quedan solo en el home de ese uid (el ejecutor comprueba que no hay nada ajeno ahí).
sudo -u aao-auditor-alt -H env -i HOME=/home/aao-auditor-alt PATH=/usr/bin:/bin:/usr/local/bin /usr/local/bin/agy
# 2. Instala el ejecutor revisado (root, solo lectura para el rol).
sudo install -d -o root -g root -m 0755 /opt/aao-audit
sudo install -o root -g root -m 0755 scripts/audit/run_agy_audit.sh /opt/aao-audit/
sudo install -o root -g root -m 0644 docs/audit-prompts/r1-chain.md /opt/aao-audit/
# 3. Auditoría: base 97ad4f1 (último SHA auditado de la pila F4), cabeza = PR #49, que incluye #48.
sudo -u aao-auditor-alt -H /opt/aao-audit/run_agy_audit.sh \
  97ad4f13655aae2b736c7ba6b3d8d666e51d4680 <SHA de cabeza de #49>
# El ejecutor solo acepta /opt/aao-audit/r1-chain.md con el sha256 revisado, fijado en el propio script.
```

El ejecutor hace lo siguiente:
- se niega a correr con otro uid;
- clona el repo público en el SHA fijado;
- ejecuta agy en modo `plan` y `--sandbox`;
- guarda `~/aao-audits/<sha>/{prompt.txt,report.md,attestation.json}`, donde `attestation.json` incluye el estado previo de agy de ese uid como evidencia de no participación.

Pega los dos sha256 y el `report.md` en la PR.
