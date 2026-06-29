# Phase 38 Plan 04: ITP Transformation Pipeline Summary

**One-liner:** `transform_guest_itp()` applies _H suffix to moleculetype name, comments out atomtypes, and validates GRO name length; wired into both GUI and CLI hydrate export paths.

---

## Frontmatter

```yaml
phase: 38-internal-pipeline-refactor
plan: 04
subsystem: output
tags: [itp, transformation, gromacs, hydrate, export, pipeline]
completed: 2026-06-29
```

---

## Dependency Graph

```yaml
requires:
  - 38-01 (HydrateConfig guest metadata — guest_type field)
  - 38-03 (validate_gro_residue_name — GRO 5-char limit validation)
provides:
  - transform_guest_itp() — unified ITP transformation for hydrate guest files
  - _H suffix application to moleculetype name in ITP files
  - GRO name validation guard before ITP content written to export
affects:
  - Phase 40 (custom guest hydrate ITPs will use this transformation pipeline)
  - Future liquid solute ITP transformation (_L suffix)
```

---

## Tech Tracking

```yaml
tech-stack:
  added: []
  patterns:
    - transform_guest_itp() as unified ITP transformation entry point
    - hydrate export path reads-transforms-writes instead of shutil.copy
```

---

## Key Files

```yaml
key-files:
  created:
    - tests/test_itp_transformation.py
  modified:
    - quickice/output/gromacs_writer.py
    - quickice/gui/hydrate_export.py
    - quickice/cli/itp_helpers.py
```

---

## What Was Done

### Task 1: Create `transform_guest_itp()` function + tests

Added `transform_guest_itp(itp_content, guest_name, suffix="_H")` to `quickice/output/gromacs_writer.py` after `comment_out_atomtypes_in_itp` (line 570). The function:

1. **Comments out [ atomtypes ] section** — delegates to existing `comment_out_atomtypes_in_itp()`
2. **Appends suffix to moleculetype name** — finds the `[ moleculetype ]` header, then replaces the first non-comment token on the name line with `{guest_name}{suffix}` (e.g., "CH4" → "CH4_H")
3. **Validates GRO name length** — calls `validate_gro_residue_name(new_name)` before any transformation, raising `ValueError` if the result exceeds 5 chars (e.g., "ETHAN_H" = 7 chars → error)

Created 19 tests in `tests/test_itp_transformation.py` covering:
- CH4 → CH4_H moleculetype name transformation
- THF → THF_H transformation
- nrexcl preservation
- Overlong base name ValueError (ETHAN + _H = 7 chars)
- Custom suffix `_L` (CH4 → CH4_L)
- Edge cases: no moleculetype section, no atomtypes section, pre-transformed ITP, lowercase moleculetype name, empty content

Commit: `592b8a2`

### Task 2: Wire ITP transformation into hydrate export paths (GUI + CLI)

**GUI path** (`quickice/gui/hydrate_export.py`):
- Replaced `shutil.copy(guest_itp_path, guest_dest_path)` with read-transform-write using `transform_guest_itp(guest_itp_content, guest_upper, suffix="_H")`
- Added `transform_guest_itp` to the import list

**CLI path** (`quickice/cli/itp_helpers.py`):
- Replaced `shutil.copy(source, dest)` in `_copy_hydrate_guest_itp()` with `transform_guest_itp(content, guest_name, suffix="_H")` + `dest.write_text(transformed)`
- Updated docstring to document the transformation

For built-in guests (ch4, thf), the transformation is effectively a no-op since the bundled `_hydrate.itp` files are already pre-transformed with `CH4_H`/`THF_H` moleculetype names and atomtypes already commented out. This is scaffolding for Phase 40 custom guest ITPs.

Full test suite passes: 1105 passed, 2 skipped.

Commit: `8a034a3`

---

## Decisions Made

1. **`transform_guest_itp` replaces the moleculetype name, not matches it.** The function finds the first non-comment token after `[ moleculetype ]` and replaces it with `{guest_name}{suffix}`. This handles both lowercase (`ch4`) and uppercase (`CH4`) source ITPs, and pre-transformed ITPs where the name already has the suffix (no-op replacement).

2. **No [ atoms ] residue name rewriting.** The plan explicitly scopes out modifying residue names in the `[ atoms ]` section. Bundled ITP files already have correct residue names. Custom guest ITPs (Phase 40) will need this as a separate concern.

3. **Validation before transformation.** `validate_gro_residue_name(new_name)` is called at the start of the function, before any string manipulation. This provides a clear early-exit error for overlong names.

4. **`_copy_hydrate_guest_itp` in CLI uses lazy import.** `transform_guest_itp` is imported inside the function body to avoid pulling GROMACS writer dependencies at module level (consistent with CLI import conventions).

---

## Deviations from Plan

None — plan executed exactly as written.

---

## Next Phase Readiness

- **Phase 40 (custom guests):** `transform_guest_itp()` is ready for custom guest ITPs. When custom guests are introduced, the transformation pipeline will:
  1. Comment out atomtypes ✓
  2. Add _H suffix to moleculetype name ✓
  3. **Missing:** Rewrite residue names in `[ atoms ]` section to match new moleculetype name (deferred per plan)
  4. **Missing:** Handle custom ITPs that may not have atomtypes already commented out (already handled by comment_out_atomtypes_in_itp)

- **GRO name limit enforcement:** Custom guest base names >3 chars will fail at `transform_guest_itp` validation. This is intentional — the GRO 5-char limit requires base names ≤3 chars for _H suffix or ≤3 chars for _L suffix.
