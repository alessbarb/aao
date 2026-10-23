#!/usr/bin/env bash
# Apply the P3 rulesets (A: main only integrator; B: integrity + required checks; C: tags)
# to a repository. Run by the CEO (repository administrator) with his own gh login.
# Default is a dry run that prints the JSON; --apply sends it.
#
#   scripts/github_apps/apply_rulesets.sh OWNER/REPO INTEGRATOR_APP_ID AUDITOR_APP_ID [--apply]
#
# First target: the public trial repository (P3-01..P3-12). The canonical repository
# only after all trial tests PASS (P3 §6). No bypass for admins or for the CEO.
set -euo pipefail
repo=${1:?OWNER/REPO}; integrator=${2:?integrator app id}; auditor=${3:?auditor app id}; mode=${4:-dry-run}
[[ "$integrator" =~ ^[0-9]+$ && "$auditor" =~ ^[0-9]+$ ]] || { echo "app ids must be numeric" >&2; exit 2; }

ruleset_a=$(cat <<JSON
{"name":"A main: integrator only","target":"branch","enforcement":"active",
 "conditions":{"ref_name":{"include":["refs/heads/main"],"exclude":[]}},
 "bypass_actors":[{"actor_id":$integrator,"actor_type":"Integration","bypass_mode":"always"}],
 "rules":[{"type":"update"},
          {"type":"pull_request","parameters":{"required_approving_review_count":0,"dismiss_stale_reviews_on_push":false,
           "require_code_owner_review":false,"require_last_push_approval":false,"required_review_thread_resolution":false}}]}
JSON
)
ruleset_b=$(cat <<JSON
{"name":"B main+staging: integrity (no bypass)","target":"branch","enforcement":"active",
 "conditions":{"ref_name":{"include":["refs/heads/main","refs/heads/aao-staging/**"],"exclude":[]}},
 "bypass_actors":[],
 "rules":[{"type":"non_fast_forward"},{"type":"deletion"},
          {"type":"required_status_checks","parameters":{"strict_required_status_checks_policy":false,
           "required_status_checks":[{"context":"aao-audit","integration_id":$auditor},{"context":"test"}]}}]}
JSON
)
ruleset_c=$(cat <<JSON
{"name":"C tags","target":"tag","enforcement":"active",
 "conditions":{"ref_name":{"include":["~ALL"],"exclude":[]}},
 "bypass_actors":[{"actor_id":$integrator,"actor_type":"Integration","bypass_mode":"always"}],
 "rules":[{"type":"creation"},{"type":"update"},{"type":"deletion"}]}
JSON
)
for body in "$ruleset_a" "$ruleset_b" "$ruleset_c"; do
  echo "$body" | python3 -m json.tool >/dev/null   # validate JSON before anything is sent
  if [[ "$mode" == --apply ]]; then
    echo "$body" | gh api -X POST "repos/$repo/rulesets" --input - --jq '"created ruleset \(.id): \(.name)"'
  else
    echo "# DRY RUN: would POST repos/$repo/rulesets"; echo "$body" | python3 -m json.tool
  fi
done
if [[ "$mode" == --apply ]]; then
  gh api -X PUT "repos/$repo/actions/permissions/workflow" -f default_workflow_permissions=read -F can_approve_pull_request_reviews=false
  echo "workflow token set to read-only; set 'Require approval for all outside collaborators' in Settings > Actions (no API for personal repos)"
fi
