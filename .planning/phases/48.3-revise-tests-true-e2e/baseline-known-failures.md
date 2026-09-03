# Pre-Phase Known Failures (Phase 48.3 Baseline)

Captured 2026-09-03 during 48.3-01 (pre-phase baseline plan).

## The single known pre-existing failure

`tests/test_entry_point.py::TestHelpAndVersion::test_version_shows_version`

- **Symptom:** asserts `"4.5.0"` in stdout but actual version is `4.7.0` (stale assert left over from the v4.5 → v4.7 version bump). Failure site: `tests/test_entry_point.py:67: AssertionError`.
- **Status at baseline:** `python -m pytest tests/test_entry_point.py -q` → `1 failed, 11 passed in 5.75s`.
- **Origin:** PRE-EXISTING (research §7) — it predates phase 48.3 entirely and is unrelated to any 48.3 test reorganization work.
- **Fix scheduled:** 48.3-03 will fix the stale version assert. A full-suite baseline is captured in 48.3-03 (the full suite deadlocks today at `tests/test_custom_molecule_panel_34_6.py` — a C-level VTK hang — which 48.3-03 also fixes, so a pre-phase full-suite run is intentionally NOT captured here).

## Rule for all downstream 48.3 gates

This failure must **NOT** be counted as a regression by any gate **before the 48.3-03 fix lands**. Until then:

- Any subset/full gate that includes `tests/test_entry_point.py` expects exactly `1 failed` — `test_version_shows_version` — with all other tests passing.
- Gate diffs must attribute this failure to this baseline record, not to the plan under verification.
- After 48.3-03 lands, the expected count becomes `0 failed` for this file, and this record applies only to plans executed before 48.3-03.

Per GATES.md, no other failures are expected anywhere in the suite at this baseline.
