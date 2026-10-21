#!/usr/bin/env bash
# Create the AAO role identities and protected directories (plan F2 / proposal P1).
#
# Modes:
#   (default)   dry run: preflight checks plus the list of intended changes
#   --apply     make the changes (root only)
#   --revert    non-destructive rollback (root only): remove the sudoers rule
#               and lock the role accounts. Keys, ledgers and the trust
#               registry are kept so no evidence is lost.
#
# Fail closed: if an existing aao-* account or file does not match the
# expected state (shell, home, supplementary groups, foreign sudoers rules),
# the script stops before changing anything and reports why.
#
# Scope: static identities and file permissions only. Runtime isolation
# (private /tmp, venv, caches, sockets) belongs to the systemd units of F3a.
# Docker containers and the CEO account (CEO_USER) are never modified.
#
# Status: R2 candidate. Do not run on the host before independent review and
# the CEO decision on P1.
set -euo pipefail

CEO_USER="${CEO_USER:-alessbarb}"
MODE="${1:-dry-run}"
case "$MODE" in dry-run|--apply|--revert) ;; *) echo "usage: $0 [--apply|--revert]" >&2; exit 2;; esac
APPLY=0; [[ "$MODE" == --apply ]] && APPLY=1

AGENT_USERS=(aao-pm aao-impl-codex aao-impl-claude aao-impl-ag)
AUDITORS=(aao-auditor aao-auditor-alt)
SERVICE_USERS=("${AUDITORS[@]}" aao-integrator aao-supervisor aao-notifier aao-trust)
ALL_USERS=("${AGENT_USERS[@]}" "${SERVICE_USERS[@]}")
SUDOERS=/etc/sudoers.d/aao-launch
MARKER="# Managed by scripts/identity_separation.sh"

# The only supplementary groups each role may have. Anything else is rejected.
declare -A ALLOWED_GROUPS=(
  [aao-integrator]="aao-ledger-read"
  [aao-supervisor]="aao-ledger-read"
  [aao-notifier]="aao-events"
)

expected_shell() {
  local u
  for u in "${AGENT_USERS[@]}"; do [[ "$1" == "$u" ]] && { echo /bin/bash; return; }; done
  echo /usr/sbin/nologin
}

run() { printf '+ %s\n' "$*"; if (( APPLY )); then "$@"; fi; }
die() { echo "PREFLIGHT FAIL: $*" >&2; exit 1; }

if [[ "$MODE" != dry-run ]] && (( EUID != 0 )); then die "$MODE requires root"; fi

# ---------- revert ----------
if [[ "$MODE" == --revert ]]; then
  if [[ -f "$SUDOERS" ]]; then
    grep -qxF "$MARKER" "$SUDOERS" || die "$SUDOERS is not managed by this script; leaving it untouched"
    rm -f "$SUDOERS"; echo "+ removed $SUDOERS"
  fi
  for u in "${ALL_USERS[@]}"; do
    if id "$u" >/dev/null 2>&1; then
      usermod -L -s /usr/sbin/nologin "$u"; echo "+ locked $u"
    fi
  done
  echo "Reverted. Data under /var/lib/aao-* and /srv/aao is kept. Remove it by hand only after archiving the evidence."
  exit 0
fi

# ---------- preflight (no changes) ----------
echo "# preflight"
id "$CEO_USER" >/dev/null 2>&1 || die "CEO account $CEO_USER not found"
for u in "${ALL_USERS[@]}"; do
  id "$u" >/dev/null 2>&1 || continue
  shell=$(getent passwd "$u" | cut -d: -f7); home=$(getent passwd "$u" | cut -d: -f6)
  [[ "$shell" == "$(expected_shell "$u")" ]] || die "$u has shell $shell, expected $(expected_shell "$u")"
  [[ "$home" == "/home/$u" ]] || die "$u has home $home, expected /home/$u"
  for g in $(id -nG "$u"); do
    [[ "$g" == "$u" ]] && continue
    [[ " ${ALLOWED_GROUPS[$u]:-} " == *" $g "* ]] || die "$u is in unexpected group '$g'"
  done
done
# No other sudoers rule may mention a role account (e.g. leftovers from manual setup).
if [[ -d /etc/sudoers.d ]]; then
  for f in /etc/sudoers /etc/sudoers.d/*; do
    [[ -f "$f" && "$f" != "$SUDOERS" ]] || continue
    if grep -Eq '(^|[^[:alnum:]_-])aao-' "$f" 2>/dev/null; then die "foreign sudoers rule mentions aao- in $f"; fi
  done
fi
if [[ -f "$SUDOERS" ]] && ! grep -qxF "$MARKER" "$SUDOERS"; then die "$SUDOERS exists and is not managed by this script"; fi
echo "# preflight OK"
echo "# docker group members (not modified): $(getent group docker | cut -d: -f4)"
(( APPLY )) || echo "# DRY RUN: no changes will be made."

# ---------- apply ----------
ensure_group() { getent group "$1" >/dev/null || run groupadd --system "$1"; }
ensure_user() {
  id "$1" >/dev/null 2>&1 || run useradd --create-home --home-dir "/home/$1" --shell "$(expected_shell "$1")" --user-group "$1"
  run chmod 0700 "/home/$1"
}
ensure_dir() { run install -d -o "$2" -g "$3" -m "$4" "$1"; }  # path owner group mode

ensure_group aao-ledger-read
ensure_group aao-events
for u in "${ALL_USERS[@]}"; do ensure_user "$u"; done
for u in "${!ALLOWED_GROUPS[@]}"; do run usermod -aG "${ALLOWED_GROUPS[$u]}" "$u"; done

# Auditors: each keeps its own private key; its ledger is readable by the
# supervisor and the integrator only. The two auditors cannot read each other.
for a in "${AUDITORS[@]}"; do
  ensure_dir "/var/lib/$a"        "$a" aao-ledger-read 0750
  ensure_dir "/var/lib/$a/keys"   "$a" "$a"            0700
  ensure_dir "/var/lib/$a/ledger" "$a" aao-ledger-read 0750
done

ensure_dir /var/lib/aao-supervisor        aao-supervisor aao-events 0750
ensure_dir /var/lib/aao-supervisor/events aao-supervisor aao-events 0750

# Trust registry and one frozen checkout per component, owned by aao-trust.
# No role can write here, so no auditor can change its own code, key or policy.
ensure_dir /srv/aao             aao-trust aao-trust 0755
ensure_dir /srv/aao/trust       aao-trust aao-trust 0755
ensure_dir /srv/aao/trust/keys  aao-trust aao-trust 0755
ensure_dir /srv/aao/frozen      aao-trust aao-trust 0755
for c in "${AUDITORS[@]}" aao-integrator aao-supervisor; do
  ensure_dir "/srv/aao/frozen/$c" aao-trust aao-trust 0755
done

# Key path used by independent_audit.py:  --key /var/lib/<auditor>/keys/auditor-ed25519.pem
# The public key goes to the trust registry. policy.json is R3 trust root and is NOT written here.
for a in "${AUDITORS[@]}"; do
  key="/var/lib/$a/keys/auditor-ed25519.pem"
  pub="/srv/aao/trust/keys/$a-ed25519.pub"
  if (( APPLY )); then
    if [[ ! -f "$key" ]]; then
      runuser -u "$a" -- sh -c "umask 077 && openssl genpkey -algorithm ed25519 -out '$key'"
      echo "+ generated $key as $a"
    fi
    runuser -u "$a" -- openssl pkey -in "$key" -pubout > "$pub"
    chown aao-trust:aao-trust "$pub"; chmod 0644 "$pub"
    echo "+ published $pub"
  else
    echo "+ (would generate $key as $a if absent and publish $pub)"
  fi
done

# The CEO may launch AGENTS only. Auditors are not reachable through sudo;
# they run as systemd services (F3a). The rule still requires the CEO password.
rule="$CEO_USER ALL=($(IFS=,; echo "${AGENT_USERS[*]}")) ALL"
if (( APPLY )); then
  tmp=$(mktemp)
  printf '%s\n' "$MARKER" "$rule" > "$tmp"
  visudo -cf "$tmp" >/dev/null
  install -o root -g root -m 0440 "$tmp" "$SUDOERS"
  rm -f "$tmp"
  echo "+ wrote $SUDOERS"
else
  echo "+ (would write $SUDOERS: $rule)"
fi

cat <<'EOF'

Next steps (manual, one time):
  1. Log in each agent CLI as its own user, e.g.  sudo -u aao-impl-codex -i codex login
     Never copy the CEO's GitHub token (~/.config/gh) into an agent account.
  2. Clone the repository inside each agent home (not a shared working copy).
  3. Leave PostgreSQL running from the CEO account; agents reach it over
     TCP at 127.0.0.1:54329 and never use the docker socket.
  4. Run scripts/verify_identity_separation.sh as every role and attach the output to the F2 evidence.
  Rollback:  sudo scripts/identity_separation.sh --revert
EOF
