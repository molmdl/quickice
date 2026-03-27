# Summary: Fix Phase Diagram and Ranking Output

**Task:** 002-fix-diagram-and-ranking-output
**Status:** Complete
**Date:** 2026-03-27

---

## Changes Made

### 1. Phase Diagram Boundary Visibility
**File:** `quickice/output/phase_diagram.py`

- Increased melting curve linewidth from 1.5 to 3.0 for better visibility
- Added liquid-vapor boundary using IAPWS97 saturation curve (solid blue line)
- Vapor label positioned at T=460K, P=0.5 MPa (below saturation curve in vapor region)

### 2. Ranking Score Display
**File:** `quickice/main.py`

- Added formatted table showing top 5 candidates with:
  - Rank (1 = best)
  - Energy score (lower = better)
  - Density score (lower = better)
  - Diversity score (higher = more unique)
  - Combined score (weighted combination)

---

## Verification

```bash
$ python quickice.py -T 273 -P 0.1 -N 216 -o out_test5

Ranking scores (lower combined = better):
----------------------------------------------------------------------
Rank  Energy      Density     Diversity   Combined    
----------------------------------------------------------------------
1     0.0898      0.0008      1.0000      1.0000      
2     0.0899      0.0008      1.0000      1.0353      
3     0.0900      0.0008      1.0000      1.0839      
...
----------------------------------------------------------------------
```

---

## Files Modified

1. `quickice/output/phase_diagram.py` - IAPWS saturation curve, thicker melting curves
2. `quickice/main.py` - Added ranking score table output
