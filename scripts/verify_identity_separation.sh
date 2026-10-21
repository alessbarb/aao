#!/usr/bin/env bash
# F2 isolation checks (plan §8.1). Run as each AAO role account, from the same
# launch path the agent uses, for example:
#   sudo -u aao-impl-codex -i bash /path/to/verify_identity_separation.sh
#
# Prints PASS or FAIL per check and exits non-zero on any FAIL. Each check
# expects an access attempt to be DENIED for a non-privileged role.
set -uo pipefail

CEO_USER="${CEO_USER:-alessbarb}"
me=$(id -un)
fails=0

expect_denied() {  # description, required path ("-" for none), command to try
  local desc=$1 need=$2; shift 2
  # A missing target would make any access "fail" and look like a PASS.
  # Treat it as NOT RUN, which counts as a failure (fail closed).
  if [[ "$need" != "-" && ! -e "$need" ]]; then
    echo "NOT RUN  $desc (missing $need)"
    fails=$((fails + 1))
    return
  fi
  if "$@" >/dev/null 2>&1; then
    echo "FAIL  $desc"
    fails=$((fails + 1))
  else
    echo "PASS  $desc"
  fi
}

echo "# identity: $(id)"

expect_denied "passwordless sudo"            - sudo -n true
expect_denied "docker socket access"         /var/run/docker.sock test -w /var/run/docker.sock
expect_denied "CEO home readable"            "/home/$CEO_USER" ls "/home/$CEO_USER"
expect_denied "CEO GitHub token readable"    "/home/$CEO_USER" cat "/home/$CEO_USER/.config/gh/hosts.yml"
expect_denied "write to trust registry"      /srv/aao/trust touch /srv/aao/trust/.probe
expect_denied "write to frozen checkouts"    /srv/aao/frozen touch /srv/aao/frozen/.probe

for a in aao-auditor aao-auditor-alt; do
  [[ "$me" == "$a" ]] && continue
  expect_denied "read $a signing key"   "/var/lib/$a" cat "/var/lib/$a/keys/auditor-ed25519.pem"
  expect_denied "write $a ledger"       "/var/lib/$a" touch "/var/lib/$a/ledger/.probe"
done

[[ "$me" != aao-supervisor ]] && expect_denied "write supervisor events" /var/lib/aao-supervisor touch /var/lib/aao-supervisor/events/.probe

shopt -s nullglob
homes=(/home/aao-*)
(( ${#homes[@]} )) || { echo "NOT RUN  role homes (none exist)"; fails=$((fails + 1)); }
for other in "${homes[@]}"; do
  [[ "$other" == "/home/$me" ]] && continue
  expect_denied "read $other" "$other" ls "$other"
done

if (( fails )); then
  echo "# $fails check(s) FAILED for $me"
  exit 1
fi
echo "# all checks PASSED for $me"
