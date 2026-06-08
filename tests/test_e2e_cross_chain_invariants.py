"""End-to-end tests for cross-chain structural invariants.

Validates structural invariants ACROSS chains by comparing properties like
ITP count, molecule type count, and base atom count across different chain
depths. These tests catch data loss across pipeline steps.

Class TestCrossChainInvariants:
1. test_itp_count_increases_with_chain_depth — F5(2) < F6(3) < F1(4) ITP counts
2. test_base_atom_count_preserved_across_chains — F5 and F1 from same interface_slab, SOL count identical
3. test_molecule_type_count_increases_with_chain_depth — F5(3) < F6(4) < F1(5) molecule types
4. test_hydrate_chain_adds_guest_itp — F3 has ch4_hydrate.itp, F5 does not

Implementation: Build chains inline, use same interface_slab fixture for F5/F6/F1 comparisons.
F3 uses inline hydrate candidate generation: _hydrate_sI_ch4_candidate() + _make_slab_interface()

CRITICAL NOTES from prior plans:
- Custom molecule GRO residue name is "MOL", TOP [molecules] uses ITP name "etoh"
- F6/F7 use _insert_ions_from_solute() with BUG I5 workaround
- THF has 13 atoms, CH4 has 5 atoms, ethanol has 9 atoms
- ion.itp must be generated to tmp_path before write_ion_top_file
- Use sys.path.insert(0, ...) for e2e_export_helpers import (established pattern)
- SOL counts should come from ion.molecule_index (not original interface counts)
"""

import sys
import pytest
import numpy as np
from pathlib import Path

# Add tests/ directory to sys.path for e2e_export_helpers import
# (avoids conftest.py import which is unreliable in pytest)
sys.path.insert(0, str(Path(__file__).parent))

from quickice.output.gromacs_writer import (
    write_ion_gro_file,
    write_ion_top_file,
)

from quickice.structure_generation.gromacs_ion_export import write_ion_itp
from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry

# Import parsing helpers and chain-building helpers from the shared module
from e2e_export_helpers import (
    parse_gro_residue_names,
    parse_gro_atom_count,
    parse_top_molecules,
    parse_top_includes,
    check_itp_has_moleculetype,
    assert_gro_residue_ordering,
    _insert_ions,
    _insert_ions_from_solute,
    _insert_custom_molecules,
    _insert_solutes,
    _hydrate_sI_ch4_candidate,
    _make_slab_interface,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_data_dir() -> Path:
    """Get the path to quickice/data/ directory containing bundled ITP files."""
    import quickice
    return Path(quickice.__file__).parent / "data"


def _build_and_export_chain(interface, chain_builder, tmp_path, chain_name):
    """Build a chain, export GRO/TOP, and return parsed results.

    Args:
        interface: Source interface structure
        chain_builder: Callable(ion_structure) -> ion
        tmp_path: Temporary directory for output files
        chain_name: Name prefix for output files

    Returns:
        Dict with 'molecules', 'includes', 'ion' keys
    """
    ion = chain_builder(interface)

    # Generate ion.itp before writing top file
    write_ion_itp(tmp_path / f"{chain_name}_ion.itp", ion.na_count, ion.cl_count)

    # Export TOP file
    top_path = str(tmp_path / f"{chain_name}.top")
    write_ion_top_file(ion, top_path)

    return {
        'molecules': parse_top_molecules(top_path),
        'includes': parse_top_includes(top_path),
        'ion': ion,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Cross-chain invariant tests
# ══════════════════════════════════════════════════════════════════════════════


class TestCrossChainInvariants:
    """Tests for structural invariants across different chain depths.

    These tests compare properties across chains to catch data loss.
    They verify that deeper chains accumulate more ITP files and molecule
    types without losing base (SOL) atom counts.
    """

    def _build_f5(self, interface_slab):
        """Build F5: Interface→Ion (minimal chain)."""
        return _insert_ions(interface_slab, concentration=0.15)

    def _build_f6(self, interface_slab):
        """Build F6: Interface→Solute(CH4)→Ion."""
        registry = MoleculetypeRegistry()
        registry.register_liquid_solute("CH4")
        solute = _insert_solutes(interface_slab, solute_type='CH4', concentration=0.3)
        return _insert_ions_from_solute(solute, concentration=0.15)

    def _build_f1(self, interface_slab):
        """Build F1: Interface→Custom→Solute(CH4,Custom source)→Ion."""
        custom = _insert_custom_molecules(interface_slab, n_molecules=3)
        registry = MoleculetypeRegistry()
        registry.register_liquid_solute("CH4")
        solute = _insert_solutes(custom, solute_type='CH4', concentration=0.3)
        return _insert_ions_from_solute(solute, concentration=0.15)

    def _build_f3(self):
        """Build F3: Hydrate→Interface(slab)→Solute(CH4)→Ion.

        Uses inline hydrate candidate generation, not conftest fixtures.
        """
        hydrate_candidate = _hydrate_sI_ch4_candidate()
        interface = _make_slab_interface(hydrate_candidate)
        registry = MoleculetypeRegistry()
        registry.register_hydrate_guest("CH4")
        registry.register_liquid_solute("CH4")
        solute = _insert_solutes(interface, solute_type='CH4', concentration=0.3)
        return _insert_ions_from_solute(solute, concentration=0.15)

    def test_itp_count_increases_with_chain_depth(self, interface_slab, tmp_path):
        """Deeper chains have more ITP files than shallower chains.

        F5 (Interface→Ion): 2 ITPs (tip4p-ice.itp + ion.itp)
        F6 (Interface→Solute→Ion): 3 ITPs (tip4p-ice.itp + ch4_liquid.itp + ion.itp)
        F1 (Interface→Custom→Solute→Ion): 4 ITPs (tip4p-ice.itp + etoh.itp + ch4_liquid.itp + ion.itp)

        Assert: len(f5_includes) < len(f6_includes) < len(f1_includes)
        """
        # Build and export F5
        f5_result = _build_and_export_chain(
            interface_slab, self._build_f5, tmp_path, "f5"
        )

        # Build and export F6
        f6_result = _build_and_export_chain(
            interface_slab, self._build_f6, tmp_path, "f6"
        )

        # Build and export F1
        f1_result = _build_and_export_chain(
            interface_slab, self._build_f1, tmp_path, "f1"
        )

        f5_count = len(f5_result['includes'])
        f6_count = len(f6_result['includes'])
        f1_count = len(f1_result['includes'])

        assert f5_count == 2, f"F5 should have 2 ITPs, got {f5_count}: {f5_result['includes']}"
        assert f6_count == 3, f"F6 should have 3 ITPs, got {f6_count}: {f6_result['includes']}"
        assert f1_count == 4, f"F1 should have 4 ITPs, got {f1_count}: {f1_result['includes']}"

        assert f5_count < f6_count < f1_count, (
            f"ITP count should increase with chain depth: "
            f"F5={f5_count} < F6={f6_count} < F1={f1_count}"
        )

    def test_base_atom_count_preserved_across_chains(self, interface_slab, tmp_path):
        """Ice molecule count is preserved across chains from same interface.

        Build F5 and F1 from the SAME interface_slab fixture.
        Ice molecules (crystalline region) are never replaced by ions, so
        the ice count should be identical across all chain depths.

        NOTE: The total SOL count (ice+water) differs across chains because
        ion replacement targets water molecules in the liquid region, and
        different chains replace different numbers of water molecules.
        The ICE count is the true invariant — it's the crystalline base
        that no pipeline step modifies.
        """
        # Build and export F5
        f5_result = _build_and_export_chain(
            interface_slab, self._build_f5, tmp_path, "f5_base"
        )

        # Build and export F1
        f1_result = _build_and_export_chain(
            interface_slab, self._build_f1, tmp_path, "f1_base"
        )

        f5_sol = f5_result['molecules'].get("SOL", 0)
        f1_sol = f1_result['molecules'].get("SOL", 0)

        # SOL counts come from ion.molecule_index (some water replaced by ions)
        f5_ice_water = sum(
            1 for m in f5_result['ion'].molecule_index
            if m.mol_type in ("ice", "water")
        )
        f1_ice_water = sum(
            1 for m in f1_result['ion'].molecule_index
            if m.mol_type in ("ice", "water")
        )

        # Verify TOP SOL count matches molecule_index ice+water count
        assert f5_sol == f5_ice_water, (
            f"F5 TOP SOL count ({f5_sol}) should match ice+water molecule_index count ({f5_ice_water})"
        )
        assert f1_sol == f1_ice_water, (
            f"F1 TOP SOL count ({f1_sol}) should match ice+water molecule_index count ({f1_ice_water})"
        )

        # ICE molecule count is the true invariant — never replaced by ions
        f5_ice = sum(
            1 for m in f5_result['ion'].molecule_index
            if m.mol_type == "ice"
        )
        f1_ice = sum(
            1 for m in f1_result['ion'].molecule_index
            if m.mol_type == "ice"
        )

        assert f5_ice == f1_ice, (
            f"Ice molecule count should be preserved across chains from same interface: "
            f"F5={f5_ice}, F1={f1_ice}"
        )

        # Verify both chains have a reasonable number of SOL molecules
        # (total SOL count differs due to different ion replacement amounts)
        assert f5_sol > 0, "F5 should have SOL molecules"
        assert f1_sol > 0, "F1 should have SOL molecules"

    def test_molecule_type_count_increases_with_chain_depth(self, interface_slab, tmp_path):
        """Number of distinct molecule types increases with chain depth.

        F5: 3 types (SOL, NA, CL)
        F6: 4 types (SOL, CH4_L, NA, CL)
        F1: 5 types (SOL, MOL, CH4_L, NA, CL)

        Assert: len(f5_molecules) < len(f6_molecules) < len(f1_molecules)
        """
        # Build and export F5
        f5_result = _build_and_export_chain(
            interface_slab, self._build_f5, tmp_path, "f5_types"
        )

        # Build and export F6
        f6_result = _build_and_export_chain(
            interface_slab, self._build_f6, tmp_path, "f6_types"
        )

        # Build and export F1
        f1_result = _build_and_export_chain(
            interface_slab, self._build_f1, tmp_path, "f1_types"
        )

        f5_types = len(f5_result['molecules'])
        f6_types = len(f6_result['molecules'])
        f1_types = len(f1_result['molecules'])

        assert f5_types == 3, (
            f"F5 should have 3 molecule types (SOL,NA,CL), got {f5_types}: {f5_result['molecules']}"
        )
        assert f6_types == 4, (
            f"F6 should have 4 molecule types (SOL,CH4_L,NA,CL), got {f6_types}: {f6_result['molecules']}"
        )
        assert f1_types == 5, (
            f"F1 should have 5 molecule types (SOL,MOL,CH4_L,NA,CL), got {f1_types}: {f1_result['molecules']}"
        )

        assert f5_types < f6_types < f1_types, (
            f"Molecule type count should increase with chain depth: "
            f"F5={f5_types} < F6={f6_types} < F1={f1_types}"
        )

    def test_hydrate_chain_adds_guest_itp(self, interface_slab, tmp_path):
        """Hydrate chain (F3) adds ch4_hydrate.itp which non-hydrate chain (F5) lacks.

        F3 (Hydrate→Interface→Solute→Ion): includes ch4_hydrate.itp
        F5 (Interface→Ion): does NOT include ch4_hydrate.itp

        Assert: "ch4_hydrate.itp" in f3_includes
                "ch4_hydrate.itp" not in f5_includes
        """
        # Build and export F5 (from interface_slab fixture)
        f5_ion = self._build_f5(interface_slab)
        write_ion_itp(tmp_path / "f5_hyd_ion.itp", f5_ion.na_count, f5_ion.cl_count)
        f5_top_path = str(tmp_path / "f5_hyd.top")
        write_ion_top_file(f5_ion, f5_top_path)

        # Build F3 (inline hydrate generation)
        f3_ion = self._build_f3()
        write_ion_itp(tmp_path / "f3_hyd_ion.itp", f3_ion.na_count, f3_ion.cl_count)
        f3_top_path = str(tmp_path / "f3_hyd.top")
        write_ion_top_file(f3_ion, f3_top_path)

        f5_includes = parse_top_includes(f5_top_path)
        f3_includes = parse_top_includes(f3_top_path)

        assert "ch4_hydrate.itp" in f3_includes, (
            f"F3 (hydrate chain) should include ch4_hydrate.itp, got {f3_includes}"
        )
        assert "ch4_hydrate.itp" not in f5_includes, (
            f"F5 (no hydrate) should NOT include ch4_hydrate.itp, got {f5_includes}"
        )
