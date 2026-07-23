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
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import numpy as np

from quickice.structure_generation.gro_parser import (
    extract_residue_name_from_gro,
    parse_gro_file,
)
from quickice.structure_generation.itp_parser import (
    parse_itp_defaults_comb_rule,
    parse_itp_file,
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


def validate_custom_guest_files(
    gro_path: Path | str,
    itp_path: Path | str,
    guest_type: str,
) -> CustomGuestValidation:
    """Validate a custom guest GRO+ITP pair for hydrate generation.

    Runs the full validation checklist (validate BEFORE injection, per the
    research checklist) and returns a :class:`CustomGuestValidation` with
    specific, user-facing error/warning messages. Blocking errors set
    ``is_valid=False``; warnings (e.g. missing ``[ atomtypes ]``) do not.

    Validation order (each step appends to ``errors``/``warnings``):

    1. GRO parseable (reuses :func:`parse_gro_file`, rejects >50 nm Å-mixup).
    2. ITP parseable (reuses :func:`parse_itp_file`).
    3. Atom count matches between GRO and ITP ``[ atoms ]``.
    4. Residue name <=3 chars (base name, before the ``_H`` suffix).
    5. comb-rule == 2 when ``[ defaults ]`` is present in the ITP (absent is
       accepted — QuickIce's main ``.top`` supplies comb-rule=2).
    6. ``[ atomtypes ]`` section present (warning, not error).
    7. ``guest_type`` passes GenIce2 :func:`audit_name`.

    Args:
        gro_path: Path to the custom guest ``.gro`` file.
        itp_path: Path to the custom guest ``.itp`` file.
        guest_type: Slugified plugin name (must match ``^[A-Za-z0-9-_]+$``).

    Returns:
        :class:`CustomGuestValidation` with ``is_valid``, ``errors``,
        ``warnings``, atom counts, residue name, and comb-rule. When GRO or
        ITP parsing fails, an early invalid result is returned with the
        parse error and zeroed counts.

    Example:
        >>> r = validate_custom_guest_files('etoh.gro', 'etoh.itp', 'etoh_x')
        >>> r.is_valid, r.gro_atom_count, r.comb_rule
        (True, 9, None)
    """
    errors: List[str] = []
    warnings: List[str] = []

    # 1. GRO parseable. IndexError covers truncated/malformed GRO files with
    #    too few lines (e.g. a plain-text file), which parse_gro_file surfaces
    #    when indexing lines[]. ValueError covers float-conversion and the
    #    >50 nm Å-mixup guard; OSError covers missing/unreadable files.
    try:
        positions, _, _ = parse_gro_file(gro_path)
    except (ValueError, OSError, IndexError) as exc:
        errors.append(f"Failed to parse GRO file {gro_path}: {exc}")
        return CustomGuestValidation(
            is_valid=False,
            errors=errors,
            warnings=warnings,
        )

    # 2. ITP parseable.
    try:
        itp_info = parse_itp_file(Path(itp_path))
    except (ValueError, OSError, IndexError) as exc:
        errors.append(f"Failed to parse ITP file {itp_path}: {exc}")
        return CustomGuestValidation(
            is_valid=False,
            errors=errors,
            warnings=warnings,
            gro_atom_count=len(positions),
        )

    # 3. Atom count match between GRO and ITP.
    if len(positions) != itp_info.atom_count:
        errors.append(
            f"Atom count mismatch: GRO={len(positions)}, "
            f"ITP={itp_info.atom_count}"
        )

    # 4. Residue name <=3 chars (base name; the _H suffix adds 2 chars, and GRO
    #    allows 5-char residue names). Exact message per success criteria #2.
    resname = extract_residue_name_from_gro(gro_path)
    if resname and len(resname) > 3:
        errors.append(
            f"Custom guest residue name '{resname}' ({len(resname)} chars) "
            f"exceeds 3 chars. GRO format allows 5-char residue names; "
            f"QuickIce reserves 2 chars for the '_H' hydrate suffix. "
            f"Use a residue name of 3 chars or fewer (e.g. 'MOL')."
        )

    # 5. comb-rule == 2 when [ defaults ] is present. Absent is accepted
    #    (the main .top supplies comb-rule=2). Exact message per success
    #    criteria #3.
    comb: int | None = None
    try:
        comb = parse_itp_defaults_comb_rule(Path(itp_path).read_text())
    except OSError as exc:
        # Extremely unlikely (parse_itp_file already read the file), but be
        # defensive: treat as absent rather than crashing validation.
        logger.warning(
            "Could not re-read ITP %s for comb-rule: %s", itp_path, exc
        )
        comb = None
    if comb is not None and comb != 2:
        errors.append(
            f"ITP comb-rule must be 2 (Lorentz-Berthelot / AMBER-GAFF2); "
            f"got comb-rule={comb}. QuickIce does not auto-convert A/B rules. "
            f"Please regenerate the ITP with comb-rule=2."
        )

    # 6. [ atomtypes ] present (warning, not error — the main .top may
    #    define them).
    if not itp_info.has_atomtypes_section:
        warnings.append(
            "No [ atomtypes ] in ITP; ensure types are defined in the "
            "main .top"
        )
        logger.warning(
            "Custom guest ITP %s has no [ atomtypes ] section; types must "
            "be defined in the main .top.",
            itp_path,
        )

    # 7. audit_name(guest_type). Lazy import per AGENTS.md.
    from genice2.plugin import audit_name

    if not audit_name(guest_type):
        errors.append(
            f"Invalid guest type name '{guest_type}'; "
            f"allowed chars: A-Z a-z 0-9 _ -"
        )

    return CustomGuestValidation(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        gro_atom_count=len(positions),
        itp_atom_count=itp_info.atom_count,
        residue_name=resname or "",
        comb_rule=comb,
    )


@contextmanager
def custom_guest_module(guest_type: str, module: types.ModuleType):
    """Context manager that registers a custom guest module in ``sys.modules``.

    Registers ``module`` under ``genice2.molecules.<guest_type>`` so GenIce2's
    ``safe_import('molecule', <guest_type>)`` finds it, then ALWAYS removes it
    on exit (try/finally) — even if an exception propagates out of the block.
    Call this on the main thread (thread-safe per v4.7 decision): register
    before generation, cleanup after.

    Args:
        guest_type: Slugified plugin name (must match ``^[A-Za-z0-9-_]+$``).
        module: The synthetic module built by
            :func:`build_custom_guest_module`.

    Yields:
        The ``sys.modules`` key (``genice2.molecules.<guest_type>``).

    Raises:
        RuntimeError: If the key is already present in ``sys.modules``
            (stale state from a previous un-cleaned-up registration).

    Example:
        >>> mod = build_custom_guest_module('etoh.gro', 'etoh_cm', 'MOL')
        >>> with custom_guest_module('etoh_cm', mod) as key:
        ...     loaded = safe_import('molecule', 'etoh_cm')
        ...     assert loaded is mod
        >>> # key removed from sys.modules here
    """
    key = f"genice2.molecules.{guest_type}"
    if key in sys.modules:
        raise RuntimeError(f"{key} already registered (stale state?)")
    sys.modules[key] = module
    logger.debug("Registered custom guest module '%s' in sys.modules.", key)
    try:
        yield key
    finally:
        sys.modules.pop(key, None)
        logger.debug("Cleaned up custom guest module '%s' from sys.modules.", key)


def register_custom_guest(guest_type: str, module: types.ModuleType) -> str:
    """Register a custom guest module in ``sys.modules`` (GUI async path).

    For use with QThread-based generation: call this on the main thread BEFORE
    ``HydrateWorker.start()`` so the module is visible when the worker thread
    runs ``safe_import``. Pair with :func:`unregister_custom_guest` in the
    QThread ``finished`` signal to guarantee cleanup.

    Unlike :func:`custom_guest_module` (context manager), this does NOT assert
    the key is absent — it unconditionally overwrites, which is intentional for
    the GUI async flow where the register/unregister pair is the lifecycle
    owner. Use the context manager for synchronous/CLI flows.

    Args:
        guest_type: Slugified plugin name (must match ``^[A-Za-z0-9-_]+$``).
        module: The synthetic module built by :func:`build_custom_guest_module`.

    Returns:
        The ``sys.modules`` key (``genice2.molecules.<guest_type>``).
    """
    key = f"genice2.molecules.{guest_type}"
    sys.modules[key] = module
    logger.debug("Registered custom guest module '%s' (async pair).", key)
    return key


def unregister_custom_guest(guest_type: str) -> None:
    """Remove a custom guest module from ``sys.modules`` (GUI async path).

    Safe to call when the key is absent (uses ``pop(..., None)``). Call this in
    the QThread ``finished`` signal to clean up after generation, preventing
    stale module pollution that could shadow built-in guests on the next run.

    Args:
        guest_type: Slugified plugin name (must match ``^[A-Za-z0-9-_]+$``).
    """
    key = f"genice2.molecules.{guest_type}"
    sys.modules.pop(key, None)
    logger.debug("Unregistered custom guest module '%s' (async pair).", key)
