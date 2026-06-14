# Phase 36: CLI Feature Parity - Context

**Gathered:** 2026-06-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Add CLI flags for all v4.5 features so users can run the complete Interface→Custom→Solute→Ion pipeline from the command line with the same capabilities as the GUI. This covers: hydrate generation, custom molecule insertion, solute insertion, ion insertion with source selection, and complete system GROMACS export. No GUI dependency in CLI code.

</domain>

<decisions>
## Implementation Decisions

### Flag design & naming
- Tab-aligned flag names matching GUI terminology: --hydrate, --solute-type, --ion-source, --custom-gro, --custom-itp
- Flag groups organized by pipeline step in --help: "hydrate generation", "custom molecule insertion", "solute insertion", "ion insertion"
- Explicit --source flags for source selection: --ion-source {interface,custom,solute}, --solute-source {interface,custom}
- Strict flag validation: --hydrate requires --lattice-type AND --guest; --solute-type requires --solute-concentration; errors caught before any computation runs

### Pipeline behavior & output
- Export only the most downstream (final) structure at pipeline end: ions > solutes > custom > interface > ice
- Output files named by step: ion.gro/ion.top, solute.gro/solute.top, custom.gro/custom.top, interface.gro/interface.top, ice.gro/ice.top
- All ITP files (tip4p-ice.itp, ch4_hydrate.itp, ion.itp, custom.itp, etc.) placed in same directory as .gro/.top
- Single -o directory for all output (existing pattern, created if needed)

### Error handling & validation
- Flag dependency errors: clear message describing what's missing + exit code 2 (argparse convention)
- Mid-pipeline failure: fail fast — print error, exit non-zero, don't attempt remaining steps or export
- File overwrite: default to auto-overwrite (removes current interactive stdin prompt that breaks piping); add --no-overwrite flag to error if files exist
- Exit codes: Unix convention — 0=success, 1=runtime error (insertion failure, overlap), 2=argument error (missing/invalid flags)

### Custom molecule input format
- Custom placement positions via CSV file (--custom-positions-file) with columns: x,y,z,alpha,beta,gamma
- Euler angles (ZXZ convention, degrees) — matches GUI table format
- --custom-count and --custom-concentration are mutually exclusive flags for random mode
- --custom-placement defaults to "random"; explicit "custom" value required for CSV input mode
- Provide example CSV file for testing and document format in CLI help/docs

### OpenCode's Discretion
- Exact short flag assignments (avoiding collisions with existing -T, -P, -N, -o, -g)
- Pipeline executor internal structure (pipeline.py class design)
- Progress message format and granularity
- Whether to use tqdm (optional dependency) for progress bars
- Internal error message wording (as long as it's clear and identifies the missing flag)

</decisions>

<specifics>
## Specific Ideas

- "Keep simple, consistent, human-friendly, and allow full GUI capability in CLI for easy automation"
- Example CSV file should be provided for testing and explained in documentation
- CSV format should be scientific-tool-friendly (easy to generate from Python/MATLAB)
- Existing CLI patterns (argument groups, validators, check_output_file) should be extended, not replaced
- No GUI imports in CLI code (critical for future unified entry point and CLI-only PyInstaller bundle)

</specifics>

<deferred>
## Deferred Ideas

- Multiple custom molecule types in one run (GUI only supports one .gro/.itp pair currently) — future phase
- CLI-only PyInstaller bundle — pending todo, depends on Phase 36 completion
- Unified GUI/CLI entry point — Phase 37, depends on Phase 36 completion

</deferred>

---

*Phase: 36-cli-feature-parity*
*Context gathered: 2026-06-14*
