#!/usr/bin/env bash
# Workflow A: Automated Unit & Validation Tests (Phase 38, 40)
# Covers: metadata-driven identification, GRO residue name validation,
#         ITP transformation, custom guest bridge validation, sys.modules injection/cleanup.
#
# Usage:  bash .planning/uat-workflows/A-unit-validation.sh
# Env:    conda env quickice must be active (python + pytest on PATH)

set -uo pipefail

PASS=0; FAIL=0; SKIP=0
results=()

check() {
  # $1 = test label, $2 = pass/fail/skip
  results+=("$1: $2")
  case "$2" in
    PASS) PASS=$((PASS+1)) ;;
    FAIL) FAIL=$((FAIL+1)) ;;
    SKIP) SKIP=$((SKIP+1)) ;;
  esac
}

run_pytest() {
  # $1 = label, rest = pytest args
  local label="$1"; shift
  if python -m pytest "$@" -q --no-header --tb=line 2>/dev/null | tail -1 | grep -qE "passed|[0-9]+ error"; then
    if python -m pytest "$@" -q --no-header --tb=line 2>/dev/null | tail -1 | grep -qE "failed|[0-9]+ error"; then
      check "$label" FAIL
    else
      check "$label" PASS
    fi
  else
    check "$label" FAIL
  fi
}

echo "=== Workflow A: Unit & Validation Tests ==="
echo ""

# 38-1: _build_molecule_index metadata-driven identification (THF not misidentified as water)
run_pytest "38-1 metadata-driven molecule index" tests/test_build_molecule_index.py

# 38-2: HydrateConfig guest metadata threads through pipeline
run_pytest "38-2 HydrateConfig guest metadata" tests/test_hydrate_config_metadata.py

# 38-3: GRO writer rejects residue names >5 chars with ValueError
if python -m pytest tests/test_gro_resname_validation.py -q --no-header --tb=line 2>/dev/null | tail -1 | grep -qE "passed"; then
  check "38-3 GRO residue name validation" PASS
else
  check "38-3 GRO residue name validation" FAIL
fi

# 38-4: ITP transformation applies _H suffix + comments atomtypes + rewrites residue names
# Covered by test_gro_resname_validation (transform path) + custom guest tests
run_pytest "38-4 ITP transformation pipeline" tests/test_custom_guest_bridge.py -k "transform or itp"

# 40-2: Custom guest residue name >3 chars rejected with specific error
run_pytest "40-2 custom guest residue name validation" tests/test_custom_guest_bridge.py -k "name or residue"

# 40-3: ITP comb-rule=1 rejected, comb-rule=2 accepted, no-[defaults] accepted
run_pytest "40-3 ITP comb-rule validation" tests/test_custom_guest_bridge.py -k "comb"

# 40-4 + 40-5: sys.modules injection on main thread + cleanup after generation
run_pytest "40-4/5 sys.modules injection + cleanup" tests/test_custom_guest_bridge.py -k "module or inject or cleanup or register"

# Print results table
echo ""
echo "=== Results ==="
for r in "${results[@]}"; do
  color=""
  case "$r" in
    *": PASS") color="\033[32m" ;;
    *": FAIL") color="\033[31m" ;;
    *": SKIP") color="\033[33m" ;;
  esac
  printf "${color}%-55s %s\033[0m\n" "${r%%:*}" "${r##*: }"
done
echo ""
echo "Passed: $PASS  Failed: $FAIL  Skipped: $SKIP"
[ "$FAIL" -eq 0 ]
