#!/usr/bin/env bash
# F2 isolation checks (plan §8.1). Run as each AAO role account from the same
# launch path the agent uses, for example:
#   sudo -u aao-impl-codex -i bash /path/to/verify_identity_separation.sh
#
# Each check asks the kernel for effective access with test -r / -w / -x,
# which honours modes, ACLs and group membership. A check passes only when
# the target exists AND access is denied. A missing target is NOT RUN, which
# counts as a failure. Exit status is non-zero on any failure.
#
# Not covered (declared, not implied): polkit rules, cron, systemd lingering,
# setuid binaries and network sockets other than docker. Those belong to the
# host review of P1.
set -uo pipefail

CEO_USER="${CEO_USER:-alessbarb}"
me=$(id -un)
fails=0
pass() { echo "PASS     $1"; }
fail() { echo "FAIL     $1"; fails=$((fails + 1)); }
notrun() { echo "NOT RUN  $1"; fails=$((fails + 1)); }

# denied <r|w|x> <path> <description>
denied() {
  local mode=$1 path=$2 desc=$3 up
  if [[ ! -e "$path" ]]; then
    # Not visible: either it does not exist, or an ancestor blocks traversal.
    # Only the second case is an access denial; the first is NOT RUN.
    up=$(dirname "$path")
    while [[ ! -e "$up" && "$up" != / ]]; do up=$(dirname "$up"); done
    if [[ -d "$up" && ! -x "$up" ]] && is_managed_path "$path"; then
      pass "$desc (denied at $up)"
    else
      notrun "$desc (missing $path)"
    fi
    return
  fi
  if test "-$mode" "$path"; then fail "$desc"; else pass "$desc"; fi
}

# Paths created by identity_separation.sh. When one of them is hidden behind
# an ancestor we cannot traverse, that counts as denial. Any other hidden
# path is NOT RUN.
is_managed_path() {
  case "$1" in
    /var/lib/aao-auditor/*|/var/lib/aao-auditor-alt/*|/var/lib/aao-supervisor/*|/home/aao-*) return 0 ;;
    *) return 1 ;;
  esac
}

echo "# identity: $(id)"

# sudo: a role must have no sudo rights at all, with or without a password.
if out=$(sudo -n -l 2>&1); then
  fail "sudo rights listed: $(echo "$out" | tail -1)"
elif grep -qiE "may not run sudo|not allowed|a password is required|unknown user" <<<"$out"; then
  pass "no passwordless sudo"
else
  notrun "sudo check (unexpected output: $out)"
fi
priv=0
for g in sudo admin wheel docker adm lxd libvirt "$CEO_USER"; do
  if id -nG | tr ' ' '\n' | grep -qx "$g"; then fail "member of privileged group $g"; priv=1; fi
done
(( priv )) || pass "no privileged group membership"

denied w /var/run/docker.sock          "docker socket"
denied x "/home/$CEO_USER"             "enter CEO home"
denied r "/home/$CEO_USER"             "list CEO home"
denied w /srv/aao/trust                "write trust registry"
denied w /srv/aao/trust/keys           "write trust keys"
denied w /srv/aao/frozen               "write frozen checkouts"
for c in /srv/aao/frozen/*/; do denied w "${c%/}" "write ${c%/}"; done

for a in aao-auditor aao-auditor-alt; do
  [[ "$me" == "$a" ]] && continue
  denied x "/var/lib/$a/keys"                         "enter $a keys dir"
  denied w "/var/lib/$a/ledger"                       "write $a ledger"
  # Only the supervisor and the integrator may read ledgers.
  if [[ "$me" != aao-supervisor && "$me" != aao-integrator ]]; then
    denied r "/var/lib/$a/ledger"                     "read $a ledger"
  fi
done

if [[ "$me" != aao-supervisor ]]; then
  denied w /var/lib/aao-supervisor/events "write supervisor events"
fi

# Ptrace of other users' processes must be restricted.
scope=$(cat /proc/sys/kernel/yama/ptrace_scope 2>/dev/null || echo missing)
if [[ "$scope" =~ ^[1-3]$ ]]; then pass "ptrace_scope=$scope"; else fail "ptrace_scope=$scope (expected 1-3)"; fi

shopt -s nullglob
homes=(/home/aao-*)
(( ${#homes[@]} )) || notrun "role homes (none exist)"
for other in "${homes[@]}"; do
  [[ "$other" == "/home/$me" ]] && continue
  denied x "$other" "enter $other"
done

if (( fails )); then echo "# $fails check(s) FAILED for $me"; exit 1; fi
echo "# all checks PASSED for $me"
