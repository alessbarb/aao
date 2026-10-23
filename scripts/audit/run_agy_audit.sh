#!/usr/bin/env bash
# Independent audit by Antigravity (agy) as the alternate auditor (delegated resolution, #25).
# Run ONLY as aao-auditor-alt (never as the CEO, never as aao-impl-ag):
#   sudo -u aao-auditor-alt -H /opt/aao-audit/run_agy_audit.sh <base_sha> <head_sha>
# Read-only: public clone at the frozen SHA, plan mode, sandbox, clean environment, the reviewed prompt only.
# Writes ~/aao-audits/<head_sha>/{prompt.txt,report.md,attestation.json} and prints their sha256.
set -euo pipefail
PROMPT=/opt/aao-audit/r1-chain.md
PROMPT_SHA256=81c7bca96a8dd16fbb08e23cd130d6de7b64eaba3912ac5a27f22e39f66ec156   # reviewed docs/audit-prompts/r1-chain.md
me=$(id -un); [[ $me == aao-auditor-alt ]] || { echo "refusing: must run as aao-auditor-alt, not $me" >&2; exit 1; }
[[ $# -eq 2 ]] || { echo "usage: $0 <base_sha> <head_sha>" >&2; exit 2; }
base=$1 head=$2
[[ $base =~ ^[0-9a-f]{40}$ && $head =~ ^[0-9a-f]{40}$ ]] || { echo "full 40-hex SHAs required" >&2; exit 2; }
home=$(getent passwd "$me" | cut -d: -f6)
[[ $HOME == "$home" ]] || { echo "refusing: HOME=$HOME is not $me's home ($home)" >&2; exit 1; }
# The reviewed prompt: root-owned, not group/other writable, exact digest.
[[ $(stat -c '%u %a' "$PROMPT") == "0 644" ]] || { echo "refusing: $PROMPT must be root:0644" >&2; exit 1; }
[[ $(sha256sum "$PROMPT" | cut -d' ' -f1) == "$PROMPT_SHA256" ]] || { echo "refusing: $PROMPT is not the reviewed prompt" >&2; exit 1; }
# agy session state must belong to this uid only (no copied or shared session).
for d in "$home/.antigravity" "$home/.gemini" "$home/.config/antigravity"; do
  [[ -e $d ]] || continue
  bad=$(find "$d" \( ! -uid "$(id -u)" -o -perm /022 \) -print -quit)
  [[ -z $bad ]] || { echo "refusing: $bad is not exclusively $me's" >&2; exit 1; }
done
out="$home/aao-audits/$head"; [[ ! -e $out ]] || { echo "refusing: $out exists (one audit per SHA)" >&2; exit 1; }
mkdir -p -m 0700 "$out"
prior=$(find "$home/.antigravity" "$home/.gemini" "$home/.config/antigravity" -type f 2>/dev/null | wc -l || true)
work=$(mktemp -d); trap 'rm -rf "$work"' EXIT
# Every git call: no system/global config (so no filters/hooks/credentials), no prompt.
g() { env -i PATH=/usr/bin:/bin HOME=/nonexistent LANG=C.UTF-8 GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 \
        GIT_TERMINAL_PROMPT=0 git -c core.hooksPath=/dev/null "$@"; }
g clone -q --no-hardlinks --no-checkout https://github.com/alessbarb/aao.git "$work/repo"
g -C "$work/repo" cat-file -e "$head^{commit}"; g -C "$work/repo" cat-file -e "$base^{commit}"
g -C "$work/repo" -c advice.detachedHead=false checkout -q "$head"
[[ $(g -C "$work/repo" rev-parse HEAD) == "$head" ]]
sed -e "s/{{BASE}}/$base/g" -e "s/{{HEAD}}/$head/g" "$PROMPT" > "$out/prompt.txt"
# agy with a clean environment: only this uid's HOME; nothing inherited from the caller.
( cd "$work/repo" && env -i PATH=/usr/bin:/bin:/usr/local/bin HOME="$home" USER="$me" LOGNAME="$me" LANG=C.UTF-8 \
    agy -p --mode plan --sandbox --effort high --print-timeout 0 < "$out/prompt.txt" ) > "$out/report.md"
cat > "$out/attestation.json" <<JSON
{"auditor":"antigravity","os_user":"$me","uid":$(id -u),"base":"$base","head":"$head",
 "checked_out_head":"$(g -C "$work/repo" rev-parse HEAD)","prompt_template_sha256":"$PROMPT_SHA256",
 "agy_version":"$(agy --version 2>/dev/null | head -1 | tr -d '"')","prior_agy_state_files":$prior,
 "prompt_sha256":"$(sha256sum "$out/prompt.txt" | cut -d' ' -f1)",
 "report_sha256":"$(sha256sum "$out/report.md" | cut -d' ' -f1)","finished_at":"$(date -u +%FT%TZ)"}
JSON
sha256sum "$out/report.md" "$out/attestation.json"
