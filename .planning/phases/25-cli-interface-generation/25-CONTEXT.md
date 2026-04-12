# Phase 25: CLI Interface Generation - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can generate ice-water interfaces entirely from the command line with full parameter control. The `--interface` flag triggers interface generation with mode parameter (slab/pocket/piece), box dimensions, mode-specific parameters (thickness, diameter, shape), and GROMACS export. CLI behavior follows existing CLI conventions for consistency with the GUI.

</domain>

<decisions>
## Implementation Decisions

### Flag Naming Conventions

- **Follow existing CLI convention:** Long flags use lowercase with hyphens for multi-word parameters (`--box-x`, `--ice-thickness`, `--pocket-diameter`)
- **Short flags:** OpenCode's discretion — add short flags for common parameters if beneficial for usability (e.g., `-x` for `--box-x`, `-m` for `--mode`)
- **Required vs optional:** `--mode` is required, other parameters have sensible defaults (box size from structure, reasonable thickness values)

### Output Verbosity

- **Default output:** Follow existing CLI style plus GUI log panel content:
  - Header with input parameters
  - Mode and box dimensions (like GUI log panel)
  - Candidate info (phase, molecule count)
  - Generation progress
  - Completion message with file paths
- **Format:** Plain text with labels (matching existing CLI style)
- **Verbose/quiet flags:** OpenCode's discretion — add `--verbose` for debugging details or `--quiet` for scripting if useful

### Error Handling

- **Consistency with GUI:** Clear, descriptive error messages (GUI shows QMessageBox, CLI prints to stderr)
- **Exit codes:** Exit code 0 on success, non-zero on error
- **Validation timing:** Fail-fast on argument parsing (consistent with existing CLI behavior)

### File Export Behavior

- **Output location:** Follow existing `--output` flag behavior (default to `output/`, user can specify path)
- **Overwrite behavior:** Interactive y/n prompt for confirmation if file exists
- **File naming:** Auto-generate as `interface_{phase}_{mode}.gro` (e.g., `interface_Ih_slab.gro`)

### OpenCode's Discretion

- Short flag assignments for interface parameters
- Whether to add `--verbose` or `--quiet` flags
- Exact error message formatting
- Progress indicators for long operations

</decisions>

<specifics>
## Specific Ideas

- "Follow current convention for CLI" — match existing quickice.py flag style
- "Follow GUI behavior if possible for consistency" — output should match GUI log panel content
- Output style reference: see `quickice/main.py` for current CLI output format
- GUI log panel reference: see `quickice/gui/main_window.py` lines 448-481 for interface generation logging

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 25-cli-interface-generation*
*Context gathered: 2026-04-12*
