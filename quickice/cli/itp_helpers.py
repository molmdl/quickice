"""ITP path resolver functions for CLI export.

Provides reliable path resolution for bundled ITP files with
case normalization. No GUI imports — works without PySide6/VTK.
"""

import logging
from pathlib import Path

import quickice

logger = logging.getLogger(__name__)


def get_hydrate_guest_itp_path(guest_type: str) -> Path:
    """Resolve path to the hydrate guest ITP file.

    Args:
        guest_type: Hydrate guest molecule type (e.g. 'CH4', 'ch4', 'THF', 'thf').
                   Case-insensitive — normalized to lowercase internally.

    Returns:
        Path to the bundled hydrate guest ITP file.

    Raises:
        FileNotFoundError: If the ITP file does not exist in the data directory.
    """
    guest_type = guest_type.lower()
    path = Path(quickice.__file__).parent / "data" / f"{guest_type}_hydrate.itp"
    if not path.exists():
        raise FileNotFoundError(
            f"Hydrate guest ITP file not found: {path} "
            f"(guest_type={guest_type!r})"
        )
    return path


def get_solute_liquid_itp_path(solute_type: str) -> Path:
    """Resolve path to the solute liquid ITP file.

    Args:
        solute_type: Solute molecule type (e.g. 'CH4', 'ch4', 'THF', 'thf').
                    Case-insensitive — normalized to lowercase internally.

    Returns:
        Path to the bundled solute liquid ITP file.

    Raises:
        FileNotFoundError: If the ITP file does not exist in the data directory.
    """
    solute_type = solute_type.lower()
    path = Path(quickice.__file__).parent / "data" / f"{solute_type}_liquid.itp"
    if not path.exists():
        raise FileNotFoundError(
            f"Solute liquid ITP file not found: {path} "
            f"(solute_type={solute_type!r})"
        )
    return path


def get_tip4p_itp_path() -> Path:
    """Resolve path to the TIP4P-ICE ITP file.

    Re-exported from quickice.output.gromacs_writer for convenience.

    Returns:
        Path to the bundled TIP4P-ICE ITP file.
    """
    from quickice.output.gromacs_writer import get_tip4p_itp_path as _get_tip4p

    return _get_tip4p()
