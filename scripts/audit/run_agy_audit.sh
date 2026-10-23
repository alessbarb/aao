#!/usr/bin/env bash
# Independent audit by Antigravity (agy) as the alternate auditor (delegated resolution, #25).
# Run ONLY as aao-auditor-alt (never as the CEO, never as aao-impl-ag):
#   sudo -u aao-auditor-alt -H /opt/aao-audit/run_agy_audit.sh <base_sha> <head_sha> <prompt_file>
# Read-only: public clone at the frozen SHA, plan mode, sandbox, no credentials of other accounts.
# Writes ~/aao-audits/<head_sha>/{report.md,attestation.json} and prints their sha256.
set -euo pipefail
[[ $(id -un) == aao-auditor-alt ]] || { echo "refusing: must run as aao-auditor-alt, not $(id -un)" >&2; exit 1; }
[[ $# -eq 3 ]] || { echo "usage: $0 <base_sha> <head_sha> <prompt_file>" >&2; exit 2; }
base=$1 head=$2 prompt=$3
[[ $base =~ ^[0-9a-f]{40}$ && $head =~ ^[0-9a-f]{40}$ ]] || { echo "full 40-hex SHAs required" >&2; exit 2; }
[[ -r $prompt ]] || { echo "prompt not readable: $prompt" >&2; exit 2; }
out="$HOME/aao-audits/$head"; [[ ! -e $out ]] || { echo "refusing: $out exists (one audit per SHA)" >&2; exit 1; }
mkdir -p -m 0700 "$out"
# Non-participation evidence: this identity's agy state before the audit (must hold no prior AAO work).
prior=$(find "$HOME/.antigravity" "$HOME/.gemini" "$HOME/.config/antigravity" -type f 2>/dev/null | wc -l || true)
work=$(mktemp -d); trap 'rm -rf "$work"' EXIT
GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 GIT_TERMINAL_PROMPT=0 \
  git clone -q --no-hardlinks https://github.com/alessbarb/aao.git "$work/repo"
git -C "$work/repo" cat-file -e "$head^{commit}" && git -C "$work/repo" cat-file -e "$base^{commit}"
git -C "$work/repo" -c advice.detachedHead=false checkout -q "$head"
{ sed -e "s/{{BASE}}/$base/g" -e "s/{{HEAD}}/$head/g" "$prompt"; } > "$out/prompt.txt"
( cd "$work/repo" && agy -p --mode plan --sandbox --effort high --print-timeout 0 < "$out/prompt.txt" ) > "$out/report.md"
cat > "$out/attestation.json" <<JSON
{"auditor":"antigravity","os_user":"$(id -un)","uid":$(id -u),"base":"$base","head":"$head",
 "agy_version":"$(agy --version 2>/dev/null | head -1 | tr -d '"')","prior_agy_state_files":$prior,
 "prompt_sha256":"$(sha256sum "$out/prompt.txt" | cut -d' ' -f1)",
 "report_sha256":"$(sha256sum "$out/report.md" | cut -d' ' -f1)","finished_at":"$(date -u +%FT%TZ)"}
JSON
sha256sum "$out/report.md" "$out/attestation.json"
