"""Shared test helpers for e2e GROMACS export validation.

This module provides GRO/TOP/ITP parsing functions and chain-building helpers
used by bridge test files that validate REAL computation pipeline output flows
correctly through GROMACS writer functions.

NOT test_-prefixed to avoid pytest auto-collection.
Import with: from e2e_export_helpers import ...
"""

import numpy as np
from collections import namedtuple
from pathlib import Path

from quickice.structure_generation.generator import IceStructureGenerator
from quickice.structure_generation.hydrate_generator import HydrateStructureGenerator
from quickice.structure_generation.interface_builder import generate_interface
from quickice.structure_generation.ion_inserter import IonInserter
from quickice.structure_generation.solute_inserter import SoluteInserter
from quickice.structure_generation.custom_molecule_inserter import CustomMoleculeInserter
from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry
from quickice.structure_generation.types import (
    InterfaceConfig,
    HydrateConfig,
    IonConfig,
    IonStructure,
    SoluteConfig,
    SoluteStructure,
    CustomMoleculeConfig,
    CustomMoleculeStructure,
    MoleculeIndex,
    WATER_VOLUME_NM3,
)


# ── Staging result type ─────────────────────────────────────────────────────

StagingResult = namedtuple("StagingResult", ["staged", "missing"])
"""Result from _stage_itp_files: lists of staged and missing ITP filenames."""


# ── Test data paths ──────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).resolve().parent.parent / "quickice" / "data" / "custom"
ETOH_GRO = DATA_DIR / "etoh.gro"
ETOH_ITP = DATA_DIR / "etoh.itp"


# ── GRO/TOP/ITP parsing functions ───────────────────────────────────────────

def parse_gro_residue_names(gro_path: str) -> list[str]:
    """Parse residue names from GROMACS .gro file.

    GRO format (per GROMACS documentation):
        Line 1: Title
        Line 2: Number of atoms
        Lines 3+: Atom records
            Columns 1-5: Residue number (right-justified)
            Columns 6-10: Residue name (left-justified)
            Columns 11-15: Atom name (left-justified)
            ...

    Args:
        gro_path: Path to .gro file

    Returns:
        List of residue names in order they appear in the file
    """
    residue_names = []

    with open(gro_path, 'r') as f:
        lines = f.readlines()

        # Skip title and atom count lines
        if len(lines) < 3:
            return residue_names

        # Parse atom lines
        for line in lines[2:]:
            # Check if this is an atom line (not box vectors)
            # Box vectors have 9 float values, atom lines have formatted numbers
            if len(line.strip()) < 20:
                continue

            # Extract residue name from columns 6-10 (0-indexed: [5:10])
            # Format: "    1SOL  OW    1   0.123   0.456   0.789"
            res_name = line[5:10].strip()

            # Skip box vector lines: residue names must contain at least
            # one alphabetic character. Box vector lines have only numbers
            # (e.g., "1.56457" from line "   1.56457   1.47072...").
            if res_name and any(c.isalpha() for c in res_name):
                residue_names.append(res_name)

    return residue_names


def parse_gro_atom_count(gro_path: str) -> int:
    """Read atom count from line 2 of a .gro file.

    Args:
        gro_path: Path to .gro file

    Returns:
        Number of atoms as declared in the header
    """
    with open(gro_path, 'r') as f:
        lines = f.readlines()
        if len(lines) < 2:
            return 0
        return int(lines[1].strip())


def parse_top_molecules(top_path: str) -> dict[str, int]:
    """Parse [ molecules ] section from a GROMACS .top file.

    Tracks whether we're inside [ molecules ] by detecting `[` brackets.
    Skips comment lines (starting with `;`) and blank lines.

    Args:
        top_path: Path to .top file

    Returns:
        Dict of molecule_name -> count
    """
    molecules = {}
    in_molecules = False

    with open(top_path, 'r') as f:
        for line in f:
            stripped = line.strip()

            # Detect section headers
            if stripped.startswith('['):
                section = stripped.strip('[] \t').lower()
                in_molecules = (section == 'molecules')
                continue

            # Skip comments and blank lines
            if not stripped or stripped.startswith(';') or stripped.startswith('#'):
                continue

            # Parse molecule entries inside [ molecules ]
            if in_molecules:
                parts = stripped.split()
                if len(parts) >= 2:
                    name = parts[0]
                    try:
                        count = int(parts[1])
                        molecules[name] = count
                    except ValueError:
                        pass

    return molecules


def parse_top_includes(top_path: str) -> list[str]:
    """Parse all #include directives from a .top file.

    Extracts filename between double quotes.

    Args:
        top_path: Path to .top file

    Returns:
        List of ITP filenames (e.g., ["tip4p-ice.itp", "ch4_hydrate.itp"])
    """
    includes = []

    with open(top_path, 'r') as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith('#include'):
                # Extract filename between double quotes
                start = stripped.find('"')
                end = stripped.rfind('"')
                if start != -1 and end != -1 and start < end:
                    filename = stripped[start + 1:end]
                    includes.append(filename)

    return includes


def check_itp_has_moleculetype(itp_path: str) -> bool:
    """Check if an ITP file contains [ moleculetype ] section.

    Args:
        itp_path: Path to .itp file

    Returns:
        True if [ moleculetype ] appears in the file
    """
    with open(itp_path, 'r') as f:
        for line in f:
            if '[ moleculetype ]' in line:
                return True
    return False


def assert_gro_residue_ordering(residue_names: list[str], expected_order: list[str]) -> None:
    """Assert that residue names appear in the specified order with no interleaving.

    For each pair of consecutive expected types, finds the last index of the
    first type and first index of the second type, asserts last < first.
    Skips types not present in residue_names.

    Args:
        residue_names: List of residue names parsed from .gro file
        expected_order: List of residue name types in expected order
            (e.g., ["SOL", "CH4"])

    Raises:
        AssertionError: If residues are interleaved or out of order
    """
    # Filter to only types that are present
    present_types = [t for t in expected_order if t in residue_names]

    for i in range(len(present_types) - 1):
        first_type = present_types[i]
        second_type = present_types[i + 1]

        first_indices = [j for j, name in enumerate(residue_names) if name == first_type]
        second_indices = [j for j, name in enumerate(residue_names) if name == second_type]

        if first_indices and second_indices:
            last_first = max(first_indices)
            first_second = min(second_indices)
            assert last_first < first_second, (
                f"Residue type '{first_type}' (last at {last_first}) should come before "
                f"'{second_type}' (first at {first_second}). "
                f"Residues are interleaved!"
            )


# ── Chain-building helpers ───────────────────────────────────────────────────
# COPIED from test_e2e_workflow_chains.py (lines 37-169)
# Do NOT import from that file — import from e2e_export_helpers instead.

def _liquid_volume_nm3(structure) -> float:
    """Estimate liquid volume from water molecule count (TIP4P: WATER_VOLUME_NM3 nm³/mol)."""
    water_nmolecules = getattr(structure, 'water_nmolecules', 0)
    if water_nmolecules == 0:
        water_atom_count = getattr(structure, 'water_atom_count', 0)
        water_nmolecules = water_atom_count // 4 if water_atom_count > 0 else 0
    return water_nmolecules * WATER_VOLUME_NM3


def _insert_custom_molecules(interface, n_molecules=3):
    """Helper: place custom ethanol molecules on interface."""
    config = CustomMoleculeConfig(
        placement_mode="random",
        gro_path=ETOH_GRO,
        itp_path=ETOH_ITP,
        molecule_count=n_molecules,
    )
    inserter = CustomMoleculeInserter(config)
    return inserter.place_random(interface, n_molecules)


def _insert_solutes(source_structure, solute_type='CH4', concentration=0.3, seed=42):
    """Helper: insert solutes from a source structure."""
    config = SoluteConfig(concentration_molar=concentration, solute_type=solute_type)
    inserter = SoluteInserter(config=config, seed=seed)
    return inserter.insert_solutes(source_structure, config)


def _solute_to_ion_source(solute):
    """Helper: prepare solute.interface_structure for ion insertion (workaround for BUG I5).

    Attaches solute attributes to the interface_structure so IonInserter
    can access them via getattr.
    """
    interface_for_ions = solute.interface_structure
    interface_for_ions.solute_type = solute.solute_type
    interface_for_ions.solute_positions = solute.positions
    interface_for_ions.solute_atom_names = solute.atom_names
    interface_for_ions.solute_n_molecules = solute.n_molecules
    interface_for_ions.solute_molecule_indices = solute.molecule_indices
    interface_for_ions.solute_registry = solute.registry
    # Preserve custom molecule attributes if present
    if solute.custom_molecule_count > 0:
        interface_for_ions.custom_molecule_count = solute.custom_molecule_count
        interface_for_ions.custom_molecule_atom_count = solute.custom_molecule_atom_count
        interface_for_ions.custom_molecule_positions = solute.custom_molecule_positions
        interface_for_ions.custom_molecule_atom_names = solute.custom_molecule_atom_names
        interface_for_ions.custom_molecule_moleculetype = solute.custom_molecule_moleculetype
        interface_for_ions.custom_gro_path = solute.custom_gro_path
        interface_for_ions.custom_itp_path = solute.custom_itp_path
    return interface_for_ions


def _insert_ions(source_structure, concentration=0.15, seed=42):
    """Helper: insert ions from a source structure."""
    config = IonConfig(concentration_molar=concentration)
    inserter = IonInserter(config=config, seed=seed)
    volume = _liquid_volume_nm3(source_structure)
    ion_pairs = inserter.calculate_ion_pairs(concentration, volume)
    return inserter.replace_water_with_ions(source_structure, ion_pairs)


def _insert_ions_from_solute(solute, concentration=0.15, seed=42):
    """Helper: insert ions using the solute workaround."""
    ion_source = _solute_to_ion_source(solute)
    return _insert_ions(ion_source, concentration, seed)


def _hydrate_sI_ch4_candidate():
    """Generate hydrate sI+CH4 candidate inline (for chains needing different config)."""
    gen = HydrateStructureGenerator()
    config = HydrateConfig(
        lattice_type="sI",
        guest_type="ch4",
        supercell_x=1,
        supercell_y=1,
        supercell_z=1,
    )
    structure = gen.generate(config)
    return structure.to_candidate()


def _hydrate_sI_thf_candidate():
    """Generate hydrate sI+THF candidate inline."""
    gen = HydrateStructureGenerator()
    config = HydrateConfig(
        lattice_type="sI",
        guest_type="thf",
        supercell_x=1,
        supercell_y=1,
        supercell_z=1,
    )
    structure = gen.generate(config)
    return structure.to_candidate()


def _hydrate_sII_ch4_candidate():
    """Generate hydrate sII+CH4 candidate inline (for chains needing different config)."""
    gen = HydrateStructureGenerator()
    config = HydrateConfig(
        lattice_type="sII",
        guest_type="ch4",
        supercell_x=1,
        supercell_y=1,
        supercell_z=1,
    )
    structure = gen.generate(config)
    return structure.to_candidate()


def _hydrate_sII_thf_candidate():
    """Generate hydrate sII+THF candidate inline."""
    gen = HydrateStructureGenerator()
    config = HydrateConfig(
        lattice_type="sII",
        guest_type="thf",
        supercell_x=1,
        supercell_y=1,
        supercell_z=1,
    )
    structure = gen.generate(config)
    return structure.to_candidate()


def _make_slab_interface(candidate, box_x=3.0, box_y=3.0, box_z=8.0,
                         ice_thickness=2.0, water_thickness=4.0, seed=42):
    """Helper: generate slab interface from a candidate."""
    config = InterfaceConfig(
        mode="slab",
        box_x=box_x,
        box_y=box_y,
        box_z=box_z,
        seed=seed,
        ice_thickness=ice_thickness,
        water_thickness=water_thickness,
    )
    return generate_interface(candidate, config)


def _make_pocket_interface(candidate, box_x=3.0, box_y=3.0, box_z=8.0,
                            pocket_diameter=1.5, seed=42):
    """Helper: generate pocket interface from a candidate."""
    config = InterfaceConfig(
        mode="pocket",
        box_x=box_x,
        box_y=box_y,
        box_z=box_z,
        seed=seed,
        pocket_diameter=pocket_diameter,
        pocket_shape="sphere",
    )
    return generate_interface(candidate, config)


# ── GROMACS grompp validation helpers ─────────────────────────────────────────

MDP_PATH = Path(__file__).resolve().parent / "em.mdp"
"""Path to the energy minimization MDP file for grompp validation."""


def _stage_itp_files(top_path: str, workspace: Path) -> StagingResult:
    """Copy all #include-referenced ITP files to workspace with atomtypes commented out.
    
    Reads the TOP file, finds #include directives, locates source ITP files in
    quickice/data/ (or quickice/data/custom/ for custom molecule ITPs), applies
    comment_out_atomtypes_in_itp() if the ITP has an active [atomtypes] section,
    and writes the (possibly modified) ITP to the workspace directory.
    
    Skips ion.itp (already generated by write_ion_itp in the workspace).
    
    Args:
        top_path: Path to the .top file to scan for #include directives
        workspace: Directory to copy ITP files into
        
    Returns:
        StagingResult with:
            staged: List of ITP filenames that were successfully staged
            missing: List of ITP filenames referenced by #include but not
                     found in any data directory
    """
    from quickice.output.gromacs_writer import comment_out_atomtypes_in_itp
    
    import quickice
    data_dir = Path(quickice.__file__).parent / "data"
    custom_data_dir = data_dir / "custom"
    
    includes = parse_top_includes(top_path)
    staged = []
    missing = []
    
    for itp_name in includes:
        # Skip ion.itp — generated by write_ion_itp(), already in workspace
        if itp_name == "ion.itp":
            continue
        
        # Find source ITP file
        src = data_dir / itp_name
        if not src.exists():
            src = custom_data_dir / itp_name
        
        if not src.exists():
            # ITP not found in data dirs — track as missing
            missing.append(itp_name)
            continue
        
        # Read and optionally comment out atomtypes
        content = src.read_text()
        if "[ atomtypes ]" in content.lower():
            content = comment_out_atomtypes_in_itp(content)
        
        # Write to workspace
        (workspace / itp_name).write_text(content)
        staged.append(itp_name)
    
    return StagingResult(staged=staged, missing=missing)


def assert_itp_completeness(top_path: str, workspace: Path) -> None:
    """Assert every #include'd ITP file (except ion.itp) exists in workspace.

    Catches the "top references ITP but file is missing from export" class of bugs.
    This is the test gap that allowed the CH4 hydrate guest ITP copy bug to escape
    detection — the .top writer correctly includes ch4_hydrate.itp, but the GUI
    exporter failed to copy it, and _stage_itp_files silently skipped it.

    Args:
        top_path: Path to the .top file to scan for #include directives
        workspace: Directory where ITP files should exist

    Raises:
        AssertionError: If any #include'd ITP file is missing from workspace
    """
    includes = parse_top_includes(top_path)
    missing = []
    for itp_name in includes:
        if itp_name == "ion.itp":
            continue  # Generated by write_ion_itp(), not staged
        if not (workspace / itp_name).exists():
            missing.append(itp_name)
    assert not missing, (
        f"Missing ITP files in workspace (referenced by #include in .top): {missing}. "
        f"This indicates the export pipeline or ITP staging failed to provide "
        f"a required topology file that GROMACS needs."
    )


def run_gmx_grompp(workspace: Path, gro_file: str = "struct.gro",
                    top_file: str = "struct.top",
                    mdp_file: str = "em.mdp",
                    tpr_file: str = "em.tpr",
                    maxwarn: int = 5) -> tuple[int, str]:
    """Run gmx grompp in the workspace directory and return exit code + stderr.
    
    Args:
        workspace: Directory containing all input files (.gro, .top, .itp, .mdp)
        gro_file: Name of .gro file (relative to workspace)
        top_file: Name of .top file (relative to workspace)
        mdp_file: Name of .mdp file (relative to workspace)
        tpr_file: Name of output .tpr file (relative to workspace)
        maxwarn: Maximum number of warnings to accept
        
    Returns:
        Tuple of (exit_code, stderr_text). exit_code 0 means success.
    """
    import subprocess
    
    # Clean stale .tpr backups to avoid GROMACS "Won't make more than 99 backups" error
    for f in workspace.glob("em.tpr*"):
        f.unlink(missing_ok=True)
    # Also remove the specific tpr_file if it exists (no backup needed for tests)
    tpr_path = workspace / tpr_file
    tpr_path.unlink(missing_ok=True)
    
    cmd = [
        "gmx", "grompp",
        "-f", mdp_file,
        "-c", gro_file,
        "-p", top_file,
        "-o", tpr_file,
        "-maxwarn", str(maxwarn),
    ]
    
    result = subprocess.run(
        cmd,
        cwd=str(workspace),
        capture_output=True,
        text=True,
        timeout=60,
    )
    
    return result.returncode, result.stderr
