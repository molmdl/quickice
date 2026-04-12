---
phase: 22-ice-ih-iapws-density
verified: 2026-04-12T10:30:00Z
status: passed
score: 3/3 must-haves verified
gaps: []
---

# Phase 22: Ice Ih IAPWS Density Verification Report

**Phase Goal:** Users can view accurate Ice Ih density that varies with temperature, replacing the hardcoded 0.9167 g/cm³ value.

**Verified:** 2026-04-12
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth   | Status     | Evidence       |
| --- | ------- | ---------- | -------------- |
| 1   | System calculates Ice Ih density from IAPWS equation of state using temperature input | ✓ VERIFIED | `ice_ih_density.py` imports `iapws._iapws._Ice()` and returns temperature-dependent values (0.9330 at 100K, 0.9167 at 273.15K) |
| 2   | System displays Ice Ih density in the UI with proper units (g/cm³) | ✓ VERIFIED | GUI (main_window.py:764-766) and CLI (main.py:38-42) both display IAPWS density with "g/cm³" units |
| 3   | System uses IAPWS calculation throughout instead of hardcoded 0.9167 value | ✓ VERIFIED | `lookup.py:64-65` calls `ice_ih_density_gcm3(T,P)` for ice_ih; density varies with temperature in actual use |

**Score:** 3/3 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quickice/phase_mapping/ice_ih_density.py` | IAPWS density calculation module | ✓ VERIFIED | 95 lines, imports `iapws._iapws._Ice()`, provides `ice_ih_density_gcm3()` with @lru_cache |
| `quickice/phase_mapping/lookup.py` | Backend integration | ✓ VERIFIED | Line 64-65 calls `ice_ih_density_gcm3(T,P)` for ice_ih phase in `_build_result()` |
| `quickice/gui/main_window.py` | GUI display | ✓ VERIFIED | Line 764-766 calculates IAPWS density for ice_ih, line 773 displays with "g/cm³" |
| `quickice/main.py` | CLI display | ✓ VERIFIED | Line 38-42 displays density from lookup_phase with "g/cm³" units |
| `tests/test_phase_mapping.py` | Tests | ✓ VERIFIED | 98 tests pass |
| `tests/test_cli_integration.py` | CLI tests | ✓ VERIFIED | 23 tests pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|---|-----|--------|---------|
| `ice_ih_density.py` | `lookup.py` | Import in _build_result() | ✓ WIRED | Line 64: `from quickice.phase_mapping.ice_ih_density import ice_ih_density_gcm3` |
| `lookup.py` | GUI | lookup_phase() call | ✓ WIRED | main_window.py:764 calls IAPWS function |
| `lookup.py` | CLI | lookup_phase() call | ✓ WIRED | main.py:34 calls lookup_phase, returns IAPWS density |
| IAPWS library | ice_ih_density.py | iapws._iapws._Ice() | ✓ WIRED | Line 26 imports, line 65 calls with T,P to get density |

### Requirements Coverage

| Requirement | Status | Blocking Issue |
|-------------| -------- | -------------- |
| ICE-01: System calculates Ice Ih density from IAPWS (temperature-dependent) | ✓ SATISFIED | None |
| ICE-02: System displays Ice Ih density in UI | ✓ SATISFIED | None |
| ICE-03: System replaces hardcoded 0.9167 with IAPWS calculation | ✓ SATISFIED | None |

### Anti-Patterns Found

No anti-patterns found. All 0.9167 references in codebase are appropriate:
- Documentation explaining fallback values
- Error fallback when IAPWS can't be used (ice_ih_density.py:30)
- Default metadata values when not provided (scorer.py:162)
- The actual lookup path uses IAPWS calculation as verified

### Human Verification Required

None required - all verifiable programmatically.

### Gaps Summary

No gaps found. All success criteria met:
- IAPWS R10-06(2009) equation of state calculates temperature-dependent Ice Ih density
- GUI displays density with proper units (g/cm³)
- CLI displays density with proper units (g/cm³)
- All tests pass (121 total: 98 + 23)
- Density varies with temperature (0.9330 at 100K to 0.9167 at 273.15K) - confirms IAPWS is being used, not hardcoded value

---

_Verified: 2026-04-12T10:30:00Z_
_Verifier: OpenCode (gsd-verifier)_