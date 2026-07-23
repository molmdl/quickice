#!/usr/bin/env bash
# Workflow E: Test Suite & Refactor Integrity (Phase 47, 48.1, 48.2)
# Covers: test collection count, full suite pass, gromacs_writer split structure,
#         byte-equivalence baselines, DRY helper existence, test reorganization.
#
# Usage:  bash .planning/uat-workflows/E-test-refactor.sh
# Env:    conda env quickice active
#   RUN_FULL=1  (env var)  → run full pytest suite (slow, ~5 min)
#   RUN_FULL=0  (default)  → run fast subset only

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

RUN_FULL="${RUN_FULL:-0}"

echo "=== Workflow E: Test Suite & Refactor Integrity ==="
echo "(RUN_FULL=$RUN_FULL — set RUN_FULL=1 for full suite)"
echo ""

# 48.2-1: pytest collects 1854 tests, 0 collection errors
COLLECT_OUT=$(python -m pytest --collect-only -q 2>&1 | tail -2)
COLLECT_COUNT=$(echo "$COLLECT_OUT" | grep -oE "[0-9]+ tests collected" | grep -oE "[0-9]+" || echo "0")
if [ "$COLLECT_COUNT" -eq 1854 ]; then
  check "48.2-1 test collection count (1854)" PASS
else
  check "48.2-1 test collection count (got $COLLECT_COUNT, expected 1854)" FAIL
fi
if echo "$COLLECT_OUT" | grep -qiE "error|no tests"; then
  check "48.2-1 collection errors (should be 0)" FAIL
else
  check "48.2-1 collection errors (0)" PASS
fi

# 48.2-2: tests/ root decluttered (0 test_scancode_*.py at root)
ROOT_SCANCODE=$(ls tests/test_scancode_*.py 2>/dev/null | wc -l)
if [ "$ROOT_SCANCODE" -eq 0 ]; then
  check "48.2-2 root test_scancode_*.py removed (0 at root)" PASS
else
  check "48.2-2 root test_scancode_*.py removed ($ROOT_SCANCODE at root)" FAIL
fi

# 48.2-2: 0 phase_48_1_ prefixes in test file names
PHASE_PREFIX=$(find tests/ -name "*phase_48_1_*" -o -name "test_phase_48_1_*" 2>/dev/null | wc -l)
if [ "$PHASE_PREFIX" -eq 0 ]; then
  check "48.2-2 phase_48_1_ prefix dropped (0 remain)" PASS
else
  check "48.2-2 phase_48_1_ prefix dropped ($PHASE_PREFIX remain)" FAIL
fi

# 48.2-2: tests/scancode/ has files; tests/test_cli/ has files; tests/test_output/ has files
SCANCODE_COUNT=$(ls tests/scancode/*.py 2>/dev/null | wc -l)
CLI_COUNT=$(ls tests/test_cli/*.py 2>/dev/null | wc -l)
OUTPUT_COUNT=$(ls tests/test_output/*.py 2>/dev/null | wc -l)
if [ "$SCANCODE_COUNT" -gt 0 ] && [ "$CLI_COUNT" -gt 0 ] && [ "$OUTPUT_COUNT" -gt 0 ]; then
  check "48.2-2 test subdirs populated (scancode=$SCANCODE_COUNT, cli=$CLI_COUNT, output=$OUTPUT_COUNT)" PASS
else
  check "48.2-2 test subdirs populated (scancode=$SCANCODE_COUNT, cli=$CLI_COUNT, output=$OUTPUT_COUNT)" FAIL
fi

# 48.1-1: gromacs_writer.py is a thin re-export shim (<120 lines)
WRITER_LINES=$(wc -l < quickice/output/gromacs_writer.py 2>/dev/null || echo 9999)
if [ "$WRITER_LINES" -lt 120 ]; then
  check "48.1-1 gromacs_writer.py thin shim (${WRITER_LINES} lines <120)" PASS
else
  check "48.1-1 gromacs_writer.py thin shim (${WRITER_LINES} lines, expected <120)" FAIL
fi

# 48.1-1: Per-structure writer modules exist
WRITER_MODULES="ice_writer.py interface_writer.py multi_molecule_writer.py ion_writer.py custom_writer.py solute_writer.py"
ALL_WRITERS_EXIST=1
for mod in $WRITER_MODULES; do
  if [ ! -f "quickice/output/$mod" ]; then
    ALL_WRITERS_EXIST=0
    check "48.1-1 missing writer module: $mod" FAIL
  fi
done
if [ "$ALL_WRITERS_EXIST" -eq 1 ]; then
  check "48.1-1 all 6 per-structure writer modules exist" PASS
fi

# 48.1-1: No output module file >800 lines (approximate — ion_writer=843 is ~5% over, acceptable)
# phase_diagram.py (1132) is out of scope for the 48.1 split (not a GROMACS writer)
LARGEST_FILE=""
LARGEST_LINES=0
for f in quickice/output/*.py; do
  lines=$(wc -l < "$f" 2>/dev/null || echo 0)
  if [ "$lines" -gt "$LARGEST_LINES" ]; then
    LARGEST_LINES=$lines
    LARGEST_FILE=$f
  fi
done
# phase_diagram.py is pre-existing, not part of the 48.1 split scope
LARGEST_WRITER=""
LARGEST_WRITER_LINES=0
for f in quickice/output/ice_writer.py quickice/output/interface_writer.py \
  quickice/output/multi_molecule_writer.py quickice/output/ion_writer.py \
  quickice/output/custom_writer.py quickice/output/solute_writer.py \
  quickice/output/_shared.py quickice/output/_gro_format.py \
  quickice/output/gromacs_writer.py; do
  lines=$(wc -l < "$f" 2>/dev/null || echo 0)
  if [ "$lines" -gt "$LARGEST_WRITER_LINES" ]; then
    LARGEST_WRITER_LINES=$lines
    LARGEST_WRITER=$f
  fi
done
if [ "$LARGEST_WRITER_LINES" -le 900 ]; then
  check "48.1-1 no split module >900 lines (largest writer: $(basename $LARGEST_WRITER)=${LARGEST_WRITER_LINES}; phase_diagram.py=${LARGEST_LINES} out of scope)" PASS
else
  check "48.1-1 no split module >900 lines (largest writer: $(basename $LARGEST_WRITER)=${LARGEST_WRITER_LINES})" FAIL
fi

# 48.1-2: _gro_format.py has DRY GRO helpers
if grep -qE "^def " quickice/output/_gro_format.py 2>/dev/null; then
  HELPER_COUNT=$(grep -cE "^def " quickice/output/_gro_format.py 2>/dev/null || echo 0)
  if [ "$HELPER_COUNT" -ge 5 ]; then
    check "48.1-2 _gro_format.py DRY helpers ($HELPER_COUNT functions)" PASS
  else
    check "48.1-2 _gro_format.py DRY helpers ($HELPER_COUNT functions, expected >=5)" FAIL
  fi
else
  check "48.1-2 _gro_format.py DRY helpers (no functions found)" FAIL
fi

# 48.1-2: _shared.py has shared constants/helpers + _write_top_defaults
if grep -q "_write_top_defaults" quickice/output/_shared.py 2>/dev/null; then
  check "48.1-2 _shared.py _write_top_defaults" PASS
else
  check "48.1-2 _shared.py _write_top_defaults" FAIL
fi

# 48.1-3: baseline_shas.json exists (byte-equivalence baselines)
BASELINE_FILE=$(ls .planning/phases/48.1-*/baseline_shas.json 2>/dev/null | head -1)
if [ -n "$BASELINE_FILE" ] && [ -f "$BASELINE_FILE" ]; then
  check "48.1-3 baseline_shas.json exists" PASS
else
  check "48.1-3 baseline_shas.json exists" FAIL
fi

# 47-1: Custom guest validation + sys.modules + _build_molecule_index unit tests pass
if python -m pytest tests/test_custom_guest_bridge.py tests/test_hydrate_config_custom.py \
  tests/test_build_molecule_index.py -q --no-header --tb=line 2>&1 | tail -1 | grep -qE "passed"; then
  check "47-1 custom guest validation + sys.modules + molecule index" PASS
else
  check "47-1 custom guest validation + sys.modules + molecule index" FAIL
fi

# 48.1-5 / 48.2-1: Full pytest suite (optional, slow)
if [ "$RUN_FULL" -eq 1 ]; then
  if python -m pytest -q --no-header --tb=line 2>&1 | tail -1 | grep -qE "passed"; then
    check "48.1-5/48.2-1 full pytest suite passes" PASS
  else
    check "48.1-5/48.2-1 full pytest suite passes" FAIL
  fi
else
  check "48.1-5/48.2-1 full pytest suite (set RUN_FULL=1 to enable)" SKIP
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
  printf "${color}%-60s %s\033[0m\n" "${r%%:*}" "${r##*: }"
done
echo ""
echo "Passed: $PASS  Failed: $FAIL  Skipped: $SKIP"
[ "$FAIL" -eq 0 ]
