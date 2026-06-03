"""End-to-end tests for ITP file baseline validation.

Validates that ALL ITP files referenced by GROMACS exporters exist in
quickice/data/ and contain valid [ moleculetype ] sections. Also validates
that generated ion.itp contains both NA and CL moleculetypes.

If any ITP file is missing or corrupted, ALL exports that reference it
will produce invalid GROMACS files. This catches data directory issues early.
"""

import sys
import re
import pytest
from pathlib import Path

# Add tests/ directory to sys.path for e2e_export_helpers import
sys.path.insert(0, str(Path(__file__).parent))

import quickice

from quickice.structure_generation.gromacs_ion_export import write_ion_itp

from e2e_export_helpers import check_itp_has_moleculetype


# ── Data directory ───────────────────────────────────────────────────────────

DATA_DIR = Path(quickice.__file__).parent / "data"


class TestITPBaseline:
    """Validate ITP files in quickice/data/ exist and have [ moleculetype ] sections.

    8 tests covering all ITP files referenced by GROMACS exporters:
    - tip4p-ice.itp (water model, used by ALL exporters)
    - ch4_hydrate.itp, thf_hydrate.itp (hydrate cage guests)
    - ch4_liquid.itp, thf_liquid.itp (liquid solutes)
    - custom/etoh.itp (custom molecule example)
    - generated ion.itp (NA + CL ions from Madrid2019)
    - No duplicate moleculetype names across ITP files
    """

    def test_tip4p_ice_itp(self):
        """quickice/data/tip4p-ice.itp exists and has [ moleculetype ]."""
        itp_path = DATA_DIR / "tip4p-ice.itp"
        assert itp_path.exists(), f"tip4p-ice.itp not found at {itp_path}"
        assert check_itp_has_moleculetype(str(itp_path)), (
            "tip4p-ice.itp should contain [ moleculetype ] section"
        )

    def test_ch4_hydrate_itp(self):
        """quickice/data/ch4_hydrate.itp exists and has [ moleculetype ]."""
        itp_path = DATA_DIR / "ch4_hydrate.itp"
        assert itp_path.exists(), f"ch4_hydrate.itp not found at {itp_path}"
        assert check_itp_has_moleculetype(str(itp_path)), (
            "ch4_hydrate.itp should contain [ moleculetype ] section"
        )

    def test_thf_hydrate_itp(self):
        """quickice/data/thf_hydrate.itp exists and has [ moleculetype ]."""
        itp_path = DATA_DIR / "thf_hydrate.itp"
        assert itp_path.exists(), f"thf_hydrate.itp not found at {itp_path}"
        assert check_itp_has_moleculetype(str(itp_path)), (
            "thf_hydrate.itp should contain [ moleculetype ] section"
        )

    def test_ch4_liquid_itp(self):
        """quickice/data/ch4_liquid.itp exists and has [ moleculetype ]."""
        itp_path = DATA_DIR / "ch4_liquid.itp"
        assert itp_path.exists(), f"ch4_liquid.itp not found at {itp_path}"
        assert check_itp_has_moleculetype(str(itp_path)), (
            "ch4_liquid.itp should contain [ moleculetype ] section"
        )

    def test_thf_liquid_itp(self):
        """quickice/data/thf_liquid.itp exists and has [ moleculetype ]."""
        itp_path = DATA_DIR / "thf_liquid.itp"
        assert itp_path.exists(), f"thf_liquid.itp not found at {itp_path}"
        assert check_itp_has_moleculetype(str(itp_path)), (
            "thf_liquid.itp should contain [ moleculetype ] section"
        )

    def test_etoh_itp(self):
        """quickice/data/custom/etoh.itp exists and has [ moleculetype ]."""
        itp_path = DATA_DIR / "custom" / "etoh.itp"
        assert itp_path.exists(), f"etoh.itp not found at {itp_path}"
        assert check_itp_has_moleculetype(str(itp_path)), (
            "etoh.itp should contain [ moleculetype ] section"
        )

    def test_generated_ion_itp(self, tmp_path):
        """write_ion_itp() generates valid ion.itp with NA and CL sections."""
        ion_itp_path = tmp_path / "ion.itp"
        write_ion_itp(ion_itp_path, na_count=6, cl_count=6)

        assert ion_itp_path.exists(), "Generated ion.itp should exist"
        assert check_itp_has_moleculetype(str(ion_itp_path)), (
            "Generated ion.itp should contain [ moleculetype ] section"
        )

        # Verify it contains both NA and CL moleculetype definitions
        content = ion_itp_path.read_text()
        # The ion.itp has two [ moleculetype ] sections: one for NA, one for CL
        moleculetype_matches = re.findall(
            r'\[ moleculetype \]\s*\n\s*;?\s*Name\s+nrexcl\s*\n\s*(\S+)',
            content
        )
        assert "NA" in moleculetype_matches, (
            f"ion.itp should contain NA moleculetype, found: {moleculetype_matches}"
        )
        assert "CL" in moleculetype_matches, (
            f"ion.itp should contain CL moleculetype, found: {moleculetype_matches}"
        )

    def test_no_duplicate_moleculetype_names(self):
        """Parse moleculetype names from tip4p-ice.itp, ch4_hydrate.itp, ch4_liquid.itp.

        Verify they are all different — no "SOL" appearing in both tip4p-ice.itp
        and ch4_hydrate.itp moleculetype sections.
        """
        itp_files = [
            DATA_DIR / "tip4p-ice.itp",
            DATA_DIR / "ch4_hydrate.itp",
            DATA_DIR / "ch4_liquid.itp",
        ]

        # Parse moleculetype names from each ITP file
        all_names = []
        for itp_path in itp_files:
            assert itp_path.exists(), f"{itp_path.name} not found at {itp_path}"
            with open(itp_path) as f:
                content = f.read()

            # Parse the line after [ moleculetype ] to extract the moleculetype name
            # Pattern: [ moleculetype ] followed by optional comment line, then name
            names = re.findall(
                r'\[ moleculetype \]\s*\n\s*;?\s*Name\s+nrexcl\s*\n\s*(\S+)',
                content
            )
            all_names.extend(names)

        # Check for duplicates
        name_counts = {}
        for name in all_names:
            name_counts[name] = name_counts.get(name, 0) + 1

        duplicates = {name: count for name, count in name_counts.items() if count > 1}
        assert len(duplicates) == 0, (
            f"Duplicate moleculetype names found across ITP files: {duplicates}. "
            f"All names: {all_names}"
        )
