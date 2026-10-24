#!/bin/bash -p
set -euo pipefail
[[ $- == *p* ]] || { echo 'FAIL: invoke directly as root' >&2; exit 2; }
export PATH=/usr/sbin:/usr/bin:/sbin:/bin HOME=/root LANG=C.UTF-8
unset BASH_ENV ENV CDPATH GLOBIGNORE PYTHONPATH PYTHONHOME PYTHONSTARTUP LD_PRELOAD LD_LIBRARY_PATH
REV= ONLY=()
while (($#)); do case $1 in
  --rev) (($# >= 2)) || exit 2; REV=$2; shift;;
  --only) (($# >= 2)) || exit 2; IFS=, read -r -a ONLY <<<"$2"; shift;;
  *) echo "unknown argument: $1" >&2; exit 2;; esac; shift; done
[[ $EUID == 0 && $REV =~ ^[0-9a-f]{40}$ ]] || { echo 'FAIL: root and --rev <40-hex> required' >&2; exit 2; }
CEO=${SUDO_USER:-}; [[ -n $CEO && $CEO != root ]] || { echo 'FAIL: run via sudo from the CEO login' >&2; exit 2; }
[[ $CEO == alessbarb ]] || { echo 'FAIL: SUDO_USER must be the configured CEO alessbarb' >&2; exit 2; }
SRC=/root/aao-src; REPO=autoaiorg/aao-governance-trial
GIT=(/usr/bin/env -i PATH=/usr/bin:/bin HOME=/nonexistent LANG=C.UTF-8 GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 GIT_NO_REPLACE_OBJECTS=1 GIT_TERMINAL_PROMPT=0 git -c core.hooksPath=/dev/null -c safe.directory='*')
die(){ echo "FAIL: $*" >&2; exit 1; }
[[ -d $SRC/.git && ! -L $SRC/.git ]] || die "$SRC must be a root-owned plain git clone"
[[ -z $(find "$SRC" \( ! -uid 0 -o \( ! -type l -perm /022 \) \) -print -quit) ]] || die "$SRC must be entirely root-owned and not group/other writable"
origin=$("${GIT[@]}" -C "$SRC" remote get-url origin)
[[ $origin =~ (^|[:/])autoaiorg/aao(\.git)?$ ]] || die "$SRC origin must be autoaiorg/aao"
"${GIT[@]}" -C "$SRC" cat-file -e "$REV^{commit}" || die "revision absent from root clone"
script=$(readlink -f -- "$0"); [[ $script == "$SRC/scripts/trial/run_trial.sh" ]] || die "invoke the pinned runner from $SRC/scripts/trial/run_trial.sh"
[[ $(stat -c '%u %a' "$script") == '0 755' ]] || die 'runner must be root-owned mode 0755'
blob_sha=$("${GIT[@]}" -C "$SRC" show "$REV:scripts/trial/run_trial.sh" | sha256sum | cut -d' ' -f1)
file_sha=$(sha256sum "$script" | cut -d' ' -f1)
[[ $blob_sha == "$file_sha" ]] || die "runner bytes do not match scripts/trial/run_trial.sh at $REV"
# Export only src/ from Git objects; no working-tree content or hooks/config is trusted.
[[ ! -L /opt/aao-trial ]] || die '/opt/aao-trial must not be a symlink'
install -d -o root -g root -m 0755 /opt/aao-trial
INSTALL=/opt/aao-trial/$REV
if [[ -e $INSTALL ]]; then
  [[ ! -L $INSTALL && $(stat -c '%u' "$INSTALL") == 0 ]] || die "$INSTALL is not a safe root-owned directory"
  [[ -z $(find "$INSTALL" \( ! -uid 0 -o -perm /022 \) -print -quit) ]] || die "$INSTALL contains non-root-owned or writable content"
fi
install -d -o root -g root -m 0755 "$INSTALL"
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
"${GIT[@]}" -C "$SRC" archive "$REV" src | tar -x -C "$tmp"
chown -R root:root "$tmp/src"; chmod -R go-w "$tmp/src"
if [[ -e $INSTALL/src ]]; then [[ -d $INSTALL/src && ! -L $INSTALL/src && $(stat -c '%u' "$INSTALL/src") == 0 ]] || die "$INSTALL/src is not a safe root-owned directory"; rm -rf -- "$INSTALL/src"; fi
install -d -o root -g root -m 0755 "$INSTALL/src"; cp -a "$tmp/src/." "$INSTALL/src/"
REG=$SRC/deploy/github-apps/aao-github-apps-registry.json
[[ -f $REG ]] || die 'registry missing at pinned revision'
mkdir -p /var/tmp/aao-trial
mapfile -t APPS < <(python3 -I -c 'import json,sys; d=json.load(open(sys.argv[1])); [print(a["name"],a["linux_uid"]) for a in d["apps"]]' "$REG")
# Verify the exact three live trial rulesets, including the auditor identity on B.
check_rulesets(){
  local data; data=$(runuser -u "$CEO" -- env -i HOME="$(getent passwd "$CEO"|cut -d: -f6)" PATH=/usr/bin:/bin gh api "repos/$REPO/rulesets?includes_parents=true") || return 1
  python3 -I -c 'import json,sys; rows=json.load(sys.stdin); by={r.get("name"):r for r in rows}; a=by.get("A main: integrator only"); b=by.get("B main+staging: integrity (no bypass)"); c=by.get("C tags"); ok=all(x and x.get("enforcement")=="active" for x in (a,b,c)); rules=(b or {}).get("rules",[]); required=next((r.get("parameters",{}).get("required_status_checks",[]) for r in rules if r.get("type")=="required_status_checks"),[]); arules={r.get("type") for r in (a or {}).get("rules",[])}; brules={r.get("type") for r in rules}; crules={r.get("type") for r in (c or {}).get("rules",[])}; abypass=(a or {}).get("bypass_actors",[]); ok=ok and {x.get("context"):x.get("integration_id") for x in required}.get("aao-audit")==5448107 and "test" in {x.get("context") for x in required} and not b.get("bypass_actors") and "non_fast_forward" in brules and "deletion" in brules and {"update","pull_request"}.issubset(arules) and any(x.get("actor_id")==5447984 and x.get("actor_type")=="Integration" for x in abypass) and (c or {}).get("target")=="tag" and {"creation","update","deletion"}.issubset(crules); sys.exit(0 if ok else 1)' <<<"$data"
}
check_rulesets || die 'trial rulesets A/B/C are not active with required auditor/test and no B bypass'
TS=$(date -u +%Y%m%dT%H%M%S.%NZ); export AAO_TRIAL_RUN_ID=$TS AAO_TRIAL_HARNESS_REV=$REV; LOG=/var/log/aao-trial/$TS; install -d -o root -g root -m 0750 "$LOG"
fixture_num= fixture_head=
need_pr=0; for id in "${ONLY[@]}"; do [[ $id != A-02 && $id != P3-09 && $id != A-05 && $id != P3-06 ]] || need_pr=1; done
if ((${#ONLY[@]} == 0)); then need_pr=1; fi
make_fixture_pr(){
  ceohome=$(getent passwd "$CEO" | cut -d: -f6)
  # Create a uniquely named open PR only in the disposable trial repository.
  fixture_ts=$(date -u +%Y%m%dT%H%M%S%NZ); branch="aao-trial/runner-$fixture_ts"
  main_sha=$(runuser -u "$CEO" -- env -i HOME="$ceohome" PATH=/usr/bin:/bin gh api "repos/$REPO/git/ref/heads/main" --jq .object.sha)
  blob=$(runuser -u "$CEO" -- env -i HOME="$ceohome" PATH=/usr/bin:/bin gh api -X POST "repos/$REPO/git/blobs" -f content="AAO disposable trial fixture $fixture_ts" -f encoding=utf-8 --jq .sha)
  tree=$(runuser -u "$CEO" -- env -i HOME="$ceohome" PATH=/usr/bin:/bin gh api -X POST "repos/$REPO/git/trees" -f "base_tree=$main_sha" -f "tree[0][path]=trial-fixtures/$fixture_ts.txt" -f 'tree[0][mode]=100644' -f 'tree[0][type]=blob' -f "tree[0][sha]=$blob" --jq .sha)
  commit=$(runuser -u "$CEO" -- env -i HOME="$ceohome" PATH=/usr/bin:/bin gh api -X POST "repos/$REPO/git/commits" -f message="AAO trial fixture $fixture_ts" -f "tree=$tree" -f "parents[]=$main_sha" --jq .sha)
  runuser -u "$CEO" -- env -i HOME="$ceohome" PATH=/usr/bin:/bin gh api -X POST "repos/$REPO/git/refs" -f "ref=refs/heads/$branch" -f "sha=$commit" >/dev/null
  runuser -u "$CEO" -- env -i HOME="$ceohome" PATH=/usr/bin:/bin gh pr create --repo "$REPO" --base main --head "$branch" --title "AAO disposable trial fixture $fixture_ts" --body 'Runner-created disposable fixture; do not merge manually.' >/dev/null
  pr=$(runuser -u "$CEO" -- env -i HOME="$ceohome" PATH=/usr/bin:/bin gh pr view "$branch" --repo "$REPO" --json number,headRefOid)
  fixture_num=$(python3 -I -c 'import json,sys;d=json.loads(sys.stdin.read());print(d["number"])' <<<"$pr")
  fixture_head=$(python3 -I -c 'import json,sys;d=json.loads(sys.stdin.read());print(d["headRefOid"])' <<<"$pr")
}
if ((need_pr)); then make_fixture_pr; fi
declare -a IDS=(A-01 A-02 A-03 A-04 A-05 A-06 A-09 A-12 A-14 P3-01 P3-02 P3-03 P3-05 P3-06 P3-07 P3-09 P3-12)
declare -A ROLE=([A-01]=aao-impl-codex [A-02]=aao-impl-codex [A-03]=aao-integrator [A-04]=aao-integrator [A-05]=aao-integrator [A-06]=aao-auditor [A-09]=aao-notifier [A-12]=aao-integrator [A-14]=aao-probe-noworkflows [P3-01]=ceo [P3-02]=aao-impl-codex [P3-03]=aao-integrator [P3-05]=aao-integrator [P3-06]=aao-integrator [P3-07]=aao-integrator [P3-09]=ceo [P3-12]=aao-integrator)
declare -A APP_UID=(); for row in "${APPS[@]}"; do read -r app uid <<<"$row"; APP_UID[$app]=$uid; done
APP_UID[aao-probe-noworkflows]=aao-probe-noworkflows
printf 'test\trole\tstatus\tevidence\n' | tee "$LOG/summary.tsv"
rc=0
for id in "${IDS[@]}"; do
  if ((${#ONLY[@]})) && [[ ! " ${ONLY[*]} " =~ " $id " ]]; then continue; fi
  if [[ $id == A-05 || $id == P3-06 ]]; then make_fixture_pr; fi
  role=${ROLE[$id]}; uid=${APP_UID[$role]:-$CEO}; [[ $role == ceo ]] && uid=$CEO
  target=$REPO; clone_name=trial
  [[ $id != A-14 ]] || { target=autoaiorg/aao-trial-probe; clone_name=probe; }
  home=$(getent passwd "$uid" | cut -d: -f6); [[ -n $home ]] || { printf '%s\t%s\tFAIL\tmissing uid\n' "$id" "$role" | tee -a "$LOG/summary.tsv"; rc=1; continue; }
  work=/var/tmp/aao-trial/$uid; install -d -o "$uid" -g "$(id -gn "$uid")" -m 0700 "$work"
  clone=$work/$clone_name
  if [[ ! -d $clone/.git ]]; then runuser -u "$uid" -- env -i HOME="$home" PATH=/usr/bin:/bin git clone --quiet "https://github.com/$target.git" "$clone" || { printf '%s\t%s\tFAIL\tclone failed\n' "$id" "$role" | tee -a "$LOG/summary.tsv"; rc=1; continue; }; fi
  # A disposable child commit is available for tests which need a distinct candidate.
  runuser -u "$uid" -- env -i HOME="$home" PATH=/usr/bin:/bin git -C "$clone" fetch --quiet origin main || { printf '%s\t%s\tFAIL\torigin main fetch failed\n' "$id" "$role" | tee -a "$LOG/summary.tsv"; rc=1; continue; }
  if [[ $id == P3-07 || $id == P3-12 ]]; then
    runuser -u "$uid" -- env -i HOME="$home" PATH=/usr/bin:/bin git -C "$clone" checkout -q -B trial-candidate origin/main^
  else
    runuser -u "$uid" -- env -i HOME="$home" PATH=/usr/bin:/bin git -C "$clone" checkout -q -B trial-candidate origin/main
  fi
  if [[ $id == A-14 ]]; then
    runuser -u "$uid" -- env -i HOME="$home" PATH=/usr/bin:/bin git -C "$clone" -c user.name='AAO Trial Fixture' -c user.email=trial-fixture@users.noreply.github.com commit --allow-empty -m 'AAO workflow probe fixture' >/dev/null
    runuser -u "$uid" -- mkdir -p "$clone/.github/workflows"
    runuser -u "$uid" -- /bin/sh -c 'printf "name: trial-probe\non: push\njobs:\n  probe:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo probe\n" > "$1/.github/workflows/probe.yml"' sh "$clone"
  fi
  if [[ $id == A-14 ]]; then
    runuser -u "$uid" -- env -i HOME="$home" PATH=/usr/bin:/bin git -C "$clone" add .github/workflows/probe.yml
    runuser -u "$uid" -- env -i HOME="$home" PATH=/usr/bin:/bin git -C "$clone" -c user.name='AAO Trial Fixture' -c user.email=trial-fixture@users.noreply.github.com commit -m 'Add workflow probe fixture' >/dev/null
  else
    runuser -u "$uid" -- env -i HOME="$home" PATH=/usr/bin:/bin git -C "$clone" -c user.name='AAO Trial Fixture' -c user.email=trial-fixture@users.noreply.github.com commit --allow-empty -m "AAO trial fixture $id" >/dev/null
  fi
  args=("$id" --repo "$target" --role "$role")
  allow="$REPO"; [[ $id != A-14 ]] || allow="$REPO,$target"
  envs=(HOME="$home" PATH=/usr/bin:/bin AAO_GITHUB_TRIAL_REPOS="$allow" AAO_GITHUB_TRIAL_FORK_PARENT="$REPO" AAO_TRIAL_RUN_ID="$AAO_TRIAL_RUN_ID" AAO_TRIAL_HARNESS_REV="$REV" AAO_TRIAL_CANDIDATE_SHA=$(runuser -u "$uid" -- git -C "$clone" rev-parse HEAD))
  case $id in A-02|P3-09|A-05|P3-06) envs+=(AAO_GITHUB_TRIAL_PR="$fixture_num" AAO_GITHUB_TRIAL_PR_HEAD="$fixture_head");; esac
  case $id in A-01|A-02|P3-02)
    impl_fork=autoaiorg/aao-trial-codex; envs+=(AAO_GITHUB_TRIAL_FORK="$impl_fork" AAO_GITHUB_TRIAL_FORKS="autoaiorg/aao-codex,$impl_fork")
    args+=(--equivalence);;
  esac
  case $id in A-05|P3-06) envs+=(AAO_GITHUB_TRIAL_PHASE=stage);; esac
  # Seed the exact required audit check only after the candidate exists in the trial repo.
  if [[ $id == A-03 || $id == A-04 || $id == P3-05 || $id == P3-07 || $id == P3-12 ]]; then
    candidate=$(runuser -u "$uid" -- git -C "$clone" rev-parse HEAD)
    set +e
    (cd "$clone" && runuser -u "$uid" -- env -i HOME="$home" PATH=/usr/bin:/bin AAO_GITHUB_TRIAL_REPOS="$REPO" AAO_GITHUB_TRIAL_BRANCH="aao-trial/required-$id" AAO_GITHUB_TRIAL_EXPECTED_SHA="$candidate" AAO_TRIAL_CANDIDATE_SHA="$candidate" AAO_TRIAL_RUN_ID="$AAO_TRIAL_RUN_ID" AAO_TRIAL_HARNESS_REV="$REV" /usr/bin/python3 -I -c "import sys;sys.path.insert(0,'$INSTALL/src');from aao.github_trial import main;raise SystemExit(main())" STAGE-COMMIT --repo "$REPO" --role aao-integrator --branch "aao-trial/required-$id") >"$LOG/$id-STAGE-COMMIT.out" 2>&1
    helper_rc=$?
    set -e
    cat "$LOG/$id-STAGE-COMMIT.out"
    if ((helper_rc != 0)); then helper_reason=$(head -n 1 "$LOG/$id-STAGE-COMMIT.out"); printf '%s\t%s\tFAIL\t%s\n' "$id" "$role" "$helper_reason" | tee -a "$LOG/summary.tsv"; rc=1; continue; fi
    staged_sha=$(grep -Eo 'staged local commit [0-9a-f]{40}' "$LOG/$id-STAGE-COMMIT.out" | awk '{print $4}' | tail -1)
    if [[ $staged_sha != "$candidate" ]]; then printf '%s\t%s\tFAIL\tSTAGE-COMMIT SHA mismatch\n' "$id" "$role" | tee -a "$LOG/summary.tsv"; rc=1; continue; fi
    auditor_home=$(getent passwd "${APP_UID[aao-auditor]}" | cut -d: -f6)
    auditor_clone=/var/tmp/aao-trial/${APP_UID[aao-auditor]}/trial
    if [[ ! -d $auditor_clone/.git ]]; then install -d -o "${APP_UID[aao-auditor]}" -g "$(id -gn "${APP_UID[aao-auditor]}")" -m 0700 "$(dirname "$auditor_clone")"; runuser -u "${APP_UID[aao-auditor]}" -- env -i HOME="$auditor_home" PATH=/usr/bin:/bin git clone --quiet "https://github.com/$REPO.git" "$auditor_clone"; fi
    set +e
    (cd "$auditor_clone" && runuser -u "${APP_UID[aao-auditor]}" -- env -i HOME="$auditor_home" PATH=/usr/bin:/bin AAO_GITHUB_TRIAL_REPOS="$REPO" AAO_GITHUB_TRIAL_SHA="$candidate" AAO_TRIAL_CANDIDATE_SHA="$candidate" AAO_TRIAL_RUN_ID="$AAO_TRIAL_RUN_ID" AAO_TRIAL_HARNESS_REV="$REV" /usr/bin/python3 -I -c "import sys;sys.path.insert(0,'$INSTALL/src');from aao.github_trial import main;raise SystemExit(main())" PUBLISH-AUDIT --repo "$REPO" --role aao-auditor) >"$LOG/$id-PUBLISH-AUDIT.out" 2>&1
    helper_rc=$?
    set -e
    cat "$LOG/$id-PUBLISH-AUDIT.out"
    if ((helper_rc != 0)); then helper_reason=$(head -n 1 "$LOG/$id-PUBLISH-AUDIT.out"); printf '%s\t%s\tFAIL\t%s\n' "$id" "$role" "$helper_reason" | tee -a "$LOG/summary.tsv"; rc=1; continue; fi
  fi
  if [[ $id == A-05 || $id == P3-06 ]]; then runuser -u "$uid" -- env -i HOME="$home" PATH=/usr/bin:/bin git -C "$clone" fetch --quiet origin "refs/pull/$fixture_num/head"; fi
  set +e
  (cd "$clone" && runuser -u "$uid" -- env -i "${envs[@]}" /usr/bin/python3 -I -c "import sys;sys.path.insert(0,'$INSTALL/src');from aao.github_trial import main;raise SystemExit(main())" "${args[@]}") >"$LOG/$id-$role.out" 2>&1
  status=$?
  set -e
  cat "$LOG/$id-$role.out"
  evidence=$(find "$home/aao-trial-evidence" -maxdepth 1 -type f -name "$id-*.json" -print 2>/dev/null | sort | while IFS= read -r f; do [[ $(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1])).get("run_id", ""))' "$f") == "$AAO_TRIAL_RUN_ID" ]] && { printf "%s\n" "$f"; }; done | tail -1)
  state='NOT RUN (no evidence from this run)'; [[ -n $evidence ]] && state=$(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1])).get("status","FAIL"))' "$evidence")
  if [[ ( $id == A-05 || $id == P3-06 ) && $state == STAGED ]]; then
    merge_sha=$(python3 -I -c 'import json,sys; d=json.load(open(sys.argv[1])); print(next(x["sha"] for x in d["evidence"] if x.get("method")=="staged merge commit"))' "$evidence")
    auditor_home=$(getent passwd "${APP_UID[aao-auditor]}" | cut -d: -f6); auditor_clone=/var/tmp/aao-trial/${APP_UID[aao-auditor]}/trial
    set +e
    runuser -u "${APP_UID[aao-auditor]}" -- env -i HOME="$auditor_home" PATH=/usr/bin:/bin AAO_GITHUB_TRIAL_REPOS="$REPO" AAO_GITHUB_TRIAL_SHA="$merge_sha" AAO_TRIAL_CANDIDATE_SHA="$merge_sha" AAO_TRIAL_RUN_ID="$AAO_TRIAL_RUN_ID" AAO_TRIAL_HARNESS_REV="$REV" /usr/bin/python3 -I -c "import sys;sys.path.insert(0,'$INSTALL/src');from aao.github_trial import main;raise SystemExit(main())" PUBLISH-AUDIT --repo "$REPO" --role aao-auditor >"$LOG/$id-PUBLISH-AUDIT.out" 2>&1
    helper_rc=$?
    set -e
    cat "$LOG/$id-PUBLISH-AUDIT.out"
    if ((helper_rc != 0)); then state=FAIL; status=1; rc=1; fi
    if ((helper_rc == 0)); then
    promote_envs=(HOME="$home" PATH=/usr/bin:/bin AAO_GITHUB_TRIAL_REPOS="$REPO" AAO_GITHUB_TRIAL_PR="$fixture_num" AAO_GITHUB_TRIAL_PR_HEAD="$fixture_head" AAO_GITHUB_TRIAL_PHASE=promote AAO_GITHUB_TRIAL_PROMOTE_SHA="$merge_sha" AAO_TRIAL_RUN_ID="$AAO_TRIAL_RUN_ID" AAO_TRIAL_HARNESS_REV="$REV" AAO_TRIAL_CANDIDATE_SHA="$merge_sha")
    set +e
    (cd "$clone" && runuser -u "$uid" -- env -i "${promote_envs[@]}" /usr/bin/python3 -I -c "import sys;sys.path.insert(0,'$INSTALL/src');from aao.github_trial import main;raise SystemExit(main())" "$id" --repo "$REPO" --role "$role") >"$LOG/$id-$role-promote.out" 2>&1
    status=$?
    set -e
    cat "$LOG/$id-$role-promote.out"
    evidence=$(find "$home/aao-trial-evidence" -maxdepth 1 -type f -name "$id-*.json" -print 2>/dev/null | sort | while IFS= read -r f; do [[ $(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1])).get("run_id", ""))' "$f") == "$AAO_TRIAL_RUN_ID" ]] && { printf "%s\n" "$f"; }; done | tail -1)
    [[ -n $evidence ]] && state=$(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1])).get("status","FAIL"))' "$evidence")
    fi
  fi
  printf '%s\t%s\t%s\t%s\n' "$id" "$role" "$state" "${evidence:-none}" | tee -a "$LOG/summary.tsv"
  [[ -n $evidence ]] && install -o root -g root -m 0640 "$evidence" "$LOG/$(basename "$evidence")"
  [[ $state != FAIL ]] || rc=1
  [[ $status -ne 1 || $state == FAIL ]] || rc=1
  if [[ $id == A-01 || $id == A-02 || $id == P3-02 ]]; then
    for impl in aao-impl-claude aao-impl-agy; do
      impl_uid=${APP_UID[$impl]}; impl_home=$(getent passwd "$impl_uid" | cut -d: -f6); impl_work=/var/tmp/aao-trial/$impl_uid
      install -d -o "$impl_uid" -g "$(id -gn "$impl_uid")" -m 0700 "$impl_work"
      impl_clone=$impl_work/trial
      if [[ ! -d $impl_clone/.git ]]; then runuser -u "$impl_uid" -- env -i HOME="$impl_home" PATH=/usr/bin:/bin git clone --quiet "https://github.com/$REPO.git" "$impl_clone"; fi
      runuser -u "$impl_uid" -- env -i HOME="$impl_home" PATH=/usr/bin:/bin git -C "$impl_clone" fetch --quiet origin main
      impl_fork=autoaiorg/aao-trial-claude; production_fork=autoaiorg/aao-claude; [[ $impl != aao-impl-agy ]] || { impl_fork=autoaiorg/aao-trial-agy; production_fork=autoaiorg/aao-agy; }
      set +e
      (cd "$impl_clone" && runuser -u "$impl_uid" -- env -i HOME="$impl_home" PATH=/usr/bin:/bin AAO_GITHUB_TRIAL_REPOS="$REPO" AAO_GITHUB_TRIAL_FORKS="$production_fork,$impl_fork" AAO_GITHUB_TRIAL_FORK="$impl_fork" AAO_TRIAL_RUN_ID="$AAO_TRIAL_RUN_ID" AAO_TRIAL_HARNESS_REV="$REV" AAO_TRIAL_CANDIDATE_SHA=$(runuser -u "$impl_uid" -- git -C "$impl_clone" rev-parse origin/main) /usr/bin/python3 -I -c "import sys;sys.path.insert(0,'$INSTALL/src');from aao.github_trial import main;raise SystemExit(main())" "$id" --repo "$REPO" --role "$impl" --equivalence) >"$LOG/$id-$impl.out" 2>&1
      extra_rc=$?
      set -e
      cat "$LOG/$id-$impl.out"
      extra_ev=$(find "$impl_home/aao-trial-evidence" -maxdepth 1 -type f -name "$id-*.json" -print 2>/dev/null | sort | while IFS= read -r f; do [[ $(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1])).get("run_id", ""))' "$f") == "$AAO_TRIAL_RUN_ID" ]] && { printf "%s\n" "$f"; }; done | tail -1)
      extra_state=NOT\ RUN; [[ -n $extra_ev ]] && extra_state=$(python3 -I -c 'import json,sys;print(json.load(open(sys.argv[1])).get("status","FAIL"))' "$extra_ev")
      printf '%s\t%s\t%s\t%s\n' "$id" "$impl" "$extra_state" "${extra_ev:-none}" | tee -a "$LOG/summary.tsv"
      [[ $extra_state != FAIL ]] || rc=1
    done
  fi
done
# A-10 covers every configured App. Implementers are inspected on their trial forks;
# other Apps are inspected on the trial repository. The probe has no A-10 column.
declare -a A10_ROLES=(aao-integrator aao-auditor aao-auditor-alt aao-supervisor aao-notifier aao-pm aao-impl-claude aao-impl-codex aao-impl-agy aao-probe-noworkflows)
for role in "${A10_ROLES[@]}"; do
  if ((${#ONLY[@]})) && [[ ! " ${ONLY[*]} " =~ " A-10 " ]]; then break; fi
  uid=${APP_UID[$role]:-aao-probe-noworkflows}; [[ $role != aao-probe-noworkflows ]] || uid=aao-probe-noworkflows
  home=$(getent passwd "$uid" | cut -d: -f6)
  if [[ -z $home ]]; then printf 'A-10\t%s\tFAIL\tmissing uid\n' "$role" | tee -a "$LOG/summary.tsv"; rc=1; continue; fi
  target=$REPO; parent=$REPO
  case $role in
    aao-impl-claude) target=autoaiorg/aao-trial-claude;;
    aao-impl-codex) target=autoaiorg/aao-trial-codex;;
    aao-impl-agy) target=autoaiorg/aao-trial-agy;;
    aao-probe-noworkflows) target=autoaiorg/aao-trial-probe;;
  esac
  set +e
  runuser -u "$uid" -- env -i HOME="$home" PATH=/usr/bin:/bin AAO_GITHUB_TRIAL_REPOS="$target" AAO_GITHUB_TRIAL_FORK_PARENT="$parent" AAO_TRIAL_RUN_ID="$AAO_TRIAL_RUN_ID" AAO_TRIAL_HARNESS_REV="$REV" /usr/bin/python3 -I -c "import sys;sys.path.insert(0,'$INSTALL/src');from aao.github_trial import main;raise SystemExit(main())" A-10 --repo "$target" --role "$role" >"$LOG/A-10-$role.out" 2>&1
  a10_rc=$?
  set -e
  cat "$LOG/A-10-$role.out"
  ev=$(find "$home/aao-trial-evidence" -maxdepth 1 -type f -name 'A-10-*.json' -print 2>/dev/null | sort | while IFS= read -r f; do [[ $(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1])).get("run_id", ""))' "$f") == "$AAO_TRIAL_RUN_ID" && $(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1])).get("role", ""))' "$f") == "$role" ]] && printf '%s\n' "$f"; done | tail -1)
  state='NOT RUN (no evidence from this run)'; [[ -n $ev ]] && state=$(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1])).get("status", "FAIL"))' "$ev")
  printf 'A-10\t%s\t%s\t%s\n' "$role" "$state" "${ev:-none}" | tee -a "$LOG/summary.tsv"
  [[ $state != FAIL && $a10_rc -ne 1 ]] || rc=1
  [[ -z $ev ]] || install -o root -g root -m 0640 "$ev" "$LOG/$(basename "$ev")"
done
# Manual tests remain explicit, never silently omitted.
for id in A-07 A-08 A-11 A-13 P3-04 P3-08 P3-10 P3-11; do
  if ((${#ONLY[@]} == 0)) || [[ " ${ONLY[*]} " =~ " $id " ]]; then printf '%s\tmanual\tNOT RUN\tmanual step documented in trial setup\n' "$id" | tee -a "$LOG/summary.tsv"; fi
done
declare -A HOMES=(); HOMES[$CEO]=$(getent passwd "$CEO" | cut -d: -f6)
for app in "${!APP_UID[@]}"; do user=${APP_UID[$app]}; HOMES[$user]=$(getent passwd "$user" | cut -d: -f6); done
for user in "${!HOMES[@]}"; do
  evidence_dir=${HOMES[$user]}/aao-trial-evidence
  [[ -d $evidence_dir ]] || continue
  while IFS= read -r -d '' file; do
    [[ -f $file && ! -L $file ]] || continue
    install -o root -g root -m 0640 "$file" "$LOG/${user}-$(basename "$file")"
  done < <(find "$evidence_dir" -maxdepth 1 -type f -print0)
done
check_rulesets || { echo 'FAIL: trial rulesets changed or are no longer active at end' >&2; rc=1; }
(cd "$LOG" && find . -maxdepth 1 -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)
chmod 0640 "$LOG"/*; echo "Evidence: $LOG"; column -t -s $'\t' "$LOG/summary.tsv" 2>/dev/null || cat "$LOG/summary.tsv"
exit "$rc"
