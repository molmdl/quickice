---
phase: 08-gui-infrastructure-core-input
plan: 01
subsystem: gui-model
tags: [validators, workers, pyside6, qthread, mvvm]
completed: 2026-03-31
duration: 5m
---

# Phase 08 Plan 01: GUI Model Layer Summary

**One-liner:** Created GUI-specific validators returning (bool, str) tuples and QThread-based GenerationWorker for background processing.

---

## What Was Built

### 1. GUI Validators Module (`quickice/gui/validators.py`)
Three validator functions for inline error display in GUI:

- **`validate_temperature(value: str) -> tuple[bool, str]`**
  - Range: 0-500 K
  - Returns `(True, "")` on success, `(False, "error message")` on failure

- **`validate_pressure(value: str) -> tuple[bool, str]`**
  - Range: 0-10000 **BAR** (not MPa like CLI validators)
  - Returns `(True, "")` on success, `(False, "error message")` on failure

- **`validate_nmolecules(value: str) -> tuple[bool, str]`**
  - Range: 4-216 molecules (max 216, not 100000 like CLI)
  - Rejects non-integer values (e.g., "4.5")
  - Returns `(True, "")` on success, `(False, "error message")` on failure

### 2. Generation Worker Module (`quickice/gui/workers.py`)
QThread-compatible worker for background ice structure generation:

- **`GenerationResult` dataclass**
  - `success: bool`
  - `result: Optional[Any]` - ranking result on success
  - `error: Optional[str]` - error message on failure

- **`GenerationWorker(QObject)`**
  - Worker-object pattern (QObject with run method, NOT QThread subclass)
  - Signals: `progress(int)`, `status(str)`, `finished(object)`, `error(str)`, `cancelled()`
  - Pressure conversion: bar → MPa (`pressure_mpa = pressure * 0.1`)
  - Cancellation checks at each pipeline stage via `isInterruptionRequested()`
  - Modules imported inside `run()` to avoid blocking main thread
  - Progress stages: 10% start → 20% phase lookup → 60% candidates → 90% ranking → 100% complete

---

## Key Differences from CLI Validators

| Feature | CLI Validators | GUI Validators |
|---------|---------------|----------------|
| Return type | Value or raise `ArgumentTypeError` | `tuple[bool, str]` |
| Pressure unit | MPa (0-10000 MPa) | bar (0-10000 bar) |
| Max molecules | 100000 | 216 |
| Usage | argparse type converters | QLineEdit validation |

---

## Dependency Graph

```
Phase 08-01 provides:
├── quickice/gui/validators.py
│   └── validate_temperature, validate_pressure, validate_nmolecules
│       └── Will be imported by quickice/gui/view.py (Phase 08-02)
└── quickice/gui/workers.py
    └── GenerationWorker, GenerationResult
        └── Will be used by quickice/gui/viewmodel.py (Phase 08-03)

Phase 08-01 requires:
├── quickice/phase_mapping (lookup_phase)
├── quickice/structure_generation (generate_candidates)
└── quickice/ranking (rank_candidates)
```

---

## Tech Stack Added

| Component | Technology | Notes |
|-----------|-----------|-------|
| GUI Framework | PySide6 6.10.2 | Already in environment |
| Worker Pattern | QObject + QThread | Standard Qt threading |
| Data Transfer | dataclass | GenerationResult for clean result handling |

---

## Files Created

| Path | Lines | Purpose |
|------|-------|---------|
| `quickice/gui/__init__.py` | 1 | Package initialization |
| `quickice/gui/validators.py` | 98 | GUI-specific input validators |
| `quickice/gui/workers.py` | 129 | Background generation worker |

---

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Use bar for pressure | More intuitive for users; standard atmospheric unit |
| Max 216 molecules | Computational limit for interactive GUI; prevents UI freezing |
| Worker-object pattern | Proper Qt pattern for cancellable work with signal emission |
| Import inside run() | Avoids blocking main thread during heavy module imports |
| bar→MPa conversion | API uses MPa internally, GUI uses bar for UX |

---

## Verification Results

All validators and worker verified working:
- Temperature: 300K ✓, 600K (rejected) ✓, "abc" (rejected) ✓
- Pressure: 100 bar ✓, 10001 bar (rejected) ✓
- Molecules: 96 ✓, 216 ✓, 217 (rejected) ✓, 4.5 (rejected) ✓
- Worker: Signals verified, instantiation verified, result dataclass verified

---

## Deviations from Plan

None - plan executed exactly as written.

---

## Next Phase Readiness

**Blockers:** None

**Ready for Phase 08-02:** ✓
- View layer can import validators for QLineEdit validation
- ViewModel can instantiate GenerationWorker for background processing

**Recommendations:**
- Ensure QThread lifecycle management in ViewModel (moveToThread, quit, wait)
- Connect progress/status signals to UI elements in View
