#!/usr/bin/env bash
# Workflow D: Documentation Audit (Phase 48)
# Covers: README custom guest workflow, GUI guide, CLI reference, GRO/ITP guide,
#         version string, deprecated banners.
#
# Usage:  bash .planning/uat-workflows/D-documentation.sh
# Env:    conda env quickice active

set -uo pipefail

PASS=0; FAIL=0; SKIP=0
results=()

check() {
  results+=("$1: $2")
  case "$2" in
    PASS) PASS=$((PASS+1)) ;;
    FAIL) FAIL=$((FAIL+1)) ;;
    SKIP) SKIP=$((SKIP+1)) ;;
  esac
}

grep_check() {
  # $1 = label, $2 = file, $3 = pattern
  if [ ! -f "$2" ]; then
    check "$1 (file missing: $2)" FAIL
    return
  fi
  if grep -qE "$3" "$2" 2>/dev/null; then
    check "$1" PASS
  else
    check "$1" FAIL
  fi
}

echo "=== Workflow D: Documentation Audit ==="
echo ""

# 48-1: README documents custom guest hydrate workflow (upload → validate → generate → export)
grep_check "48-1 README custom guest workflow" README.md "custom.*(guest|hydrate).*(upload|gro.*itp|workflow)"
grep_check "48-1 README mentions .gro + .itp upload" README.md "\.gro.*\.itp|\.itp.*\.gro"
grep_check "48-1 README mentions validate/generate/export" README.md "(validate|validation).*(generate|export)"

# 48-2: README version references say v4.7 (check version string, not stale v4.5 as current)
grep_check "48-2 README has v4.7 reference" README.md "4\.7"
# Stale check: v4.5 should NOT appear as "current version" (historical mentions ok)
STALE_COUNT=$(grep -cE "v4\.5[^0-9]|version.*4\.5" README.md 2>/dev/null || echo 0)
if [ "$STALE_COUNT" -gt 0 ]; then
  # Check if v4.5 mentions are historical (past tense)
  if grep -qE "v4\.5 (added|shipped|was)|added in v4\.5|since v4\.5" README.md 2>/dev/null; then
    check "48-2 README v4.5 references are historical" PASS
  else
    check "48-2 README v4.5 references (may be stale)" FAIL
  fi
else
  check "48-2 README no stale v4.5 as current" PASS
fi

# 48-3: GUI guide has 10-row lattice types table
grep_check "48-3 GUI guide lattice table (sI)" docs/gui-guide.md "sI"
grep_check "48-3 GUI guide lattice table (sH)" docs/gui-guide.md "sH"
grep_check "48-3 GUI guide lattice table (c0te)" docs/gui-guide.md "c0te|C0"
grep_check "48-3 GUI guide lattice table (sTprime)" docs/gui-guide.md "sTprime|sT'|sT&#39;"
grep_check "48-3 GUI guide lattice table (Ice XVII / 17)" docs/gui-guide.md "17|XVII"
NEW_LATTICE_COUNT=$(grep -oE "sI|sII|sH|c0te|c1te|c2te|ice1hte|sTprime|16|17" docs/gui-guide.md 2>/dev/null | sort -u | wc -l)
if [ "$NEW_LATTICE_COUNT" -ge 8 ]; then
  check "48-3 GUI guide covers >=8 lattice types ($NEW_LATTICE_COUNT/10)" PASS
else
  check "48-3 GUI guide covers >=8 lattice types ($NEW_LATTICE_COUNT/10)" FAIL
fi

# 48-4: GUI guide has custom guest upload + mixed occupancy + depol subsections
grep_check "48-4 GUI guide custom guest upload" docs/gui-guide.md "custom.*guest|guest.*upload|\.gro.*\.itp"
grep_check "48-4 GUI guide mixed occupancy" docs/gui-guide.md "mixed.*occupancy|per-cage|cage.*type.*guest"
grep_check "48-4 GUI guide depol mode" docs/gui-guide.md "depol|depolari"

# 48-5: GUI guide version says v4.7
grep_check "48-5 GUI guide v4.7 reference" docs/gui-guide.md "4\.7"

# 48-6: CLI reference documents --lattice-type (10 choices), --cage-guest, --depol
grep_check "48-6 CLI ref --lattice-type" docs/cli-reference.md "lattice-type"
grep_check "48-6 CLI ref --cage-guest" docs/cli-reference.md "cage-guest"
grep_check "48-6 CLI ref --depol" docs/cli-reference.md "depol"

# 48-6: CLI reference marks deprecated flags
grep_check "48-6 CLI ref DEPRECATED --guest" docs/cli-reference.md "deprecated.*--guest|--guest.*deprecated|DEPRECATED"
grep_check "48-6 CLI ref DEPRECATED --cage-occupancy" docs/cli-reference.md "deprecated.*cage-occupancy|cage-occupancy.*deprecated"

# 48-7: CLI reference version says v4.7
grep_check "48-7 CLI ref v4.7 reference" docs/cli-reference.md "4\.7"

# 48-8: GRO/ITP guide documents custom guest ITP requirements
grep_check "48-8 GRO/ITP guide comb-rule=2" docs/gro-itp-guide.md "comb-rule.*2|Lorentz-Berthelot|comb.rule.*2"
grep_check "48-8 GRO/ITP guide residue <=3 chars" docs/gro-itp-guide.md "residue.*3|3.*char|5.*char|<=.*3"
grep_check "48-8 GRO/ITP guide _H suffix convention" docs/gro-itp-guide.md "_H|suffix"

# 48-13: Version string is 4.7.0
VER_OUT=$(python -m quickice --version 2>&1)
if echo "$VER_OUT" | grep -q "4.7.0"; then
  check "48-13 version string 4.7.0" PASS
else
  check "48-13 version string 4.7.0 (got: $VER_OUT)" FAIL
fi

# Print results
echo ""
echo "=== Results ==="
for r in "${results[@]}"; do
  color=""
  case "$r" in
    *: PASS) color="\033[32m" ;;
    *: FAIL) color="\033[31m" ;;
    *: SKIP) color="\033[33m" ;;
  esac
  printf "${color}%-60s %s\033[0m\n" "${r%%:*}" "${r##*: }"
done
echo ""
echo "Passed: $PASS  Failed: $FAIL  Skipped: $SKIP"
[ "$FAIL" -eq 0 ]
