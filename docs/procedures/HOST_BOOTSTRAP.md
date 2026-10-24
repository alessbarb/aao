# Arranque completo de un host AAO (`scripts/bootstrap/host_bootstrap.sh`)

**Quién:** el CEO, con sudo (P5 (a)). Ningún agente ejecuta estos pasos.
**Para qué:** dejar un host nuevo en el mismo estado que el actual, o mover AAO de una máquina a otra.
**Qué hace:** encadena las piezas revisadas, en este orden:
1. cuentas y directorios de P1;
2. claves de las Apps, cada una en su uid;
3. verificación 9/9 de las Apps;
4. Antigravity como auditor alternativo;
5. de forma opcional, la raíz de confianza.

**El integrador queda apagado.** Solo se enciende con `--enable-integrator`, y el script se niega mientras algún RA del registro instalado no esté en PASS.

Por defecto el script **simula**: imprime lo que haría sin cambiar nada. Con `--apply` lo hace. Falla en cerrado y nunca regenera una clave privada que ya exista. Las fases 1 a 4 se pueden repetir sin riesgo. La fase de la raíz de confianza solo corre en un host que no tenga ninguna instalada: si ya existe cualquiera de sus archivos, se niega antes de escribir nada. Rotar la raíz es otro procedimiento.

## 0. Requisitos del host

Ubuntu 24.04 o equivalente, con `git` ≥ 2.38, `python3`, `python3-venv`, `openssl`, `systemd` y `acl`:

```bash
sudo apt-get install -y git python3 python3-venv openssl acl
```

## 1. Clon de root en la revisión exacta

El script nunca corre desde tu copia de trabajo: los agentes pueden escribir en ella, incluido `.git`. Root clona el repo público en un directorio suyo y comprueba el SHA:

```bash
REV=<SHA de main auditado>       # 40 hex
sudo rm -rf /root/aao-src
sudo env -i PATH=/usr/bin:/bin HOME=/root GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 GIT_NO_REPLACE_OBJECTS=1 \
  git -c core.hooksPath=/dev/null clone -q https://github.com/autoaiorg/aao.git /root/aao-src
sudo git -C /root/aao-src -c advice.detachedHead=false checkout -q "$REV"
[ "$(sudo git -C /root/aao-src rev-parse HEAD)" = "$REV" ] && echo "clon OK en $REV"
B="sudo /root/aao-src/scripts/bootstrap/host_bootstrap.sh --rev $REV --ceo-user $USER"
```

## 2. Claves de las GitHub Apps

Hay dos caminos. Elige uno:

- **(a) Traer las claves de la máquina anterior, de root a root.** Copia `/home/<uid>/.config/aao/<app>.pem` de cada App a un directorio de root en la máquina nueva: `/root/aao-keys`, modo 0700, con los nueve archivos `<app>.pem` (`aao-impl-agy.pem` incluido). El script rechaza cualquier directorio bajo `/home` o `/tmp`.
- **(b) Generar claves nuevas** en la configuración de cada App en GitHub (*Private keys → Generate*). GitHub descarga el `.pem` en tu home, donde los agentes pueden leerlo. Para este camino:
  1. Para antes las sesiones de los agentes.
  2. Mueve los archivos a `/root/aao-keys` nada más descargarlos.
  3. Ejecuta `shred -u` sobre las descargas.

  Después revoca en GitHub las claves de la máquina anterior.

## 3. Ejecución

```bash
$B                                            # simulación: revisa la salida
$B --apply --keys-dir /root/aao-keys          # P1 + claves + 9/9 + Antigravity
```

**agy.** Se instala solo contra un hash que das tú: `--agy ~/.local/bin/agy --agy-sha256 <hex>`. Calcula ese hash con `sha256sum` sobre el binario que descargaste de la fuente oficial, no sobre uno que hayan podido tocar los agentes. Si ya hay un `/usr/local/bin/agy`, el script lo deja como está.

Si nunca has iniciado sesión de agy como `aao-auditor-alt` en esta máquina, el script imprime el comando de login. Hazlo una vez y une la URL en **una sola línea** antes de abrirla.

Luego, la auditoría independiente de la revisión que vas a instalar:

```bash
sudo -u aao-auditor-alt -H /opt/aao-audit/run_agy_audit.sh <base auditada> "$REV"
```

Instala la raíz de confianza solo si el `report.md` dice **APPROVE**:

```bash
$B --apply --keys-dir /root/aao-keys --trust-root --loop-repo <OWNER/REPO>
```

`--loop-repo` es el repo que servirá el bucle R1. Hasta que pase el ensayo P2/P3, debe ser el repo de ensayo, que tienes que crear tú (`autoaiorg/aao-governance-trial`, ver `P2_P3_TRIAL_SETUP.md`).

El script lee la auditoría de ese mismo `REV` en `/home/aao-auditor-alt/aao-audits/$REV/`, donde solo escribe `aao-auditor-alt`. Comprueba que el sha256 del informe coincide con la atestación y que el veredicto es APPROVE; si no, se niega. Después verifica el host y exige `RESULT: PASS`. Después activa la reverificación diaria y el despacho del auditor, pero **no** el integrador. Los logs quedan en `/var/log/aao-bootstrap/<fecha>/`.

Cuando el ensayo P2/P3 dé PASS y reinstales el registro con los RA en PASS:

```bash
$B --apply --keys-dir /root/aao-keys --enable-integrator
```

## 4. Si es un traslado: la máquina anterior

Haz esto **antes** de activar el bucle en la máquina nueva, para que nunca haya dos integradores con claves válidas a la vez:

```bash
sudo systemctl disable --now aao-integrator-tick.timer aao-auditor-dispatch.path aao-auditor-dispatch.timer \
  aao-supervisor-intake.service aao-supervisor-heartbeat.timer aao-trust-root-verify.timer 2>/dev/null
sudo /root/aao-src/scripts/identity_separation.sh --purge    # (clon de root del paso 1) archiva ledgers, claves y registro en /root/aao-identity-archive-*.tar.gz
```

Guarda el archivo `.tar.gz`, porque los logs no se borran. Si usaste el camino (b), revoca en GitHub las claves antiguas de las Apps en cuanto la máquina nueva dé 9/9.
