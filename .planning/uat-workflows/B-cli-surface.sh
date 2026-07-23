#!/usr/bin/env bash
# Workflow B: CLI Surface & Flags (Phase 43, 45)
# Covers: depol CLI flag, CLI lattice type choices, --cage-guest flag.
#
# Usage:  bash .planning/uat-workflows/B-cli-surface.sh
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

echo "=== Workflow B: CLI Surface & Flags ==="
echo ""

HELP_OUT=$(python -m quickice --cli --help 2>&1 || python -m quickice --help 2>&1)

# 43-1: --depol flag present in CLI help with strict/optimal choices
if echo "$HELP_OUT" | grep -q -- "--depol {strict,optimal}"; then
  check "43-1 --depol flag with strict/optimal choices" PASS
else
  check "43-1 --depol flag with strict/optimal choices" FAIL
fi

# 45-7: --lattice-type shows all 10 choices
LATTICE_LINE=$(echo "$HELP_OUT" | grep -oE -- "--lattice-type \{[^}]*\}" | head -1)
EXPECTED_LATTICES="{sI,sII,sH,c0te,c1te,c2te,ice1hte,sTprime,16,17}"
if [ "$LATTICE_LINE" = "--lattice-type $EXPECTED_LATTICES" ]; then
  check "45-7 --lattice-type all 10 choices" PASS
else
  check "45-7 --lattice-type all 10 choices" FAIL
fi

# 45-7: --cage-guest repeatable flag present
if echo "$HELP_OUT" | grep -q -- "--cage-guest KEY=GUEST:OCC"; then
  check "45-7 --cage-guest repeatable flag" PASS
else
  check "45-7 --cage-guest repeatable flag" FAIL
fi

# 45-7: deprecated flags marked
if echo "$HELP_OUT" | grep -qi "deprecated.*cage-guest\|cage-guest.*deprecated"; then
  check "45-7 --guest/--cage-occupancy deprecated banners" PASS
else
  check "45-7 --guest/--cage-occupancy deprecated banners" FAIL
fi

# 43-1 / 45-7: --depol strict runs (sI hydrate, minimal supercell)
# --output must be under the working directory (CLI validates this)
TMP="_uat_tmp_b"
mkdir -p "$TMP"
if python -m quickice --cli --hydrate --lattice-type sI --depol strict \
  --supercell-x 1 --supercell-y 1 --supercell-z 1 \
  -T 250 -P 1.0 --output "$TMP/strict" --no-diagram >/dev/null 2>&1; then
  check "43-1/45-7 --depol strict runs" PASS
else
  check "43-1/45-7 --depol strict runs" FAIL
fi

# 45-7: --depol optimal runs
if python -m quickice --cli --hydrate --lattice-type sI --depol optimal \
  --supercell-x 1 --supercell-y 1 --supercell-z 1 \
  -T 250 -P 1.0 --output "$TMP/optimal" --no-diagram >/dev/null 2>&1; then
  check "45-7 --depol optimal runs" PASS
else
  check "45-7 --depol optimal runs" FAIL
fi

# 45-7: default (no --depol) = strict (verify flag absence doesn't crash + produces output)
if python -m quickice --cli --hydrate --lattice-type sI \
  --supercell-x 1 --supercell-y 1 --supercell-z 1 \
  -T 250 -P 1.0 --output "$TMP/default" --no-diagram >/dev/null 2>&1; then
  check "45-7 default depol (strict) runs" PASS
else
  check "45-7 default depol (strict) runs" FAIL
fi

rm -rf "$TMP"

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
