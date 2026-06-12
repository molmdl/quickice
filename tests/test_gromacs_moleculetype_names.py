"""Regression tests for TEST-09: TOP/ITP moleculetype name consistency.

GROMACS requires that every molecule name listed in the [molecules] section
of a .top file exactly matches a [moleculetype] name in a referenced .itp file.
A mismatch causes GROMACS to crash with a fatal error. These regression tests
verify this consistency across all 6 GROMACS export types.

The e2e-compute-export phase (Plan 06) fixed a bug where moleculetype names
were mismatched. These tests prevent that bug from recurring.

Test coverage:
- TestIceCandidateTopNames: write_top_file (inline [moleculetype])
- TestInterfaceExportNames: write_interface_top_file (#include tip4p-ice.itp)
- TestMultiMoleculeExportNames: write_multi_molecule_top_file (multiple #include)
- TestSoluteExportNames: write_solute_top_file (#include liquid ITP)
- TestIonExportNames: write_ion_top_file (#include ion.itp + other ITPs)
- TestCustomMoleculeExportNames: write_custom_molecule_top_file (#include custom ITP)
"""

import re
import sys

import pytest
from pathlib import Path

# Add tests/ directory to sys.path for e2e_export_helpers import
sys.path.insert(0, str(Path(__file__).parent))

from quickice.output.gromacs_writer import (
    write_top_file,
    write_interface_top_file,
    write_multi_molecule_top_file,
    write_ion_top_file,
    write_solute_top_file,
    write_custom_molecule_top_file,
    get_tip4p_itp_path,
    MoleculeIndex,
)
from quickice.structure_generation.itp_parser import parse_itp_file
from quickice.structure_generation.gromacs_ion_export import write_ion_itp
from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry
from quickice.structure_generation.types import MoleculeIndex as MoleculeIndexType

from e2e_export_helpers import (
    _insert_custom_molecules,
    _insert_ions,
    _insert_solutes,
    _insert_ions_from_solute,
    _hydrate_sI_ch4_candidate,
    _make_slab_interface,
    ETOH_ITP,
    parse_top_includes,
)


# ══════════════════════════════════════════════════════════════════════════════
# Helper functions
# ══════════════════════════════════════════════════════════════════════════════


def _parse_molecules_section(top_path: Path) -> list[str]:
    """Parse moleculetype names from [ molecules ] section of a TOP file.

    Finds the [ molecules ] section, skips comments and blank lines,
    and returns the first field (moleculetype name) from each data line.

    Args:
        top_path: Path to .top file

    Returns:
        List of moleculetype names in order they appear in [ molecules ]
    """
    names = []
    content = top_path.read_text()
    match = re.search(
        r'\[\s*molecules\s*\](.*?)(?=\[\s*\w+\s*\]|\Z)',
        content,
        re.DOTALL,
    )
    if match:
        for line in match.group(1).split('\n'):
            stripped = line.strip()
            if not stripped or stripped.startswith(';') or stripped.startswith('#'):
                continue
            parts = stripped.split()
            if len(parts) >= 2:
                names.append(parts[0])
    return names


def _parse_moleculetype_name_from_itp(itp_path: Path) -> str:
    """Parse [ moleculetype ] name from an ITP file.

    Uses the project's parse_itp_file() for single-moleculetype ITPs.

    Args:
        itp_path: Path to .itp file

    Returns:
        The moleculetype name string (e.g., "SOL", "CH4_H", "etoh")
    """
    itp_info = parse_itp_file(itp_path)
    return itp_info.molecule_name


def _parse_all_moleculetype_names_from_file(file_path: Path) -> list[str]:
    """Parse ALL [ moleculetype ] names from a file (TOP or ITP).

    Handles files with multiple [moleculetype] sections (like ion.itp
    which defines both NA and CL). Also handles inline [moleculetype]
    sections in TOP files (like ice candidate write_top_file output).

    Args:
        file_path: Path to .top or .itp file

    Returns:
        List of all moleculetype names found in the file
    """
    names = []
    content = file_path.read_text()

    # Match [moleculetype] header, optional comment line, then name
    for match in re.finditer(
        r'\[\s*moleculetype\s*\]\s*\n(?:\s*;[^\n]*\n)?\s*(\w+)',
        content,
        re.IGNORECASE,
    ):
        names.append(match.group(1))

    return names


def _find_itp_path(itp_name: str, tmp_path: Path) -> Path | None:
    """Find ITP file path given filename.

    Checks tmp_path first (for generated files like ion.itp),
    then quickice/data/, then quickice/data/custom/.

    Args:
        itp_name: ITP filename (e.g., "tip4p-ice.itp", "ion.itp")
        tmp_path: Temporary directory path (pytest built-in)

    Returns:
        Path to ITP file, or None if not found
    """
    import quickice

    # Check tmp_path first (for generated files like ion.itp)
    tmp_itp = tmp_path / itp_name
    if tmp_itp.exists():
        return tmp_itp

    # Check quickice/data/
    data_dir = Path(quickice.__file__).parent / "data"
    data_itp = data_dir / itp_name
    if data_itp.exists():
        return data_itp

    # Check quickice/data/custom/
    custom_itp = data_dir / "custom" / itp_name
    if custom_itp.exists():
        return custom_itp

    return None


def _collect_available_moleculetype_names(top_path: Path, tmp_path: Path) -> set[str]:
    """Get all [moleculetype] names available to a TOP file.

    Combines inline [moleculetype] names from the TOP file itself
    with [moleculetype] names from all #include'd ITP files.

    Args:
        top_path: Path to .top file
        tmp_path: Temporary directory path

    Returns:
        Set of all available moleculetype names
    """
    names = set()

    # Inline moleculetype names in TOP (ice candidate pattern)
    inline_names = _parse_all_moleculetype_names_from_file(top_path)
    names.update(inline_names)

    # ITP moleculetype names from #include directives
    includes = parse_top_includes(str(top_path))
    for itp_name in includes:
        itp_path = _find_itp_path(itp_name, tmp_path)
        if itp_path is not None:
            try:
                itp_names = _parse_all_moleculetype_names_from_file(itp_path)
                names.update(itp_names)
            except Exception:
                pass

    return names


def _assert_molecules_match_moleculetypes(top_path: Path, tmp_path: Path) -> None:
    """Assert every [molecules] name has a matching [moleculetype] definition.

    This is the core assertion pattern for all test classes.

    Args:
        top_path: Path to .top file
        tmp_path: Temporary directory path

    Raises:
        AssertionError: If any [molecules] name lacks a matching [moleculetype]
    """
    molecules_names = _parse_molecules_section(top_path)
    available_names = _collect_available_moleculetype_names(top_path, tmp_path)

    for name in molecules_names:
        assert name in available_names, (
            f"[molecules] name '{name}' has no matching [moleculetype]. "
            f"Available moleculetype names: {sorted(available_names)}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Test class 1: Ice candidate export (write_top_file)
# ══════════════════════════════════════════════════════════════════════════════


class TestIceCandidateTopNames:
    """Ice candidate export uses write_top_file with inline [moleculetype].

    The ice candidate writer writes the full SOL [moleculetype] definition
    inline in the TOP file (no #include). This test verifies that the
    [molecules] "SOL" entry matches the inline [moleculetype] "SOL" name.
    """

    def test_molecules_solar_matches_inline_moleculetype(self, ice_ih_candidate, tmp_path):
        """[molecules] SOL matches inline [moleculetype] SOL in ice TOP."""
        top_path = tmp_path / "ice.top"
        write_top_file(ice_ih_candidate, str(top_path))

        molecules_names = _parse_molecules_section(top_path)
        assert "SOL" in molecules_names, (
            f"[molecules] should contain SOL, got {molecules_names}"
        )

        inline_names = _parse_all_moleculetype_names_from_file(top_path)
        assert "SOL" in inline_names, (
            f"Inline [moleculetype] should define SOL, got {inline_names}"
        )

    def test_every_molecules_name_has_matching_moleculetype(self, ice_ih_candidate, tmp_path):
        """Every name in [molecules] has a matching [moleculetype] definition."""
        top_path = tmp_path / "ice.top"
        write_top_file(ice_ih_candidate, str(top_path))
        _assert_molecules_match_moleculetypes(top_path, tmp_path)


# ══════════════════════════════════════════════════════════════════════════════
# Test class 2: Interface export (write_interface_top_file)
# ══════════════════════════════════════════════════════════════════════════════


class TestInterfaceExportNames:
    """Interface export uses write_interface_top_file with #include.

    The interface writer #includes tip4p-ice.itp (defining [moleculetype] SOL)
    and optionally a hydrate guest ITP (defining e.g. [moleculetype] CH4_H).
    This test verifies that [molecules] names match the ITP [moleculetype] names.
    """

    def test_interface_solar_matches_tip4p_ice_moleculetype(self, interface_slab, tmp_path):
        """[molecules] SOL matches tip4p-ice.itp [moleculetype] SOL."""
        top_path = tmp_path / "interface.top"
        write_interface_top_file(interface_slab, str(top_path))

        molecules_names = _parse_molecules_section(top_path)
        assert "SOL" in molecules_names

        # Verify tip4p-ice.itp defines [moleculetype] SOL
        tip4p_itp = get_tip4p_itp_path()
        itp_mol_name = _parse_moleculetype_name_from_itp(tip4p_itp)
        assert itp_mol_name == "SOL", (
            f"tip4p-ice.itp [moleculetype] should be SOL, got {itp_mol_name}"
        )

    def test_interface_molecules_names_match_moleculetypes(self, interface_slab, tmp_path):
        """Every name in [molecules] has a matching [moleculetype] in #include'd ITP."""
        top_path = tmp_path / "interface.top"
        write_interface_top_file(interface_slab, str(top_path))
        _assert_molecules_match_moleculetypes(top_path, tmp_path)

    def test_hydrate_guest_molecules_name_matches_hydrate_itp(self, tmp_path):
        """[molecules] guest name matches hydrate ITP [moleculetype] name."""
        # Create interface from hydrate candidate with CH4 guests
        candidate = _hydrate_sI_ch4_candidate()
        interface = _make_slab_interface(candidate)

        top_path = tmp_path / "interface_hydrate.top"
        write_interface_top_file(interface, str(top_path))

        molecules_names = _parse_molecules_section(top_path)

        # Find guest names (everything except SOL)
        guest_names = [n for n in molecules_names if n != "SOL"]

        # If guests present, verify each matches its hydrate ITP [moleculetype]
        if guest_names:
            includes = parse_top_includes(str(top_path))
            hydrate_itps = [inc for inc in includes if "_hydrate.itp" in inc]

            for itp_name in hydrate_itps:
                itp_path = _find_itp_path(itp_name, tmp_path)
                assert itp_path is not None, f"Hydrate ITP {itp_name} not found"
                itp_mol_name = _parse_moleculetype_name_from_itp(itp_path)

                # The hydrate guest [molecules] name must match the ITP [moleculetype] name
                assert itp_mol_name in guest_names, (
                    f"Hydrate ITP {itp_name} defines [moleculetype] '{itp_mol_name}' "
                    f"but [molecules] has {guest_names}"
                )


# ══════════════════════════════════════════════════════════════════════════════
# Test class 3: Multi-molecule export (write_multi_molecule_top_file)
# ══════════════════════════════════════════════════════════════════════════════


class TestMultiMoleculeExportNames:
    """Multi-molecule export uses write_multi_molecule_top_file.

    The multi-molecule writer builds [molecules] names from the molecule_index
    and MoleculetypeRegistry, and includes ITP files based on mol_type.
    This test verifies that [molecules] names match ITP [moleculetype] names,
    especially for hydrate guests which require registry-based naming (CH4_H).
    """

    def test_ice_water_molecules_names_match_tip4p_itp(self, interface_slab, tmp_path):
        """Ice+water [molecules] SOL matches tip4p-ice.itp [moleculetype] SOL."""
        mol_idx = [
            MoleculeIndexType(start_idx=i * 3, count=3, mol_type="ice")
            for i in range(interface_slab.ice_nmolecules)
        ] + [
            MoleculeIndexType(
                start_idx=interface_slab.ice_atom_count + i * 4,
                count=4,
                mol_type="water",
            )
            for i in range(interface_slab.water_nmolecules)
        ]

        top_path = tmp_path / "multi.top"
        write_multi_molecule_top_file(mol_idx, str(top_path), system_name="Test")

        molecules_names = _parse_molecules_section(top_path)
        assert "SOL" in molecules_names
        _assert_molecules_match_moleculetypes(top_path, tmp_path)

    def test_hydrate_guest_with_registry_names_match(self, tmp_path):
        """With registry, hydrate guest [molecules] CH4_H matches ch4_hydrate.itp [moleculetype]."""
        # Build molecule_index with ice, water, and ch4 guest
        # Use registry for correct CH4_H naming
        reg = MoleculetypeRegistry()
        reg.register_hydrate_guest("CH4")

        mol_idx = [
            MoleculeIndexType(start_idx=0, count=3, mol_type="ice"),
            MoleculeIndexType(start_idx=3, count=4, mol_type="water"),
            MoleculeIndexType(start_idx=7, count=5, mol_type="ch4"),
        ]

        top_path = tmp_path / "multi_hydrate.top"
        write_multi_molecule_top_file(
            mol_idx, str(top_path), system_name="Test", registry=reg
        )

        molecules_names = _parse_molecules_section(top_path)
        # With registry, ch4 should appear as CH4_H in [molecules]
        assert "CH4_H" in molecules_names, (
            f"[molecules] should contain CH4_H (from registry), got {molecules_names}"
        )
        _assert_molecules_match_moleculetypes(top_path, tmp_path)


# ══════════════════════════════════════════════════════════════════════════════
# Test class 4: Solute export (write_solute_top_file)
# ══════════════════════════════════════════════════════════════════════════════


class TestSoluteExportNames:
    """Solute export uses write_solute_top_file with liquid ITP #include.

    The solute writer includes tip4p-ice.itp (SOL) and a liquid solute ITP
    (ch4_liquid.itp defining CH4_L or thf_liquid.itp defining THF_L).
    This test verifies that [molecules] names match ITP [moleculetype] names,
    especially for the liquid solute suffix (CH4_L, THF_L).
    """

    def test_ch4_solute_molecules_names_match_itps(self, interface_slab, tmp_path):
        """CH4 solute: every [molecules] name matches an ITP [moleculetype] name."""
        solute = _insert_solutes(interface_slab, solute_type='CH4', concentration=0.3)

        top_path = tmp_path / "solute_ch4.top"
        write_solute_top_file(solute, str(top_path))

        molecules_names = _parse_molecules_section(top_path)
        _assert_molecules_match_moleculetypes(top_path, tmp_path)

    def test_ch4_liquid_moleculetype_matches_molecules_entry(self, interface_slab, tmp_path):
        """CH4_L [moleculetype] in ch4_liquid.itp matches [molecules] entry."""
        solute = _insert_solutes(interface_slab, solute_type='CH4', concentration=0.3)

        top_path = tmp_path / "solute_ch4.top"
        write_solute_top_file(solute, str(top_path))

        molecules_names = _parse_molecules_section(top_path)

        # The solute name in [molecules] should come from registry
        solute_names = [n for n in molecules_names if n not in ("SOL",)]
        assert len(solute_names) > 0, "Expected at least one solute name in [molecules]"

        # Parse ch4_liquid.itp [moleculetype]
        import quickice
        ch4_liquid_itp = Path(quickice.__file__).parent / "data" / "ch4_liquid.itp"
        itp_mol_name = _parse_moleculetype_name_from_itp(ch4_liquid_itp)

        # The solute [molecules] name must match the ITP [moleculetype] name
        for solute_name in solute_names:
            assert solute_name == itp_mol_name, (
                f"Solute [molecules] name '{solute_name}' doesn't match "
                f"ch4_liquid.itp [moleculetype] '{itp_mol_name}'"
            )

    def test_thf_solute_molecules_names_match_itps(self, interface_slab, tmp_path):
        """THF solute: every [molecules] name matches an ITP [moleculetype] name."""
        solute = _insert_solutes(interface_slab, solute_type='THF', concentration=0.3)

        top_path = tmp_path / "solute_thf.top"
        write_solute_top_file(solute, str(top_path))

        molecules_names = _parse_molecules_section(top_path)
        _assert_molecules_match_moleculetypes(top_path, tmp_path)

    def test_thf_liquid_moleculetype_matches_molecules_entry(self, interface_slab, tmp_path):
        """THF_L [moleculetype] in thf_liquid.itp matches [molecules] entry."""
        solute = _insert_solutes(interface_slab, solute_type='THF', concentration=0.3)

        top_path = tmp_path / "solute_thf.top"
        write_solute_top_file(solute, str(top_path))

        molecules_names = _parse_molecules_section(top_path)

        # The solute name in [molecules] should be THF_L from registry
        solute_names = [n for n in molecules_names if n not in ("SOL",)]
        assert len(solute_names) > 0, "Expected at least one solute name in [molecules]"

        # Parse thf_liquid.itp [moleculetype]
        import quickice
        thf_liquid_itp = Path(quickice.__file__).parent / "data" / "thf_liquid.itp"
        itp_mol_name = _parse_moleculetype_name_from_itp(thf_liquid_itp)

        for solute_name in solute_names:
            assert solute_name == itp_mol_name, (
                f"Solute [molecules] name '{solute_name}' doesn't match "
                f"thf_liquid.itp [moleculetype] '{itp_mol_name}'"
            )


# ══════════════════════════════════════════════════════════════════════════════
# Test class 5: Ion export (write_ion_top_file)
# ══════════════════════════════════════════════════════════════════════════════


class TestIonExportNames:
    """Ion export uses write_ion_top_file with ion.itp #include.

    The ion writer includes tip4p-ice.itp (SOL), optionally hydrate guest ITP,
    optionally solute ITP, optionally custom ITP, and always ion.itp.
    The ion.itp is GENERATED (not copied from data/) and contains both
    [moleculetype] NA and [moleculetype] CL. This test verifies that
    NA and CL in [molecules] match the ion.itp [moleculetype] names.
    """

    def test_ion_molecules_names_match_itps(self, interface_slab, tmp_path):
        """Ion [molecules] names match ion.itp and tip4p-ice.itp [moleculetype] names."""
        ion = _insert_ions(interface_slab, concentration=0.15)

        # Generate ion.itp in tmp_path (required by #include "ion.itp")
        write_ion_itp(tmp_path / "ion.itp", ion.na_count, ion.cl_count)

        top_path = tmp_path / "ion.top"
        write_ion_top_file(ion, str(top_path))

        _assert_molecules_match_moleculetypes(top_path, tmp_path)

    def test_na_cl_moleculetype_matches_ion_itp(self, interface_slab, tmp_path):
        """NA and CL [molecules] entries match ion.itp [moleculetype] names."""
        ion = _insert_ions(interface_slab, concentration=0.15)

        # Generate ion.itp
        write_ion_itp(tmp_path / "ion.itp", ion.na_count, ion.cl_count)

        top_path = tmp_path / "ion.top"
        write_ion_top_file(ion, str(top_path))

        # Parse ion.itp [moleculetype] names (has both NA and CL)
        ion_itp_names = _parse_all_moleculetype_names_from_file(tmp_path / "ion.itp")
        assert "NA" in ion_itp_names, f"ion.itp should define [moleculetype] NA, got {ion_itp_names}"
        assert "CL" in ion_itp_names, f"ion.itp should define [moleculetype] CL, got {ion_itp_names}"

        # [molecules] should include NA and CL
        molecules_names = _parse_molecules_section(top_path)
        assert "NA" in molecules_names, f"[molecules] should include NA, got {molecules_names}"
        assert "CL" in molecules_names, f"[molecules] should include CL, got {molecules_names}"


# ══════════════════════════════════════════════════════════════════════════════
# Test class 6: Custom molecule export (write_custom_molecule_top_file)
# ══════════════════════════════════════════════════════════════════════════════


class TestCustomMoleculeExportNames:
    """Custom molecule export uses write_custom_molecule_top_file.

    The custom molecule writer includes tip4p-ice.itp (SOL) and the
    user-provided custom ITP (e.g., etoh.itp defining [moleculetype] "etoh").
    The [molecules] entry for the custom molecule uses the name parsed from
    the ITP file (Bug 2 fix from e2e-compute-export-06). This test verifies
    that the custom molecule [molecules] name matches the ITP [moleculetype]
    name, which is the exact scenario that previously caused GROMACS crashes.
    """

    def test_custom_molecules_names_match_itps(self, interface_slab, tmp_path):
        """Custom molecule [molecules] names match ITP [moleculetype] names."""
        custom = _insert_custom_molecules(interface_slab, n_molecules=3)

        top_path = tmp_path / "custom.top"
        write_custom_molecule_top_file(custom, str(top_path))

        _assert_molecules_match_moleculetypes(top_path, tmp_path)

    def test_custom_moleculetype_name_matches_etoh_itp(self, interface_slab, tmp_path):
        """Custom molecule [molecules] name matches etoh.itp [moleculetype] 'etoh'.

        This is the exact scenario that caused GROMACS crashes before the
        Bug 2 fix (e2e-compute-export-06): the [molecules] name must match
        the ITP [moleculetype] name, not the registry default "MOL".
        """
        custom = _insert_custom_molecules(interface_slab, n_molecules=3)

        top_path = tmp_path / "custom.top"
        write_custom_molecule_top_file(custom, str(top_path))

        molecules_names = _parse_molecules_section(top_path)

        # etoh.itp has [moleculetype] name "etoh" (NOT "MOL" or "ETOH")
        etoh_mol_name = _parse_moleculetype_name_from_itp(ETOH_ITP)
        assert etoh_mol_name == "etoh", (
            f"etoh.itp [moleculetype] should be 'etoh', got '{etoh_mol_name}'"
        )

        # The custom molecule name in [molecules] should match the ITP name
        custom_names = [n for n in molecules_names if n not in ("SOL",)]
        assert len(custom_names) > 0, "Expected custom molecule name in [molecules]"

        assert etoh_mol_name in custom_names, (
            f"[molecules] should contain '{etoh_mol_name}' (from etoh.itp [moleculetype]), "
            f"got {custom_names}. A mismatch here causes GROMACS fatal error."
        )
