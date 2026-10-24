#!/usr/bin/env bash
# Bootstrap an AAO host from zero, by chaining the reviewed pieces in this repository.
#
# Run ONLY as root, from a root-owned clone checked out at the exact REV (see
# docs/procedures/HOST_BOOTSTRAP.md for the stub that makes that clone). Never from a
# working tree an agent can write.
#
#   host_bootstrap.sh --rev <40-hex> --ceo-user <name> [--apply] [phases/options]
#
# Phases (in order; each ends with its own check and stops on failure):
#   identities   P1 accounts, groups, directories, auditor keys   (scripts/identity_separation.sh)
#   app-keys     each GitHub App key into its uid's ~/.config/aao  (--keys-dir, root-owned 0700)
#   p2-verify    the nine Apps authenticate, permissions = manifests, exact repo scope (9/9 required)
#   antigravity  root copy of agy, audit runner + pinned prompt, read-only allowlist for aao-auditor-alt
#   trust-root   OPT-IN (--trust-root): frozen trees, units, supervisor/integrator keys, anchor,
#                registry (RA PENDING), verifier PASS, auditor dispatch. The integrator stays OFF.
#   integrator   OPT-IN (--enable-integrator): only if every RA in the installed registry is PASS.
#
# Default is a dry run that prints what it would do. Idempotent and fail closed: it never
# regenerates an existing private key, never overwrites an installed trust anchor or ledger.
set -euo pipefail
umask 022

die() { echo "FAIL: $*" >&2; exit 1; }
say() { echo "== $*"; }
APPLY=0 REV="" CEO="" KEYS_DIR="" AGY_SRC="" TRUST_ROOT=0 LOOP_REPO="" ATTEST="" ENABLE_INTEGRATOR=0
while [[ $# -gt 0 ]]; do
  case $1 in
    --apply) APPLY=1;;
    --rev) REV=$2; shift;;
    --ceo-user) CEO=$2; shift;;
    --keys-dir) KEYS_DIR=$2; shift;;
    --agy) AGY_SRC=$2; shift;;
    --trust-root) TRUST_ROOT=1;;
    --loop-repo) LOOP_REPO=$2; shift;;
    --audit-attestation) ATTEST=$2; shift;;
    --enable-integrator) ENABLE_INTEGRATOR=1;;
    *) die "unknown option $1 (see the header of $0)";;
  esac
  shift
done
run() { if ((APPLY)); then "$@"; else printf 'DRY:'; printf ' %q' "$@"; echo; fi; }

# ---------- 0. preflight ----------
say "preflight"
[[ $EUID -eq 0 ]] || die "run as root"
[[ $REV =~ ^[0-9a-f]{40}$ ]] || die "--rev must be a full 40-hex SHA"
[[ -n $CEO ]] && getent passwd "$CEO" >/dev/null || die "--ceo-user must name an existing account"
SRC=$(cd "$(dirname "$0")/../.." && pwd)
# Every git call: no system/global config, no hooks, no replace refs, no prompt.
g() { env -i PATH=/usr/bin:/bin HOME=/nonexistent LANG=C.UTF-8 GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 \
        GIT_NO_REPLACE_OBJECTS=1 GIT_TERMINAL_PROMPT=0 git -c core.hooksPath=/dev/null -c safe.directory="*" "$@"; }
[[ $(stat -c %u "$SRC") == 0 && $(stat -c %u "$SRC/.git") == 0 ]] || die "$SRC must be a root-owned clone"
[[ $(g -C "$SRC" rev-parse HEAD) == "$REV" ]] || die "$SRC is not checked out at $REV"
[[ -z $(g -C "$SRC" status --porcelain) ]] || die "$SRC has local changes"
for tool in git python3 openssl systemctl systemd-tmpfiles runuser install getfacl; do command -v $tool >/dev/null || die "missing $tool (packages: git python3 python3-venv openssl systemd acl)"; done
python3 -c 'import venv, ensurepip' 2>/dev/null || die "python3-venv is missing"
gv=$(git --version | awk '{print $3}'); [[ $(printf '%s\n2.38\n' "$gv" | sort -V | head -1) == 2.38 ]] || die "git >= 2.38 required (merge-tree --write-tree), found $gv"
REGISTRY=$SRC/deploy/github-apps/aao-github-apps-registry.json
LOG=/var/log/aao-bootstrap/$(date +%Y%m%dT%H%M%S); ((APPLY)) && install -d -m 0755 "$LOG" || LOG=$(mktemp -d)
echo "rev=$REV ceo=$CEO src=$SRC apply=$APPLY log=$LOG"
# Fork scope of each implementer App (verify_app_auth --fork). Change here if the forks move.
declare -A FORKS=([aao-impl-claude]=autoaiorg/aao-claude [aao-impl-codex]=autoaiorg/aao-codex [aao-impl-agy]=autoaiorg/aao-agy)
apps() { python3 -I -c 'import json,sys
for a in json.load(open(sys.argv[1]))["apps"]: print(a["name"], a["linux_uid"], a["key_file"])' "$REGISTRY"; }

# ---------- 1. identities ----------
say "identities (P1)"
if ((APPLY)); then CEO_USER=$CEO "$SRC/scripts/identity_separation.sh" --apply; else CEO_USER=$CEO "$SRC/scripts/identity_separation.sh"; fi

# ---------- 2. App keys ----------
say "app-keys"
if [[ -n $KEYS_DIR ]]; then
  kd=$(realpath -e "$KEYS_DIR")
  [[ $kd != /home/* && $kd != /tmp/* ]] || die "--keys-dir must be outside /home and /tmp (agents can read those)"
  [[ $(stat -c '%u %a' "$kd") == "0 700" ]] || die "--keys-dir must be root:0700"
fi
missing=0
while read -r app uid key; do
  home=$(getent passwd "$uid" | cut -d: -f6) || die "no account $uid"
  [[ $key == "$home/.config/aao/$app.pem" ]] || die "registry key_file for $app is not $home/.config/aao/$app.pem"
  if [[ -f $key ]]; then
    [[ $(stat -c '%U %a' "$key") == "$uid 600" ]] || die "$key exists but is not $uid:0600"
    echo "ok   $app key present"; continue
  fi
  if [[ -n $KEYS_DIR && -f $kd/$app.pem ]]; then
    [[ ! -L $kd/$app.pem && $(stat -c %u "$kd/$app.pem") == 0 ]] || die "$kd/$app.pem must be a root-owned regular file"
    run install -d -o "$uid" -g "$uid" -m 0700 "$home/.config" "$home/.config/aao"
    run install -o "$uid" -g "$uid" -m 0600 "$kd/$app.pem" "$key"
    echo "new  $app key installed for $uid"
  else
    echo "MISSING $app key ($key)"; missing=1
  fi
done < <(apps)
((missing == 0 || APPLY == 0)) || die "App keys missing: put <app>.pem in --keys-dir (see HOST_BOOTSTRAP.md)"

# ---------- 3. P2 verification ----------
say "p2-verify (9/9 required)"
run install -d -o root -g root -m 0755 /opt/aao-p2 /opt/aao-p2/github-apps
run install -o root -g root -m 0755 "$SRC/scripts/github_apps/verify_app_auth.py" /opt/aao-p2/
run install -o root -g root -m 0644 "$REGISTRY" /opt/aao-p2/
for m in "$SRC"/docs/proposals/github-apps/*.json; do run install -o root -g root -m 0644 "$m" /opt/aao-p2/github-apps/; done
if ((APPLY)); then
  pass=0
  while read -r app uid _; do
    extra=(); [[ -n ${FORKS[$app]:-} ]] && extra=(--fork "${FORKS[$app]}")
    if runuser -u "$uid" -- env -i HOME="$(getent passwd "$uid" | cut -d: -f6)" PATH=/usr/bin:/bin \
         /usr/bin/python3 -I /opt/aao-p2/verify_app_auth.py "$app" "${extra[@]}" >> "$LOG/app-auth.jsonl"; then
      pass=$((pass + 1))
    fi
  done < <(apps)
  echo "app auth: $pass/9 ($LOG/app-auth.jsonl)"; [[ $pass == 9 ]] || die "App verification not 9/9"
fi

# ---------- 4. Antigravity (alternate auditor) ----------
say "antigravity"
AGY_SRC=${AGY_SRC:-$(getent passwd "$CEO" | cut -d: -f6)/.local/bin/agy}
if [[ -f $AGY_SRC ]]; then run install -o root -g root -m 0755 "$AGY_SRC" /usr/local/bin/agy; else echo "WARN: no agy at $AGY_SRC (--agy PATH); skipping"; fi
run install -d -o root -g root -m 0755 /opt/aao-audit
run install -o root -g root -m 0755 "$SRC/scripts/audit/run_agy_audit.sh" /opt/aao-audit/
run install -o root -g root -m 0644 "$SRC/docs/audit-prompts/r1-chain.md" /opt/aao-audit/
alt_home=$(getent passwd aao-auditor-alt | cut -d: -f6)
# Only single read-only git commands; agy denies everything else in print mode (see the audit prompt).
run runuser -u aao-auditor-alt -- env -i HOME="$alt_home" PATH=/usr/bin:/bin /usr/bin/python3 -I -c '
import json, os
p = os.path.expanduser("~/.gemini/antigravity-cli/settings.json")
os.makedirs(os.path.dirname(p), mode=0o700, exist_ok=True)
d = json.load(open(p)) if os.path.exists(p) else {}
d.setdefault("permissions", {})["allow"] = ["command(git diff)", "command(git show)", "command(git log)",
                                            "command(git ls-files)", "command(git grep)"]
fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
os.write(fd, (json.dumps(d, indent=1) + "\n").encode()); os.close(fd)'
if runuser -u aao-auditor-alt -- test -s "$alt_home/.gemini/antigravity-cli/antigravity-oauth-token"; then
  echo "ok   agy session present for aao-auditor-alt"
else
  echo "TODO agy login (interactive, once):"
  echo "     sudo -u aao-auditor-alt -H env -i HOME=$alt_home PATH=/usr/bin:/bin:/usr/local/bin /usr/local/bin/agy"
  echo "     Join the printed URL into ONE line before opening it."
fi

# ---------- 5. trust root (opt-in) ----------
if ((TRUST_ROOT)); then
  say "trust-root"
  [[ $LOOP_REPO =~ ^[A-Za-z0-9-]+/[A-Za-z0-9._-]+$ ]] || die "--loop-repo OWNER/REPO is required (the repo the R1 loop serves)"
  [[ -f $ATTEST ]] || die "--audit-attestation <attestation.json of the Antigravity audit of $REV> is required"
  python3 -I -c 'import json,sys; a=json.load(open(sys.argv[1]))
assert a["head"]==sys.argv[2] and a["os_user"]=="aao-auditor-alt" and a["auditor"]=="antigravity", "attestation is not for this REV"' \
    "$ATTEST" "$REV" || die "attestation does not cover $REV"
  echo "audit attestation sha256=$(sha256sum "$ATTEST" | cut -d' ' -f1) (its report must say APPROVE: the CEO checks it)"
  [[ ! -e /etc/aao-audit/trust-anchor.json ]] || die "a trust anchor is already installed; rotation is a separate, reviewed procedure"
  for role in aao-auditor aao-supervisor aao-integrator; do
    f=/srv/aao/frozen/$role
    [[ -e $f/tree ]] && die "$f/tree exists; remove it deliberately before a fresh bootstrap"
    run g clone -q --no-hardlinks "$SRC" "$f/tree"
    run g -C "$f/tree" -c advice.detachedHead=false checkout -q "$REV"
    run g -C "$f/tree" remote remove origin
    run python3 -m venv "$f/venv"
    run "$f/venv/bin/pip" install -q -r "$f/tree/deploy/auditor-venv-constraints.txt"
  done
  run chown -R aao-auditor:aao-auditor /srv/aao/frozen/aao-auditor/tree
  run chmod -R go-w /srv/aao/frozen
  T=$SRC/deploy
  run install -o root -g root -m 0644 "$T"/systemd/*.service "$T"/systemd/*.timer "$T"/systemd/*.path /etc/systemd/system/
  run install -o root -g root -m 0644 "$T/tmpfiles.d/aao-trust-root.conf" /etc/tmpfiles.d/
  run systemd-tmpfiles --create /etc/tmpfiles.d/aao-trust-root.conf
  newkey() {  # uid private public: never overwrite an existing key
    if [[ -e $2 ]]; then echo "ok   $2 exists (kept)"; return; fi
    run runuser -u "$1" -- sh -c "umask 077 && openssl genpkey -algorithm ed25519 -out '$2'"
    if ((APPLY)); then runuser -u "$1" -- openssl pkey -in "$2" -pubout | install -o aao-trust -g aao-trust -m 0644 /dev/stdin "$3"; fi
  }
  newkey aao-supervisor /var/lib/aao-supervisor/keys/supervisor-ed25519.pem /srv/aao/trust/keys/aao-supervisor-ed25519.pub
  newkey aao-integrator /var/lib/aao-integrator/integrator-ed25519.pem /srv/aao/trust/keys/aao-integrator-ed25519.pub
  G=$(mktemp -d)/out
  run /usr/bin/python3 -I /srv/aao/frozen/aao-supervisor/tree/scripts/make_trust_root_files.py --revision "$REV" \
    --policy-template /srv/aao/frozen/aao-supervisor/tree/docs/audit-runs/20261019-provisional/policy.json \
    --developer "$CEO" --repo "$LOOP_REPO" --out "$G"
  run install -d -o root -g root -m 0755 /etc/aao-audit /etc/aao-supervisor /etc/aao-integrator
  run install -o root -g root -m 0644 "$G/integrator-config.json" /etc/aao-integrator/config.json
  run install -o root -g root -m 0644 "$G/dispatch.json" /etc/aao-audit/dispatch.json
  run install -o root -g root -m 0644 "$G/trust-anchor.json" /etc/aao-audit/trust-anchor.json
  run install -o root -g root -m 0644 "$G/supervisor-config.json" /etc/aao-supervisor/config.json
  run install -o aao-trust -g aao-trust -m 0644 "$G/registry.json" /srv/aao/trust/registry.json
  run install -o aao-auditor -g aao-auditor -m 0644 "$G/policy.json" /var/lib/aao-auditor/policy.json
  if [[ ! -e /etc/aao-audit/ledger.anchor ]]; then
    ((APPLY)) && printf '%064d\n' 0 | install -o root -g root -m 0644 /dev/stdin /etc/aao-audit/ledger.anchor
  fi
  ((APPLY)) && echo "$REV" | install -o root -g root -m 0644 /dev/stdin /etc/aao-audit/expected-revision
  run systemctl daemon-reload
  run systemctl enable --now aao-supervisor-intake.service aao-supervisor-heartbeat.timer
  if ((APPLY)); then
    /usr/bin/python3 -I /srv/aao/frozen/aao-supervisor/tree/scripts/verify_trust_root_host.py --expected-revision "$REV" \
      --status-file /var/lib/aao-trust-verify/status.json | tee "$LOG/trust-root-verify.log" \
      || die "host verification FAILED: the auditor dispatch is NOT enabled ($LOG/trust-root-verify.log)"
  fi
  # Audits run; the integrator stays OFF (CEO order: not before P2/P3 PASS).
  run systemctl enable --now aao-trust-root-verify.timer aao-auditor-dispatch.path aao-auditor-dispatch.timer
fi

# ---------- 6. integrator (opt-in, gated on RA PASS) ----------
if ((ENABLE_INTEGRATOR)); then
  say "integrator"
  python3 -I -c 'import json,sys; s=json.load(open(sys.argv[1]))["ra_status"]
bad=[k for k,v in s.items() if v!="PASS"]; sys.exit("RA not PASS: "+", ".join(bad) if bad else 0)' /srv/aao/trust/registry.json \
    || die "the integrator stays off until the P2/P3 trial sets every RA to PASS in the registry"
  run systemctl enable --now aao-integrator-tick.timer
fi
say "done (apply=$APPLY). Log: $LOG"
