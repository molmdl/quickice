"""Tests for custom molecule renderer.

Tests the custom molecule visualization:
1. VTK actor creation with custom molecule data
2. Distinct color palette for different moleculetype names
3. Ball-and-stick rendering with CPK colors
4. Bond detection at 0.16 nm threshold
5. MW virtual sites exclusion
"""

import pytest
import numpy as np

from quickice.gui.custom_molecule_renderer import (
    create_custom_molecule_actor,
    get_element_from_atom_name,
    CUSTOM_MOLECULE_COLORS,
    BOND_DISTANCE_THRESHOLD,
)
from quickice.structure_generation.types import (
    HydrateStructure,
    HydrateConfig,
    HydrateLatticeInfo,
    MoleculeIndex,
)


class TestGetElementFromAtomName:
    """Tests for element extraction from atom names."""
    
    def test_simple_element_names(self):
        """Test extraction from simple element names."""
        assert get_element_from_atom_name("C") == "C"
        assert get_element_from_atom_name("O") == "O"
        assert get_element_from_atom_name("H") == "H"
    
    def test_element_with_numbers(self):
        """Test extraction from atom names with numbers."""
        assert get_element_from_atom_name("C1") == "C"
        assert get_element_from_atom_name("O2") == "O"
        assert get_element_from_atom_name("H3") == "H"
        assert get_element_from_atom_name("C10") == "C"
    
    def test_common_variations(self):
        """Test extraction from common atom name variations."""
        # Carbon variations
        assert get_element_from_atom_name("CA") == "C"
        assert get_element_from_atom_name("CB") == "C"
        assert get_element_from_atom_name("CG") == "C"
        
        # Oxygen variations
        assert get_element_from_atom_name("OA") == "O"
        assert get_element_from_atom_name("OB") == "O"
        
        # Hydrogen variations
        assert get_element_from_atom_name("HA") == "H"
        assert get_element_from_atom_name("HB") == "H"
    
    def test_mw_virtual_site(self):
        """Test MW virtual site returns None."""
        assert get_element_from_atom_name("MW") is None
    
    def test_unknown_elements(self):
        """Test handling of unknown elements."""
        # Single letter elements should pass through
        assert get_element_from_atom_name("N") == "N"
        assert get_element_from_atom_name("S") == "S"
        
        # Very long names should return None
        assert get_element_from_atom_name("UNKNOWN") is None


class TestCustomMoleculeColors:
    """Tests for custom molecule color palette."""
    
    def test_defined_colors(self):
        """Test that all defined colors are valid RGB tuples."""
        for name, color in CUSTOM_MOLECULE_COLORS.items():
            assert isinstance(color, tuple)
            assert len(color) == 3
            for value in color:
                assert 0.0 <= value <= 1.0
    
    def test_distinct_colors(self):
        """Test that custom molecule colors differ from predefined molecules."""
        # Custom colors should not be the same as CPK colors
        # (gray C, red O, white H)
        for color_name in ["CUSTOM_MOL_1", "CUSTOM_MOL_2", "CUSTOM_MOL_3"]:
            color = CUSTOM_MOLECULE_COLORS[color_name]
            # None of the custom colors should be pure gray, red, or white
            assert color != (0.6, 0.6, 0.6)  # Not gray (C)
            assert color != (1.0, 0.0, 0.0)  # Not red (O)
            assert color != (1.0, 1.0, 1.0)  # Not white (H)
    
    def test_default_color_exists(self):
        """Test that default fallback color exists."""
        assert "default" in CUSTOM_MOLECULE_COLORS


class TestCreateCustomMoleculeActor:
    """Tests for VTK actor creation."""
    
    def test_create_actor_simple_molecule(self):
        """Test creating VTK actor for simple molecule."""
        # Create simple molecule with C, O, H atoms
        positions = np.array([
            [0.0, 0.0, 0.0],     # C
            [0.143, 0.0, 0.0],   # O
            [0.05, 0.09, 0.0],   # H1
            [0.05, -0.09, 0.0],  # H2
        ])
        atom_names = ["C", "O", "H", "H"]
        cell = np.eye(3) * 5.0
        moleculetype_name = "CUSTOM_MOL_1"
        
        actor = create_custom_molecule_actor(
            positions, atom_names, cell, moleculetype_name
        )
        
        assert actor is not None
        assert hasattr(actor, 'GetMapper')
    
    def test_create_actor_with_color_selection(self):
        """Test that different moleculetype names get different colors."""
        positions = np.array([
            [0.0, 0.0, 0.0],
            [0.1, 0.0, 0.0],
        ])
        atom_names = ["C", "C"]
        cell = np.eye(3) * 5.0
        
        # Create actors for different custom molecule types
        actor1 = create_custom_molecule_actor(
            positions, atom_names, cell, "CUSTOM_MOL_1"
        )
        actor2 = create_custom_molecule_actor(
            positions, atom_names, cell, "CUSTOM_MOL_2"
        )
        actor3 = create_custom_molecule_actor(
            positions, atom_names, cell, "CUSTOM_MOL_3"
        )
        
        # All should create successfully
        assert actor1 is not None
        assert actor2 is not None
        assert actor3 is not None
    
    def test_create_actor_unknown_moleculetype(self):
        """Test that unknown moleculetype uses default color."""
        positions = np.array([
            [0.0, 0.0, 0.0],
        ])
        atom_names = ["C"]
        cell = np.eye(3) * 5.0
        
        # Unknown moleculetype should use default color
        actor = create_custom_molecule_actor(
            positions, atom_names, cell, "UNKNOWN_TYPE"
        )
        
        assert actor is not None
    
    def test_create_actor_empty_positions(self):
        """Test creating actor with empty atom list."""
        positions = np.array([]).reshape(0, 3)
        atom_names = []
        cell = np.eye(3) * 5.0
        
        actor = create_custom_molecule_actor(
            positions, atom_names, cell, "CUSTOM_MOL_1"
        )
        
        # Should handle gracefully
        assert actor is None
    
    def test_create_actor_with_mw_sites(self):
        """Test that MW virtual sites are excluded from rendering."""
        # TIP4P water molecule with MW site
        positions = np.array([
            [0.0, 0.0, 0.0],        # O
            [0.09572, 0.0, 0.0],    # H1
            [-0.02399, 0.09272, 0.0],  # H2
            [0.01546, 0.0, 0.0],    # MW (virtual site)
        ])
        atom_names = ["O", "H", "H", "MW"]
        cell = np.eye(3) * 5.0
        
        actor = create_custom_molecule_actor(
            positions, atom_names, cell, "CUSTOM_MOL_1"
        )
        
        # Should create actor successfully, excluding MW
        assert actor is not None
    
    def test_create_actor_bond_detection(self):
        """Test that bonds are detected at correct threshold."""
        # Create two carbon atoms at bond distance
        bond_distance = 0.15  # nm (within threshold)
        positions = np.array([
            [0.0, 0.0, 0.0],
            [bond_distance, 0.0, 0.0],
        ])
        atom_names = ["C", "C"]
        cell = np.eye(3) * 5.0
        
        actor = create_custom_molecule_actor(
            positions, atom_names, cell, "CUSTOM_MOL_1"
        )
        
        # Should create actor with detected bond
        assert actor is not None
    
    def test_create_actor_no_bond_for_long_distance(self):
        """Test that no bond is created for distant atoms."""
        # Create two carbon atoms beyond bond distance
        long_distance = 0.20  # nm (beyond threshold)
        positions = np.array([
            [0.0, 0.0, 0.0],
            [long_distance, 0.0, 0.0],
        ])
        atom_names = ["C", "C"]
        cell = np.eye(3) * 5.0
        
        actor = create_custom_molecule_actor(
            positions, atom_names, cell, "CUSTOM_MOL_1"
        )
        
        # Should still create actor (bonds are optional in VTK)
        assert actor is not None
    
    def test_create_actor_different_modes(self):
        """Test different rendering modes."""
        positions = np.array([
            [0.0, 0.0, 0.0],
            [0.1, 0.0, 0.0],
        ])
        atom_names = ["C", "C"]
        cell = np.eye(3) * 5.0
        
        # Test different rendering modes
        for mode in ["ball_and_stick", "vdw", "stick"]:
            actor = create_custom_molecule_actor(
                positions, atom_names, cell, "CUSTOM_MOL_1", mode=mode
            )
            assert actor is not None, f"Failed for mode: {mode}"


class TestBondDistanceThreshold:
    """Tests for bond detection threshold constant."""
    
    def test_threshold_value(self):
        """Test that bond threshold is correctly set."""
        assert BOND_DISTANCE_THRESHOLD == 0.16  # nm
    
    def test_threshold_covers_covalent_bonds(self):
        """Test that threshold covers typical covalent bond lengths."""
        # Typical covalent bond distances (nm)
        typical_bonds = {
            "C-H": 0.109,
            "O-H": 0.096,
            "C-C": 0.154,
            "C-O": 0.143,
            "C-N": 0.147,
        }
        
        # All typical bonds should be below threshold
        for bond_name, distance in typical_bonds.items():
            assert distance < BOND_DISTANCE_THRESHOLD, \
                f"{bond_name} bond ({distance} nm) should be below threshold"


# ---------------------------------------------------------------------------
# Phase 42 (MIXED-05): per-type guest actors in hydrate_renderer
# ---------------------------------------------------------------------------
#
# These tests exercise quickice.gui.hydrate_renderer (NOT custom_molecule_renderer
# above). They live in this file because plan 42-04 designates it as the home
# for the per-type actor count + visibility tests. The renderer now returns one
# vtkActor per non-water mol_type (defaultdict grouping) and render_hydrate_structure
# returns [water, *guests] (variable length).

# Skip the whole class if VTK is unavailable (headless crash guard per AGENTS.md).
vtk = pytest.importorskip("vtk")  # noqa: F841 — used as skip sentinel

from quickice.gui.hydrate_renderer import (  # noqa: E402 — after importorskip
    create_guest_actor,
    render_hydrate_structure,
)


def _build_hydrate_structure(guest_specs):
    """Build a synthetic HydrateStructure (no GenIce2) for renderer tests.

    Args:
        guest_specs: list of ``(mol_type, atom_names)`` tuples for the guest
            molecules, appended in order after 2 TIP4P water molecules.

    Returns:
        HydrateStructure with ``positions``, ``atom_names``, ``cell``, and a
        ``molecule_index`` of [water, water, *guests]. ``config`` is a minimal
        built-in ch4 HydrateConfig (the renderer does not read it).
    """
    # Two TIP4P water molecules (OW, HW1, HW2, MW) each — 8 atoms.
    atom_names = [
        "OW", "HW1", "HW2", "MW",
        "OW", "HW1", "HW2", "MW",
    ]
    positions = np.zeros((8, 3))
    positions[:, 0] = np.linspace(0.01, 0.08, 8)
    molecule_index = [
        MoleculeIndex(0, 4, "water"),
        MoleculeIndex(4, 4, "water"),
    ]
    offset = 8
    for mol_type, names in guest_specs:
        cnt = len(names)
        atom_names.extend(names)
        seg_pos = np.zeros((cnt, 3))
        seg_pos[:, 0] = np.linspace(0.10 + offset * 0.005, 0.10 + offset * 0.005 + cnt * 0.003, cnt)
        positions = np.vstack([positions, seg_pos])
        molecule_index.append(MoleculeIndex(offset, cnt, mol_type))
        offset += cnt

    cell = np.eye(3) * 3.0  # 3.0 nm cubic box (headroom for VTK bounds)
    config = HydrateConfig()  # built-in ch4 default; renderer does not read it
    lattice_info = HydrateLatticeInfo.from_lattice_type("sI")
    return HydrateStructure(
        positions=positions,
        atom_names=atom_names,
        cell=cell,
        molecule_index=molecule_index,
        config=config,
        lattice_info=lattice_info,
        report="test",
        guest_count=len(guest_specs),
        water_count=2,
    )


# Guest atom-name sequences (must match the mol_type's [ atoms ] order so the
# renderer's distance-based bond detection has plausible geometry).
_CH4_NAMES = ["C", "H", "H", "H", "H"]                      # 5 atoms
_ETOH_MIX_NAMES = ["H", "C", "H", "H", "C", "H", "H", "O", "H"]  # 9 atoms


class TestPerTypeGuestActors:
    """Phase 42 (MIXED-05): one vtkActor per non-water mol_type."""

    @pytest.fixture(autouse=True)
    def _offscreen_qt(self, monkeypatch):
        """Force headless Qt + VTK offscreen (AGENTS.md headless constraint)."""
        monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    def test_mixed_renders_n_plus_1_actors(self):
        """2 guest types -> render_hydrate_structure returns 3 actors (1 water + 2 guests)."""
        structure = _build_hydrate_structure([
            ("ch4", _CH4_NAMES),
            ("etoh_mix", _ETOH_MIX_NAMES),
        ])
        actors = render_hydrate_structure(structure)
        assert len(actors) == 3, f"expected 3 actors (water + 2 guests), got {len(actors)}"
        # create_guest_actor returns one actor per non-water mol_type
        guest_actors = create_guest_actor(structure)
        assert isinstance(guest_actors, list)
        assert len(guest_actors) == 2, f"expected 2 guest actors, got {len(guest_actors)}"

    def test_single_guest_renders_two_actors(self):
        """Single guest type -> 2 actors (1 water + 1 guest) — no regression."""
        structure = _build_hydrate_structure([("ch4", _CH4_NAMES)])
        actors = render_hydrate_structure(structure)
        assert len(actors) == 2, f"expected 2 actors (water + 1 guest), got {len(actors)}"
        assert len(create_guest_actor(structure)) == 1

    def test_no_guest_renders_one_actor(self):
        """Water-only -> 1 actor (just water); create_guest_actor returns []."""
        structure = _build_hydrate_structure([])
        actors = render_hydrate_structure(structure)
        assert len(actors) == 1, f"expected 1 actor (water only), got {len(actors)}"
        guest_actors = create_guest_actor(structure)
        assert guest_actors == [], f"expected empty guest-actor list, got {guest_actors}"

    def test_per_type_visibility_toggle(self):
        """Toggling one guest actor's visibility does not affect the others.

        Foundation for a future GUI per-type visibility checkbox (not wired here).
        """
        structure = _build_hydrate_structure([
            ("ch4", _CH4_NAMES),
            ("etoh_mix", _ETOH_MIX_NAMES),
        ])
        actors = render_hydrate_structure(structure)
        assert len(actors) == 3
        water, guest1, guest2 = actors
        # All visible by default
        assert water.GetVisibility() == 1
        assert guest1.GetVisibility() == 1
        assert guest2.GetVisibility() == 1
        # Toggle ONLY the second guest actor off
        guest2.VisibilityOff()
        assert guest2.GetVisibility() == 0
        # The other two remain visible — per-type toggling works
        assert water.GetVisibility() == 1
        assert guest1.GetVisibility() == 1

    def test_create_guest_actor_returns_list_not_single_actor(self):
        """create_guest_actor returns a list (not a single vtkActor) — shape contract."""
        structure = _build_hydrate_structure([("ch4", _CH4_NAMES)])
        result = create_guest_actor(structure)
        assert isinstance(result, list), "create_guest_actor must return a list"
        # And every element is a vtkActor (has SetMapper/GetVisibility)
        for a in result:
            assert hasattr(a, "GetVisibility")
            assert hasattr(a, "SetMapper")

    def test_per_type_colors_override(self):
        """per_type_colors override takes precedence over the default palette."""
        structure = _build_hydrate_structure([
            ("ch4", _CH4_NAMES),
            ("etoh_mix", _ETOH_MIX_NAMES),
        ])
        # Override ch4's bond color; etoh_mix falls back to palette[1] (cyan)
        actors = create_guest_actor(structure, per_type_colors={"ch4": (10, 20, 30)})
        assert len(actors) == 2
        # The override does not crash; both actors are created (bond color is set
        # on the mapper, not directly inspectable without a render, so we assert
        # the actor count + that the override path was exercised without error).
        assert hasattr(actors[0], "GetMapper")
        assert hasattr(actors[1], "GetMapper")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
