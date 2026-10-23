#!/usr/bin/env bash
# Post-hoc check for Apps already exchanged: the permissions GitHub reported at creation (stored in the
# role's metadata) must equal the reviewed manifest. Run as the CEO; reads each role's metadata via sudo.
# Usage: scripts/github_apps/verify_app_permissions.sh aao-integrator aao-auditor ...
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
fail=0
for app in "$@"; do
  want=$(python3 -c 'import json,sys;print(json.dumps(json.load(open(sys.argv[1]))["default_permissions"],sort_keys=True))' \
         "$here/../../docs/proposals/github-apps/$app.json")
  uid=$app; [[ $app == aao-impl-agy ]] && uid=aao-impl-ag
  got=$(sudo -u "$uid" -H python3 -c 'import json,os,sys;print(json.dumps(json.load(open(os.path.expanduser("~/.config/aao/"+sys.argv[1]+".json")))["permissions"],sort_keys=True))' "$app")
  if [[ "$want" == "$got" ]]; then echo "PASS $app $got"; else echo "FAIL $app expected=$want got=$got"; fail=1; fi
done
exit $fail
