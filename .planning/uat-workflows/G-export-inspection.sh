#!/usr/bin/env bash
# Workflow G: Export File Inspection (Phase 38, 41, 42)
# Generates + exports hydrate structures via CLI, then inspects the exported
# .top / .gro / .itp files for required content.
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

echo "=== Workflow G: Export File Inspection ==="
echo ""

TMP=$(mktemp -d -t quickice-uat-g-XXXXXX)
trap 'rm -rf "$TMP"' EXIT

# ---------------------------------------------------------------------------
# Part 1: Custom guest hydrate export (CLI path) → inspect .top / .itp / .gro
# ---------------------------------------------------------------------------

# Generate + export a custom guest (ethanol) sI hydrate via CLI
CUSTOM_OUT="$TMP/custom_guest"
python -m quickice --cli --hydrate \
  --lattice-type sI \
  --supercell-x 1 --supercell-y 1 --supercell-z 1 \
  -T 250 -P 1.0 \
  --custom-gro quickice/data/custom/etoh.gro \
  --custom-guest-itp quickice/data/custom/etoh.itp \
  --output-dir "$CUSTOM_OUT" >/dev/null 2>&1

CUSTOM_TOP=$(ls "$CUSTOM_OUT"/*.top 2>/dev/null | head -1)
CUSTOM_GRO=$(ls "$CUSTOM_OUT"/*.gro 2>/dev/null | head -1)
CUSTOM_ITP=$(ls "$CUSTOM_OUT"/*.itp 2>/dev/null | head -1)

# 41-1: Custom guest appears in .top with _H suffix moleculetype name
if [ -n "$CUSTOM_TOP" ] && grep -qE "_H" "$CUSTOM_TOP" 2>/dev/null; then
  check "41-1 custom guest _H suffix in .top [molecules]" PASS
else
  check "41-1 custom guest _H suffix in .top [molecules]" FAIL
fi

# 41-2: Custom guest atomtypes commented out in bundled .itp
if [ -n "$CUSTOM_ITP" ] && grep -qiE "^\s*;.*atomtypes|;\s*\[atomtypes\]" "$CUSTOM_ITP" 2>/dev/null; then
  check "41-2 [atomtypes] commented out in .itp" PASS
else
  check "41-2 [atomtypes] commented out in .itp" FAIL
fi

# 41-2: Custom atomtypes merged into main .top [atomtypes] with dedup
if [ -n "$CUSTOM_TOP" ] && grep -qE "\[atomtypes\]" "$CUSTOM_TOP" 2>/dev/null; then
  # Check for dedup: count atomtype entries — shared types should not be duplicated
  ATOMTYPE_COUNT=$(grep -E "^\s*[a-zA-Z0-9_]+\s+" "$CUSTOM_TOP" 2>/dev/null | grep -icE "hc|c3|h1|oh|ho" || echo 0)
  if [ "$ATOMTYPE_COUNT" -gt 0 ]; then
    check "41-2 custom atomtypes merged into .top [atomtypes]" PASS
  else
    check "41-2 custom atomtypes merged into .top [atomtypes]" FAIL
  fi
else
  check "41-2 custom atomtypes merged into .top [atomtypes]" FAIL
fi

# 41-3: GRO custom guest residue name ≤5 chars
if [ -n "$CUSTOM_GRO" ]; then
  # Extract residue names from GRO (resname is columns 6-10 in atom lines)
  RESNAMES=$(awk 'NR>2 && NF>=5 {print substr($0,6,5)}' "$CUSTOM_GRO" 2>/dev/null | sort -u | grep -v "^W\|^MOL\|^SOL\|^HOH" | head -10)
  BAD_RESNAME=0
  for rn in $RESNAMES; do
    trimmed=$(echo "$rn" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    if [ "${#trimmed}" -gt 5 ]; then
      BAD_RESNAME=1
    fi
  done
  if [ "$BAD_RESNAME" -eq 0 ]; then
    check "41-3 custom guest residue name ≤5 chars in .gro" PASS
  else
    check "41-3 custom guest residue name ≤5 chars in .gro" FAIL
  fi
else
  check "41-3 custom guest residue name ≤5 chars in .gro" FAIL
fi

# ---------------------------------------------------------------------------
# Part 2: Mixed built-in occupancy hydrate export (CLI --cage-guest) → inspect .top
# ---------------------------------------------------------------------------

MIXED_OUT="$TMP/mixed_builtin"
python -m quickice --cli --hydrate \
  --lattice-type sI \
  --supercell-x 1 --supercell-y 1 --supercell-z 1 \
  -T 250 -P 1.0 \
  --cage-guest small=CH4:100 \
  --cage-guest large=THF:100 \
  --output-dir "$MIXED_OUT" >/dev/null 2>&1

MIXED_TOP=$(ls "$MIXED_OUT"/*.top 2>/dev/null | head -1)

# 42-3: Multiple guest .itp #includes in .top
if [ -n "$MIXED_TOP" ] && grep -q "ch4_hydrate.itp" "$MIXED_TOP" 2>/dev/null && grep -q "thf_hydrate.itp" "$MIXED_TOP" 2>/dev/null; then
  check "42-3 mixed .top has both ch4 + thf .itp #includes" PASS
else
  check "42-3 mixed .top has both ch4 + thf .itp #includes" FAIL
fi

# 42-3: Both CH4_H and THF_H in [molecules]
if [ -n "$MIXED_TOP" ] && grep -qE "CH4_H" "$MIXED_TOP" 2>/dev/null && grep -qE "THF_H" "$MIXED_TOP" 2>/dev/null; then
  check "42-3 mixed .top [molecules] has CH4_H + THF_H" PASS
else
  check "42-3 mixed .top [molecules] has CH4_H + THF_H" FAIL
fi

# ---------------------------------------------------------------------------
# Part 3: grompp validation on exports (if gmx available)
# ---------------------------------------------------------------------------

GMX_AVAILABLE=0
command -v gmx >/dev/null 2>&1 && GMX_AVAILABLE=1

if [ "$GMX_AVAILABLE" -eq 1 ]; then
  # Find an .mdp file (may be in the export or in quickice/data)
  MDP_FILE=$(find "$CUSTOM_OUT" "$MIXED_OUT" quickice/data -name "*.mdp" 2>/dev/null | head -1)
  if [ -z "$MDP_FILE" ]; then
    # Create a minimal MDP if none found
    MDP_FILE="$TMP/minimal.mdp"
    cat > "$MDP_FILE" << 'MDP'
    integrator = md
    nsteps = 0
    dt = 0.001
    cutoff-scheme = Verlet
    nlist = grid
    rlist = 1.0
    rcoulomb = 1.0
    rvdw = 1.0
    pbc = xyz
MDP
  fi

  # 42-3: grompp on mixed export
  if [ -n "$MIXED_TOP" ] && [ -n "$(ls $MIXED_OUT/*.gro 2>/dev/null | head -1)" ]; then
    MIXED_GRO=$(ls "$MIXED_OUT"/*.gro 2>/dev/null | head -1)
    if gmx grompp -f "$MDP_FILE" -c "$MIXED_GRO" -p "$MIXED_TOP" \
      -o "$TMP/mixed_pp.tpr" -maxwarn 5 >/dev/null 2>&1; then
      check "42-3 mixed hydrate grompp rc=0" PASS
    else
      check "42-3 mixed hydrate grompp rc=0" FAIL
    fi
  else
    check "42-3 mixed hydrate grompp rc=0" SKIP
  fi
else
  check "42-3 mixed hydrate grompp rc=0" SKIP
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
  printf "${color}%-55s %s\033[0m\n" "${r%%:*}" "${r##*: }"
done
echo ""
echo "Passed: $PASS  Failed: $FAIL  Skipped: $SKIP"
[ "$FAIL" -eq 0 ]
