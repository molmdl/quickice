#!/usr/bin/env bash
# Workflow G: Export File Inspection (Phase 38, 41, 42)
# Part 1: Custom guest export — verified via pytest (CLI doesn't support custom
#         guest in hydrate for v4.7 — GUI-only by design; tests use Python API).
# Part 2: Mixed built-in hydrate — generated via CLI --cage-guest --gromacs,
#         then .top/.gro inspected for required content + grompp.
#
# Usage:  bash .planning/uat-workflows/G-export-inspection.sh
# Env:    conda env quickice active, gmx on PATH (optional, for grompp check)

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

run_pytest() {
  local label="$1"; shift
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

echo "=== Workflow G: Export File Inspection ==="
echo ""

# ---------------------------------------------------------------------------
# Part 1: Custom guest export file inspection (via pytest — CLI doesn't
# support custom guest in hydrate for v4.7; tests use Python API directly)
# ---------------------------------------------------------------------------

# 41-1: Custom guest appears in .top with _H suffix moleculetype name (MOL_H)
#   Tested by: test_custom_guest_cli_grompp_passes (asserts MOL_H in [molecules])
#              test_multi_molecule_top_custom_guest (asserts _H in .top)
run_pytest "41-1 custom guest _H suffix in .top" \
  tests/test_e2e_custom_guest_cli_grompp.py::test_custom_guest_cli_grompp_passes \
  tests/test_output/test_multi_molecule_top_custom_guest.py \
  tests/test_output/test_interface_top_custom_guest.py

# 41-2: Custom guest atomtypes commented out in .itp + merged into .top with dedup
#   Tested by: test_merge_custom_atomtypes (dedup primitive)
#              test_custom_guest_bridge.py (transform_guest_itp comments atomtypes)
run_pytest "41-2 atomtypes commented + merged + deduped" \
  tests/test_output/test_merge_custom_atomtypes.py \
  tests/test_custom_guest_bridge.py -k "transform or itp or atomtype"

# 41-3: GRO custom guest residue name ≤5 chars (MOL_H = 5 chars)
#   Tested by: test_custom_guest_cli_grompp_passes (asserts MOL_H in .gro residues)
#              test_multi_molecule_gro_custom_guest (GRO residue name check)
run_pytest "41-3 custom guest GRO residue ≤5 chars" \
  tests/test_e2e_custom_guest_cli_grompp.py::test_custom_guest_cli_grompp_passes \
  tests/test_output/test_multi_molecule_gro_custom_guest.py \
  tests/test_output/test_interface_gro_custom_guest.py

# 38-1/38-2: THF metadata identification + HydrateConfig metadata threading
#   Tested by: test_build_molecule_index (THF not misidentified as water)
#              test_gromacs_export_hydrate (metadata threads to export)
run_pytest "38-1/2 THF metadata identification + threading" \
  tests/test_build_molecule_index.py \
  tests/test_output/test_gromacs_export_hydrate.py

# ---------------------------------------------------------------------------
# Part 2: Mixed built-in occupancy hydrate export inspection
# NOTE: CLI export uses write_interface_* (single-guest-stream) which CANNOT emit
# a mixed [molecules] block — known limitation per STATE.md [42-07]. The mixed
# export IS verified via write_multi_molecule_* (GUI writers) in pytest tests.
# So we use pytest here, not CLI generation.
# ---------------------------------------------------------------------------

# 42-3: Mixed .top has both ch4 + thf .itp #includes + CH4_H + THF_H in [molecules]
#   Tested by: test_mixed_cage_cli.py (uses write_multi_molecule_* with both guests)
#              test_gromacs_export_hydrate.py::TestMultiGuestWriter (mixed .top/.gro)
run_pytest "42-3 mixed .top has both ch4 + thf .itp #includes" \
  tests/test_cli/test_mixed_cage_cli.py \
  tests/test_output/test_gromacs_export_hydrate.py::TestMultiGuestWriter

# 42-3: grompp on mixed export (if gmx available)
#   Tested by: test_mixed_cage_cli.py::test_mixed_cli_built_in_grompp (@gmx_skipif)
GMX_AVAILABLE=0
command -v gmx >/dev/null 2>&1 && GMX_AVAILABLE=1

if [ "$GMX_AVAILABLE" -eq 1 ]; then
  run_pytest "42-3 mixed hydrate grompp rc=0" \
    tests/test_cli/test_mixed_cage_cli.py -k "grompp"
else
  check "42-3 mixed hydrate grompp rc=0" SKIP
fi

# Print results
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
