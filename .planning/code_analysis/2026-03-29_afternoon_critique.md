# QuickIce Code Analysis Report
**Timestamp**: 2026-03-29_afternoon
**Scope**: Security, Correctness, Performance, Code Quality
**Status**: Cache code has been REVERTED. This report covers remaining issues.

---

## Verification: Cache Code Reverted

Confirmed removed:
- `quickice/output/precompute_diagram.py` — **deleted**
- `phase_diagram.py` — no `load_cached_diagram`, no `use_cached` parameter
- `main.py` — no cache imports, no `--compute-diagram` flag
- `parser.py` — `--compute-diagram` flag **removed**
- `orchestrator.py` — calls `generate_phase_diagram()` without `use_cached`

**Security issue S1 (pickle deserialization) is now resolved.**

---

## VII/VIII Boundary Update (User-Note)

`solid_boundaries.py:vii_viii_boundary()` now uses `VII_VIII_X` triple point (100K, 62000 MPa) as the low-temperature endpoint instead of a hardcoded pressure. This is a real triple point in `triple_points.py`. The boundary is now:

```python
# Linear interpolation from (278K, 2100 MPa) to (100K, 62000 MPa)
```

**Logic check** (via `lookup_phase`):
- At T=90K, P=3000 MPa: `T <= 100` → returns `ice_viii` ✅
- At T=150K, P=3000 MPa: `100 < T < 278` → compares against boundary (~11500 MPa) → `3000 < 11500` → returns `ice_vii` ✅
- At T=90K, P=80000 MPa: `T <= 100` → returns `ice_viii` (correct — still below X boundary of 62000 MPa... wait, 80000 > 62000, so should be ice_x)

Actually there is still an issue in `lookup_phase` — the Ice X check only triggers when P > 30000 MPa, and then it calls `x_boundary(T)`. At T=90K, `x_boundary(90)` returns 62000 (clamped). So P=80000 > 62000 → Ice X. The code at `lookup.py:158-165` handles this:

```python
if P > 30000:
    P_x = x_boundary(T)
    if P > P_x:
        phase_id = "ice_x"
```

At T=90K, P=80000: 80000 > 30000 → enters block, x_boundary(90) = 62000, 80000 > 62000 → Ice X ✅

The VII/VIII boundary update is internally consistent.

---

## Issue Summary

### Still Present

| ID | Severity | Category | File | Line(s) | Status |
|----|----------|----------|------|---------|--------|
| C1 | 🔴 Critical | Correctness | lookup.py | 231-260 | **NOT FIXED** |
| C2 | 🔴 Critical | Correctness | lookup.py | 220-225 | **NOT FIXED** |
| S2 | 🔴 Critical | Security | orchestrator.py | 48-49 | **NOT FIXED** |
| S3 | 🔴 Critical | Correctness | generator.py | 83 | **NOT FIXED** |
| P2 | 🟡 Moderate | Performance | phase_diagram.py | 747-749 | **NOT FIXED** |
| P3 | 🟡 Moderate | Performance | phase_diagram.py | 916 | **NOT FIXED** |
| PH1 | 🟡 Moderate | Physics | lookup.py | 331-346 | **NOT FIXED** |
| Q1 | 🟢 Minor | Quality | lookup.py | 11 | **NOT FIXED** |
| Q2 | 🟢 Minor | Quality | generator.py | 123 | **NOT FIXED** |

### Resolved

| ID | Severity | Category | File | Reason |
|----|----------|----------|------|--------|
| S1 | 🔴 Critical | Security | precompute_diagram.py | Cache file deleted |
| P1 | 🟡 Moderate | Performance | phase_diagram.py | Cache removed, but IAPWS97 loop still runs |

---

## 🔴 CRITICAL — Not Fixed

### C1: Ice VI region misclassification at high pressure
**File**: `quickice/phase_mapping/lookup.py:231-260`

```python
if T >= 218.95 and P > 620:
    ...
    elif T > 278:
        P_vi_vii = vi_vii_boundary(T)
        phase_id = "ice_vii" if P > P_vi_vii else "ice_vi"
    else:
        # T in [218.95, 278] → returns ice_vi WITHOUT boundary check
        phase_id = "ice_vi"
    return _build_result(phase_id, T, P)
```

**Problem**: For T ∈ [218.95, 278] and P ∈ (vi_vii_boundary(T), 2100], the code returns `ice_vi` without checking the VI-VII boundary.

Example: T=250K, P=2070 MPa:
- `vi_vii_boundary(250) = 2063.5 MPa`
- 2070 > 2063.5, so it should be `ice_vii`
- But P=2070 NOT > 2100, so enters Ice VI block
- T=250 > 354.75? No. T=250 > 278? No → `else` returns `ice_vi` ← **WRONG**

**Impact**: Wrong phase assigned at moderate-low T, high P.

**Fix**: Add boundary check for T in [218.95, 278]:
```python
else:
    # T in [218.95, 278]: check VI-VII-VIII boundary
    P_vi_viii = vi_vii_boundary(T)
    phase_id = "ice_vii" if P > P_vi_viii else "ice_vi"
```

---

### C2: Ice XV boundary check is too narrow
**File**: `quickice/phase_mapping/lookup.py:220-225`

```python
if 80.0 <= T <= 108.0 and 1000 <= P <= 1200:
    P_xv = xv_boundary(T)
    if abs(P - P_xv) < 100:
        phase_id = "ice_xv"
```

**Problem**: `xv_boundary(T)` always returns 1100.0 for T in [80, 108]. The check `abs(P - 1100) < 100` means `1000 <= P <= 1200`. But `phase_diagram.py` shows Ice XV extends from P=950 to P=2100 MPa. At T=90K, P=1500 MPa (Ice XV per diagram) would NOT match here.

**Impact**: Ice XV misclassified.

**Fix**: Either widen the pressure range, or change the boundary check to use the actual polygon geometry.

---

### S2: Path traversal in --output argument
**File**: `quickice/output/orchestrator.py:48-49`

```python
output_path = Path(output_dir)
output_path.mkdir(parents=True, exist_ok=True)
```

**Problem**: No validation of `output_dir`. User can write to arbitrary paths:
```bash
python quickice.py -T 273 -P 0.1 -N 216 -o ../../etc/evil
```

**Fix**:
```python
output_path = Path(output_dir).resolve()
allowed_base = Path.cwd().resolve()
if not str(output_path).startswith(str(allowed_base)):
    raise ValueError(f"Output path must be within {allowed_base}")
output_path.mkdir(parents=True, exist_ok=True)
```

---

### S3: Global numpy random state pollution
**File**: `quickice/structure_generation/generator.py:83`

```python
np.random.seed(seed)
```

**Problem**: `np.random.seed()` sets GLOBAL state. Any other library using `np.random` during or after this call gets affected. GenIce may also use numpy internally, leading to non-deterministic hydrogen bond network generation.

**Fix**: Use a local random generator:
```python
rng = np.random.Generator(np.random.PCG64(seed))
# Use rng.uniform(...), rng.integers(...), etc. instead of np.random.*
```

---

## 🟡 MODERATE — Not Fixed

### P2: Shapely centroid computed every render
**File**: `quickice/output/phase_diagram.py:747-749`

```python
shapely_poly = ShapelyPolygon(vertices)
centroid = shapely_poly.centroid
```

**Problem**: Computed for 11 phases on every render. Only used for label placement — not precision-critical.

---

### P3: 300 DPI PNG on every CLI run
**File**: `quickice/output/phase_diagram.py:916`

```python
plt.savefig(png_path, dpi=dpi, bbox_inches='tight', facecolor='white')  # dpi=300
```

**Problem**: 300 DPI is publication quality. No option for lower DPI. Combined with all other rendering, this is a dominant slow step.

---

### PH1: Ice Ih fallback approximation is too broad
**File**: `quickice/phase_mapping/lookup.py:331-346`

```python
except ValueError:
    if P < 200:
        phase_id = "ice_ih"
```

**Problem**: At T < 251.165K, the fallback `P < 200` covers conditions where Ice Ic (T<150K, P<100), Ice XI (T<72K), or Ice II (P>200) should be checked first.

---

## 🟢 MINOR — Not Fixed

### Q1: Unused `import math`
**File**: `quickice/phase_mapping/lookup.py:11`

### Q2: Overly broad exception in GenIce wrapper
**File**: `quickice/structure_generation/generator.py:123`
Catches `Exception` instead of specific GenIce exceptions.

---

## Recommendations

### Immediate (Critical — must fix before use)

1. **Fix C1 (Ice VI misclassification)** — add boundary check in the `else` branch at lookup.py:258
2. **Fix S2 (path traversal)** — validate output directory path
3. **Fix C2 (Ice XV)** — widen pressure range or switch to polygon-based check

### Recommended (Should fix)

4. **Fix S3 (np.random.seed)** — use `np.random.Generator` with `PCG64` for proper seed isolation
5. **Fix P3 (300 DPI)** — add CLI flag for DPI, default to 150 for routine use
6. **Fix PH1 (Ice Ih fallback)** — check Ice XI, Ice Ic before falling back to Ice Ih

### Nice to have

7. Remove unused `import math` (Q1)
8. Catch specific exceptions instead of `Exception` (Q2)
9. Precompute centroid or use a bounding-box heuristic instead of Shapely (P2)
