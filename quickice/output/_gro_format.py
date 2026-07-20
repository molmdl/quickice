"""DRY-extracted GRO formatting helpers (TD-01).

Shared by the 6 GRO writer functions (write_gro_file, write_interface_gro_file,
write_multi_molecule_gro_file, write_ion_gro_file, write_custom_molecule_gro_file,
write_solute_gro_file) to eliminate ~590 lines of near-byte-identical code.

Each helper appends formatted GRO atom lines to a `lines: list[str]` argument.
The caller controls ordering, residue-number assignment, and the atom_num
counter — the helper is a pure formatter with no per-structure logic.

Reference pattern: write_gro_file (quickice/output/gromacs_writer.py:905-1017
in the pre-refactor source) is the canonical source of the format strings.
The helpers below copy those f-strings byte-for-byte. The format strings were
verified against the CURRENT source (post-48.1-02) at gromacs_writer.py lines
56-169 (write_gro_file), 231-547 (write_interface_gro_file),
750-897 (write_multi_molecule_gro_file), 1106-1541 (write_ion_gro_file),
1865-2161 (write_custom_molecule_gro_file), 2398-2827 (write_solute_gro_file).

CRITICAL constraints (research §3 + §7):
- DO NOT use _write_gro_header for write_custom_molecule_gro_file — it uses
  f"{total_atoms}\\n" without :5d (divergent format). Keep that writer's
  inline header write.
- DO NOT use _write_gro_box_vectors for write_custom_molecule_gro_file — it
  uses a divergent 3-value DIAGONAL box format
  (f"{cell[0,0]:10.5f}{cell[1,1]:10.5f}{cell[2,2]:10.5f}\\n"), not the
  9-value triclinic format. Keep that writer's inline box write. (Found during
  Wave 2a source verification — research §3 incorrectly claimed all 6 writers
  share the 9-value triclinic box format.)
- DO NOT add try/except cleanup to write_multi_molecule_gro_file and
  write_solute_gro_file — they intentionally lack the cleanup block that
  the other 4 have. The helpers do NOT add try/except — callers control
  I/O error handling.
- DO NOT unify the custom_active gate logic across writers. The helpers
  take `res_name` as a parameter (caller-resolved) so the gate stays in
  the per-structure writer.
- atom_num_counter is a 1-element list[int] (mutable box) so the helper
  can increment it in place; the caller reads the updated value to thread
  the running atom_num across molecule boundaries. Wrap at 100000
  (GROMACS convention for >99999 atoms).
- res_num is the ALREADY-WRAPPED residue number (caller does % 100000).
  The helper formats it with :5d directly.

`compute_mw_position` is imported from `_shared` so downstream per-structure
modules (plans 48.1-08..13) can import both the helpers and the MW computor
from this module's neighborhood. The helpers themselves take ``mw_pos`` as a
caller-computed parameter — they do NOT call compute_mw_position internally
(the caller decides whether MW is computed from O,H,H or pulled from a
4-atom hydrated structure).
"""

import numpy as np

from quickice.output._shared import compute_mw_position  # noqa: F401  (re-exported for downstream per-structure modules; helpers take mw_pos as a caller-computed param)


def _write_gro_header(lines: list[str], title: str, n_atoms: int) -> None:
    """Append title line + atom count line to lines list.

    Used by: write_gro_file, write_interface_gro_file,
             write_multi_molecule_gro_file, write_ion_gro_file,
             write_solute_gro_file (5 of 6).

    Format (byte-identical to write_gro_file:103-104, write_interface_gro_file:341,344,
            write_multi_molecule_gro_file:821-822, write_ion_gro_file:1280,1283,
            write_solute_gro_file:2608,2611):
        f"{title}\\n"
        f"{n_atoms:5d}\\n"

    NOTE: write_custom_molecule_gro_file uses f"{total_atoms}\\n" (no :5d) —
          DO NOT use this helper for that writer; keep its divergent format
          (gromacs_writer.py:1976-1979 builds header via lines.append with
          f"{total_atoms}\\n", not f"{n_atoms:5d}\\n").
    """
    lines.append(f"{title}\n")
    lines.append(f"{n_atoms:5d}\n")


def _format_sol_ice_molecule(
    lines: list[str],
    o_pos: np.ndarray,
    h1_pos: np.ndarray,
    h2_pos: np.ndarray,
    mw_pos: np.ndarray,
    res_num: int,
    atom_num_counter: list[int],
) -> None:
    """Append 4 GRO atom lines for a SOL ice molecule (OW, HW1, HW2, MW).

    Used by: write_gro_file, write_interface_gro_file, write_ion_gro_file,
             write_custom_molecule_gro_file, write_solute_gro_file (5 of 6).
    NOT used by write_multi_molecule_gro_file (it uses a generic per-atom loop
    driven by MoleculeIndex.atom_names — its SOL molecules are not special-cased
    to the OW/HW1/HW2/MW expansion).

    Format strings (byte-identical to write_gro_file:136-156, and to the ice
    AND water branches of write_ion_gro_file:1320-1343/1356-1379,
    write_custom_molecule_gro_file:2005-2028/2044-2067,
    write_solute_gro_file:2637-2660/2673-2696):
        f"{res_num:5d}SOL     OW{atom_num_wrapped:5d}{o_pos[0]:8.3f}..."
        f"{res_num:5d}SOL    HW1{atom_num_wrapped:5d}{h1_pos[0]:8.3f}..."
        f"{res_num:5d}SOL    HW2{atom_num_wrapped:5d}{h2_pos[0]:8.3f}..."
        f"{res_num:5d}SOL     MW{atom_num_wrapped:5d}{mw_pos[0]:8.3f}..."

    The literal f-strings below use the explicit "   OW" / "  HW1" / "  HW2" /
    "   MW" atom-name fields (5-char right-justified), matching the inline code
    byte-for-byte.

    Args:
        o_pos, h1_pos, h2_pos: 3-atom ice input (O, H, H) — caller slices these
            from wrapped_positions[base_idx : base_idx+3].
        mw_pos: caller-computed MW virtual site. For classic 3-atom ice the
            caller passes compute_mw_position(o_pos, h1_pos, h2_pos); for
            4-atom hydrated ice the caller passes wrapped_positions[base_idx+3].
        res_num: ALREADY-WRAPPED residue number (caller did % 100000).
        atom_num_counter: 1-element list [current_atom_num]. The helper
            increments it by 4 (OW, HW1, HW2, MW) and wraps at 100000.
    """
    atom_num_counter[0] += 1
    atom_num_wrapped = atom_num_counter[0] % 100000
    lines.append(f"{res_num:5d}SOL  "
                 f"   OW{atom_num_wrapped:5d}"
                 f"{o_pos[0]:8.3f}{o_pos[1]:8.3f}{o_pos[2]:8.3f}\n")
    atom_num_counter[0] += 1
    atom_num_wrapped = atom_num_counter[0] % 100000
    lines.append(f"{res_num:5d}SOL  "
                 f"  HW1{atom_num_wrapped:5d}"
                 f"{h1_pos[0]:8.3f}{h1_pos[1]:8.3f}{h1_pos[2]:8.3f}\n")
    atom_num_counter[0] += 1
    atom_num_wrapped = atom_num_counter[0] % 100000
    lines.append(f"{res_num:5d}SOL  "
                 f"  HW2{atom_num_wrapped:5d}"
                 f"{h2_pos[0]:8.3f}{h2_pos[1]:8.3f}{h2_pos[2]:8.3f}\n")
    atom_num_counter[0] += 1
    atom_num_wrapped = atom_num_counter[0] % 100000
    lines.append(f"{res_num:5d}SOL  "
                 f"   MW{atom_num_wrapped:5d}"
                 f"{mw_pos[0]:8.3f}{mw_pos[1]:8.3f}{mw_pos[2]:8.3f}\n")


def _format_sol_water_molecule(
    lines: list[str],
    positions: np.ndarray,
    res_num: int,
    atom_num_counter: list[int],
) -> None:
    """Append 4 GRO atom lines for a SOL water molecule (pass-through, no MW recompute).

    Used by: write_interface_gro_file, write_ion_gro_file,
             write_custom_molecule_gro_file, write_solute_gro_file (4 of 6).
    NOT used by write_multi_molecule_gro_file (generic per-atom loop) and
    NOT used by write_gro_file (ice-only — uses _format_sol_ice_molecule
    because it computes MW from O,H,H 3-atom input).

    NOTE: write_ion_gro_file, write_custom_molecule_gro_file, and
          write_solute_gro_file inline the water branch with the SAME explicit
          "   OW"/"  HW1"/"  HW2"/"   MW" literals as _format_sol_ice_molecule
          (not a generic {name:>5s} loop). The {name:>5s} format used here
          produces byte-identical output: "OW".rjust(5) == "   OW",
          "HW1".rjust(5) == "  HW1", "HW2".rjust(5) == "  HW2",
          "MW".rjust(5) == "   MW". Only write_interface_gro_file:421-433 uses
          the generic {name:>5s} loop inline; the other 3 use explicit literals.
          Both forms produce identical bytes — this helper unifies them.

    Format (byte-identical to write_interface_gro_file:431-433 generic loop):
        f"{res_num:5d}SOL  {atom_name:>5s}{atom_num_wrapped:5d}{pos[0]:8.3f}..."
    """
    atom_names = ["OW", "HW1", "HW2", "MW"]
    for i, name in enumerate(atom_names):
        atom_num_counter[0] += 1
        atom_num_wrapped = atom_num_counter[0] % 100000
        # Match the exact column alignment used by write_interface_gro_file
        # (5-char right-justified atom name: "   OW" / "  HW1" / "  HW2" / "   MW").
        lines.append(f"{res_num:5d}SOL  "
                     f"{name:>5s}{atom_num_wrapped:5d}"
                     f"{positions[i][0]:8.3f}{positions[i][1]:8.3f}{positions[i][2]:8.3f}\n")


def _format_guest_molecule(
    lines: list[str],
    mol_atom_names: list[str],
    mol_positions,
    res_num: int,
    res_name: str,
    atom_num_counter: list[int],
) -> None:
    """Append GRO atom lines for a guest molecule (CH4, THF, or custom guest).

    Used by: write_interface_gro_file, write_multi_molecule_gro_file,
             write_ion_gro_file, write_solute_gro_file (4 of 6).

    Format (byte-identical to write_interface_gro_file:480-482 custom branch
            and 529-531 built-in branch, write_ion_gro_file:1442-1444,
            write_solute_gro_file:2754-2756, write_multi_molecule_gro_file:887-889):
        f"{res_num:5d}{res_name:<5s}{atom_name:>5s}{atom_num_wrapped:5d}{pos[0]:8.3f}..."

    Args:
        mol_atom_names: atom names for this molecule (already reordered to
            .itp canonical order by the caller when guest_type is ch4/thf).
        mol_positions: positions aligned with mol_atom_names (caller reorders
            both names and positions together via reorder_guest_atoms).
        res_num: ALREADY-WRAPPED residue number (caller did % 100000).
        res_name: validated ≤5 chars (caller must call validate_gro_residue_name
            BEFORE calling this helper — the helper is a pure formatter).
        atom_num_counter: 1-element list [current_atom_num]. Incremented by
            len(mol_atom_names); wrapped at 100000 per atom.
    """
    for i, atom_name in enumerate(mol_atom_names):
        atom_num_counter[0] += 1
        atom_num_wrapped = atom_num_counter[0] % 100000
        pos = mol_positions[i]
        lines.append(f"{res_num:5d}{res_name:<5s}{atom_name:>5s}"
                     f"{atom_num_wrapped:5d}"
                     f"{pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}\n")


def _format_custom_molecule(
    lines: list[str],
    mol_atom_names: list[str],
    mol_positions,
    res_num: int,
    res_name: str,
    atom_num_counter: list[int],
) -> None:
    """Append GRO atom lines for a custom molecule.

    Used by: write_ion_gro_file, write_custom_molecule_gro_file,
             write_solute_gro_file (3 of 6).

    NOTE: the format string is identical to _format_guest_molecule — these
          could be unified, but keeping them separate makes the call sites
          readable and allows future divergence if custom molecule
          formatting ever changes. (Per research §3 + plan 48.1-03 Task 1.)

    Format (byte-identical to write_ion_gro_file:1471-1473,
            write_custom_molecule_gro_file:2121-2124/2143-2146,
            write_solute_gro_file:2780-2782):
        f"{res_num:5d}{res_name:<5s}{atom_name:>5s}{atom_num_wrapped:5d}{pos[0]:8.3f}..."
    """
    for i, atom_name in enumerate(mol_atom_names):
        atom_num_counter[0] += 1
        atom_num_wrapped = atom_num_counter[0] % 100000
        pos = mol_positions[i]
        lines.append(f"{res_num:5d}{res_name:<5s}{atom_name:>5s}"
                     f"{atom_num_wrapped:5d}"
                     f"{pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}\n")


def _format_solute_molecule(
    lines: list[str],
    mol_atom_names: list[str],
    mol_positions,
    res_num: int,
    res_name: str,
    atom_num_counter: list[int],
) -> None:
    """Append GRO atom lines for a solute molecule (CH4_L / THF_L / custom).

    Used by: write_ion_gro_file, write_solute_gro_file (2 of 6).

    Format identical to _format_custom_molecule / _format_guest_molecule
    (same f-string). Kept separate for call-site readability so the per-structure
    writer reads "solute" at the call site, not "guest" or "custom".

    Format (byte-identical to write_ion_gro_file:1503-1505,
            write_solute_gro_file:2810-2812):
        f"{res_num:5d}{res_name:<5s}{atom_name:>5s}{atom_num_wrapped:5d}{pos[0]:8.3f}..."
    """
    for i, atom_name in enumerate(mol_atom_names):
        atom_num_counter[0] += 1
        atom_num_wrapped = atom_num_counter[0] % 100000
        pos = mol_positions[i]
        lines.append(f"{res_num:5d}{res_name:<5s}{atom_name:>5s}"
                     f"{atom_num_wrapped:5d}"
                     f"{pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}\n")


def _format_na_ion(
    lines: list[str],
    pos: np.ndarray,
    res_num: int,
    atom_num_counter: list[int],
) -> None:
    """Append 1 GRO atom line for an NA ion.

    Used by: write_ion_gro_file (1 of 6 — unique to the ion writer).

    Format (byte-identical to write_ion_gro_file:1515-1517 — verified by direct
            source read; the plan's placeholder template was a rough guide and
            was ADJUSTED to match the source byte-for-byte):
        f"{res_num:5d}NA   "          # resname field = "NA" + 3 spaces (5 chars)
        f"   NA{atom_num_wrapped:5d}"  # atom-name field = 3 spaces + "NA" (5 chars)
        f"{pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}\\n"

    The 5-char residue-name field is "NA   " (NA left-justified, 3 trailing
    spaces); the 5-char atom-name field is "   NA" (NA right-justified, 3
    leading spaces). This matches GROMACS .gro column alignment.
    """
    atom_num_counter[0] += 1
    atom_num_wrapped = atom_num_counter[0] % 100000
    lines.append(f"{res_num:5d}NA   "
                 f"   NA{atom_num_wrapped:5d}"
                 f"{pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}\n")


def _format_cl_ion(
    lines: list[str],
    pos: np.ndarray,
    res_num: int,
    atom_num_counter: list[int],
) -> None:
    """Append 1 GRO atom line for a CL ion.

    Used by: write_ion_gro_file (1 of 6 — unique to the ion writer).

    Format (byte-identical to write_ion_gro_file:1526-1528 — verified by direct
            source read; adjusted from the plan's placeholder template to
            match the source byte-for-byte):
        f"{res_num:5d}CL   "          # resname field = "CL" + 3 spaces (5 chars)
        f"   CL{atom_num_wrapped:5d}"  # atom-name field = 3 spaces + "CL" (5 chars)
        f"{pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}\\n"
    """
    atom_num_counter[0] += 1
    atom_num_wrapped = atom_num_counter[0] % 100000
    lines.append(f"{res_num:5d}CL   "
                 f"   CL{atom_num_wrapped:5d}"
                 f"{pos[0]:8.3f}{pos[1]:8.3f}{pos[2]:8.3f}\n")


def _write_gro_box_vectors(f, cell: np.ndarray) -> None:
    """Write the 9-value triclinic box vector line.

    Used by: write_gro_file, write_interface_gro_file,
             write_multi_molecule_gro_file, write_ion_gro_file,
             write_solute_gro_file (5 of 6).

    Format (byte-identical to write_gro_file:161-163, write_interface_gro_file:539-541,
            write_multi_molecule_gro_file:894-896, write_ion_gro_file:1534-1536,
            write_solute_gro_file:2818-2820):
        f"{cell[0,0]:10.5f}{cell[1,1]:10.5f}{cell[2,2]:10.5f}"
        f"{cell[0,1]:10.5f}{cell[0,2]:10.5f}{cell[1,0]:10.5f}"
        f"{cell[1,2]:10.5f}{cell[2,0]:10.5f}{cell[2,1]:10.5f}\\n"

    NOTE: write_custom_molecule_gro_file uses a DIVERGENT 3-value diagonal
          box format (gromacs_writer.py:2149):
              f"{cell[0,0]:10.5f}{cell[1,1]:10.5f}{cell[2,2]:10.5f}\\n"
          — DO NOT use this helper for that writer; keep its inline divergent
          box write. (Discovered during Wave 2a source verification: research
          §3 incorrectly claimed all 6 writers share the 9-value triclinic
          format. The custom writer's box line is a 3-value diagonal — this
          is a pre-existing divergence, not introduced by this refactor.)
    """
    f.write(f"{cell[0,0]:10.5f}{cell[1,1]:10.5f}{cell[2,2]:10.5f}"
            f"{cell[0,1]:10.5f}{cell[0,2]:10.5f}{cell[1,0]:10.5f}"
            f"{cell[1,2]:10.5f}{cell[2,0]:10.5f}{cell[2,1]:10.5f}\n")


def _wrap_aux_positions(positions, cell: np.ndarray):
    """PBC-wrap solute/custom-molecule positions via diagonal modulo (AN-03 fix).

    Used by: write_interface_gro_file, write_ion_gro_file,
             write_solute_gro_file (3 of 6).

    Pattern: `positions % np.diag(cell)` — the AN-03 fix pattern. Verified
    byte-identical across all 3 callers:
        write_interface_gro_file:330,334
        write_ion_gro_file:1256,1262
        write_solute_gro_file:2574,2584
    All three use the simple diagonal modulo (NOT wrap_positions_into_box),
    because solute/custom-molecule positions are single small molecules that
    don't span PBC boundaries — simple modulo is sufficient.

    Returns the input unchanged when positions is None or empty (caller-
    friendly no-op, mirroring the `is not None and len(positions) > 0` guards
    in the 3 callers).
    """
    if positions is None or len(positions) == 0:
        return positions
    return positions % np.diag(cell)
