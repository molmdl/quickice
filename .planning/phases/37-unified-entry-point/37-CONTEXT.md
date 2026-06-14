# Phase 37: Unified Entry Point - Context

**Gathered:** 2026-06-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Create a single entry point (`python -m quickice`) that routes to CLI or GUI mode based on command-line flags and display availability. Includes graceful fallback when GUI dependencies are missing, backward compatibility with `quickice.py`, PyInstaller spec update, test invocation normalization, and documentation updates. Does NOT include CLI-only PyInstaller binary (future phase) or new CLI/GUI features.

</domain>

<decisions>
## Implementation Decisions

### Mode Detection & Routing
- `python -m quickice` with NO arguments → show help message (like `git` with no args), NOT auto-launch GUI
- Any computation flag (`--temperature`/`-T`, `--interface`, `--hydrate`, etc.) → CLI mode automatically (implicit, no `--cli` required)
- `--cli` flag is a convenience alias meaning "skip PySide6 import entirely" — useful in headless/CI environments. It does NOT need to be set when pipeline flags are present
- `--gui` flag explicitly requests GUI mode — for explicitness or overriding display detection
- `python -m quickice.gui` stays unchanged as direct GUI launch (bypasses router)
- Routing priority: explicit `--gui` > pipeline flags (→CLI) > display available (→GUI) > no display (→help or fallback)

### Missing Dependency Behavior
- No args + display available + PySide6 missing → auto-fallback to CLI mode with informative message
- Explicit `--gui` + PySide6 missing → exit with error (user asked for something that can't work)
- Pre-check only PySide6, not VTK (VTK fails with its own clear ImportError if missing; PySide6 implies VTK in practice)
- Message points to installation method: git install → "See environment.yml for GUI dependencies"; binary → "Reinstall or report bug — GUI should be included in binary distribution"
- Brief message + actionable pointer, not a wall of text

### Backward Compatibility
- `quickice.py` stays permanently as thin 2-line wrapper — no deprecation warning (zero maintenance cost)
- `quickice.py` updated to delegate to `entry.main()` instead of `main()` directly
- PyInstaller spec (`quickice-gui.spec`) updated: entry point changes from `quickice/gui/__main__.py` → `quickice/__main__.py`
- Binary gets both CLI+GUI capability via single spec; CLI-only spec is future phase
- `--cli` and `--gui` flags added to existing parser (`quickice/cli/parser.py`) for discoverability via `--help`
- Routing logic lives in `quickice/entry.py` (testable independently); `__main__.py` just calls `entry.main()`

### Test Invocation Patterns
- All 4 test files using subprocess switch from `quickice.py` to `python -m quickice` (canonical invocation)
- Consolidate 3 near-identical `run_cli()` helpers into shared `tests/conftest.py` helper with `timeout` parameter
- Dedicated `test_entry_point.py` with ~8-10 tests: no-args→help, `--cli`, pipeline flags→CLI, missing PySide6 fallback, `--gui` explicit, invalid combos, etc.
- One backward compat sanity test: `python quickice.py` still returns exit 0 for basic CLI invocation
- `quickice.py` not exhaustively tested — it's a 2-line wrapper

### Documentation Updates
- Update all existing doc references from `python quickice.py` to `python -m quickice` (primary); quickice.py mentioned as "also works" for backward compat
- No dedicated Quick Task document — infrastructure change, not user-facing feature
- CLI `--help` epilog examples updated from `python quickice.py` to `python -m quickice`
- In-app help dialog NOT updated — binary users don't invoke via command line; they're already in the app
- Platform invocation table in docs:
  - Source install: `python -m quickice [options]`
  - Binary (Linux/macOS): `quickice-gui [options]`
  - Binary (Windows): `quickice-gui.exe [options]` (same flags)
- Brief "Windows: append .exe" note avoids per-platform example duplication

### OpenCode's Discretion
- Exact wording of missing-dependency messages (follows pattern above)
- Error exit codes for specific routing failures
- Whether `python -m quickice` with display available but no computation flags launches GUI or shows help (DECIDED: shows help, like git)
- Conftest helper function signature and timeout defaults
- Test file organization within tests/

</decisions>

<specifics>
## Specific Ideas

- "No-args behavior like git" — `git` with no args shows usage, doesn't launch something
- `python -m quickice.gui` preserved for direct GUI access (bypasses router entirely)
- PyInstaller binary supports both modes after spec update — `quickice-gui` becomes the universal binary name
- Windows binary: `quickice-gui.exe [options]` with same flags as Linux/macOS
- Consistency principle: one primary invocation in docs (`python -m quickice`), one-line binary note, no platform-specific sections

</specifics>

<deferred>
## Deferred Ideas

- CLI-only PyInstaller bundle — stays as pending todo, future phase
- Separate `quickice-cli.spec` for CLI-only binary — future when CLI-only distribution is needed
- Subcommand structure (`quickice generate`, `quickice gui`) — could be v5.0 consideration, but current flat flag structure works well and doesn't need restructuring now

</deferred>

---

*Phase: 37-unified-entry-point*
*Context gathered: 2026-06-14*
