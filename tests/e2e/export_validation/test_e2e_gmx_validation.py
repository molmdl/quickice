"""End-to-end GROMACS grompp validation tests.

Validates that exported .gro+.top+.itp files are GROMACS-simulation-ready
by running `gmx grompp` with tests/em.mdp (energy minimization).

Tests cover:
  - Ice candidate (inline moleculetype, no ITPs needed)
  - Interface slab (#include tip4p-ice.itp)
  - F5-F7 simple chains (2-3 ITPs)
  - F1, F3, F4 complex chains (4-5 ITPs)
  - F2 (Interface→Custom→Ion, 3 ITPs, no solute)
  - F1+THF, F3+THF, F4+CH4 cross-combinations (dedup validation)

48.3-15 consolidation batch A: the deep file-level asserts from the writer-direct
files tests/test_e2e_chain_export_1.py (F1-F4, 26 tests), test_e2e_chain_export_2.py
(F5-F7, 21 tests) and test_e2e_cross_chain_invariants.py (4 tests) were ported INTO
these grompp-backed chains (see the _assert_* helpers below) and the source files
deleted — same asserts, strictly stronger validation (file asserts + grompp).

48.3-19 consolidation batch B: the four single-structure writer files
tests/test_e2e_ice_interface_export.py (16), test_e2e_custom_export.py (7),
test_e2e_solute_export.py (15) and test_e2e_ion_export.py (20, holds the unique
BUG I5 regression asserts) validated the SAME writer flows by file-parsing only
(no grompp — P3). 48.3-19 ports their UNIQUE deep asserts into these
grompp-backed chains (ice/interface/hydrate/custom/solute chains + F2/F6
provenance + one new focused custom→solute grompp chain) and deletes the
sources — same asserts, strictly stronger validation. Bundled-ITP
existence/[moleculetype] checks were NOT ported:
tests/e2e/export_validation/test_itp_baseline_data.py already covers every
bundled ITP, and staged ITPs are validated by
_stage_itp_files + assert_itp_completeness + grompp failing on a missing or
malformed ITP (same drop rationale as 48.3-15).

Uses conftest.py fixtures for real GenIce2-generated structures.
"""

import shutil
import quickice
import pytest
from pathlib import Path

from tests.conftest import gmx_skipif

from quickice.output.gromacs_writer import (
    write_gro_file,
    write_top_file,
    write_interface_gro_file,
    write_interface_top_file,
    write_ion_gro_file,
    write_ion_top_file,
    write_custom_molecule_gro_file,
    write_custom_molecule_top_file,
    write_solute_gro_file,
    write_solute_top_file,
    get_hydrate_guest_residue_name,
)
from quickice.structure_generation.gromacs_ion_export import write_ion_itp
from quickice.phase_mapping.lookup import lookup_phase
from quickice.structure_generation.generator import IceStructureGenerator
from quickice.structure_generation.types import InterfaceConfig

from tests.e2e_export_helpers import (
    parse_top_includes,
    parse_top_molecules,
    parse_gro_residue_names,
    parse_gro_atom_count,
    assert_gro_residue_ordering,
    _insert_custom_molecules,
    _insert_solutes,
    _insert_ions,
    _insert_ions_from_solute,
    _make_slab_interface,
    _hydrate_sI_ch4_candidate,
    _hydrate_sI_thf_candidate,
    _hydrate_sII_ch4_candidate,
    _hydrate_sII_thf_candidate,
    _stage_itp_files,
    assert_itp_completeness,
    run_gmx_grompp,
    MDP_PATH,
)


@pytest.fixture
def gmx_workspace(request):
    """Persistent workspace under tmp/e2e-gmx-validation/ for GROMACS grompp.

    Each test gets its own subdirectory named after the test.
    Files persist after test run for debugging.
    """
    # Repo-root-anchored via the quickice package (48.3-21 move): the persistent
    # debug workspace stays under <root>/tmp/ regardless of this file's location.
    base = Path(quickice.__file__).resolve().parent.parent / "tmp" / "e2e-gmx-validation"
    workspace = base / request.node.name.replace("::", "_")
    workspace.mkdir(parents=True, exist_ok=True)
    yield workspace


# ── Ported deep-file asserts (48.3-15 consolidation batch A) ─────────────────
# tests/test_e2e_chain_export_1.py (F1-F4, 26 tests), tests/test_e2e_chain_export_2.py
# (F5-F7, 21 tests) and tests/test_e2e_cross_chain_invariants.py (4 tests) validated
# the SAME F1-F7 writer chains by file-parsing only (no grompp — P3). 48.3-15 ports
# their UNIQUE deep asserts into these grompp-backed chains and deletes the sources:
# same asserts, strictly stronger validation (file asserts + gmx grompp).
# Dropped as subsumed (no port needed): the per-chain test_itp_files_valid checks
# (ITP existence + [moleculetype] presence are implied by _stage_itp_files +
# assert_itp_completeness + grompp failing on a missing/malformed ITP) and the
# trivial "CH4_H" != "CH4_L" string compares (their TOP-presence half is subsumed
# by _assert_top_molecule_counts).


def _assert_residue_ordering(gro_path, expected_order):
    """Assert .gro residues are EXACTLY expected_order (as a set) and non-interleaved.

    Ported from test_e2e_chain_export_1/2.py::test_gro_residue_ordering (F1-F7).
    write_ion_gro_file molecule order: SOL -> guest -> custom -> solute -> NA -> CL.
    The exact-set assert also covers the F2 negative assert ("no solute residues").
    """
    residue_names = parse_gro_residue_names(gro_path)
    unique_names = set(residue_names)
    expected_set = set(expected_order)
    assert unique_names == expected_set, (
        f"GRO residues should be exactly {sorted(expected_set)}, got {sorted(unique_names)}"
    )
    assert_gro_residue_ordering(residue_names, expected_order)


def _assert_atom_conservation(gro_path, ion, solute_atoms_per_mol=None):
    """GRO header atom count == atom lines == conservation arithmetic from the ion structure.

    Ported from test_e2e_chain_export_1.py::test_gro_atom_count_matches_header +
    ::test_atom_conservation (F1) and test_e2e_chain_export_2.py
    ::test_gro_atom_count_matches_header + ::test_atom_conservation_and_charge_neutrality
    (F5-F7).

    Writer accounting (write_ion_gro_file ordered_mols, ion_writer.py:199-218):
    - SOL section: 4 atoms per ice molecule (3 input atoms + added MW virtual
      site) and mol.count (4) per water molecule
    - guest section: mol.count per guest molecule_index entry
    - custom section: custom_molecule_atom_count atoms from
      custom_molecule_positions (molecule_index 'custom' entries are NOT
      written here — skipped to avoid double counting)
    - solute section: per solute_molecule_indices (start, end) spans
    - NA/CL: 1 atom per ion entry
    """
    header_count = parse_gro_atom_count(gro_path)
    residue_names = parse_gro_residue_names(gro_path)
    assert header_count == len(residue_names), (
        f"GRO header says {header_count} atoms but found {len(residue_names)} atom lines"
    )

    # molecule_index conservation: index entries sum to positions rows
    total_from_index = sum(m.count for m in ion.molecule_index)
    assert total_from_index == ion.positions.shape[0], (
        f"Atom conservation: molecule_index sums to {total_from_index} "
        f"but positions has {ion.positions.shape[0]} rows"
    )

    expected = 0
    for m in ion.molecule_index:
        if m.mol_type == "ice":
            expected += 4  # 3 input atoms -> 4 output atoms (OW, HW1, HW2, MW)
        elif m.mol_type in ("na", "cl"):
            expected += 1
        elif m.mol_type == "custom":
            continue  # written once by the custom section, not from molecule_index
        else:
            expected += m.count  # water + guest entries written as-is
    expected += ion.custom_molecule_atom_count
    solute_atoms = (
        sum(end - start for start, end in ion.solute_molecule_indices)
        if ion.solute_molecule_indices
        else 0
    )
    if solute_atoms_per_mol is not None and ion.solute_molecule_indices:
        for start, end in ion.solute_molecule_indices:
            assert end - start == solute_atoms_per_mol, (
                f"Solute molecule should have {solute_atoms_per_mol} atoms per molecule, "
                f"got {end - start}"
            )
    expected += solute_atoms
    assert header_count == expected, (
        f"Atom conservation: expected {expected} atoms "
        f"(molecule_index-derived {total_from_index} with ice MW normalisation "
        f"+ custom {ion.custom_molecule_atom_count} + solute {solute_atoms}), "
        f"got {header_count}"
    )

    # Charge neutrality: NaCl inserts ion pairs (F5-F7 source asserts).
    assert ion.na_count == ion.cl_count, (
        f"Charge neutrality: na_count ({ion.na_count}) should equal cl_count ({ion.cl_count})"
    )


def _assert_top_molecule_counts(top_path, ion):
    """[molecules] count-parity asserts ported from test_e2e_chain_export_1/2.py
    ::test_top_molecules_section (F1-F7).

    - SOL == ice+water molecule_index entries (ions replace water AFTER indexing)
    - NA == ion.na_count, CL == ion.cl_count
    - custom (when present): [moleculetype] count == custom_molecule_count
    - solute (when present): [<SOLUTE>_L] count == solute_n_molecules
    - hydrate guest (when present): guest ITP name present with count > 0
    """
    molecules = parse_top_molecules(top_path)

    expected_sol = sum(
        1 for m in ion.molecule_index if m.mol_type in ("ice", "water")
    )
    assert molecules.get("SOL") == expected_sol, (
        f"Expected SOL count {expected_sol} (ice+water molecule_index entries), "
        f"got {molecules.get('SOL')} in [molecules]"
    )
    assert molecules.get("NA") == ion.na_count, (
        f"Expected NA count {ion.na_count}, got {molecules.get('NA')}"
    )
    assert molecules.get("CL") == ion.cl_count, (
        f"Expected CL count {ion.cl_count}, got {molecules.get('CL')}"
    )

    if ion.custom_molecule_count > 0:
        custom_name = ion.custom_molecule_moleculetype
        assert molecules.get(custom_name) == ion.custom_molecule_count, (
            f"Expected custom moleculetype '{custom_name}' count "
            f"{ion.custom_molecule_count}, got {molecules.get(custom_name)}"
        )

    if ion.solute_n_molecules > 0:
        solute_name = f"{ion.solute_type.upper()}_L"
        assert molecules.get(solute_name) == ion.solute_n_molecules, (
            f"Expected solute moleculetype '{solute_name}' count "
            f"{ion.solute_n_molecules}, got {molecules.get(solute_name)}"
        )

    # Hydrate guest (F3/F4 family): TOP name may be the registry "X_H" ITP name or
    # the older bare "CH4"/"THF" fallback — accept either (provenance: chain_export_1
    # F3/F4 test_top_molecules_section guest_key logic).
    if ion.guest_nmolecules > 0 or ion.guest_atom_count > 0:
        guest_key = next(
            (k for k in molecules if k.endswith("_H") or k in ("CH4", "THF")),
            None,
        )
        assert guest_key is not None, (
            f"TOP should list the hydrate guest molecule, got {list(molecules.keys())}"
        )
        assert molecules[guest_key] > 0, (
            f"Hydrate guest count should be > 0, got {molecules[guest_key]}"
        )


def _assert_top_includes(top_path, expected, forbidden=(), exact_count=None):
    """#include asserts ported from test_e2e_chain_export_1/2.py::test_top_includes.

    Args:
        expected: ITP filenames that MUST be #included.
        forbidden: ITP filenames that must NOT be #included (F2 negative asserts).
        exact_count: Exact number of #include lines where a source asserted it
            (F5 == 2, F6/F7 == 3; F1 == 4 via the cross-chain invariant port).
    """
    includes = parse_top_includes(top_path)
    for name in expected:
        assert name in includes, f"TOP should include {name}, got {includes}"
    for name in forbidden:
        assert name not in includes, f"TOP should NOT include {name}, got {includes}"
    if exact_count is not None:
        assert len(includes) == exact_count, (
            f"Chain should have exactly {exact_count} ITPs, got {len(includes)}: {includes}"
        )


# ── Ported deep-file asserts (48.3-19 consolidation batch B) ─────────────────
# tests/test_e2e_ice_interface_export.py (16), tests/test_e2e_custom_export.py (7),
# tests/test_e2e_solute_export.py (15) and tests/test_e2e_ion_export.py (20)
# validated the single-structure writer flows by file-parsing only (no grompp —
# P3). 48.3-19 ports their UNIQUE deep asserts into the grompp-backed chains below
# and deletes the sources. Dropped as subsumed (no port needed):
# - the per-chain test_itp_files_valid / test_*_itp_has_moleculetype bundled-ITP
#   checks: tests/e2e/export_validation/test_itp_baseline_data.py already
#   covers every bundled ITP (existence + [moleculetype]), and staged ITPs
#   are validated by
#   _stage_itp_files + assert_itp_completeness + grompp (48.3-15 rationale).
# - intra-file duplicates of the atom-count check (test_atom_conservation bodies
#   that repeat test_gro_atom_count_matches_header arithmetic).
# The BUG I5 regression asserts from ion_export were ported into the F6 chain
# (Interface→Solute→Ion, the same Scenario 9 chain) with the original
# "BUG I5" (space) spelling preserved so provenance greps match source history.


def _assert_gro_header_matches_lines(gro_path):
    """GRO header atom count == actual atom lines.

    Ported from the 4 single-structure writer files' test_gro_atom_count_matches_header
    (48.3-19): every writer-file test opened with this consistency check.
    """
    header_count = parse_gro_atom_count(gro_path)
    residue_names = parse_gro_residue_names(gro_path)
    assert header_count == len(residue_names), (
        f"GRO header says {header_count} atoms but found {len(residue_names)} atom lines"
    )


def _assert_solute_positions_pbc_wrapped(gro_path):
    """Solute atom positions must be within PBC box in GRO output.

    Ported from test_e2e_solute_export.py::TestSoluteFromInterface
    ::test_solute_positions_pbc_wrapped (deleted by 48.3-19).

    Regression test for B NEW-01/11: write_solute_gro_file did not
    PBC-wrap solute_structure.positions, producing invalid GRO files.
    Solute positions are a SEPARATE array from interface.positions,
    so wrap_molecules_into_box does NOT cover them.
    """
    with open(gro_path) as f:
        lines = f.readlines()

    # Skip title (line 0), atom count (line 1), and box (last line)
    atom_lines = lines[2:-1]

    # Extract box dimensions from last line
    box_line = lines[-1].strip().split()
    box_x, box_y, box_z = float(box_line[0]), float(box_line[1]), float(box_line[2])

    # Find solute atoms (CH4_L or THF_L residue)
    solute_positions = []
    for line in atom_lines:
        res_name = line[5:10].strip()
        if res_name in ("CH4_L", "THF_L", "CH4_P"):
            x = float(line[20:28])
            y = float(line[28:36])
            z = float(line[36:44])
            solute_positions.append((x, y, z))

    assert len(solute_positions) > 0, "No solute atoms found in GRO output"

    # All solute positions must be within [0, box_dim + 0.01)
    tolerance = 0.01  # nm — float precision tolerance at boundaries
    for x, y, z in solute_positions:
        assert -tolerance <= x < box_x + tolerance, f"Solute x={x} outside PBC [0, {box_x})"
        assert -tolerance <= y < box_y + tolerance, f"Solute y={y} outside PBC [0, {box_y})"
        assert -tolerance <= z < box_z + tolerance, f"Solute z={z} outside PBC [0, {box_z})"


# ══════════════════════════════════════════════════════════════════════════════
# Ice Candidate (inline [moleculetype], no ITPs needed)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
class TestIceCandidateGmxValidation:
    """Validate ice candidate export passes gmx grompp.

    Uses write_gro_file/write_top_file (inline [moleculetype], no ITPs needed).
    Generates 256 molecules for a box large enough for 1.0 nm cutoffs.
    """

    def test_gmx_grompp_succeeds(self, gmx_workspace):
        """Ice candidate .gro+.top+em.mdp passes gmx grompp."""
        # Generate larger ice candidate (256 molecules for > 2.0 nm box)
        phase_info = lookup_phase(250, 0.1)
        gen = IceStructureGenerator(phase_info, 256)
        candidates = gen.generate_all(1)
        candidate = candidates[0]

        # Export files
        gro_path = str(gmx_workspace / "ice.gro")
        top_path = str(gmx_workspace / "ice.top")
        write_gro_file(candidate, gro_path)
        write_top_file(candidate, top_path)

        # Copy MDP
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")

        # No ITP staging needed — ice candidate uses inline [moleculetype]

        # Run gmx grompp
        exit_code, stderr = run_gmx_grompp(
            gmx_workspace, gro_file="ice.gro", top_file="ice.top"
        )
        assert exit_code == 0, (
            f"gmx grompp failed for ice candidate:\n{stderr[-500:]}"
        )

        # Assert expected molecule types in .top [molecules]
        molecules = parse_top_molecules(top_path)
        expected_top_keys = {"SOL"}
        for key in expected_top_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in molecules), (
                    f"Expected molecule type '{base}' or '{key}' in [molecules] for ice, "
                    f"got: {list(molecules.keys())}"
                )
            else:
                assert key in molecules, (
                    f"Expected molecule type '{key}' in [molecules] for ice, "
                    f"got: {list(molecules.keys())}"
                )

        # Assert expected residue names in .gro
        residue_names = parse_gro_residue_names(gro_path)
        unique_residues = set(residue_names)
        expected_gro_keys = {"SOL"}
        for key in expected_gro_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in unique_residues), (
                    f"Expected residue '{base}' or '{key}' in .gro for ice, "
                    f"got: {sorted(unique_residues)}"
                )
            else:
                assert key in unique_residues, (
                    f"Expected residue '{key}' in .gro for ice, "
                    f"got: {sorted(unique_residues)}"
                )

        # ── Ported deep asserts (48.3-19: tests/test_e2e_ice_interface_export.py
        # TestIceCandidateExport) ──
        # test_gro_only_sol_residues: ice candidate GRO has ONLY SOL residues
        assert unique_residues == {"SOL"}, (
            f"Ice candidate GRO should have only SOL residues, got {unique_residues}"
        )
        # test_gro_atom_count_matches_header + test_atom_conservation:
        # header == lines == nmolecules * 4 (TIP4P-ICE 3→4 expansion: OW, HW1,
        # HW2, MW virtual site)
        _assert_gro_header_matches_lines(gro_path)
        header_count = parse_gro_atom_count(gro_path)
        assert header_count == candidate.nmolecules * 4, (
            f"Expected {candidate.nmolecules * 4} atoms "
            f"(nmolecules={candidate.nmolecules} * 4), got {header_count}"
        )
        # test_top_molecules_section: [molecules] SOL == nmolecules
        assert molecules["SOL"] == candidate.nmolecules, (
            f"Expected SOL count {candidate.nmolecules}, got {molecules['SOL']}"
        )
        # test_top_has_moleculetype_inline: write_top_file writes the SOL
        # molecule definition INLINE (no #include directives) and never
        # references a hydrate ITP for plain ice
        with open(top_path) as f:
            top_content = f.read()
        assert "[ moleculetype ]" in top_content, (
            "Ice TOP should have [ moleculetype ] section inline"
        )
        guest_refs = [line for line in top_content.split('\n')
                      if 'hydrate' in line.lower() and '#include' in line]
        assert len(guest_refs) == 0, (
            f"Ice candidate should not reference hydrate ITPs, got {guest_refs}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Interface (requires tip4p-ice.itp)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
class TestInterfaceGmxValidation:
    """Validate interface export passes gmx grompp.

    Uses write_interface_gro_file/write_interface_top_file.
    Requires tip4p-ice.itp in same directory.
    """

    def test_gmx_grompp_succeeds(self, interface_slab, gmx_workspace):
        """Interface .gro+.top+tip4p-ice.itp+em.mdp passes gmx grompp."""
        gro_path = str(gmx_workspace / "iface.gro")
        top_path = str(gmx_workspace / "iface.top")
        write_interface_gro_file(interface_slab, gro_path)
        write_interface_top_file(interface_slab, top_path)

        # Copy MDP
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")

        # Stage ITPs
        _stage_itp_files(top_path, gmx_workspace)
        assert_itp_completeness(top_path, gmx_workspace)

        # Run gmx grompp
        exit_code, stderr = run_gmx_grompp(
            gmx_workspace, gro_file="iface.gro", top_file="iface.top"
        )
        assert exit_code == 0, (
            f"gmx grompp failed for interface:\n{stderr[-500:]}"
        )

        # Assert expected molecule types in .top [molecules]
        molecules = parse_top_molecules(top_path)
        expected_top_keys = {"SOL"}
        for key in expected_top_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in molecules), (
                    f"Expected molecule type '{base}' or '{key}' in [molecules] for interface, "
                    f"got: {list(molecules.keys())}"
                )
            else:
                assert key in molecules, (
                    f"Expected molecule type '{key}' in [molecules] for interface, "
                    f"got: {list(molecules.keys())}"
                )

        # Assert expected residue names in .gro
        residue_names = parse_gro_residue_names(gro_path)
        unique_residues = set(residue_names)
        expected_gro_keys = {"SOL"}
        for key in expected_gro_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in unique_residues), (
                    f"Expected residue '{base}' or '{key}' in .gro for interface, "
                    f"got: {sorted(unique_residues)}"
                )
            else:
                assert key in unique_residues, (
                    f"Expected residue '{key}' in .gro for interface, "
                    f"got: {sorted(unique_residues)}"
                )

        # ── Ported deep asserts (48.3-19: tests/test_e2e_ice_interface_export.py
        # TestInterfaceExport — interface WITHOUT guests) ──
        # test_gro_only_sol_residues: interface (no guests) GRO has ONLY SOL
        # residues (ice + water both SOL)
        assert unique_residues == {"SOL"}, (
            f"Interface (no guests) GRO should have only SOL residues, "
            f"got {unique_residues}"
        )
        # test_gro_atom_count_matches_header: header == lines ==
        # ice*4 + water*4 (ice uses TIP4P-ICE 3→4 expansion, water already 4)
        _assert_gro_header_matches_lines(gro_path)
        header_count = parse_gro_atom_count(gro_path)
        assert header_count == (
            interface_slab.ice_nmolecules * 4 + interface_slab.water_nmolecules * 4
        ), (
            f"Expected {interface_slab.ice_nmolecules * 4 + interface_slab.water_nmolecules * 4} atoms "
            f"(ice={interface_slab.ice_nmolecules}*4 + "
            f"water={interface_slab.water_nmolecules}*4), got {header_count}"
        )
        # test_top_molecules_section: combined SOL count for ice + water
        expected_sol = interface_slab.ice_nmolecules + interface_slab.water_nmolecules
        assert molecules["SOL"] == expected_sol, (
            f"Expected SOL count {expected_sol} "
            f"(ice={interface_slab.ice_nmolecules} + "
            f"water={interface_slab.water_nmolecules}), got {molecules['SOL']}"
        )
        # test_top_includes_tip4p_ice_only: only tip4p-ice.itp (no guest ITP
        # for non-hydrate interface)
        includes = parse_top_includes(top_path)
        assert "tip4p-ice.itp" in includes, "Should include tip4p-ice.itp"
        guest_itps = [inc for inc in includes if "hydrate" in inc]
        assert len(guest_itps) == 0, (
            f"Interface without guests should not include hydrate ITPs, got {guest_itps}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# F5: Interface→Ion (minimal chain, 2 ITPs)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
class TestChainF5GmxValidation:
    """Validate F5 chain (Interface→Ion) export passes gmx grompp.

    2 ITPs: tip4p-ice.itp, ion.itp
    """

    @pytest.fixture(autouse=True)
    def _build_chain(self, interface_slab):
        self.ion = _insert_ions(interface_slab, concentration=0.15)

    def test_gmx_grompp_succeeds(self, gmx_workspace):
        gro_path = str(gmx_workspace / "f5.gro")
        top_path = str(gmx_workspace / "f5.top")
        write_ion_gro_file(self.ion, gro_path)
        write_ion_top_file(self.ion, top_path)
        write_ion_itp(gmx_workspace / "ion.itp", self.ion.na_count, self.ion.cl_count)
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")
        _stage_itp_files(top_path, gmx_workspace)
        assert_itp_completeness(top_path, gmx_workspace)
        exit_code, stderr = run_gmx_grompp(gmx_workspace, gro_file="f5.gro", top_file="f5.top")
        assert exit_code == 0, f"gmx grompp failed for F5:\n{stderr[-500:]}"

        # Assert expected molecule types in .top [molecules]
        molecules = parse_top_molecules(top_path)
        expected_top_keys = {"SOL", "NA", "CL"}
        for key in expected_top_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in molecules), (
                    f"Expected molecule type '{base}' or '{key}' in [molecules] for F5, "
                    f"got: {list(molecules.keys())}"
                )
            else:
                assert key in molecules, (
                    f"Expected molecule type '{key}' in [molecules] for F5, "
                    f"got: {list(molecules.keys())}"
                )

        # Assert expected residue names in .gro
        residue_names = parse_gro_residue_names(gro_path)
        unique_residues = set(residue_names)
        expected_gro_keys = {"SOL", "NA", "CL"}
        for key in expected_gro_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in unique_residues), (
                    f"Expected residue '{base}' or '{key}' in .gro for F5, "
                    f"got: {sorted(unique_residues)}"
                )
            else:
                assert key in unique_residues, (
                    f"Expected residue '{key}' in .gro for F5, "
                    f"got: {sorted(unique_residues)}"
                )

        # ── Ported deep asserts (48.3-15: tests/test_e2e_chain_export_2.py TestChainF5) ──
        # test_gro_sol_before_na_before_cl: exactly 3 molecule types (SOL, NA, CL),
        # non-interleaved
        _assert_residue_ordering(gro_path, ["SOL", "NA", "CL"])
        # test_gro_atom_count_matches_header + test_atom_conservation_and_charge_neutrality:
        # header == lines == ice*4 + water*4 + na + cl, molecule_index == positions,
        # na_count == cl_count
        _assert_atom_conservation(gro_path, self.ion)
        # test_top_molecules_section: SOL/NA/CL count parity
        _assert_top_molecule_counts(top_path, self.ion)
        # test_top_includes_minimal_itps: exactly 2 ITPs (minimal chain)
        _assert_top_includes(top_path, ["tip4p-ice.itp", "ion.itp"], exact_count=2)
        # test_no_guests_custom_solutes: F5 has no guests, no custom molecules, no solutes
        assert self.ion.custom_molecule_count == 0, (
            f"F5 should have no custom molecules, got {self.ion.custom_molecule_count}"
        )
        assert self.ion.solute_n_molecules == 0, (
            f"F5 should have no solutes, got {self.ion.solute_n_molecules}"
        )
        guest_count = sum(
            1 for m in self.ion.molecule_index if m.mol_type == "guest"
        )
        assert guest_count == 0, f"F5 should have no guests, got {guest_count}"


# ══════════════════════════════════════════════════════════════════════════════
# F6: Interface→Solute(CH4)→Ion (3 ITPs, Bug 1 fix)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
class TestChainF6GmxValidation:
    """Validate F6 chain (Interface→Solute(CH4)→Ion) export passes gmx grompp.

    3 ITPs: tip4p-ice.itp, ch4_liquid.itp, ion.itp
    Tests Bug 1 fix: CH4 solute atomtypes (c3, hc) must be in TOP [atomtypes].

    48.3-19 provenance: this IS "Scenario 9: Ion from Solute Export" from the
    deleted tests/test_e2e_ion_export.py (TestIonFromSolute) — the chain whose
    BUG I5 workaround is MANDATORY. The ion_export file was a no-grompp
    file-parsing duplicate of this chain; its unique regression asserts are
    preserved here (solute metadata after the workaround + charge neutrality,
    both below).
    """

    @pytest.fixture(autouse=True)
    def _build_chain(self, interface_slab):
        # CRITICAL: Uses _insert_ions_from_solute() which applies the BUG I5
        # workaround (_solute_to_ion_source). Without this workaround,
        # IonInserter raises AttributeError: 'InterfaceStructure' object has
        # no attribute 'solute_type'.
        # (Provenance: 48.3-19 merge of tests/test_e2e_ion_export.py
        # TestIonFromSolute — "Ion from Solute Export (BUG I5 workaround
        # MANDATORY)"; _insert_ions_from_solute in e2e_export_helpers applies
        # the _solute_to_ion_source workaround.)
        solute = _insert_solutes(interface_slab, solute_type='CH4', concentration=0.3)
        # CRITICAL: Uses BUG I5 workaround
        self.ion = _insert_ions_from_solute(solute, concentration=0.15)

    def test_gmx_grompp_succeeds(self, gmx_workspace):
        gro_path = str(gmx_workspace / "f6.gro")
        top_path = str(gmx_workspace / "f6.top")
        write_ion_gro_file(self.ion, gro_path)
        write_ion_top_file(self.ion, top_path)
        write_ion_itp(gmx_workspace / "ion.itp", self.ion.na_count, self.ion.cl_count)
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")
        _stage_itp_files(top_path, gmx_workspace)
        assert_itp_completeness(top_path, gmx_workspace)
        exit_code, stderr = run_gmx_grompp(gmx_workspace, gro_file="f6.gro", top_file="f6.top")
        assert exit_code == 0, f"gmx grompp failed for F6:\n{stderr[-500:]}"

        # Assert expected molecule types in .top [molecules]
        molecules = parse_top_molecules(top_path)
        expected_top_keys = {"SOL", "CH4_L", "NA", "CL"}
        for key in expected_top_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in molecules), (
                    f"Expected molecule type '{base}' or '{key}' in [molecules] for F6, "
                    f"got: {list(molecules.keys())}"
                )
            else:
                assert key in molecules, (
                    f"Expected molecule type '{key}' in [molecules] for F6, "
                    f"got: {list(molecules.keys())}"
                )

        # Assert expected residue names in .gro
        residue_names = parse_gro_residue_names(gro_path)
        unique_residues = set(residue_names)
        expected_gro_keys = {"SOL", "CH4_L", "NA", "CL"}
        for key in expected_gro_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in unique_residues), (
                    f"Expected residue '{base}' or '{key}' in .gro for F6, "
                    f"got: {sorted(unique_residues)}"
                )
            else:
                assert key in unique_residues, (
                    f"Expected residue '{key}' in .gro for F6, "
                    f"got: {sorted(unique_residues)}"
                )

        # ── Ported deep asserts (48.3-15: tests/test_e2e_chain_export_2.py TestChainF6) ──
        # test_gro_sol_before_ch4l_before_na_before_cl: exactly 4 molecule types,
        # SOL→CH4_L→NA→CL non-interleaved
        _assert_residue_ordering(gro_path, ["SOL", "CH4_L", "NA", "CL"])
        # test_gro_atom_count_matches_header + test_atom_conservation_and_charge_neutrality
        # (CH4 solute = 5 atoms per molecule)
        _assert_atom_conservation(gro_path, self.ion, solute_atoms_per_mol=5)
        # test_top_molecules_section: SOL/CH4_L/NA/CL count parity
        # (CH4_L == solute_n_molecules)
        _assert_top_molecule_counts(top_path, self.ion)
        # test_top_includes_three_itps: exactly 3 ITPs
        _assert_top_includes(
            top_path, ["tip4p-ice.itp", "ch4_liquid.itp", "ion.itp"], exact_count=3
        )
        # test_no_custom_molecules
        assert self.ion.custom_molecule_count == 0, (
            f"F6 should have no custom molecules, got {self.ion.custom_molecule_count}"
        )
        # test_solute_preserved + test_solute_info_preserved (48.3-19: from
        # tests/test_e2e_ion_export.py TestIonFromSolute): solute metadata is
        # preserved in IonStructure after the BUG I5 workaround — solute_type
        # "CH4" and solute_n_molecules > 0 survive _solute_to_ion_source
        assert self.ion.solute_type == "CH4", (
            f"IonStructure.solute_type should be 'CH4', got '{self.ion.solute_type}'"
        )
        assert self.ion.solute_n_molecules > 0, (
            f"IonStructure.solute_n_molecules should be > 0, "
            f"got {self.ion.solute_n_molecules}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# F7: Interface→Solute(THF)→Ion (3 ITPs, Bug 1 fix)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
class TestChainF7GmxValidation:
    """Validate F7 chain (Interface→Solute(THF)→Ion) export passes gmx grompp.

    3 ITPs: tip4p-ice.itp, thf_liquid.itp, ion.itp
    Tests Bug 1 fix: THF solute atomtypes (os, c5, hc, h1) must be in TOP [atomtypes].
    """

    @pytest.fixture(autouse=True)
    def _build_chain(self, interface_slab):
        # Same BUG I5 workaround as F6 (THF variant): _insert_ions_from_solute
        # applies _solute_to_ion_source so IonInserter can read solute_type.
        solute = _insert_solutes(interface_slab, solute_type='THF', concentration=0.3)
        self.ion = _insert_ions_from_solute(solute, concentration=0.15)

    def test_gmx_grompp_succeeds(self, gmx_workspace):
        gro_path = str(gmx_workspace / "f7.gro")
        top_path = str(gmx_workspace / "f7.top")
        write_ion_gro_file(self.ion, gro_path)
        write_ion_top_file(self.ion, top_path)
        write_ion_itp(gmx_workspace / "ion.itp", self.ion.na_count, self.ion.cl_count)
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")
        _stage_itp_files(top_path, gmx_workspace)
        assert_itp_completeness(top_path, gmx_workspace)
        exit_code, stderr = run_gmx_grompp(gmx_workspace, gro_file="f7.gro", top_file="f7.top")
        assert exit_code == 0, f"gmx grompp failed for F7:\n{stderr[-500:]}"

        # Assert expected molecule types in .top [molecules]
        molecules = parse_top_molecules(top_path)
        expected_top_keys = {"SOL", "THF_L", "NA", "CL"}
        for key in expected_top_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in molecules), (
                    f"Expected molecule type '{base}' or '{key}' in [molecules] for F7, "
                    f"got: {list(molecules.keys())}"
                )
            else:
                assert key in molecules, (
                    f"Expected molecule type '{key}' in [molecules] for F7, "
                    f"got: {list(molecules.keys())}"
                )

        # Assert expected residue names in .gro
        residue_names = parse_gro_residue_names(gro_path)
        unique_residues = set(residue_names)
        expected_gro_keys = {"SOL", "THF_L", "NA", "CL"}
        for key in expected_gro_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in unique_residues), (
                    f"Expected residue '{base}' or '{key}' in .gro for F7, "
                    f"got: {sorted(unique_residues)}"
                )
            else:
                assert key in unique_residues, (
                    f"Expected residue '{key}' in .gro for F7, "
                    f"got: {sorted(unique_residues)}"
                )

        # ── Ported deep asserts (48.3-15: tests/test_e2e_chain_export_2.py TestChainF7) ──
        # test_gro_sol_before_thfl_before_na_before_cl: exactly 4 molecule types,
        # SOL→THF_L→NA→CL non-interleaved (THF_L = 5 chars, fits GRO limit)
        _assert_residue_ordering(gro_path, ["SOL", "THF_L", "NA", "CL"])
        # test_gro_atom_count_matches_header + test_atom_conservation_and_charge_neutrality
        # + test_thf_atom_count_per_molecule (THF solute = 13 atoms per molecule)
        _assert_atom_conservation(gro_path, self.ion, solute_atoms_per_mol=13)
        # test_top_molecules_section: SOL/THF_L/NA/CL count parity
        # (THF_L == solute_n_molecules)
        _assert_top_molecule_counts(top_path, self.ion)
        # test_top_includes_three_itps: exactly 3 ITPs
        _assert_top_includes(
            top_path, ["tip4p-ice.itp", "thf_liquid.itp", "ion.itp"], exact_count=3
        )
        # test_solute_preserved_thf: solute metadata preserved with THF type
        assert self.ion.solute_type == "THF", (
            f"IonStructure.solute_type should be 'THF', got '{self.ion.solute_type}'"
        )
        assert self.ion.solute_n_molecules > 0, (
            f"IonStructure.solute_n_molecules should be > 0, "
            f"got {self.ion.solute_n_molecules}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# F1: Interface→Custom→Solute→Ion (4 ITPs, Bug 2+3)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
class TestChainF1GmxValidation:
    """Validate F1 chain (Interface→Custom→Solute→Ion) export passes gmx grompp.

    4 ITPs: tip4p-ice.itp, etoh.itp, ch4_liquid.itp, ion.itp
    Tests Bug 2 fix: [molecules] must use ITP moleculetype name "etoh" (not "MOL").
    Tests Bug 3 fix: No duplicate atomtypes (hc shared between GAFF2 and custom).
    """

    @pytest.fixture(autouse=True)
    def _build_chain(self, interface_slab):
        # Note: SoluteInserter creates its own internal MoleculetypeRegistry and
        # auto-registers the liquid solute. No external registry needed.
        custom = _insert_custom_molecules(interface_slab, n_molecules=3)
        solute = _insert_solutes(custom, solute_type='CH4', concentration=0.3)
        self.ion = _insert_ions_from_solute(solute, concentration=0.15)

    def test_gmx_grompp_succeeds(self, gmx_workspace):
        gro_path = str(gmx_workspace / "f1.gro")
        top_path = str(gmx_workspace / "f1.top")
        write_ion_gro_file(self.ion, gro_path)
        write_ion_top_file(self.ion, top_path)
        write_ion_itp(gmx_workspace / "ion.itp", self.ion.na_count, self.ion.cl_count)
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")
        _stage_itp_files(top_path, gmx_workspace)
        assert_itp_completeness(top_path, gmx_workspace)
        exit_code, stderr = run_gmx_grompp(gmx_workspace, gro_file="f1.gro", top_file="f1.top")
        assert exit_code == 0, f"gmx grompp failed for F1:\n{stderr[-500:]}"

        # Assert expected molecule types in .top [molecules]
        molecules = parse_top_molecules(top_path)
        expected_top_keys = {"SOL", "etoh", "CH4_L", "NA", "CL"}
        for key in expected_top_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in molecules), (
                    f"Expected molecule type '{base}' or '{key}' in [molecules] for F1, "
                    f"got: {list(molecules.keys())}"
                )
            else:
                assert key in molecules, (
                    f"Expected molecule type '{key}' in [molecules] for F1, "
                    f"got: {list(molecules.keys())}"
                )

        # Assert expected residue names in .gro
        residue_names = parse_gro_residue_names(gro_path)
        unique_residues = set(residue_names)
        expected_gro_keys = {"SOL", "etoh", "CH4_L", "NA", "CL"}
        for key in expected_gro_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in unique_residues), (
                    f"Expected residue '{base}' or '{key}' in .gro for F1, "
                    f"got: {sorted(unique_residues)}"
                )
            else:
                assert key in unique_residues, (
                    f"Expected residue '{key}' in .gro for F1, "
                    f"got: {sorted(unique_residues)}"
                )

        # ── Ported deep asserts (48.3-15: tests/test_e2e_chain_export_1.py TestChainF1) ──
        # test_gro_residue_ordering: SOL→etoh→CH4_L→NA→CL (5 molecule types, no
        # interleaving). NOTE (48.3-02 D1): custom GRO residue IS the ITP
        # moleculetype name "etoh", so .gro and .top agree strictly.
        _assert_residue_ordering(gro_path, ["SOL", "etoh", "CH4_L", "NA", "CL"])
        # test_gro_atom_count_matches_header + test_atom_conservation:
        # header == atom lines == molecule_index + custom atoms + CH4 solute (5/mol)
        _assert_atom_conservation(gro_path, self.ion, solute_atoms_per_mol=5)
        # test_top_molecules_section: SOL/etoh/CH4_L/NA/CL count parity
        _assert_top_molecule_counts(top_path, self.ion)
        # test_top_includes: tip4p-ice + etoh + ch4_liquid + ion (exact 4 pinned by
        # the cross-chain ITP-monotonicity port)
        _assert_top_includes(
            top_path,
            ["tip4p-ice.itp", "etoh.itp", "ch4_liquid.itp", "ion.itp"],
            exact_count=4,
        )
        # test_custom_and_solute_preserved: custom + solute metadata survive in
        # IonStructure across the chain
        assert self.ion.custom_molecule_count > 0, (
            "IonStructure should have custom_molecule_count > 0"
        )
        assert self.ion.solute_n_molecules > 0, (
            "IonStructure should have solute_n_molecules > 0"
        )


# ══════════════════════════════════════════════════════════════════════════════
# F3: Hydrate→Interface→Solute→Ion (4 ITPs)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
class TestChainF3GmxValidation:
    """Validate F3 chain (Hydrate→Interface→Solute→Ion) export passes gmx grompp.

    4 ITPs: tip4p-ice.itp, ch4_hydrate.itp, ch4_liquid.itp, ion.itp
    Tests hydrate guest (CH4_H) + solute (CH4_L) coexistence.
    """

    @pytest.fixture(autouse=True)
    def _build_chain(self):
        # Note: SoluteInserter creates its own internal MoleculetypeRegistry and
        # auto-registers the liquid solute. No external registry needed.
        hydrate = _hydrate_sI_ch4_candidate()
        interface = _make_slab_interface(hydrate)
        solute = _insert_solutes(interface, solute_type='CH4', concentration=0.3)
        self.ion = _insert_ions_from_solute(solute, concentration=0.15)

    def test_gmx_grompp_succeeds(self, gmx_workspace):
        gro_path = str(gmx_workspace / "f3.gro")
        top_path = str(gmx_workspace / "f3.top")
        write_ion_gro_file(self.ion, gro_path)
        write_ion_top_file(self.ion, top_path)
        write_ion_itp(gmx_workspace / "ion.itp", self.ion.na_count, self.ion.cl_count)
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")
        _stage_itp_files(top_path, gmx_workspace)
        assert_itp_completeness(top_path, gmx_workspace)
        exit_code, stderr = run_gmx_grompp(gmx_workspace, gro_file="f3.gro", top_file="f3.top")
        assert exit_code == 0, f"gmx grompp failed for F3:\n{stderr[-500:]}"

        # Assert expected molecule types in .top [molecules]
        molecules = parse_top_molecules(top_path)
        expected_top_keys = {"SOL", "CH4_H*", "CH4_L", "NA", "CL"}
        for key in expected_top_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in molecules), (
                    f"Expected molecule type '{base}' or '{key}' in [molecules] for F3, "
                    f"got: {list(molecules.keys())}"
                )
            else:
                assert key in molecules, (
                    f"Expected molecule type '{key}' in [molecules] for F3, "
                    f"got: {list(molecules.keys())}"
                )

        # Assert expected residue names in .gro
        residue_names = parse_gro_residue_names(gro_path)
        unique_residues = set(residue_names)
        expected_gro_keys = {"SOL", "CH4_H", "CH4_L", "NA", "CL"}
        for key in expected_gro_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in unique_residues), (
                    f"Expected residue '{base}' or '{key}' in .gro for F3, "
                    f"got: {sorted(unique_residues)}"
                )
            else:
                assert key in unique_residues, (
                    f"Expected residue '{key}' in .gro for F3, "
                    f"got: {sorted(unique_residues)}"
                )

        # ── Ported deep asserts (48.3-15: tests/test_e2e_chain_export_1.py TestChainF3) ──
        # test_gro_residue_ordering: KEY P0 test — CH4_H (hydrate guest) and CH4_L
        # (liquid solute) coexist, ordered SOL→CH4_H→CH4_L→NA→CL without interleaving.
        _assert_residue_ordering(gro_path, ["SOL", "CH4_H", "CH4_L", "NA", "CL"])
        # test_gro_atom_count_matches_header (CH4 solute = 5 atoms per molecule)
        _assert_atom_conservation(gro_path, self.ion, solute_atoms_per_mol=5)
        # test_top_molecules_section + test_registry_distinguishes_ch4_h_ch4_l:
        # guest (CH4_H/CH4) AND solute (CH4_L) both present with count parity
        _assert_top_molecule_counts(top_path, self.ion)
        # test_top_includes: tip4p-ice + ch4_hydrate + ch4_liquid + ion
        _assert_top_includes(
            top_path, ["tip4p-ice.itp", "ch4_hydrate.itp", "ch4_liquid.itp", "ion.itp"]
        )
        # test_guest_count_preserved: guest molecules preserved because the chain
        # goes through InterfaceStructure (not CustomMoleculeStructure, which drops
        # guest_nmolecules)
        assert self.ion.guest_nmolecules > 0, (
            f"guest_nmolecules should be > 0, got {self.ion.guest_nmolecules}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# F4: Hydrate→Interface→Custom→Solute→Ion (5 ITPs, ALL 3 bugs)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
class TestChainF4GmxValidation:
    """Validate F4 chain (Hydrate→Interface→Custom→Solute→Ion) export passes gmx grompp.

    5 ITPs: tip4p-ice.itp, thf_hydrate.itp, etoh.itp, thf_liquid.itp, ion.itp
    Most complex chain — tests ALL three bug fixes:
    - Solute atomtypes (THF: os, c5, hc, h1) must be in TOP [atomtypes]
    - Custom moleculetype name "etoh" in [molecules] (not "MOL")
    - No duplicate atomtypes (hc, h1 shared between THF GAFF2 and etoh custom)
    """

    @pytest.fixture(autouse=True)
    def _build_chain(self):
        # Note: SoluteInserter creates its own internal MoleculetypeRegistry and
        # auto-registers the liquid solute. No external registry needed.
        hydrate = _hydrate_sI_thf_candidate()
        interface = _make_slab_interface(hydrate)
        custom = _insert_custom_molecules(interface, n_molecules=3)
        solute = _insert_solutes(custom, solute_type='THF', concentration=0.3)
        self.ion = _insert_ions_from_solute(solute, concentration=0.15)

    def test_gmx_grompp_succeeds(self, gmx_workspace):
        gro_path = str(gmx_workspace / "f4.gro")
        top_path = str(gmx_workspace / "f4.top")
        write_ion_gro_file(self.ion, gro_path)
        write_ion_top_file(self.ion, top_path)
        write_ion_itp(gmx_workspace / "ion.itp", self.ion.na_count, self.ion.cl_count)
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")
        _stage_itp_files(top_path, gmx_workspace)
        assert_itp_completeness(top_path, gmx_workspace)
        exit_code, stderr = run_gmx_grompp(gmx_workspace, gro_file="f4.gro", top_file="f4.top")
        assert exit_code == 0, f"gmx grompp failed for F4:\n{stderr[-500:]}"

        # Assert expected molecule types in .top [molecules]
        molecules = parse_top_molecules(top_path)
        expected_top_keys = {"SOL", "THF_H*", "etoh", "THF_L", "NA", "CL"}
        for key in expected_top_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in molecules), (
                    f"Expected molecule type '{base}' or '{key}' in [molecules] for F4, "
                    f"got: {list(molecules.keys())}"
                )
            else:
                assert key in molecules, (
                    f"Expected molecule type '{key}' in [molecules] for F4, "
                    f"got: {list(molecules.keys())}"
                )

        # Assert expected residue names in .gro
        residue_names = parse_gro_residue_names(gro_path)
        unique_residues = set(residue_names)
        expected_gro_keys = {"SOL", "THF_H", "etoh", "THF_L", "NA", "CL"}
        for key in expected_gro_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in unique_residues), (
                    f"Expected residue '{base}' or '{key}' in .gro for F4, "
                    f"got: {sorted(unique_residues)}"
                )
            else:
                assert key in unique_residues, (
                    f"Expected residue '{key}' in .gro for F4, "
                    f"got: {sorted(unique_residues)}"
                )

        # ── Ported deep asserts (48.3-15: tests/test_e2e_chain_export_1.py TestChainF4) ──
        # test_gro_residue_ordering: SOL→THF_H→etoh→THF_L→NA→CL (6 molecule types)
        _assert_residue_ordering(gro_path, ["SOL", "THF_H", "etoh", "THF_L", "NA", "CL"])
        # test_gro_atom_count_matches_header (THF solute = 13 atoms per molecule)
        _assert_atom_conservation(gro_path, self.ion, solute_atoms_per_mol=13)
        # test_top_molecules_section + test_registry_distinguishes_thf_h_thf_l:
        # guest (THF_H/THF) AND solute (THF_L) both present with count parity
        _assert_top_molecule_counts(top_path, self.ion)
        # test_top_includes: 5 ITPs — tip4p-ice + thf_hydrate + etoh + thf_liquid + ion
        _assert_top_includes(
            top_path,
            ["tip4p-ice.itp", "thf_hydrate.itp", "etoh.itp", "thf_liquid.itp", "ion.itp"],
        )
        # test_guest_atom_count_positive (KNOWN LIMITATION): guest_nmolecules may be 0
        # after passing through CustomMoleculeStructure (field doesn't exist on that
        # type); guest_atom_count IS preserved, so we check that instead.
        assert self.ion.guest_atom_count > 0, (
            f"guest_atom_count should be > 0 (guest atoms are preserved), "
            f"got {self.ion.guest_atom_count}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# F2: Interface→Custom→Ion (3 ITPs, Bug 2+3 without solute atomtypes)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
class TestChainF2GmxValidation:
    """Validate F2 chain (Interface→Custom→Ion) export passes gmx grompp.

    3 ITPs: tip4p-ice.itp, etoh.itp, ion.itp
    Tests Bug 2 fix: [molecules] uses "etoh" not "MOL" without solute atomtypes present.
    Tests Bug 3 fix: Custom-only atomtype dedup (no GAFF2 interference).
    """

    @pytest.fixture(autouse=True)
    def _build_chain(self, interface_slab):
        custom = _insert_custom_molecules(interface_slab, n_molecules=3)
        self.ion = _insert_ions(custom, concentration=0.15)

    def test_gmx_grompp_succeeds(self, gmx_workspace):
        gro_path = str(gmx_workspace / "f2.gro")
        top_path = str(gmx_workspace / "f2.top")
        write_ion_gro_file(self.ion, gro_path)
        write_ion_top_file(self.ion, top_path)
        write_ion_itp(gmx_workspace / "ion.itp", self.ion.na_count, self.ion.cl_count)
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")
        _stage_itp_files(top_path, gmx_workspace)
        assert_itp_completeness(top_path, gmx_workspace)
        exit_code, stderr = run_gmx_grompp(gmx_workspace, gro_file="f2.gro", top_file="f2.top")
        assert exit_code == 0, f"gmx grompp failed for F2:\n{stderr[-500:]}"

        # Assert expected molecule types in .top [molecules]
        molecules = parse_top_molecules(top_path)
        expected_top_keys = {"SOL", "etoh", "NA", "CL"}
        for key in expected_top_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in molecules), (
                    f"Expected molecule type '{base}' or '{key}' in [molecules] for F2, "
                    f"got: {list(molecules.keys())}"
                )
            else:
                assert key in molecules, (
                    f"Expected molecule type '{key}' in [molecules] for F2, "
                    f"got: {list(molecules.keys())}"
                )

        # Assert expected residue names in .gro
        residue_names = parse_gro_residue_names(gro_path)
        unique_residues = set(residue_names)
        expected_gro_keys = {"SOL", "etoh", "NA", "CL"}
        for key in expected_gro_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in unique_residues), (
                    f"Expected residue '{base}' or '{key}' in .gro for F2, "
                    f"got: {sorted(unique_residues)}"
                )
            else:
                assert key in unique_residues, (
                    f"Expected residue '{key}' in .gro for F2, "
                    f"got: {sorted(unique_residues)}"
                )

        # ── Ported deep asserts (48.3-15: tests/test_e2e_chain_export_1.py TestChainF2) ──
        # test_gro_residue_ordering: SOL→etoh→NA→CL (no solutes — exact set also
        # covers the source's negative "CH4_L not in residues" assert)
        _assert_residue_ordering(gro_path, ["SOL", "etoh", "NA", "CL"])
        # test_gro_atom_count_matches_header
        _assert_atom_conservation(gro_path, self.ion)
        # test_top_molecules_section: SOL/etoh/NA/CL count parity
        _assert_top_molecule_counts(top_path, self.ion)
        # test_top_includes: 3 ITPs, and NO solute or guest ITP (negative asserts)
        _assert_top_includes(
            top_path,
            ["tip4p-ice.itp", "etoh.itp", "ion.itp"],
            forbidden=["ch4_liquid.itp", "ch4_hydrate.itp"],
            exact_count=3,
        )
        # test_no_solute_attributes: F2 doesn't use solutes
        assert self.ion.solute_type == "", (
            f"solute_type should be empty, got '{self.ion.solute_type}'"
        )
        assert self.ion.solute_n_molecules == 0, (
            f"solute_n_molecules should be 0, got {self.ion.solute_n_molecules}"
        )
        # test_custom_molecule_count_preserved (48.3-19: from
        # tests/test_e2e_ion_export.py TestIonFromCustom — F2 IS the
        # Interface→Custom→Ion chain): custom count survives ion insertion
        assert self.ion.custom_molecule_count > 0, (
            "IonStructure should have custom_molecule_count > 0"
        )


# ══════════════════════════════════════════════════════════════════════════════
# F1+THF: Interface→Custom→Solute(THF)→Ion (4 ITPs, Bug 3 dedup hc)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
class TestChainF1ThfGmxValidation:
    """Validate F1+THF chain (Interface→Custom→Solute(THF)→Ion) export passes gmx grompp.

    4 ITPs: tip4p-ice.itp, etoh.itp, thf_liquid.itp, ion.itp
    Tests Bug 3 fix: THF solute atomtypes (os, c5, hc, h1) + etoh custom atomtypes
    (oh, ho, hc) — "hc" shared between THF GAFF2 and etoh, tests dedup.
    """

    @pytest.fixture(autouse=True)
    def _build_chain(self, interface_slab):
        custom = _insert_custom_molecules(interface_slab, n_molecules=3)
        solute = _insert_solutes(custom, solute_type='THF', concentration=0.3)
        self.ion = _insert_ions_from_solute(solute, concentration=0.15)

    def test_gmx_grompp_succeeds(self, gmx_workspace):
        gro_path = str(gmx_workspace / "f1_thf.gro")
        top_path = str(gmx_workspace / "f1_thf.top")
        write_ion_gro_file(self.ion, gro_path)
        write_ion_top_file(self.ion, top_path)
        write_ion_itp(gmx_workspace / "ion.itp", self.ion.na_count, self.ion.cl_count)
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")
        _stage_itp_files(top_path, gmx_workspace)
        assert_itp_completeness(top_path, gmx_workspace)
        exit_code, stderr = run_gmx_grompp(gmx_workspace, gro_file="f1_thf.gro", top_file="f1_thf.top")
        assert exit_code == 0, f"gmx grompp failed for F1+THF:\n{stderr[-500:]}"

        # Assert expected molecule types in .top [molecules]
        molecules = parse_top_molecules(top_path)
        expected_top_keys = {"SOL", "etoh", "THF_L", "NA", "CL"}
        for key in expected_top_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in molecules), (
                    f"Expected molecule type '{base}' or '{key}' in [molecules] for F1+THF, "
                    f"got: {list(molecules.keys())}"
                )
            else:
                assert key in molecules, (
                    f"Expected molecule type '{key}' in [molecules] for F1+THF, "
                    f"got: {list(molecules.keys())}"
                )

        # Assert expected residue names in .gro
        residue_names = parse_gro_residue_names(gro_path)
        unique_residues = set(residue_names)
        expected_gro_keys = {"SOL", "etoh", "THF_L", "NA", "CL"}
        for key in expected_gro_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in unique_residues), (
                    f"Expected residue '{base}' or '{key}' in .gro for F1+THF, "
                    f"got: {sorted(unique_residues)}"
                )
            else:
                assert key in unique_residues, (
                    f"Expected residue '{key}' in .gro for F1+THF, "
                    f"got: {sorted(unique_residues)}"
                )

        # ── Ported deep asserts (48.3-15 helper set applied to all F-chains) ──
        _assert_residue_ordering(gro_path, ["SOL", "etoh", "THF_L", "NA", "CL"])
        _assert_atom_conservation(gro_path, self.ion, solute_atoms_per_mol=13)
        _assert_top_molecule_counts(top_path, self.ion)
        _assert_top_includes(
            top_path, ["tip4p-ice.itp", "etoh.itp", "thf_liquid.itp", "ion.itp"]
        )


# ══════════════════════════════════════════════════════════════════════════════
# F3+THF: Hydrate sI-CH4→Interface→Solute(THF)→Ion (4 ITPs)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
class TestChainF3ThfGmxValidation:
    """Validate F3+THF chain (Hydrate sI-CH4→Interface→Solute(THF)→Ion) export passes gmx grompp.

    4 ITPs: tip4p-ice.itp, ch4_hydrate.itp, thf_liquid.itp, ion.itp
    Tests CH4_H hydrate guest (c3, hc GAFF2 atomtypes) + THF_L solute
    (os, c5, hc, h1 GAFF2 atomtypes) — "hc" shared, tests dedup.
    """

    @pytest.fixture(autouse=True)
    def _build_chain(self):
        hydrate = _hydrate_sI_ch4_candidate()
        interface = _make_slab_interface(hydrate)
        solute = _insert_solutes(interface, solute_type='THF', concentration=0.3)
        self.ion = _insert_ions_from_solute(solute, concentration=0.15)

    def test_gmx_grompp_succeeds(self, gmx_workspace):
        gro_path = str(gmx_workspace / "f3_thf.gro")
        top_path = str(gmx_workspace / "f3_thf.top")
        write_ion_gro_file(self.ion, gro_path)
        write_ion_top_file(self.ion, top_path)
        write_ion_itp(gmx_workspace / "ion.itp", self.ion.na_count, self.ion.cl_count)
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")
        _stage_itp_files(top_path, gmx_workspace)
        assert_itp_completeness(top_path, gmx_workspace)
        exit_code, stderr = run_gmx_grompp(gmx_workspace, gro_file="f3_thf.gro", top_file="f3_thf.top")
        assert exit_code == 0, f"gmx grompp failed for F3+THF:\n{stderr[-500:]}"

        # Assert expected molecule types in .top [molecules]
        molecules = parse_top_molecules(top_path)
        expected_top_keys = {"SOL", "CH4_H*", "THF_L", "NA", "CL"}
        for key in expected_top_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in molecules), (
                    f"Expected molecule type '{base}' or '{key}' in [molecules] for F3+THF, "
                    f"got: {list(molecules.keys())}"
                )
            else:
                assert key in molecules, (
                    f"Expected molecule type '{key}' in [molecules] for F3+THF, "
                    f"got: {list(molecules.keys())}"
                )

        # Assert expected residue names in .gro
        residue_names = parse_gro_residue_names(gro_path)
        unique_residues = set(residue_names)
        expected_gro_keys = {"SOL", "CH4_H", "THF_L", "NA", "CL"}
        for key in expected_gro_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in unique_residues), (
                    f"Expected residue '{base}' or '{key}' in .gro for F3+THF, "
                    f"got: {sorted(unique_residues)}"
                )
            else:
                assert key in unique_residues, (
                    f"Expected residue '{key}' in .gro for F3+THF, "
                    f"got: {sorted(unique_residues)}"
                )

        # ── Ported deep asserts (48.3-15 helper set applied to all F-chains) ──
        _assert_residue_ordering(gro_path, ["SOL", "CH4_H", "THF_L", "NA", "CL"])
        _assert_atom_conservation(gro_path, self.ion, solute_atoms_per_mol=13)
        _assert_top_molecule_counts(top_path, self.ion)
        _assert_top_includes(
            top_path, ["tip4p-ice.itp", "ch4_hydrate.itp", "thf_liquid.itp", "ion.itp"]
        )


# ══════════════════════════════════════════════════════════════════════════════
# F4+CH4: Hydrate sI-THF→Custom→Solute(CH4)→Ion (5 ITPs, 3-source dedup)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
class TestChainF4Ch4GmxValidation:
    """Validate F4+CH4 chain (Hydrate sI-THF→Custom→Solute(CH4)→Ion) export passes gmx grompp.

    5 ITPs: tip4p-ice.itp, thf_hydrate.itp, etoh.itp, ch4_liquid.itp, ion.itp
    Most complex dedup scenario — THREE atomtype sources with "hc" shared across
    all three:
    - THF_H hydrate guest (os, c5, hc, h1)
    - CH4_L solute (c3, hc)
    - etoh custom (oh, ho, hc)
    """

    @pytest.fixture(autouse=True)
    def _build_chain(self):
        hydrate = _hydrate_sI_thf_candidate()
        interface = _make_slab_interface(hydrate)
        custom = _insert_custom_molecules(interface, n_molecules=3)
        solute = _insert_solutes(custom, solute_type='CH4', concentration=0.3)
        self.ion = _insert_ions_from_solute(solute, concentration=0.15)

    def test_gmx_grompp_succeeds(self, gmx_workspace):
        gro_path = str(gmx_workspace / "f4_ch4.gro")
        top_path = str(gmx_workspace / "f4_ch4.top")
        write_ion_gro_file(self.ion, gro_path)
        write_ion_top_file(self.ion, top_path)
        write_ion_itp(gmx_workspace / "ion.itp", self.ion.na_count, self.ion.cl_count)
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")
        _stage_itp_files(top_path, gmx_workspace)
        assert_itp_completeness(top_path, gmx_workspace)
        exit_code, stderr = run_gmx_grompp(gmx_workspace, gro_file="f4_ch4.gro", top_file="f4_ch4.top")
        assert exit_code == 0, f"gmx grompp failed for F4+CH4:\n{stderr[-500:]}"

        # Assert expected molecule types in .top [molecules]
        molecules = parse_top_molecules(top_path)
        expected_top_keys = {"SOL", "THF_H*", "etoh", "CH4_L", "NA", "CL"}
        for key in expected_top_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in molecules), (
                    f"Expected molecule type '{base}' or '{key}' in [molecules] for F4+CH4, "
                    f"got: {list(molecules.keys())}"
                )
            else:
                assert key in molecules, (
                    f"Expected molecule type '{key}' in [molecules] for F4+CH4, "
                    f"got: {list(molecules.keys())}"
                )

        # Assert expected residue names in .gro
        residue_names = parse_gro_residue_names(gro_path)
        unique_residues = set(residue_names)
        expected_gro_keys = {"SOL", "THF_H", "etoh", "CH4_L", "NA", "CL"}
        for key in expected_gro_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in unique_residues), (
                    f"Expected residue '{base}' or '{key}' in .gro for F4+CH4, "
                    f"got: {sorted(unique_residues)}"
                )
            else:
                assert key in unique_residues, (
                    f"Expected residue '{key}' in .gro for F4+CH4, "
                    f"got: {sorted(unique_residues)}"
                )

        # ── Ported deep asserts (48.3-15 helper set applied to all F-chains) ──
        _assert_residue_ordering(gro_path, ["SOL", "THF_H", "etoh", "CH4_L", "NA", "CL"])
        _assert_atom_conservation(gro_path, self.ion, solute_atoms_per_mol=5)
        _assert_top_molecule_counts(top_path, self.ion)
        _assert_top_includes(
            top_path,
            ["tip4p-ice.itp", "thf_hydrate.itp", "etoh.itp", "ch4_liquid.itp", "ion.itp"],
        )


# ══════════════════════════════════════════════════════════════════════════════
# F4-CH4-hydrate: Hydrate sI-CH4→Interface→Custom→Solute→Ion (5 ITPs, BUG REGRESSION)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
class TestChainF4Ch4HydrateGmxValidation:
    """Validate F4-CH4-hydrate chain (Hydrate sI-CH4→Interface→Custom→Solute→Ion) export passes gmx grompp.

    5 ITPs: tip4p-ice.itp, ch4_hydrate.itp, etoh.itp, ch4_liquid.itp, ion.itp
    This is the EXACT chain that triggered the production bug where CustomMoleculeStructure
    was missing guest_nmolecules, causing the GUI exporter to skip copying ch4_hydrate.itp.
    The .top writer correctly included #include "ch4_hydrate.itp" but the file was missing
    from the export directory.

    Regression test for: CustomMoleculeStructure.guest_nmolecules field (commit 27332f6).
    """

    @pytest.fixture(autouse=True)
    def _build_chain(self):
        # SoluteInserter creates its own internal MoleculetypeRegistry and
        # auto-registers the liquid solute. No external registry needed.
        hydrate = _hydrate_sI_ch4_candidate()
        interface = _make_slab_interface(hydrate)
        custom = _insert_custom_molecules(interface, n_molecules=3)
        solute = _insert_solutes(custom, solute_type='CH4', concentration=0.3)
        self.ion = _insert_ions_from_solute(solute, concentration=0.15)

    def test_gmx_grompp_succeeds(self, gmx_workspace):
        gro_path = str(gmx_workspace / "f4_ch4_hydrate.gro")
        top_path = str(gmx_workspace / "f4_ch4_hydrate.top")
        write_ion_gro_file(self.ion, gro_path)
        write_ion_top_file(self.ion, top_path)
        write_ion_itp(gmx_workspace / "ion.itp", self.ion.na_count, self.ion.cl_count)
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")
        _stage_itp_files(top_path, gmx_workspace)
        assert_itp_completeness(top_path, gmx_workspace)
        exit_code, stderr = run_gmx_grompp(gmx_workspace, gro_file="f4_ch4_hydrate.gro", top_file="f4_ch4_hydrate.top")
        assert exit_code == 0, f"gmx grompp failed for F4-CH4-hydrate:\n{stderr[-500:]}"

        # Assert expected molecule types in .top [molecules]
        molecules = parse_top_molecules(top_path)
        expected_top_keys = {"SOL", "CH4_H*", "etoh", "CH4_L", "NA", "CL"}
        for key in expected_top_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in molecules), (
                    f"Expected molecule type '{base}' or '{key}' in [molecules] for F4-CH4-hydrate, "
                    f"got: {list(molecules.keys())}"
                )
            else:
                assert key in molecules, (
                    f"Expected molecule type '{key}' in [molecules] for F4-CH4-hydrate, "
                    f"got: {list(molecules.keys())}"
                )

        # Assert expected residue names in .gro
        residue_names = parse_gro_residue_names(gro_path)
        unique_residues = set(residue_names)
        expected_gro_keys = {"SOL", "CH4_H", "etoh", "CH4_L", "NA", "CL"}
        for key in expected_gro_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in unique_residues), (
                    f"Expected residue '{base}' or '{key}' in .gro for F4-CH4-hydrate, "
                    f"got: {sorted(unique_residues)}"
                )
            else:
                assert key in unique_residues, (
                    f"Expected residue '{key}' in .gro for F4-CH4-hydrate, "
                    f"got: {sorted(unique_residues)}"
                )

        # ── Ported deep asserts (48.3-15 helper set applied to all F-chains) ──
        _assert_residue_ordering(gro_path, ["SOL", "CH4_H", "etoh", "CH4_L", "NA", "CL"])
        _assert_atom_conservation(gro_path, self.ion, solute_atoms_per_mol=5)
        _assert_top_molecule_counts(top_path, self.ion)
        _assert_top_includes(
            top_path,
            ["tip4p-ice.itp", "ch4_hydrate.itp", "etoh.itp", "ch4_liquid.itp", "ion.itp"],
        )


# ══════════════════════════════════════════════════════════════════════════════
# F3-sII: Hydrate sII-CH4→Interface→Solute(CH4)→Ion (4 ITPs)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
class TestChainF3SIIGmxValidation:
    """Validate F3-sII chain (Hydrate sII-CH4→Interface→Solute→Ion) passes gmx grompp.

    4 ITPs: tip4p-ice.itp, ch4_hydrate.itp, ch4_liquid.itp, ion.itp
    Tests sII hydrate guest export + grompp validation.
    sII has different cage structure (5^12 6^4 large + 5^12 small) from sI.
    """

    @pytest.fixture(autouse=True)
    def _build_chain(self):
        hydrate = _hydrate_sII_ch4_candidate()
        interface = _make_slab_interface(hydrate)
        solute = _insert_solutes(interface, solute_type='CH4', concentration=0.3)
        self.ion = _insert_ions_from_solute(solute, concentration=0.15)

    def test_gmx_grompp_succeeds(self, gmx_workspace):
        gro_path = str(gmx_workspace / "f3_sII.gro")
        top_path = str(gmx_workspace / "f3_sII.top")
        write_ion_gro_file(self.ion, gro_path)
        write_ion_top_file(self.ion, top_path)
        write_ion_itp(gmx_workspace / "ion.itp", self.ion.na_count, self.ion.cl_count)
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")
        _stage_itp_files(top_path, gmx_workspace)
        assert_itp_completeness(top_path, gmx_workspace)
        exit_code, stderr = run_gmx_grompp(gmx_workspace, gro_file="f3_sII.gro", top_file="f3_sII.top")
        assert exit_code == 0, f"gmx grompp failed for F3-sII:\n{stderr[-500:]}"

        # Assert expected molecule types in .top [molecules]
        molecules = parse_top_molecules(top_path)
        expected_top_keys = {"SOL", "CH4_H*", "CH4_L", "NA", "CL"}
        for key in expected_top_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in molecules), (
                    f"Expected molecule type '{base}' or '{key}' in [molecules] for F3-sII, "
                    f"got: {list(molecules.keys())}"
                )
            else:
                assert key in molecules, (
                    f"Expected molecule type '{key}' in [molecules] for F3-sII, "
                    f"got: {list(molecules.keys())}"
                )

        # Assert expected residue names in .gro
        residue_names = parse_gro_residue_names(gro_path)
        unique_residues = set(residue_names)
        expected_gro_keys = {"SOL", "CH4_H", "CH4_L", "NA", "CL"}
        for key in expected_gro_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in unique_residues), (
                    f"Expected residue '{base}' or '{key}' in .gro for F3-sII, "
                    f"got: {sorted(unique_residues)}"
                )
            else:
                assert key in unique_residues, (
                    f"Expected residue '{key}' in .gro for F3-sII, "
                    f"got: {sorted(unique_residues)}"
                )

        # ── Ported deep asserts (48.3-15 helper set applied to all F-chains) ──
        _assert_residue_ordering(gro_path, ["SOL", "CH4_H", "CH4_L", "NA", "CL"])
        _assert_atom_conservation(gro_path, self.ion, solute_atoms_per_mol=5)
        _assert_top_molecule_counts(top_path, self.ion)
        _assert_top_includes(
            top_path, ["tip4p-ice.itp", "ch4_hydrate.itp", "ch4_liquid.itp", "ion.itp"]
        )


# ══════════════════════════════════════════════════════════════════════════════
# F4-sII: Hydrate sII-THF→Interface→Custom→Solute(THF)→Ion (5 ITPs)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
class TestChainF4SIIGmxValidation:
    """Validate F4-sII chain (Hydrate sII-THF→Interface→Custom→Solute→Ion) passes gmx grompp.

    5 ITPs: tip4p-ice.itp, thf_hydrate.itp, etoh.itp, thf_liquid.itp, ion.itp
    Tests sII hydrate with full custom+solute+ion chain.
    Most complex sII chain — tests all 3 bug fixes with sII lattice.
    """

    @pytest.fixture(autouse=True)
    def _build_chain(self):
        hydrate = _hydrate_sII_thf_candidate()
        interface = _make_slab_interface(hydrate)
        custom = _insert_custom_molecules(interface, n_molecules=3)
        solute = _insert_solutes(custom, solute_type='THF', concentration=0.3)
        self.ion = _insert_ions_from_solute(solute, concentration=0.15)

    def test_gmx_grompp_succeeds(self, gmx_workspace):
        gro_path = str(gmx_workspace / "f4_sII.gro")
        top_path = str(gmx_workspace / "f4_sII.top")
        write_ion_gro_file(self.ion, gro_path)
        write_ion_top_file(self.ion, top_path)
        write_ion_itp(gmx_workspace / "ion.itp", self.ion.na_count, self.ion.cl_count)
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")
        _stage_itp_files(top_path, gmx_workspace)
        assert_itp_completeness(top_path, gmx_workspace)
        exit_code, stderr = run_gmx_grompp(gmx_workspace, gro_file="f4_sII.gro", top_file="f4_sII.top")
        assert exit_code == 0, f"gmx grompp failed for F4-sII:\n{stderr[-500:]}"

        # Assert expected molecule types in .top [molecules]
        molecules = parse_top_molecules(top_path)
        expected_top_keys = {"SOL", "THF_H*", "etoh", "THF_L", "NA", "CL"}
        for key in expected_top_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in molecules), (
                    f"Expected molecule type '{base}' or '{key}' in [molecules] for F4-sII, "
                    f"got: {list(molecules.keys())}"
                )
            else:
                assert key in molecules, (
                    f"Expected molecule type '{key}' in [molecules] for F4-sII, "
                    f"got: {list(molecules.keys())}"
                )

        # Assert expected residue names in .gro
        residue_names = parse_gro_residue_names(gro_path)
        unique_residues = set(residue_names)
        expected_gro_keys = {"SOL", "THF_H", "etoh", "THF_L", "NA", "CL"}
        for key in expected_gro_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in unique_residues), (
                    f"Expected residue '{base}' or '{key}' in .gro for F4-sII, "
                    f"got: {sorted(unique_residues)}"
                )
            else:
                assert key in unique_residues, (
                    f"Expected residue '{key}' in .gro for F4-sII, "
                    f"got: {sorted(unique_residues)}"
                )

        # ── Ported deep asserts (48.3-15 helper set applied to all F-chains) ──
        _assert_residue_ordering(gro_path, ["SOL", "THF_H", "etoh", "THF_L", "NA", "CL"])
        _assert_atom_conservation(gro_path, self.ion, solute_atoms_per_mol=13)
        _assert_top_molecule_counts(top_path, self.ion)
        _assert_top_includes(
            top_path,
            ["tip4p-ice.itp", "thf_hydrate.itp", "etoh.itp", "thf_liquid.itp", "ion.itp"],
        )


# ══════════════════════════════════════════════════════════════════════════════
# Hydrate-only (no interface step)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
class TestHydrateGmxValidation:
    """Validate hydrate-only export passes gmx grompp.

    Tests the hydrate-only export path used by CLI --hydrate without --interface.
    Wraps HydrateStructure as InterfaceStructure (matching CLI pipeline.py behavior:
    ice_atom_count=0, water_atom_count=water_count*4).

    Uses 2×2×2 supercell for box > 2.0 nm (required for 1.0 nm grompp cutoffs).
    """

    @pytest.fixture(autouse=True)
    def _build_hydrate(self):
        """Generate sI CH4 hydrate structure with 2x2x2 supercell for grompp."""
        from quickice.structure_generation.hydrate_generator import HydrateStructureGenerator
        from quickice.structure_generation.types import (
            HydrateConfig,
            InterfaceStructure,
            WATER_ATOMS_PER_MOLECULE,
        )
        gen = HydrateStructureGenerator()
        config = HydrateConfig(
            lattice_type="sI",
            guest_type="ch4",
            supercell_x=2,
            supercell_y=2,
            supercell_z=2,
        )
        h = gen.generate(config)
        water_atom_count = h.water_count * WATER_ATOMS_PER_MOLECULE
        guest_atom_count = len(h.positions) - water_atom_count
        self.iface = InterfaceStructure(
            positions=h.positions,
            atom_names=h.atom_names,
            cell=h.cell,
            molecule_index=h.molecule_index,
            ice_atom_count=0,  # No crystalline ice in hydrate
            water_atom_count=water_atom_count,  # Hydrate water = "water" region
            ice_nmolecules=0,
            water_nmolecules=h.water_count,
            mode="hydrate",
            report=h.report,
            guest_atom_count=guest_atom_count,
            guest_nmolecules=h.guest_count,
        )

    def test_gmx_grompp_succeeds(self, gmx_workspace):
        """Export hydrate GRO/TOP, stage ITPs, run gmx grompp."""
        gro_path = str(gmx_workspace / "hydrate.gro")
        top_path = str(gmx_workspace / "hydrate.top")
        write_interface_gro_file(self.iface, gro_path)
        write_interface_top_file(self.iface, top_path)
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")
        _stage_itp_files(top_path, gmx_workspace)
        assert_itp_completeness(top_path, gmx_workspace)
        exit_code, stderr = run_gmx_grompp(
            gmx_workspace, gro_file="hydrate.gro", top_file="hydrate.top"
        )
        assert exit_code == 0, f"gmx grompp failed for hydrate-only:\n{stderr[-500:]}"
        # Validate molecule type presence
        molecules = parse_top_molecules(top_path)
        assert "SOL" in molecules
        residue_names = parse_gro_residue_names(gro_path)
        assert "SOL" in set(residue_names)

        # ── Ported deep asserts (48.3-19: tests/test_e2e_ice_interface_export.py
        # TestInterfaceHydrateExport — interface writer WITH hydrate guests) ──
        # test_gro_sol_before_guest_residues + test_no_sol_guest_interleaving:
        # SOL before guest residues, no interleaving (after any guest residue
        # type appears, no SOL may follow)
        unique_names = set(residue_names)
        guest_names = unique_names - {"SOL"}
        assert len(guest_names) > 0, (
            f"Hydrate interface should have guest residues, got only {unique_names}"
        )
        expected_order = ["SOL"] + sorted(guest_names)
        assert_gro_residue_ordering(residue_names, expected_order)
        # test_gro_atom_count_matches_header
        _assert_gro_header_matches_lines(gro_path)
        # test_top_molecules_section: SOL == ice+water and guest count ==
        # guest_nmolecules (guest residue name from the hydrate ITP — CH4_H)
        expected_sol = self.iface.ice_nmolecules + self.iface.water_nmolecules
        assert molecules["SOL"] == expected_sol, (
            f"Expected SOL count {expected_sol}, got {molecules['SOL']}"
        )
        guest_res_name = get_hydrate_guest_residue_name("ch4")
        assert guest_res_name in molecules, (
            f"Expected guest molecule '{guest_res_name}' in [molecules], "
            f"got {list(molecules.keys())}"
        )
        assert molecules[guest_res_name] == self.iface.guest_nmolecules, (
            f"Expected {guest_res_name} count {self.iface.guest_nmolecules}, "
            f"got {molecules[guest_res_name]}"
        )
        # test_top_includes_hydrate_itp: tip4p-ice.itp + ch4_hydrate.itp
        includes = parse_top_includes(top_path)
        assert "tip4p-ice.itp" in includes, "Should include tip4p-ice.itp"
        assert "ch4_hydrate.itp" in includes, "Should include ch4_hydrate.itp for CH4 guests"


# ══════════════════════════════════════════════════════════════════════════════
# Custom molecule-only (Interface→Custom, no Solute/Ion steps)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
class TestCustomMoleculeGmxValidation:
    """Validate custom molecule-only export passes gmx grompp.

    Tests Interface→Custom export (no Solute/Ion steps).
    """

    @pytest.fixture(autouse=True)
    def _build_custom(self, interface_slab):
        custom = _insert_custom_molecules(interface_slab, n_molecules=3)
        self.custom = custom

    def test_gmx_grompp_succeeds(self, gmx_workspace):
        gro_path = str(gmx_workspace / "custom.gro")
        top_path = str(gmx_workspace / "custom.top")
        write_custom_molecule_gro_file(self.custom, gro_path)
        write_custom_molecule_top_file(self.custom, top_path)
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")
        _stage_itp_files(top_path, gmx_workspace)
        assert_itp_completeness(top_path, gmx_workspace)
        exit_code, stderr = run_gmx_grompp(
            gmx_workspace, gro_file="custom.gro", top_file="custom.top"
        )
        assert exit_code == 0, f"gmx grompp failed for custom-only:\n{stderr[-500:]}"
        molecules = parse_top_molecules(top_path)
        assert "SOL" in molecules

        # ── Ported deep asserts (48.3-19: tests/test_e2e_custom_export.py
        # TestCustomMoleculeExport) ──
        # test_gro_sol_before_custom_residues: SOL before the custom molecule
        # residue with no interleaving; the .gro residue IS the ITP
        # moleculetype name "etoh" (48.3-02 D1), matching [molecules] strictly
        mol_name = self.custom.moleculetype_name
        _assert_residue_ordering(gro_path, ["SOL", mol_name])
        # test_gro_atom_count_matches_header + test_atom_conservation:
        # header == molecule_index arithmetic (ice 3→4 expansion, water as-is)
        # + custom_molecule_atom_count
        _assert_gro_header_matches_lines(gro_path)
        header_count = parse_gro_atom_count(gro_path)
        sol_atoms = sum(
            4 if m.mol_type == "ice" else m.count
            for m in self.custom.molecule_index if m.mol_type in ("ice", "water")
        )
        expected = sol_atoms + self.custom.custom_molecule_atom_count
        assert header_count == expected, (
            f"Expected {expected} atoms (sol={sol_atoms} + "
            f"custom={self.custom.custom_molecule_atom_count}), got {header_count}"
        )
        # test_top_molecules_section: SOL == ice+water index entries and the
        # custom molecule count under the ITP moleculetype name
        sol_count = sum(
            1 for m in self.custom.molecule_index if m.mol_type in ("ice", "water")
        )
        assert molecules["SOL"] == sol_count, (
            f"Expected SOL count {sol_count}, got {molecules['SOL']}"
        )
        assert molecules[mol_name] == self.custom.custom_molecule_count, (
            f"Expected {mol_name} count {self.custom.custom_molecule_count}, "
            f"got {molecules[mol_name]}"
        )
        # test_top_includes_tip4p_ice_and_custom_itp: tip4p-ice.itp + the
        # custom ITP under its ORIGINAL filename
        includes = parse_top_includes(top_path)
        assert "tip4p-ice.itp" in includes, "Should include tip4p-ice.itp"
        custom_itp_name = self.custom.itp_path.name
        assert custom_itp_name in includes, (
            f"Should include {custom_itp_name}, got {includes}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Solute-only (Interface→Solute, no Ion step)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
class TestSoluteGmxValidation:
    """Validate solute-only export passes gmx grompp.

    Tests Interface→Solute export (no Ion step).
    Uses CH4 solute (5 atoms, simpler than THF).
    """

    @pytest.fixture(autouse=True)
    def _build_solute(self, interface_slab):
        solute = _insert_solutes(interface_slab, solute_type='CH4', concentration=0.3)
        self.solute = solute

    def test_gmx_grompp_succeeds(self, gmx_workspace):
        gro_path = str(gmx_workspace / "solute.gro")
        top_path = str(gmx_workspace / "solute.top")
        write_solute_gro_file(self.solute, gro_path)
        write_solute_top_file(self.solute, top_path)
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")
        _stage_itp_files(top_path, gmx_workspace)
        assert_itp_completeness(top_path, gmx_workspace)
        exit_code, stderr = run_gmx_grompp(
            gmx_workspace, gro_file="solute.gro", top_file="solute.top"
        )
        assert exit_code == 0, f"gmx grompp failed for solute-only:\n{stderr[-500:]}"
        molecules = parse_top_molecules(top_path)
        assert "SOL" in molecules

        # ── Ported deep asserts (48.3-19: tests/test_e2e_solute_export.py
        # TestSoluteFromInterface) ──
        # test_gro_sol_before_solute_residues: SOL before CH4_L, no interleaving
        # (CH4_L = registry.get_gromacs_name("liquid_CH4"), exactly 5 chars)
        _assert_residue_ordering(gro_path, ["SOL", "CH4_L"])
        # test_gro_atom_count_matches_header + test_atom_conservation:
        # header == ice*4 + water*4 + n_molecules*5 (CH4 = 5 atoms per molecule).
        # water_nmolecules comes from the SOLUTE's interface_structure because
        # SoluteInserter removes overlapping water molecules; the writer uses
        # ice_nmolecules/water_nmolecules fallback when molecule_index is empty.
        _assert_gro_header_matches_lines(gro_path)
        header_count = parse_gro_atom_count(gro_path)
        solute_iface = self.solute.interface_structure
        expected = (
            solute_iface.ice_nmolecules * 4
            + solute_iface.water_nmolecules * 4
            + self.solute.n_molecules * 5
        )
        assert header_count == expected, (
            f"Expected {expected} atoms "
            f"(ice={solute_iface.ice_nmolecules}*4 + "
            f"water={solute_iface.water_nmolecules}*4 + "
            f"solute={self.solute.n_molecules}*5), got {header_count}"
        )
        # test_top_molecules_section: SOL == ice+water, CH4_L == n_molecules
        expected_sol = solute_iface.ice_nmolecules + solute_iface.water_nmolecules
        assert molecules["SOL"] == expected_sol, (
            f"Expected SOL count {expected_sol}, got {molecules['SOL']}"
        )
        assert molecules["CH4_L"] == self.solute.n_molecules, (
            f"Expected CH4_L count {self.solute.n_molecules}, got {molecules['CH4_L']}"
        )
        # test_top_includes_tip4p_ice_and_solute_itp: tip4p-ice.itp +
        # ch4_liquid.itp
        includes = parse_top_includes(top_path)
        assert "tip4p-ice.itp" in includes, "Should include tip4p-ice.itp"
        assert "ch4_liquid.itp" in includes, (
            f"Should include ch4_liquid.itp, got {includes}"
        )
        # test_solute_positions_pbc_wrapped (regression B NEW-01/11)
        _assert_solute_positions_pbc_wrapped(gro_path)

    def test_solute_from_custom_grompp(self, interface_slab, gmx_workspace):
        """Interface→Custom→Solute(CH4) via write_solute_* passes gmx grompp.

        48.3-19 NEW focused chain: the 7 writer-file tests of
        tests/test_e2e_solute_export.py::TestSoluteFromCustom (deleted by
        48.3-19) were the ONLY coverage of write_solute_gro_file /
        write_solute_top_file on a CustomMoleculeStructure source — their deep
        asserts are ported below (provenance comments name the source test).
        """
        custom = _insert_custom_molecules(interface_slab, n_molecules=3)
        solute = _insert_solutes(custom, solute_type='CH4', concentration=0.3)

        gro_path = str(gmx_workspace / "solute_custom.gro")
        top_path = str(gmx_workspace / "solute_custom.top")
        write_solute_gro_file(solute, gro_path)
        write_solute_top_file(solute, top_path)
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")
        _stage_itp_files(top_path, gmx_workspace)
        assert_itp_completeness(top_path, gmx_workspace)
        exit_code, stderr = run_gmx_grompp(
            gmx_workspace, gro_file="solute_custom.gro", top_file="solute_custom.top"
        )
        assert exit_code == 0, f"gmx grompp failed for solute-from-custom:\n{stderr[-500:]}"

        # test_gro_sol_before_custom_before_solute: SOL → etoh → CH4_L, no
        # interleaving. Custom .gro residue IS the ITP moleculetype name "etoh"
        # (48.3-02 D1), matching TOP [molecules] strictly.
        mol_name = custom.moleculetype_name
        _assert_residue_ordering(gro_path, ["SOL", mol_name, "CH4_L"])

        # test_gro_atom_count_matches_header + test_atom_conservation:
        # SOL atoms (molecule_index-aware, ice 3→4 expansion) + custom atoms
        # + solute molecules * 5 (CH4)
        _assert_gro_header_matches_lines(gro_path)
        header_count = parse_gro_atom_count(gro_path)
        solute_iface = solute.interface_structure
        if solute_iface.molecule_index:
            sol_atoms = sum(
                4 if m.mol_type == "ice" else m.count
                for m in solute_iface.molecule_index
                if m.mol_type in ("ice", "water")
            )
            sol_mols = sum(
                1 for m in solute_iface.molecule_index
                if m.mol_type in ("ice", "water")
            )
        else:
            sol_atoms = (
                solute_iface.ice_nmolecules * 4 + solute_iface.water_nmolecules * 4
            )
            sol_mols = solute_iface.ice_nmolecules + solute_iface.water_nmolecules
        expected = (
            sol_atoms + solute.custom_molecule_atom_count + solute.n_molecules * 5
        )
        assert header_count == expected, (
            f"Expected {expected} atoms (SOL={sol_atoms} + "
            f"custom={solute.custom_molecule_atom_count} + "
            f"solute={solute.n_molecules}*5), got {header_count}"
        )

        # test_top_molecules_section: SOL, etoh, CH4_L count parity
        molecules = parse_top_molecules(top_path)
        assert molecules["SOL"] == sol_mols, (
            f"Expected SOL count {sol_mols}, got {molecules['SOL']}"
        )
        assert molecules[mol_name] == solute.custom_molecule_count, (
            f"Expected {mol_name} count {solute.custom_molecule_count}, "
            f"got {molecules[mol_name]}"
        )
        assert molecules["CH4_L"] == solute.n_molecules, (
            f"Expected CH4_L count {solute.n_molecules}, got {molecules['CH4_L']}"
        )

        # test_top_includes_all_itps: tip4p-ice.itp, custom ITP (ORIGINAL
        # filename), ch4_liquid.itp — IN ORDER (tip4p-ice < custom < solute)
        includes = parse_top_includes(top_path)
        assert "tip4p-ice.itp" in includes, "Should include tip4p-ice.itp"
        custom_itp_name = Path(solute.custom_itp_path).name
        assert custom_itp_name in includes, (
            f"Should include {custom_itp_name}, got {includes}"
        )
        assert "ch4_liquid.itp" in includes, (
            f"Should include ch4_liquid.itp, got {includes}"
        )
        tip4p_idx = includes.index("tip4p-ice.itp")
        custom_idx = includes.index(custom_itp_name)
        solute_idx = includes.index("ch4_liquid.itp")
        assert tip4p_idx < custom_idx < solute_idx, (
            f"ITP ordering: tip4p-ice({tip4p_idx}) < custom({custom_idx}) "
            f"< solute({solute_idx})"
        )

        # test_custom_molecule_count_preserved: custom count survives solute
        # insertion
        assert solute.custom_molecule_count == 3, (
            f"Expected custom_molecule_count=3, got {solute.custom_molecule_count}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Cross-chain invariants (48.3-15: ported from tests/test_e2e_cross_chain_invariants.py)
# ══════════════════════════════════════════════════════════════════════════════


def _assert_cross_chain_invariants(chains):
    """Cross-chain monotonicity + preservation invariants over exported chain TOPs.

    Ported from tests/test_e2e_cross_chain_invariants.py (deleted by 48.3-15):
    1. test_itp_count_increases_with_chain_depth: F5(2) < F6(3) < F1(4) ITP counts
    2. test_molecule_type_count_increases_with_chain_depth: F5(3) < F6(4) < F1(5)
    3. test_base_atom_count_preserved_across_chains: ICE molecule count identical
       across chains built from the SAME interface (total SOL differs — ion
       replacement targets liquid water — but ICE is the crystalline invariant
       no pipeline step modifies)
    4. test_hydrate_chain_adds_guest_itp: F3 includes ch4_hydrate.itp, F5 does not

    Args:
        chains: dict name -> {'top_path': str, 'ion': IonStructure} with keys
            'f5', 'f6', 'f1', 'f3'.
    """
    includes = {name: parse_top_includes(c["top_path"]) for name, c in chains.items()}
    molecules = {name: parse_top_molecules(c["top_path"]) for name, c in chains.items()}

    # 1. ITP count increases with chain depth
    f5_itps, f6_itps, f1_itps = (
        len(includes["f5"]),
        len(includes["f6"]),
        len(includes["f1"]),
    )
    assert f5_itps == 2, f"F5 should have 2 ITPs, got {f5_itps}: {includes['f5']}"
    assert f6_itps == 3, f"F6 should have 3 ITPs, got {f6_itps}: {includes['f6']}"
    assert f1_itps == 4, f"F1 should have 4 ITPs, got {f1_itps}: {includes['f1']}"
    assert f5_itps < f6_itps < f1_itps, (
        f"ITP count should increase with chain depth: "
        f"F5={f5_itps} < F6={f6_itps} < F1={f1_itps}"
    )

    # 2. Molecule-type count increases with chain depth
    f5_types, f6_types, f1_types = (
        len(molecules["f5"]),
        len(molecules["f6"]),
        len(molecules["f1"]),
    )
    assert f5_types == 3, (
        f"F5 should have 3 molecule types (SOL,NA,CL), got {f5_types}: {molecules['f5']}"
    )
    assert f6_types == 4, (
        f"F6 should have 4 molecule types (SOL,CH4_L,NA,CL), got {f6_types}: "
        f"{molecules['f6']}"
    )
    assert f1_types == 5, (
        f"F1 should have 5 molecule types (SOL,etoh,CH4_L,NA,CL), got {f1_types}: "
        f"{molecules['f1']}"
    )
    assert f5_types < f6_types < f1_types, (
        f"Molecule type count should increase with chain depth: "
        f"F5={f5_types} < F6={f6_types} < F1={f1_types}"
    )

    # 3. ICE molecule count preserved across chains from the same interface
    for name in ("f5", "f1"):
        sol = molecules[name].get("SOL", 0)
        ice_water = sum(
            1 for m in chains[name]["ion"].molecule_index
            if m.mol_type in ("ice", "water")
        )
        assert sol == ice_water, (
            f"{name.upper()} TOP SOL count ({sol}) should match ice+water "
            f"molecule_index count ({ice_water})"
        )
        assert sol > 0, f"{name.upper()} should have SOL molecules"
    f5_ice = sum(
        1 for m in chains["f5"]["ion"].molecule_index if m.mol_type == "ice"
    )
    f1_ice = sum(
        1 for m in chains["f1"]["ion"].molecule_index if m.mol_type == "ice"
    )
    assert f5_ice == f1_ice, (
        f"Ice molecule count should be preserved across chains from same interface: "
        f"F5={f5_ice}, F1={f1_ice}"
    )

    # 4. Hydrate chain adds the guest ITP; non-hydrate chains lack it
    assert "ch4_hydrate.itp" in includes["f3"], (
        f"F3 (hydrate chain) should include ch4_hydrate.itp, got {includes['f3']}"
    )
    assert "ch4_hydrate.itp" not in includes["f5"], (
        f"F5 (no hydrate) should NOT include ch4_hydrate.itp, got {includes['f5']}"
    )


class TestCrossChainInvariants:
    """Cross-chain invariants over full F-chain outputs (48.3-15 port).

    The 4 monotonicity/preservation asserts from
    tests/test_e2e_cross_chain_invariants.py (deleted by 48.3-15) compare ACROSS
    chains — they have no single-chain home — so they run in this focused test
    via _assert_cross_chain_invariants. Pure file-parse asserts (no grompp): this
    class is intentionally NOT @gmx_skipif-gated so the ported coverage still runs
    on machines without GROMACS (the same chain shapes are grompp-validated by
    the per-chain classes above).
    """

    def test_cross_chain_invariants(self, interface_slab, tmp_path):
        """F5(2)<F6(3)<F1(4) ITPs, F5(3)<F6(4)<F1(5) types, ICE preserved, F3 guest ITP."""
        # F5: Interface→Ion (minimal chain)
        f5 = _insert_ions(interface_slab, concentration=0.15)
        # F6: Interface→Solute(CH4)→Ion
        solute6 = _insert_solutes(interface_slab, solute_type='CH4', concentration=0.3)
        f6 = _insert_ions_from_solute(solute6, concentration=0.15)
        # F1: Interface→Custom→Solute(CH4)→Ion
        custom = _insert_custom_molecules(interface_slab, n_molecules=3)
        solute1 = _insert_solutes(custom, solute_type='CH4', concentration=0.3)
        f1 = _insert_ions_from_solute(solute1, concentration=0.15)
        # F3: Hydrate(sI-CH4)→Interface(slab)→Solute(CH4)→Ion (inline hydrate)
        hydrate = _hydrate_sI_ch4_candidate()
        interface3 = _make_slab_interface(hydrate)
        solute3 = _insert_solutes(interface3, solute_type='CH4', concentration=0.3)
        f3 = _insert_ions_from_solute(solute3, concentration=0.15)

        chains = {}
        for name, ion in (("f5", f5), ("f6", f6), ("f1", f1), ("f3", f3)):
            write_ion_itp(tmp_path / f"{name}_ion.itp", ion.na_count, ion.cl_count)
            top_path = str(tmp_path / f"{name}.top")
            write_ion_top_file(ion, top_path)
            chains[name] = {"top_path": top_path, "ion": ion}

        _assert_cross_chain_invariants(chains)
