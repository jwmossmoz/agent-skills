#!/usr/bin/env bash
# check-skill.sh — audit an agent skill against agentskills.io conventions.
# Runs skills-ref (official), waza, skill-validator, and skill-check and emits a unified verdict.

set -euo pipefail

show_help() {
  cat <<'EOF'
check-skill.sh — audit an agent skill against agentskills.io conventions.

Usage:
  check-skill.sh <skill-path>            Print human-readable summary.
  check-skill.sh <skill-path> --json     Emit machine-readable summary.
  check-skill.sh -h | --help             Show this help.

Validators:
  skills-ref       Official reference validator from agentskills/agentskills.
                   Hard frontmatter rules: name format, description length,
                   parent-directory match.
  waza             Compliance score, token budget, advisory checks.
  skill-validator  File structure, link integrity, density, contamination.
  skill-check      0-100 quality score plus security scan.

Per-validator reports are saved to: ${SKILL_CHECKER_OUT:-/tmp/skill-checker}/<slug>/

Exit codes:
  0  All validators pass.
  1  At least one validator reports an error or failure.
  2  Usage error or missing SKILL.md.
EOF
}

case "${1:-}" in
  -h|--help)
    show_help
    exit 0
    ;;
  "")
    show_help >&2
    exit 2
    ;;
esac

SKILL_PATH="$1"
FORMAT="${2:-text}"

if [[ ! -d "$SKILL_PATH" ]]; then
  echo "error: not a directory: $SKILL_PATH" >&2
  exit 2
fi

if [[ ! -f "$SKILL_PATH/SKILL.md" ]]; then
  echo "error: no SKILL.md in $SKILL_PATH" >&2
  exit 2
fi

ABS_PATH="$(cd "$SKILL_PATH" && pwd)"
SLUG="$(basename "$ABS_PATH")"
ARTIFACT_DIR="${SKILL_CHECKER_OUT:-/tmp/skill-checker}/$SLUG"
mkdir -p "$ARTIFACT_DIR"
WORK="$ARTIFACT_DIR"
# Clean any stale artifacts from polluted skill dirs (older versions wrote here)
rm -f "$ABS_PATH/.skill-check."*.txt 2>/dev/null || true

# --- ensure each validator is available ------------------------------------

ensure_skills_ref() {
  # skills-ref is the canonical validator from agentskills/agentskills.
  # Invoked through uvx so the version is pinned by the git ref, not @latest.
  command -v uvx >/dev/null 2>&1
}

ensure_waza() {
  if ! command -v waza >/dev/null 2>&1; then
    if command -v go >/dev/null 2>&1; then
      go install github.com/microsoft/waza/cmd/waza@latest >/dev/null 2>&1 || return 1
      export PATH="$PATH:$(go env GOPATH)/bin"
    else
      return 1
    fi
  fi
}

ensure_skill_validator() {
  if ! command -v skill-validator >/dev/null 2>&1; then
    if command -v go >/dev/null 2>&1; then
      go install github.com/agent-ecosystem/skill-validator/cmd/skill-validator@latest >/dev/null 2>&1 || return 1
      export PATH="$PATH:$(go env GOPATH)/bin"
    else
      return 1
    fi
  fi
}

ensure_skill_check() {
  command -v npx >/dev/null 2>&1
}

# --- run each validator into a tmp file ------------------------------------

SR_OUT="$WORK/skills-ref.txt"
WAZA_OUT="$WORK/waza.txt"
SV_OUT="$WORK/skill-validator.txt"
SC_OUT="$WORK/skill-check.txt"

SR_STATUS="skipped"
WAZA_STATUS="skipped"
SV_STATUS="skipped"
SC_STATUS="skipped"

if ensure_skills_ref; then
  uvx --from "git+https://github.com/agentskills/agentskills.git#subdirectory=skills-ref" \
      skills-ref validate "$ABS_PATH" >"$SR_OUT" 2>&1 || true
  SR_STATUS="ran"
fi

if ensure_waza; then
  waza check "$ABS_PATH" >"$WAZA_OUT" 2>&1 || true
  WAZA_STATUS="ran"
fi

if ensure_skill_validator; then
  skill-validator check "$ABS_PATH" >"$SV_OUT" 2>&1 || true
  SV_STATUS="ran"
fi

if ensure_skill_check; then
  ( cd "$ABS_PATH" && npx --yes skill-check@latest . >"$SC_OUT" 2>&1 ) || true
  SC_STATUS="ran"
fi

# --- parse each output ------------------------------------------------------

# Strip ANSI escape codes from a file in place
strip_ansi() {
  perl -pi -e 's/\e\[[0-9;]*[A-Za-z]//g' "$1"
}

[[ "$SR_STATUS" == "ran" ]]   && strip_ansi "$SR_OUT"
[[ "$WAZA_STATUS" == "ran" ]] && strip_ansi "$WAZA_OUT"
[[ "$SV_STATUS" == "ran" ]]   && strip_ansi "$SV_OUT"
[[ "$SC_STATUS" == "ran" ]]   && strip_ansi "$SC_OUT"

# skills-ref: hard spec rules. "Valid skill:" = pass, anything else = fail.
sr_summary() {
  [[ "$SR_STATUS" == "skipped" ]] && { echo "skipped (install uv and rerun)"; return; }
  if grep -qE "^Valid skill:" "$SR_OUT"; then
    echo "result=passed"
  else
    local first_err
    first_err=$(grep -E "Validation error|Error" "$SR_OUT" | head -1 | sed -E 's/[[:space:]]+/ /g' | cut -c1-80)
    echo "result=failed (${first_err:-see skills-ref.txt})"
  fi
}

# waza: extract Compliance Score, token count, and advisory fails
waza_summary() {
  [[ "$WAZA_STATUS" == "skipped" ]] && { echo "skipped (install go and rerun)"; return; }
  local compliance tokens advisory_fail
  compliance=$(grep -E "Compliance Score:" "$WAZA_OUT" | head -1 | sed -E 's/.*Compliance Score:[[:space:]]*([A-Za-z]+).*/\1/')
  tokens=$(grep -E "Token Budget:" "$WAZA_OUT" | head -1 | sed -E 's/.*Token Budget:[[:space:]]*([0-9]+)[[:space:]]*\/[[:space:]]*([0-9]+).*/\1\/\2/')
  advisory_fail=$(grep -cE "^[[:space:]]+❌[[:space:]]+\[" "$WAZA_OUT" 2>/dev/null || true)
  echo "compliance=${compliance:-?} tokens=${tokens:-?} advisory_fails=${advisory_fail:-0}"
}

# skill-validator: scan for "Result: passed/failed"
sv_summary() {
  [[ "$SV_STATUS" == "skipped" ]] && { echo "skipped (install go and rerun)"; return; }
  local result tokens contamination
  result=$(grep -E "^Result:" "$SV_OUT" | head -1 | awk '{print $2}')
  tokens=$(grep -E "SKILL.md body:" "$SV_OUT" | head -1 | grep -oE "[0-9,]+ tokens" | head -1 | awk '{print $1}')
  contamination=$(grep -E "Contamination level:" "$SV_OUT" | head -1 | awk '{print $3}')
  echo "result=${result:-?} tokens=${tokens:-?} contamination=${contamination:-?}"
}

# skill-check: extract score, errors, warnings
sc_summary() {
  [[ "$SC_STATUS" == "skipped" ]] && { echo "skipped (install node and rerun)"; return; }
  local score errors warnings status
  score=$(grep -oE "[0-9]+ / 100  [A-Za-z]+" "$SC_OUT" | head -1)
  errors=$(grep -oE "[0-9]+ errors?" "$SC_OUT" | head -1 | grep -oE "[0-9]+" || echo 0)
  warnings=$(grep -oE "[0-9]+ warnings?" "$SC_OUT" | head -1 | grep -oE "[0-9]+" || echo 0)
  status=$(grep -oE "validation [A-Z]+" "$SC_OUT" | head -1 | awk '{print $2}')
  echo "score=${score:-?} status=${status:-?} errors=${errors:-0} warnings=${warnings:-0}"
}

SR_LINE=$(sr_summary)
WAZA_LINE=$(waza_summary)
SV_LINE=$(sv_summary)
SC_LINE=$(sc_summary)

# --- emit ------------------------------------------------------------------

if [[ "$FORMAT" == "--json" ]]; then
  esc() { printf '%s' "$1" | sed 's/"/\\"/g'; }
  printf '{\n'
  printf '  "skill_path": "%s",\n' "$(esc "$ABS_PATH")"
  printf '  "skills_ref":      { "status": "%s", "summary": "%s" },\n' "$SR_STATUS"   "$(esc "$SR_LINE")"
  printf '  "waza":            { "status": "%s", "summary": "%s" },\n' "$WAZA_STATUS" "$(esc "$WAZA_LINE")"
  printf '  "skill_validator": { "status": "%s", "summary": "%s" },\n' "$SV_STATUS"   "$(esc "$SV_LINE")"
  printf '  "skill_check":     { "status": "%s", "summary": "%s" }\n'  "$SC_STATUS"   "$(esc "$SC_LINE")"
  printf '}\n'
  exit 0
fi

# Text format
sep="------------------------------------------------------------"
echo "Skill: $ABS_PATH"
echo "$sep"
printf '  %-18s %s\n' "skills-ref:"      "$SR_LINE"
printf '  %-18s %s\n' "waza:"            "$WAZA_LINE"
printf '  %-18s %s\n' "skill-validator:" "$SV_LINE"
printf '  %-18s %s\n' "skill-check:"     "$SC_LINE"
echo "$sep"

# Detail dump on demand
echo ""
echo "Full reports saved under: $ARTIFACT_DIR"
[[ "$SR_STATUS"   == "ran" ]] && echo "  - $SR_OUT"
[[ "$WAZA_STATUS" == "ran" ]] && echo "  - $WAZA_OUT"
[[ "$SV_STATUS"   == "ran" ]] && echo "  - $SV_OUT"
[[ "$SC_STATUS"   == "ran" ]] && echo "  - $SC_OUT"

# Determine overall exit code
fail=0
[[ "$SR_LINE" == result=failed* ]] && fail=1
if grep -qE "Result: failed" "$SV_OUT" 2>/dev/null; then fail=1; fi
if grep -qE "✖ [1-9][0-9]* error" "$SC_OUT" 2>/dev/null; then fail=1; fi
exit "$fail"
