"""Unit tests for the hydrate export success dialog guest label (Phase 42-08 Fix 2).

Tests ``quickice.gui.main_window._hydrate_export_guest_label`` — the helper
that builds the 'Guests: ...' line of the hydrate export success dialog.

Phase 42-08 Fix 2: the old label used ``config.guest_type`` (the PRIMARY single
guest) for ALL guests, mislabelling a mixed (1 CH4 + 6 THF) hydrate as
``'7 ch4'``. The helper now uses ``structure.guest_descriptors`` +
``structure.molecule_index`` for accurate per-type composition when mixed
(2+ descriptors), and keeps the legacy single-guest format otherwise.

These tests are headless (no Qt event loop needed — the helper is a pure
function of structure + config).
"""

import numpy as np

from quickice.gui.main_window import _hydrate_export_guest_label
from quickice.structure_generation.types import (
    GuestDescriptor,
    GUEST_MOLECULES,
    HydrateConfig,
    HydrateLatticeInfo,
    HydrateStructure,
    MoleculeIndex,
)


def _make_structure(molecule_index, guest_descriptors=None, guest_count=None,
                    config_guest_type="ch4", lattice_type="sI"):
    """Build a minimal HydrateStructure for label tests.

    Only molecule_index + guest_descriptors + guest_count + config matter for
    the label helper; positions/atom_names/cell are dummy values.
    """
    n_atoms = sum(m.count for m in molecule_index)
    return HydrateStructure(
        positions=np.zeros((n_atoms, 3)),
        atom_names=["X"] * n_atoms,
        cell=np.eye(3) * 1.2,
        molecule_index=molecule_index,
        config=HydrateConfig(
            lattice_type=lattice_type,
            guest_type=config_guest_type,
            supercell_x=1, supercell_y=1, supercell_z=1,
        ),
        lattice_info=HydrateLatticeInfo.from_lattice_type(lattice_type),
        report="test",
        guest_count=guest_count if guest_count is not None else
            sum(1 for m in molecule_index if m.mol_type != "water"),
        water_count=sum(1 for m in molecule_index if m.mol_type == "water"),
        guest_descriptors=guest_descriptors or [],
    )


def _desc(mol_type, cage_key="small"):
    """Build a GuestDescriptor for a built-in guest (ch4/thf)."""
    info = GUEST_MOLECULES[mol_type]
    return GuestDescriptor(
        mol_type=mol_type,
        cage_key=cage_key,
        guest_name=info["name"],
        guest_residue_name="",
        is_custom=False,
        atom_labels=list(info["atom_labels"]),
        atom_count=info["atoms"],
    )


class TestHydrateExportGuestLabel:
    """Tests for _hydrate_export_guest_label (Phase 42-08 Fix 2)."""

    def test_single_guest_no_descriptors_keeps_legacy_format(self):
        """Single-guest hydrate with NO guest_descriptors → 'Guests: N <type>'.

        Pre-Phase-42 structures have empty guest_descriptors. The label keeps
        the legacy format (no crash, no change in behaviour).
        """
        mi = [
            MoleculeIndex(0, 4, "water"),
            MoleculeIndex(4, 4, "water"),
            MoleculeIndex(8, 5, "ch4"),
        ]
        structure = _make_structure(mi, guest_descriptors=[], guest_count=1)
        label = _hydrate_export_guest_label(structure, structure.config)
        assert label == "Guests: 1 ch4", (
            f"Single-guest (no descriptors) should keep legacy format "
            f"'Guests: 1 ch4', got {label!r}"
        )

    def test_single_guest_one_descriptor_keeps_legacy_format(self):
        """Single-guest hydrate with exactly 1 guest_descriptor → legacy format.

        A single GuestDescriptor (one guest type) is not 'mixed' — the label
        keeps the legacy format using structure.guest_count + config.guest_type.
        """
        mi = [
            MoleculeIndex(0, 4, "water"),
            MoleculeIndex(4, 4, "water"),
            MoleculeIndex(8, 5, "ch4"),
        ]
        structure = _make_structure(
            mi, guest_descriptors=[_desc("ch4")], guest_count=1
        )
        label = _hydrate_export_guest_label(structure, structure.config)
        assert label == "Guests: 1 ch4", (
            f"Single-guest (1 descriptor) should keep legacy format "
            f"'Guests: 1 ch4', got {label!r}"
        )

    def test_mixed_two_descriptors_shows_per_type_composition(self):
        """Mixed hydrate (2 descriptors) → 'Guests: N <type1> + M <type2>'.

        The defining case for Fix 2: a mixed (1 CH4 + 1 THF) hydrate must NOT
        be mislabelled as '2 ch4' (the old bug). It must show per-type counts
        driven by structure.molecule_index.
        """
        mi = [
            MoleculeIndex(0, 4, "water"),
            MoleculeIndex(4, 4, "water"),
            MoleculeIndex(8, 5, "ch4"),
            MoleculeIndex(13, 13, "thf"),
        ]
        structure = _make_structure(
            mi,
            guest_descriptors=[_desc("ch4", "small"), _desc("thf", "large")],
            guest_count=2,
        )
        label = _hydrate_export_guest_label(structure, structure.config)
        assert label == "Guests: 1 ch4 + 1 thf", (
            f"Mixed (1 CH4 + 1 THF) should show per-type composition "
            f"'Guests: 1 ch4 + 1 thf', got {label!r}. The old code would have "
            f"mislabelled this as 'Guests: 2 ch4'."
        )

    def test_mixed_multiple_molecules_per_type_counts_correctly(self):
        """Mixed hydrate with multiple molecules per type → correct counts.

        e.g. 2 CH4 + 3 THF → 'Guests: 2 ch4 + 3 thf'. Counts come from
        structure.molecule_index (Counter over non-water mol_types), NOT from
        structure.guest_count (total) or config.guest_type (primary only).
        """
        mi = [
            MoleculeIndex(0, 4, "water"),
            MoleculeIndex(4, 5, "ch4"),
            MoleculeIndex(9, 5, "ch4"),
            MoleculeIndex(14, 13, "thf"),
            MoleculeIndex(27, 13, "thf"),
            MoleculeIndex(40, 13, "thf"),
        ]
        structure = _make_structure(
            mi,
            guest_descriptors=[_desc("ch4", "small"), _desc("thf", "large")],
            guest_count=5,
        )
        label = _hydrate_export_guest_label(structure, structure.config)
        assert label == "Guests: 2 ch4 + 3 thf", (
            f"Mixed (2 CH4 + 3 THF) should show 'Guests: 2 ch4 + 3 thf', "
            f"got {label!r}."
        )

    def test_missing_guest_descriptors_attribute_does_not_crash(self):
        """A structure without the guest_descriptors attribute must not crash.

        Defensive: ``hasattr(structure, 'guest_descriptors')`` guards the mixed
        path so older/incomplete HydrateStructure-like objects fall back to the
        legacy single-guest format.
        """
        mi = [
            MoleculeIndex(0, 4, "water"),
            MoleculeIndex(4, 5, "ch4"),
        ]
        structure = _make_structure(mi, guest_descriptors=[], guest_count=1)
        # Simulate a pre-Phase-42 object by deleting the attribute.
        del structure.__dict__["guest_descriptors"]
        # Should not raise — falls back to legacy format.
        label = _hydrate_export_guest_label(structure, structure.config)
        assert label == "Guests: 1 ch4", (
            f"Missing guest_descriptors attribute should fall back to legacy "
            f"'Guests: 1 ch4', got {label!r}"
        )
