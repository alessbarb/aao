# Instalación de la raíz de confianza en `ef19137` (2026-10-24)

**Resultado: PASS**, 38 de 38 comprobaciones de `verify_trust_root_host.py` (sha256 `28eae614…`). Estado copiado sin cambios en [`status.json`](status.json), verificado a las 09:08:10 UTC.

| Campo | Valor |
|---|---|
| Revisión | `ef1913799fa5c04534f7f2204ff9d5f7de4eb1d4` |
| Autorización | el CEO fijó el informe de Antigravity, sha256 `6af12e23…` ([auditoría](../20261024-agy-r1-chain-ef19137/)) |
| Bucle R1 | `autoaiorg/aao-governance-trial` (repo de ensayo) |
| Activado | intake y latido del supervisor, atribución, reverificación diaria y despacho del auditor |
| **No activado** | integrador (sigue apagado hasta que el ensayo P2/P3 dé PASS) |

**Ejecución (CEO, sudo).** `host_bootstrap.sh --apply --trust-root` desde un clon de root en `ef19137`. Hubo tres incidencias, y ninguna eludió un control:
1. **Archivos de auditoría con modo 664.** El ejecutor heredó la umask 002 y el bootstrap rechazó los archivos. El CEO quitó la escritura de grupo como `aao-auditor-alt`, sin tocar el contenido: el hash seguía siendo `6af12e23…`. Corregido en #60.
2. **Faltaban `~/.config/aao/<app>.json` (B-2).** El CEO los escribió desde el registro, cada uno con su uid. Corregido en #60.
3. **S6: faltaba el ledger del auditor.** Sin él, el latido fallaba. El CEO creó un ledger vacío y reejecutó el verificador, que dio PASS. Corregido en #61.

**Limitación.** El bloque que habilitó el despacho no comprobaba el código de salida del verificador, porque estaba enmascarado por una tubería. El `status.json` posterior confirma el PASS.

**Pendiente.** La atribución da HTTP 404 hasta que las Apps estén instaladas en el repo de ensayo. Faltan además el ensayo P2/P3, el piloto R1 y el integrador.
