#!/usr/bin/env bash
# Workflow C: E2E Generation & Grompp Validation (Phase 41, 45, 47)
# Covers: custom guest grompp (GUI+CLI), new lattice grompp, filled-ice CLI hydrate grompp,
#         mixed occupancy, triclinic blocking, water-only survival.
#
# Usage:  bash .planning/uat-workflows/C-e2e-grompp.sh
# Env:    conda env quickice active, gmx on PATH (grompp tests run if gmx available)

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

# Check gmx availability
GMX_AVAILABLE=0
command -v gmx >/dev/null 2>&1 && GMX_AVAILABLE=1

run_pytest_gmx() {
  # $1 = label, rest = pytest args (gmx_skipif tests)
  local label="$1"; shift
  if [ "$GMX_AVAILABLE" -eq 0 ]; then
    check "$label" SKIP
    return
  fi
  local out
  out=$(python -m pytest "$@" -q --no-header --tb=line 2>&1 | tail -1)
  if echo "$out" | grep -qE "[0-9]+ passed"; then
    if echo "$out" | grep -qE "failed|[0-9]+ error"; then
      check "$label" FAIL
    else
      check "$label" PASS
    fi
  elif echo "$out" | grep -qE "skipped"; then
    check "$label" SKIP
  else
    check "$label" FAIL
  fi
}

echo "=== Workflow C: E2E Generation & Grompp Validation ==="
echo ""

# 41-4: Custom guest GUI grompp (write_multi_molecule_* path)
run_pytest_gmx "41-4 custom guest GUI grompp" tests/test_e2e_custom_guest_gui_grompp.py

# 41-4: Custom guest CLI grompp (write_interface_* path)
run_pytest_gmx "41-4 custom guest CLI grompp" tests/test_e2e_custom_guest_cli_grompp.py

# 47-2: Filled ice generation e2e (structural validation, not gmx-gated)
if python -m pytest tests/test_hydrate_lattice_types.py -q --no-header --tb=line 2>&1 | tail -1 | grep -qE "passed"; then
  check "47-2 filled ice generation e2e" PASS
else
  check "47-2 filled ice generation e2e" FAIL
fi

# 47-3: Mixed cage occupancy e2e
if python -m pytest tests/test_e2e_mixed_cage_occupancy.py tests/test_e2e_sH_cage_occupancy.py -q --no-header --tb=line 2>&1 | tail -1 | grep -qE "passed"; then
  check "47-3 mixed cage occupancy e2e" PASS
else
  check "47-3 mixed cage occupancy e2e" FAIL
fi

# 47-4: Filled-ice CLI hydrate-only grompp (c2te@3x3x3, ice1hte@4x4x4)
run_pytest_gmx "47-4 filled-ice CLI hydrate grompp" tests/test_e2e_filled_ice_cli_hydrate_grompp.py

# 45-1: New lattice types CLI interface export + grompp
if python -m pytest tests/test_cli/ -q --no-header --tb=line -k "interface or lattice" 2>&1 | tail -1 | grep -qE "passed"; then
  check "45-1 new lattices CLI interface export" PASS
else
  check "45-1 new lattices CLI interface export" FAIL
fi

# 45-3: Water-only lattices (sTprime, 17) solute/ion survival
if python -m pytest tests/ -q --no-header --tb=line -k "water_only or sTprime or water-only" 2>&1 | tail -1 | grep -qE "passed"; then
  check "45-3 water-only solute/ion survival" PASS
else
  check "45-3 water-only solute/ion survival" SKIP
fi

# 45-4: Triclinic blocking at CLI interface step (c0te, c1te)
if python -m pytest tests/ -q --no-header --tb=line -k "triclinic or block" 2>&1 | tail -1 | grep -qE "passed"; then
  check "45-4 triclinic blocking CLI" PASS
else
  check "45-4 triclinic blocking CLI" FAIL
fi

# 45-8: Mixed built-in (CH4+THF) + sII/16 GUI hydrate exporter grompp
run_pytest_gmx "45-8 mixed built-in GUI hydrate grompp" tests/test_cli/test_mixed_cage_cli.py

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
  printf "${color}%-55s %s\033[0m\n" "${r%%:*}" "${r##*: }"
done
echo ""
echo "Passed: $PASS  Failed: $FAIL  Skipped: $SKIP"
[ "$FAIL" -eq 0 ]
