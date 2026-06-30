"""Custom guest bridge for GenIce2 hydrate generation.

This module is the core of Phase 40: it builds a synthetic GenIce2
``Molecule`` plugin module from a user-provided GRO file, validates a
GRO+ITP pair, and injects/cleans up the module in ``sys.modules`` so that
GenIce2's ``safe_import('molecule', <guest_type>)`` finds the custom guest
and places it in hydrate cage positions during ``generate_ice()``.

The mechanism was verified end-to-end in research (POC generated a real
sI hydrate with 2 ethanol molecules in cages). Key invariants:

* ``sites_`` MUST be centered (centroid subtracted) because GenIce2's
  ``arrange()`` adds the cage-center position to ``sites_``; it treats
  ``sites_`` as coordinates relative to the molecule center.
* ``guest_type`` (the plugin name / ``sys.modules`` key) is a slugified
  identifier matching ``^[A-Za-z0-9-_]+$`` and may exceed 3 chars, while
  ``residue_name`` (``Molecule.name_``) must be <=3 chars so the ``_H``
  hydrate suffix fits within GRO's 5-char residue name limit.
* Registration happens on the main thread (thread-safe per v4.7 decision)
  and cleanup always runs (try/finally) to avoid stale module pollution.

No new dependencies: stdlib + numpy + existing quickice parsers + genice2
(latter imported lazily inside function bodies, per AGENTS.md).
"""

import logging
import sys
import types
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import numpy as np

from quickice.structure_generation.gro_parser import (
    extract_residue_name_from_gro,
    parse_gro_file,
)

logger = logging.getLogger(__name__)


@dataclass
class CustomGuestValidation:
    """Result of validating a custom guest GRO+ITP pair.

    Attributes:
        is_valid: True when no blocking errors were found.
        errors: Blocking error messages (specific, user-facing).
        warnings: Non-blocking warnings (e.g. missing [ atomtypes ]).
        gro_atom_count: Number of atoms parsed from the GRO file.
        itp_atom_count: Number of atoms defined in the ITP [ atoms ] section.
        residue_name: Residue name extracted from the GRO (<=3 chars when valid).
        comb_rule: comb-rule from ITP [ defaults ] (int) or None when absent.
    """

    is_valid: bool
    errors: List[str]
    warnings: List[str]
    gro_atom_count: int = 0
    itp_atom_count: int = 0
    residue_name: str = ""
    comb_rule: int | None = None


def build_custom_guest_module(
    gro_path: Path | str,
    guest_type: str,
    residue_name: str,
) -> types.ModuleType:
    """Build a synthetic GenIce2 ``Molecule`` plugin module from a GRO file.

    Parses the GRO file (reusing :func:`parse_gro_file`, which validates the
    >50 nm Å-mixup automatically), centers the molecule (GenIce2's
    ``arrange()`` adds the cage center to ``sites_``), validates the
    ``guest_type`` plugin name via GenIce2's :func:`audit_name`, and builds a
    :class:`types.ModuleType` whose ``Molecule`` subclass exposes
    ``sites_``, ``labels_``, and ``name_``.

    This function does NOT register the module in ``sys.modules``; the
    caller is responsible for injection/cleanup (see
    :func:`custom_guest_module` context manager or
    :func:`register_custom_guest`/:func:`unregister_custom_guest`).

    Args:
        gro_path: Path to the custom guest ``.gro`` file (coordinates in nm).
        guest_type: Slugified plugin name (must match ``^[A-Za-z0-9-_]+$``).
            Used as the ``sys.modules`` key suffix and ``safe_import`` arg.
        residue_name: GRO residue name (``Molecule.name_``). Must be <=3 chars
            so the ``_H`` hydrate suffix fits GRO's 5-char residue limit.

    Returns:
        A :class:`types.ModuleType` named ``genice2.molecules.<guest_type>``
        with a ``Molecule`` subclass exposing ``sites_`` (centered, nm),
        ``labels_`` (atom names from GRO), and ``name_`` (residue_name).

    Raises:
        ValueError: If the GRO file cannot be parsed, or if ``guest_type``
            contains characters outside ``[A-Za-z0-9-_]``.
        FileNotFoundError: If the GRO file does not exist (re-raised as
            ValueError with context).

    Example:
        >>> mod = build_custom_guest_module('etoh.gro', 'etoh_custom', 'MOL')
        >>> mol = mod.Molecule()
        >>> mol.name_, len(mol.labels_), mol.sites_.shape
        ('MOL', 9, (9, 3))
    """
    # 1. Parse the GRO file (validates >50nm Å-mixup automatically).
    try:
        positions, atom_names, _ = parse_gro_file(gro_path)
    except (ValueError, OSError) as exc:
        # Re-raise with context (FileNotFoundError is a subclass of OSError).
        raise ValueError(
            f"Failed to parse GRO file {gro_path}: {exc}"
        ) from exc

    # 2. Center the molecule. GenIce2's arrange() treats sites_ as coordinates
    #    relative to the molecule center (it adds the cage center), so sites_
    #    MUST be centered or guests will be offset from cage centers.
    centroid = positions.mean(axis=0)
    centered = positions - centroid

    # 3. Validate the guest_type plugin name (GenIce2 audit_name requires
    #    ^[A-Za-z0-9-_]+$). Lazy import per AGENTS.md (no top-level GenIce2).
    from genice2.plugin import audit_name

    if not audit_name(guest_type):
        raise ValueError(
            f"Invalid guest type name '{guest_type}'; "
            f"allowed chars: A-Z a-z 0-9 _ -"
        )

    # 4. Build the synthetic module. The exec'd code subclasses
    #    genice2.molecules.Molecule and sets sites_/labels_/name_. A docstring
    #    on Molecule is nice (Stage7 logs gmol.__doc__) but a desc dict is NOT
    #    required for generation.
    mod_key = f"genice2.molecules.{guest_type}"
    mod = types.ModuleType(mod_key)
    mod.__doc__ = (
        f"Synthetic GenIce2 molecule plugin for custom guest '{residue_name}' "
        f"(generated by QuickIce custom_guest_bridge)."
    )
    # Use repr() of the centered list and atom names to embed literal values.
    # This avoids closure/capture issues with exec and keeps the module
    # self-contained (no reference to the caller's locals).
    code = (
        "import numpy as np\n"
        "import genice2.molecules\n"
        "class Molecule(genice2.molecules.Molecule):\n"
        f"    '''Custom guest {residue_name} (generated by QuickIce).'''\n"
        "    def __init__(self):\n"
        f"        self.sites_ = np.array({centered.tolist()!r})\n"
        f"        self.labels_ = {list(atom_names)!r}\n"
        f"        self.name_ = {residue_name!r}\n"
    )
    exec(code, mod.__dict__)

    logger.info(
        "Built custom guest module '%s': %d atoms, residue '%s', "
        "sites centered (max |mean|=%.2e).",
        mod_key,
        len(atom_names),
        residue_name,
        float(np.abs(centered.mean(axis=0)).max()),
    )

    # 5. Return the module (caller registers it in sys.modules).
    return mod
