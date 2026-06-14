"""Shared e2e test fixtures for real structure generation.

Provides module-scoped pytest fixtures that amortize expensive GenIce2 calls
(~3-5s each) across all downstream test modules. These fixtures generate REAL
structures (not synthetic), enabling genuine end-to-end pipeline testing.

IMPORTANT: No qtbot or QApplication fixture — these tests are API-only, no GUI.
"""

import pytest
import numpy as np

from quickice.phase_mapping.lookup import lookup_phase
from quickice.structure_generation.generator import IceStructureGenerator
from quickice.structure_generation.hydrate_generator import HydrateStructureGenerator
from quickice.structure_generation.interface_builder import generate_interface
from quickice.structure_generation.types import InterfaceConfig, HydrateConfig


# ── Temperature / Pressure conditions that produce each ice phase ──────────────
# Verified against lookup_phase() curve-based boundary evaluation.
PHASE_CONDITIONS = {
    "ice_ih": (250, 0.1),
    "ice_ic": (100, 0.1),
    "ice_iii": (250, 300),
    "ice_vi": (250, 700),
    "ice_vii": (300, 2500),
    "ice_viii": (100, 5000),
}


# ── Ice fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def ice_ih_candidate():
    """Generate Ice Ih candidate at 250 K, 0.1 MPa with 96 target molecules."""
    phase_info = lookup_phase(250, 0.1)
    gen = IceStructureGenerator(phase_info, 96)
    candidates = gen.generate_all(1)
    return candidates[0]


@pytest.fixture(scope="module")
def ice_ic_candidate():
    """Generate Ice Ic candidate at 100 K, 0.1 MPa with 96 target molecules."""
    phase_info = lookup_phase(100, 0.1)
    gen = IceStructureGenerator(phase_info, 96)
    candidates = gen.generate_all(1)
    return candidates[0]


# ── Hydrate fixtures ──────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def hydrate_sI_ch4_candidate():
    """Generate Hydrate sI + CH4 structure and convert to Candidate."""
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


@pytest.fixture(scope="module")
def hydrate_sI_thf_candidate():
    """Generate Hydrate sI + THF structure and convert to Candidate."""
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


@pytest.fixture(scope="module")
def hydrate_sII_ch4_candidate():
    """Generate Hydrate sII + CH4 structure and convert to Candidate."""
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


# ── Hydrate raw structures (for hydrate-specific tests) ──────────────────────

@pytest.fixture(scope="module")
def hydrate_sI_ch4_structure():
    """Generate Hydrate sI + CH4 HydrateStructure (not converted to Candidate)."""
    gen = HydrateStructureGenerator()
    config = HydrateConfig(
        lattice_type="sI",
        guest_type="ch4",
        supercell_x=1,
        supercell_y=1,
        supercell_z=1,
    )
    return gen.generate(config)


@pytest.fixture(scope="module")
def hydrate_sI_thf_structure():
    """Generate Hydrate sI + THF HydrateStructure (not converted to Candidate)."""
    gen = HydrateStructureGenerator()
    config = HydrateConfig(
        lattice_type="sI",
        guest_type="thf",
        supercell_x=1,
        supercell_y=1,
        supercell_z=1,
    )
    return gen.generate(config)


@pytest.fixture(scope="module")
def hydrate_sII_ch4_structure():
    """Generate Hydrate sII + CH4 HydrateStructure (not converted to Candidate)."""
    gen = HydrateStructureGenerator()
    config = HydrateConfig(
        lattice_type="sII",
        guest_type="ch4",
        supercell_x=1,
        supercell_y=1,
        supercell_z=1,
    )
    return gen.generate(config)


@pytest.fixture(scope="module")
def hydrate_sII_thf_structure():
    """Generate Hydrate sII + THF HydrateStructure (not converted to Candidate)."""
    gen = HydrateStructureGenerator()
    config = HydrateConfig(
        lattice_type="sII",
        guest_type="thf",
        supercell_x=1,
        supercell_y=1,
        supercell_z=1,
    )
    return gen.generate(config)


# ── Interface fixtures ────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def interface_slab(ice_ih_candidate):
    """Generate slab interface from Ice Ih candidate."""
    config = InterfaceConfig(
        mode="slab",
        box_x=3.0,
        box_y=3.0,
        box_z=8.0,
        seed=42,
        ice_thickness=2.0,
        water_thickness=4.0,
    )
    return generate_interface(ice_ih_candidate, config)


@pytest.fixture(scope="module")
def interface_pocket(ice_ih_candidate):
    """Generate pocket interface from Ice Ih candidate."""
    config = InterfaceConfig(
        mode="pocket",
        box_x=3.0,
        box_y=3.0,
        box_z=8.0,
        seed=42,
        pocket_diameter=1.5,
        pocket_shape="sphere",
    )
    return generate_interface(ice_ih_candidate, config)


@pytest.fixture(scope="module")
def interface_hydrate_slab(hydrate_sI_ch4_candidate):
    """Generate slab interface from Hydrate sI + CH4 candidate."""
    config = InterfaceConfig(
        mode="slab",
        box_x=3.0,
        box_y=3.0,
        box_z=8.0,
        seed=42,
        ice_thickness=2.0,
        water_thickness=4.0,
    )
    return generate_interface(hydrate_sI_ch4_candidate, config)


# ── Subprocess test helper ───────────────────────────────────────────────────

def run_quickice(*args: str, timeout: int = 60) -> tuple[int, str, str]:
    """Run python -m quickice with given arguments.

    Uses the canonical ``python -m quickice`` invocation (not quickice.py).
    This is the shared replacement for the per-file run_cli() helpers
    previously in test_cli_integration.py, test_cli_pipeline.py,
    and test_integration_v35.py.

    Args:
        *args: Command-line arguments to pass.
        timeout: Timeout in seconds (default: 60s).

    Returns:
        Tuple of (return_code, stdout, stderr).
    """
    import subprocess
    import sys

    cmd = [sys.executable, "-m", "quickice"] + list(args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.returncode, result.stdout, result.stderr
