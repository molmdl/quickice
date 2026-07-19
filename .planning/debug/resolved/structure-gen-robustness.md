---
status: investigating
trigger: "Investigate and fix TWO structure-generation robustness issues (scancode Group 7): SUSP-03 (fragile GRO box-line parse in hydrate_generator.py) and SUSP-06 (custom molecule placement with no overlap check and no warning in custom_molecule_inserter.py). Two atomic commits across two files."
created: 2026-07-19T00:00:00Z
updated: 2026-07-19T00:01:00Z
---

## Current Focus

hypothesis: Both findings (SUSP-03, SUSP-06) are CONFIRMED by direct code read; applying fixes now.
test: SUSP-03 — robustly identify box line + raise ValueError if none; SUSP-06 — emit logging.warning on place_custom call + distance-based overlap warning.
expecting: Standard GenIce2 GRO still parses identically; malformed input raises ValueError; place_custom emits warning.
next_action: Apply SUSP-03 fix to hydrate_generator.py:390-399, add SUSP-03 tests, commit; then SUSP-06 fix + tests + commit; run full verification suite.

## Symptoms

### SUSP-03 (hydrate_generator.py:390-399 — fragile GRO box-line parse)
expected: The GRO box line is robustly identified even with trailing blank lines or minor format variations; malformed input with no box line raises a clear ValueError.
actual: The loop skips non-digit-first lines and falls back to `lines[-1]`, which can pick a blank line or wrong line if the input has trailing whitespace/blank lines. `_parse_box_line` then silently falls back to `np.eye(3)*10.0` (default 10nm box) when given <3 values, masking malformed input.
errors: No exception on malformed input — silent wrong-box-line selection (or silent 10nm default box), or a confusing downstream error.
reproduction: Feed a standard GenIce GRO (works via fallback `box_line = lines[-1]`); feed a GRO with trailing blank lines (fragile — picks blank line); feed a malformed input with no numeric last line (no clear error, silent 10nm default).
started: Present since the box-line parse was written.

### SUSP-06 (custom_molecule_inserter.py:798-815 — place_custom no overlap warning)
expected: When `place_custom` is called and placed molecules are closer than a sensible threshold (or at minimum, whenever the function is called), a warning is emitted so users are alerted that no overlap check is performed.
actual: `place_custom` documents "No overlap checking (user responsibility)" in its docstring but emits NO warning — users silently get overlapping molecules with no alert.
errors: None — silent placement of overlapping molecules.
reproduction: Call `place_custom` with two molecules placed close together; observe no warning is emitted.
started: Present since `place_custom` was written.

## Eliminated

(none yet)

## Evidence

- timestamp: 2026-07-19T00:00:00Z
  checked: Environment — `python -c "import numpy; import quickice"` at /share/home/nglokwan/miniconda3/envs/quickice/bin/python (numpy 2.4.3, quickice imports OK).
  found: Env works without `conda activate` (python is already the quickice env binary).
  implication: Can run pytest directly with the active python.

- timestamp: 2026-07-19T00:00:10Z
  checked: hydrate_generator.py:330-401 (the `_parse_gro_result` function and box-line parse).
  found: Confirmed SUSP-03. The loop at :390-399 is:
    ```python
    box_line = None
    for line in lines[-5:]:
        if line.strip() and not line[0].isdigit():
            continue
        if line.strip():
            box_line = line
            break
    if box_line is None:
        box_line = lines[-1]
    cell = self._parse_box_line(box_line)
    ```
    For standard GenIce2 GRO, the box line begins with a leading space (e.g. `   2.00000...`), so `line[0].isdigit()` is False → `continue` (skipped). The fallback `box_line = lines[-1]` then saves it (last line is the box line). This works ONLY when `lines[-1]` is the box line. If trailing blank lines exist, `lines[-1]` is blank → `_parse_box_line` splits to `[]` (len < 3) → silently returns `np.eye(3)*10.0` (default 10nm box). No ValueError on malformed input.
  implication: Fix needed: strip trailing blank lines, take last non-blank line as box line candidate, parse it, raise ValueError if it doesn't have >=3 numeric values. Keep `_parse_box_line` behavior for valid input identical.

- timestamp: 2026-07-19T00:00:20Z
  checked: custom_molecule_inserter.py:798-870 (the `place_custom` function).
  found: Confirmed SUSP-06. Docstring at :804-815 says "No overlap checking (user responsibility)" but the function body emits NO warning. The function has access to: `positions` arg (list of COM tuples), `self.template_positions`, `self.config.min_separation` (default 0.3 nm, validated to [0.1, 1.0]). Pairwise COM distance is cheap (O(n^2) on n_molecules). Group 6 (PERF-04) already modified `_check_overlap` at :367-373 (different section, no conflict confirmed — commit c91d521a).
  implication: Fix: emit `logging.warning` (always) noting no overlap check performed + additional distance-based warning when pairwise COM < min_separation. Do NOT add hard rejection.

- timestamp: 2026-07-19T00:00:30Z
  checked: custom_molecule_inserter.py:48-106 (constructor) + types.py:952-1006 (CustomMoleculeConfig).
  found: Constructor takes `CustomMoleculeConfig`, calls `parse_gro_file(config.gro_path)` and `parse_itp_file(config.itp_path)`. `CustomMoleculeConfig.min_separation` defaults to 0.3 nm, validated to [0.1, 1.0] in `__post_init__`. Test fixture pattern exists in tests/test_scancode_bugs_inserter_perf.py:67-101 (`_make_custom_inserter` writes temp .gro/.itp files). `InterfaceStructure` constructor (types.py:348-426) is a plain dataclass; `_build_seeded_interface` at test_scancode_bugs_inserter_perf.py:279-320 shows the build pattern.
  implication: Test for SUSP-06 can reuse the `_make_custom_inserter` pattern + a minimal InterfaceStructure.

- timestamp: 2026-07-19T00:00:40Z
  checked: git status + recent log.
  found: Working tree clean. Recent commits show Groups 1-6 already done (CRIT-01 triclinic, CRIT-02/SUSP-01 ion, CRIT-04/SAFE-05 pipeline, SAFE-01/07 GUI, UNIT-02/03/04/05 constants, PERF-04/06 inserter perf). Group 6 PERF-04 commit c91d521a modified custom_molecule_inserter.py:367-373 (confirmed by reading the file — `# PERF-04: batch cKDTree query` comment present).
  implication: Safe to apply Group 7. No conflict with Group 6 (different section of the same file). Two atomic commits: SUSP-03 first, then SUSP-06.

## Resolution

root_cause: SUSP-03 — box-line parse relies on fragile fallback `lines[-1]` that breaks on trailing blank lines and silently returns a 10nm default box for malformed input (no ValueError). SUSP-06 — `place_custom` documents "no overlap check" but emits no warning, leaving users unaware of overlapping placements.
fix: (pending)
verification: (pending)
files_changed: []
