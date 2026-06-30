"""Regression tests for triclinic hydrate blocking in interface_builder.

Validates:
- C0 filled ice (hydrate_c0te) is blocked for interface generation
- C1 filled ice (hydrate_c1te) is blocked for interface generation
- sH (hydrate_sH) is NOT blocked despite being triclinic (critical regression test)
- c2te (hydrate_c2te) is NOT blocked (orthorhombic)
- ice1hte (hydrate_ice1hte) is NOT blocked (orthorhombic)
- Error messages contain 'triclinic' and the lattice name

LATTICE-08: Phase_id-based blocking prevents sH regression
(cannot use is_triclinic flag alone — sH must remain unblocked).
"""

import numpy as np
import pytest

from quickice.structure_generation.types import Candidate, InterfaceConfig
from quickice.structure_generation.interface_builder import validate_interface_config
from quickice.structure_generation.errors import InterfaceGenerationError


def _make_hydrate_candidate(phase_id: str) -> Candidate:
    """Create a minimal valid Candidate for hydrate interface validation tests."""
    return Candidate(
        positions=np.zeros((10, 3)),
        atom_names=["OW"] * 10,
        cell=np.eye(3),
        nmolecules=10,
        phase_id=phase_id,
        seed=1,
    )


def _make_interface_config() -> InterfaceConfig:
    """Create a minimal valid InterfaceConfig for testing."""
    return InterfaceConfig(
        mode="slab",
        box_x=3.0,
        box_y=3.0,
        box_z=5.0,
        seed=42,
        ice_thickness=1.5,
        water_thickness=2.0,
    )


class TestTriclinicHydrateBlocking:
    """Regression tests for triclinic hydrate blocking (LATTICE-08)."""

    # 1. C0 blocked
    def test_c0te_blocked_for_interface(self):
        candidate = _make_hydrate_candidate("hydrate_c0te")
        config = _make_interface_config()
        with pytest.raises(InterfaceGenerationError):
            validate_interface_config(config, candidate)

    # 2. C1 blocked
    def test_c1te_blocked_for_interface(self):
        candidate = _make_hydrate_candidate("hydrate_c1te")
        config = _make_interface_config()
        with pytest.raises(InterfaceGenerationError):
            validate_interface_config(config, candidate)

    # 3. sH NOT blocked (critical regression test)
    def test_sH_not_blocked_for_interface(self):
        candidate = _make_hydrate_candidate("hydrate_sH")
        config = _make_interface_config()
        # Must NOT raise — sH is triclinic but explicitly allowed
        validate_interface_config(config, candidate)

    # 4. c2te NOT blocked (orthorhombic)
    def test_c2te_not_blocked_for_interface(self):
        candidate = _make_hydrate_candidate("hydrate_c2te")
        config = _make_interface_config()
        validate_interface_config(config, candidate)

    # 5. ice1hte NOT blocked (orthorhombic)
    def test_ice1hte_not_blocked_for_interface(self):
        candidate = _make_hydrate_candidate("hydrate_ice1hte")
        config = _make_interface_config()
        validate_interface_config(config, candidate)

    # 6. Error message content validation
    def test_triclinic_blocking_error_message_content(self):
        # C0 error message
        candidate = _make_hydrate_candidate("hydrate_c0te")
        config = _make_interface_config()
        with pytest.raises(InterfaceGenerationError) as exc_info:
            validate_interface_config(config, candidate)
        message = str(exc_info.value)
        assert "triclinic" in message.lower(), (
            f"C0 error message should contain 'triclinic': {message}"
        )
        assert "C0" in message, (
            f"C0 error message should contain 'C0': {message}"
        )

        # C1 error message
        candidate = _make_hydrate_candidate("hydrate_c1te")
        with pytest.raises(InterfaceGenerationError) as exc_info:
            validate_interface_config(config, candidate)
        message = str(exc_info.value)
        assert "triclinic" in message.lower(), (
            f"C1 error message should contain 'triclinic': {message}"
        )
        assert "C1" in message, (
            f"C1 error message should contain 'C1': {message}"
        )
