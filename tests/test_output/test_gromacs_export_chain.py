"""E2E chain tests proving the incremental export pipeline works.

Tests the FULL chain: Interface → Custom Molecule → Solute → Ion.
Each level carries forward data from the previous level, and the export
must produce the correct cumulative set of files.

Individual exporter tests (Plans 02-07) prove each exporter works in
isolation. These tests prove they work TOGETHER — that IonStructure
correctly carries forward guest, solute, and custom molecule data, and
that the ion exporter produces ALL ITP files from all previous levels.

Chain structure:
    Interface (ice + water + guests)
        → Custom Molecule (interface + custom molecules, guests carried forward)
        → Solute (interface + solutes, guests + custom carried forward)
        → Ion (all data carried forward: guests + solutes + custom)

File accumulation at each level:
    Interface:   .gro, .top, tip4p-ice.itp, {guest}_hydrate.itp
    Custom:      + etoh.itp (custom), guests carried from interface
    Solute:      + {solute}_liquid.itp, guests from interface, custom from custom tab
    Ion:         + ion.itp (GENERATED), ALL previous ITPs carried forward

Test methods:
    1. test_interface_to_custom_chain
    2. test_interface_to_solute_chain
    3. test_full_chain_interface_custom_solute_ion
    4. test_chain_minimal_no_guests_no_solute_no_custom

Fixtures from conftest.py:
    - simple_interface: 2 ice + 2 water, no guests
    - interface_with_ch4_guests: extends simple_interface with CH4 guests
    - mock_save_dialog: factory -> (save_path, dialog_patch, mb_patch)
"""

from pathlib import Path

import numpy as np
import pytest

from quickice.gui.export import (
    InterfaceGROMACSExporter,
    CustomMoleculeGROMACSExporter,
    SoluteGROMACSExporter,
    IonGROMACSExporter,
)
from quickice.structure_generation.types import (
    InterfaceStructure,
    CustomMoleculeStructure,
    SoluteStructure,
    IonStructure,
    MoleculeIndex,
)
from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry


class TestFullExportChain:
    """End-to-end tests proving the incremental pipeline works across tabs.

    Each test builds structures following the chain dependency
    (Interface → Custom → Solute → Ion) and verifies that each
    export level produces ALL files from previous levels PLUS its
    own additions.
    """

    # ------------------------------------------------------------------
    # Test 1: Interface → Custom Molecule chain
    # ------------------------------------------------------------------

    def test_interface_to_custom_chain(
        self, interface_with_ch4_guests, mock_save_dialog
    ):
        """Interface export produces base files; custom adds etoh.itp and carries guest ITP.

        Step 1: Export InterfaceStructure (with CH4 guests) → produces
            .gro, .top, tip4p-ice.itp, ch4_hydrate.itp

        Step 2: Build CustomMoleculeStructure using the SAME InterfaceStructure
            (stored as custom.interface_structure) and export → produces
            .gro, .top, tip4p-ice.itp, etoh.itp, ch4_hydrate.itp

        The custom export has ALL files from interface export PLUS etoh.itp.
        The ch4_hydrate.itp is carried forward because the CustomMoleculeStructure
        has guest_atom_count > 0 and guest entries in molecule_index.
        """
        iface = interface_with_ch4_guests

        # --- Step 1: Export interface ---
        iface_save, iface_dialog, iface_mb = mock_save_dialog("iface_chain.gro")
        iface_exporter = InterfaceGROMACSExporter(parent_widget=None)

        with iface_dialog, iface_mb:
            result = iface_exporter.export_interface_gromacs(iface)

        assert result is True
        iface_dir = Path(iface_save).parent
        # Interface produces these files
        assert (iface_dir / "iface_chain.gro").exists()
        assert (iface_dir / "iface_chain.top").exists()
        assert (iface_dir / "tip4p-ice.itp").exists()
        assert (iface_dir / "ch4_hydrate.itp").exists()

        # --- Step 2: Build CustomMoleculeStructure with same interface ---
        # Atom layout: ice (6) + water (8) + guest (5 CH4) + custom (9 ethanol)
        # = 28 total atoms
        custom_positions = np.zeros((9, 3))
        for i in range(9):
            custom_positions[i] = [1.8 + 0.02 * i, 1.0, 2.5]

        positions = np.vstack([iface.positions, custom_positions])

        atom_names = (
            iface.atom_names
            + ["H", "C", "H", "H", "C", "H", "H", "O", "H"]  # ethanol from etoh.itp
        )

        molecule_index = iface.molecule_index + [
            MoleculeIndex(19, 9, "custom"),  # ethanol starts at position 19
        ]

        itp_path = Path("quickice/data/custom/etoh.itp")

        custom = CustomMoleculeStructure(
            positions=positions,
            atom_names=atom_names,
            cell=iface.cell.copy(),
            molecule_index=molecule_index,
            ice_atom_count=iface.ice_atom_count,
            water_atom_count=iface.water_atom_count,
            custom_molecule_atom_count=9,
            guest_atom_count=iface.guest_atom_count,  # guests carried forward
            moleculetype_name="ETOH",
            itp_path=itp_path,
            custom_molecule_count=1,
            interface_structure=iface,
        )

        # --- Step 2a: Export custom ---
        custom_save, custom_dialog, custom_mb = mock_save_dialog("custom_chain.gro")
        custom_exporter = CustomMoleculeGROMACSExporter(parent_widget=None)

        with custom_dialog, custom_mb:
            result = custom_exporter.export_custom_molecule_gromacs(custom)

        assert result is True
        custom_dir = Path(custom_save).parent
        # Custom produces ALL interface files PLUS etoh.itp
        assert (custom_dir / "custom_chain.gro").exists()
        assert (custom_dir / "custom_chain.top").exists()
        assert (custom_dir / "tip4p-ice.itp").exists()
        assert (custom_dir / "etoh.itp").exists()
        # Guest ITP carried forward from interface
        assert (custom_dir / "ch4_hydrate.itp").exists()

    # ------------------------------------------------------------------
    # Test 2: Interface → Solute chain
    # ------------------------------------------------------------------

    def test_interface_to_solute_chain(
        self, interface_with_ch4_guests, mock_save_dialog
    ):
        """Solute export produces both liquid and hydrate ITPs for the same molecule type.

        Step 1: Build InterfaceStructure with CH4 guests → export

        Step 2: Build SoluteStructure using the interface (CH4 solute) → export
            Produces: .gro, .top, tip4p-ice.itp, ch4_liquid.itp, ch4_hydrate.itp

        The solute export has BOTH ch4_liquid.itp (for solutes in liquid phase)
        AND ch4_hydrate.itp (for guests from interface in hydrate phase).
        """
        iface = interface_with_ch4_guests

        # Build SoluteStructure with CH4 solute, using the same interface
        # (which has CH4 guests)
        solute_positions = np.array([
            [2.0, 1.0, 2.5],
            [2.05, 1.02, 2.5],
            [1.98, 1.02, 2.5],
            [2.00, 1.05, 2.5],
            [2.00, 0.98, 2.5],
        ])

        solute_atom_names = ["C", "H", "H", "H", "H"]

        registry = MoleculetypeRegistry()
        registry.register_liquid_solute("CH4")

        solute = SoluteStructure(
            positions=solute_positions,
            atom_names=solute_atom_names,
            cell=iface.cell.copy(),
            solute_type="CH4",
            n_molecules=1,
            molecule_indices=[(0, 5)],
            registry=registry,
            interface_structure=iface,
        )

        # Export solute
        solute_save, solute_dialog, solute_mb = mock_save_dialog("solute_chain.gro")
        solute_exporter = SoluteGROMACSExporter(parent_widget=None)

        with solute_dialog, solute_mb:
            result = solute_exporter.export_solute_gromacs(solute)

        assert result is True
        solute_dir = Path(solute_save).parent
        # Solute produces: base + liquid + hydrate (from guests)
        assert (solute_dir / "solute_chain.gro").exists()
        assert (solute_dir / "solute_chain.top").exists()
        assert (solute_dir / "tip4p-ice.itp").exists()
        # Liquid solute ITP (CH4 in liquid phase)
        assert (solute_dir / "ch4_liquid.itp").exists()
        # Hydrate guest ITP (CH4 from interface, in hydrate cages)
        assert (solute_dir / "ch4_hydrate.itp").exists()

        # Verify .top file references both ITPs
        top_content = (solute_dir / "solute_chain.top").read_text()
        assert '#include "ch4_liquid.itp"' in top_content
        assert '#include "ch4_hydrate.itp"' in top_content

    # ------------------------------------------------------------------
    # Test 3: Full chain (Interface → Custom → Solute → Ion)
    # ------------------------------------------------------------------

    def test_full_chain_interface_custom_solute_ion(
        self, interface_with_ch4_guests, mock_save_dialog
    ):
        """THE main E2E test: full chain produces ALL cumulative ITP files.

        Builds the complete chain:
        1. InterfaceStructure with CH4 guests → export
        2. CustomMoleculeStructure (interface + custom) → export
        3. SoluteStructure (interface + solute + custom) → export
        4. IonStructure (all data carried forward) → export

        At each level, the cumulative file set grows:
        - Interface: tip4p-ice.itp, ch4_hydrate.itp
        - Custom: + etoh.itp
        - Solute: + ch4_liquid.itp
        - Ion: + ion.itp (GENERATED)

        Final IonStructure export should produce ALL ITP files:
        - tip4p-ice.itp (water, always)
        - ion.itp (generated by write_ion_itp)
        - ch4_hydrate.itp (from guests in interface)
        - ch4_liquid.itp (from solutes)
        - etoh.itp (from custom molecules)
        """
        iface = interface_with_ch4_guests

        # --- Level 1: Interface export ---
        iface_save, iface_dialog, iface_mb = mock_save_dialog("chain_iface.gro")
        iface_exporter = InterfaceGROMACSExporter(parent_widget=None)

        with iface_dialog, iface_mb:
            result = iface_exporter.export_interface_gromacs(iface)

        assert result is True
        iface_dir = Path(iface_save).parent
        # Interface produces: .gro, .top, tip4p-ice.itp, ch4_hydrate.itp
        assert (iface_dir / "chain_iface.gro").exists()
        assert (iface_dir / "chain_iface.top").exists()
        assert (iface_dir / "tip4p-ice.itp").exists()
        assert (iface_dir / "ch4_hydrate.itp").exists()
        # No solute or custom ITPs at this level
        assert not (iface_dir / "ch4_liquid.itp").exists()
        assert not (iface_dir / "etoh.itp").exists()
        assert not (iface_dir / "ion.itp").exists()

        # --- Level 2: Custom Molecule export ---
        custom_positions = np.zeros((9, 3))
        for i in range(9):
            custom_positions[i] = [1.8 + 0.02 * i, 1.0, 2.5]

        positions_custom = np.vstack([iface.positions, custom_positions])

        atom_names_custom = (
            iface.atom_names
            + ["H", "C", "H", "H", "C", "H", "H", "O", "H"]  # ethanol
        )

        molecule_index_custom = iface.molecule_index + [
            MoleculeIndex(19, 9, "custom"),
        ]

        custom = CustomMoleculeStructure(
            positions=positions_custom,
            atom_names=atom_names_custom,
            cell=iface.cell.copy(),
            molecule_index=molecule_index_custom,
            ice_atom_count=iface.ice_atom_count,
            water_atom_count=iface.water_atom_count,
            custom_molecule_atom_count=9,
            guest_atom_count=iface.guest_atom_count,
            moleculetype_name="ETOH",
            itp_path=Path("quickice/data/custom/etoh.itp"),
            custom_molecule_count=1,
            interface_structure=iface,
        )

        custom_save, custom_dialog, custom_mb = mock_save_dialog("chain_custom.gro")
        custom_exporter = CustomMoleculeGROMACSExporter(parent_widget=None)

        with custom_dialog, custom_mb:
            result = custom_exporter.export_custom_molecule_gromacs(custom)

        assert result is True
        custom_dir = Path(custom_save).parent
        # Custom produces: .gro, .top, tip4p-ice.itp, etoh.itp, ch4_hydrate.itp
        assert (custom_dir / "chain_custom.gro").exists()
        assert (custom_dir / "chain_custom.top").exists()
        assert (custom_dir / "tip4p-ice.itp").exists()
        assert (custom_dir / "etoh.itp").exists()
        assert (custom_dir / "ch4_hydrate.itp").exists()
        # No solute or ion ITPs at this level
        assert not (custom_dir / "ch4_liquid.itp").exists()
        assert not (custom_dir / "ion.itp").exists()

        # --- Level 3: Solute export (with custom molecules carried forward) ---
        solute_positions = np.array([
            [2.0, 1.0, 2.5],
            [2.05, 1.02, 2.5],
            [1.98, 1.02, 2.5],
            [2.00, 1.05, 2.5],
            [2.00, 0.98, 2.5],
        ])

        solute_atom_names = ["C", "H", "H", "H", "H"]

        registry = MoleculetypeRegistry()
        registry.register_liquid_solute("CH4")

        solute = SoluteStructure(
            positions=solute_positions,
            atom_names=solute_atom_names,
            cell=iface.cell.copy(),
            solute_type="CH4",
            n_molecules=1,
            molecule_indices=[(0, 5)],
            registry=registry,
            interface_structure=iface,
            # Custom molecules carried forward from custom tab
            custom_molecule_count=1,
            custom_molecule_positions=np.zeros((9, 3)),
            custom_molecule_moleculetype="ETOH",
            custom_itp_path=Path("quickice/data/custom/etoh.itp"),
        )

        solute_save, solute_dialog, solute_mb = mock_save_dialog("chain_solute.gro")
        solute_exporter = SoluteGROMACSExporter(parent_widget=None)

        with solute_dialog, solute_mb:
            result = solute_exporter.export_solute_gromacs(solute)

        assert result is True
        solute_dir = Path(solute_save).parent
        # Solute produces: .gro, .top, tip4p-ice.itp, ch4_liquid.itp,
        # ch4_hydrate.itp, etoh.itp
        assert (solute_dir / "chain_solute.gro").exists()
        assert (solute_dir / "chain_solute.top").exists()
        assert (solute_dir / "tip4p-ice.itp").exists()
        assert (solute_dir / "ch4_liquid.itp").exists()
        assert (solute_dir / "ch4_hydrate.itp").exists()
        assert (solute_dir / "etoh.itp").exists()
        # No ion ITP at this level
        assert not (solute_dir / "ion.itp").exists()

        # --- Level 4: Ion export (ALL data carried forward) ---
        # Build IonStructure with guests, solutes, and custom molecules
        # Main positions: 8 water + 1 NA + 1 CL + 5 guest CH4 = 15 atoms
        ion_positions = np.zeros((15, 3))
        # Water
        ion_positions[0:4] = np.array([
            [0.5, 0.5, 2.0], [0.55, 0.52, 2.0],
            [0.48, 0.52, 2.0], [0.50, 0.51, 2.0],
        ])
        ion_positions[4:8] = np.array([
            [1.0, 0.5, 2.0], [1.05, 0.52, 2.0],
            [0.98, 0.52, 2.0], [1.00, 0.51, 2.0],
        ])
        # Ions
        ion_positions[8] = [1.5, 1.0, 2.5]
        ion_positions[9] = [1.5, 1.0, 2.0]
        # Guest CH4 atoms (carried forward from interface)
        ion_positions[10:15] = np.array([
            [1.6, 1.0, 2.5],
            [1.65, 1.02, 2.5],
            [1.58, 1.02, 2.5],
            [1.60, 1.05, 2.5],
            [1.60, 0.98, 2.5],
        ])

        ion_atom_names = [
            "OW", "HW1", "HW2", "MW",  # water mol 1
            "OW", "HW1", "HW2", "MW",  # water mol 2
            "NA",                       # sodium
            "CL",                       # chloride
            "C", "H", "H", "H", "H",   # CH4 guest
        ]

        ion = IonStructure(
            positions=ion_positions,
            atom_names=ion_atom_names,
            cell=iface.cell.copy(),
            molecule_index=[
                MoleculeIndex(0, 4, "water"),
                MoleculeIndex(4, 4, "water"),
                MoleculeIndex(8, 1, "na"),
                MoleculeIndex(9, 1, "cl"),
                MoleculeIndex(10, 5, "guest"),
            ],
            na_count=1,
            cl_count=1,
            report="test",
            # Guest data (from interface)
            guest_nmolecules=1,
            guest_atom_count=5,
            # Solute data (from solute tab)
            solute_type="CH4",
            solute_positions=np.zeros((5, 3)),
            solute_atom_names=["C", "H", "H", "H", "H"],
            solute_n_molecules=1,
            solute_molecule_indices=[(0, 5)],
            solute_registry=registry,
            # Custom molecule data (from custom tab)
            custom_molecule_count=1,
            custom_molecule_atom_count=9,
            custom_molecule_positions=np.zeros((9, 3)),
            custom_molecule_atom_names=["H", "C", "H", "H", "C", "H", "H", "O", "H"],
            custom_molecule_moleculetype="ETOH",
            custom_itp_path=Path("quickice/data/custom/etoh.itp"),
        )

        ion_save, ion_dialog, ion_mb = mock_save_dialog("chain_ion.gro")
        ion_exporter = IonGROMACSExporter(parent_widget=None)

        with ion_dialog, ion_mb:
            result = ion_exporter.export_ion_gromacs(ion)

        assert result is True
        ion_dir = Path(ion_save).parent

        # === FINAL VERIFICATION: Ion export produces ALL cumulative files ===
        # Base files
        assert (ion_dir / "chain_ion.gro").exists()
        assert (ion_dir / "chain_ion.top").exists()

        # Water ITP (always present)
        assert (ion_dir / "tip4p-ice.itp").exists()

        # Ion ITP (GENERATED, not copied)
        assert (ion_dir / "ion.itp").exists()
        ion_itp_content = (ion_dir / "ion.itp").read_text()
        assert "[ moleculetype ]" in ion_itp_content
        assert "Madrid2019" in ion_itp_content

        # Guest ITP (from interface chain — ch4_hydrate.itp)
        assert (ion_dir / "ch4_hydrate.itp").exists()

        # Solute liquid ITP (from solute chain — ch4_liquid.itp)
        assert (ion_dir / "ch4_liquid.itp").exists()

        # Custom molecule ITP (from custom chain — etoh.itp)
        assert (ion_dir / "etoh.itp").exists()

        # Verify .top file references ALL ITPs
        top_content = (ion_dir / "chain_ion.top").read_text()
        assert '#include "tip4p-ice.itp"' in top_content
        assert '#include "ion.itp"' in top_content
        assert '#include "ch4_hydrate.itp"' in top_content
        assert '#include "ch4_liquid.itp"' in top_content
        assert '#include "etoh.itp"' in top_content

        # Verify custom ITP has atomtypes commented out
        custom_itp_content = (ion_dir / "etoh.itp").read_text()
        assert (
            "Modified for QuickIce" in custom_itp_content
            or "; [ atomtypes ]" in custom_itp_content
        )

    # ------------------------------------------------------------------
    # Test 4: Minimal chain (no guests, no solutes, no custom)
    # ------------------------------------------------------------------

    def test_chain_minimal_no_guests_no_solute_no_custom(
        self, simple_interface, mock_save_dialog
    ):
        """Minimal IonStructure with NO guests, solutes, or custom molecules.

        When IonStructure carries only water and Na+/Cl- ions (no chain
        dependencies), the export should produce ONLY the base files:
        - .gro, .top, tip4p-ice.itp, ion.itp

        NO conditional ITPs should be present:
        - No ch4_hydrate.itp (no guests)
        - No ch4_liquid.itp (no solutes)
        - No etoh.itp (no custom molecules)

        This validates the "empty chain" — ions with just water and Na/Cl.
        """
        # Build minimal IonStructure (no guests, solutes, or custom molecules)
        positions = np.zeros((10, 3))
        positions[0:4] = np.array([
            [0.5, 0.5, 2.0], [0.55, 0.52, 2.0],
            [0.48, 0.52, 2.0], [0.50, 0.51, 2.0],
        ])
        positions[4:8] = np.array([
            [1.0, 0.5, 2.0], [1.05, 0.52, 2.0],
            [0.98, 0.52, 2.0], [1.00, 0.51, 2.0],
        ])
        positions[8] = [1.5, 1.0, 2.5]
        positions[9] = [1.5, 1.0, 2.0]

        atom_names = [
            "OW", "HW1", "HW2", "MW",  # water mol 1
            "OW", "HW1", "HW2", "MW",  # water mol 2
            "NA",                       # sodium
            "CL",                       # chloride
        ]

        ion = IonStructure(
            positions=positions,
            atom_names=atom_names,
            cell=simple_interface.cell.copy(),
            molecule_index=[
                MoleculeIndex(0, 4, "water"),
                MoleculeIndex(4, 4, "water"),
                MoleculeIndex(8, 1, "na"),
                MoleculeIndex(9, 1, "cl"),
            ],
            na_count=1,
            cl_count=1,
            report="test",
            # No guests, no solutes, no custom molecules
            guest_nmolecules=0,
            guest_atom_count=0,
        )

        # Export
        save_path, dialog_p, mb_p = mock_save_dialog("minimal_ion.gro")
        exporter = IonGROMACSExporter(parent_widget=None)

        with dialog_p, mb_p:
            result = exporter.export_ion_gromacs(ion)

        assert result is True
        tmp_path = Path(save_path).parent

        # Base files ONLY
        assert (tmp_path / "minimal_ion.gro").exists()
        assert (tmp_path / "minimal_ion.top").exists()
        assert (tmp_path / "tip4p-ice.itp").exists()
        assert (tmp_path / "ion.itp").exists()

        # NO conditional ITP files
        assert not (tmp_path / "ch4_hydrate.itp").exists()
        assert not (tmp_path / "thf_hydrate.itp").exists()
        assert not (tmp_path / "ch4_liquid.itp").exists()
        assert not (tmp_path / "thf_liquid.itp").exists()
        assert not (tmp_path / "etoh.itp").exists()

        # Verify .top does NOT reference conditional ITPs
        top_content = (tmp_path / "minimal_ion.top").read_text()
        assert "ch4_hydrate" not in top_content
        assert "ch4_liquid" not in top_content
        assert "etoh" not in top_content
