"""Atomtype formatting, conflict-checking, and merge helpers.

Extracted from ``gromacs_writer.py`` (Phase 48.1, Wave 1). All function bodies
are byte-identical to the pre-refactor source — only the file path changed.

Imports:
    - ``GAFF2_ATOMTYPES`` from ``_constants`` (used by ``_write_atomtypes_block``)
    - ``parse_itp_atomtypes`` from ``_itp`` (used by ``_merge_custom_atomtypes``)
"""

import logging

from quickice.output._constants import GAFF2_ATOMTYPES
from quickice.output._itp import parse_itp_atomtypes

logger = logging.getLogger(__name__)


def _format_atomtype_line(name: str, params: tuple[str, ...]) -> str:
    """Format a GAFF2/ion atomtype tuple as a GROMACS [ atomtypes ] line.

    Args:
        name: Atomtype name (also used as bond_type for GAFF2 convention)
        params: (bond_type, atomic_number, mass, charge, ptype, sigma, epsilon)

    Returns:
        Formatted line string with newline.
    """
    bond_type, anum, mass, charge, ptype, sigma, epsilon = params
    return (f"{name:<8s} {bond_type:<8s} {anum:>6d} "
            f"{mass:>12.4f} {charge:>6.1f} {ptype:<4s} "
            f"{sigma:>12.5e} {epsilon:>12.5e}\n")


def _format_custom_atomtype_line(fields: tuple[str, ...]) -> str:
    """Format a custom-molecule atomtype tuple as a GROMACS [ atomtypes ] line.

    Custom atomtypes come from parse_itp_atomtypes() as string tuples.
    Uses string formatting to preserve the original ITP file's numeric format.

    Args:
        fields: 8-element string tuple (name, bond_type, at.num, mass, charge,
                ptype, sigma, epsilon)

    Returns:
        Formatted line string with newline.
    """
    return (f"{fields[0]:<8s} {fields[1]:<8s} {fields[2]:>6s} "
            f"{fields[3]:>12s} {fields[4]:>6s} {fields[5]:<4s} "
            f"{fields[6]:>12s} {fields[7]:>12s}\n")


def _write_atomtypes_block(
    f, names: list[str], source_label: str,
    written: dict[str, tuple[str, int, float, float, str, float, float]],
) -> None:
    """Write a GAFF2 atomtypes block with deduplication.

    For each atomtype name in *names*, checks if it has already been written
    (present in *written*).  If not, writes the atomtype line and records it.
    If the name was already written, skips it silently (built-in GAFF2 types
    from the same GAFF2_ATOMTYPES dict are guaranteed to have identical
    parameters).

    Args:
        f: Open file handle for the .top file.
        names: Atomtype names to write (e.g., CH4_ATOMTYPE_NAMES).
        source_label: Comment label for the block (e.g., "CH4 atom types (GAFF2)").
        written: Mutable dict of already-written atomtypes
                 (name → params tuple).  Updated in place.
    """
    f.write(f"; {source_label}\n")
    for name in names:
        if name in written:
            continue  # Already written — identical params guaranteed for GAFF2
        params = GAFF2_ATOMTYPES[name]
        f.write(_format_atomtype_line(name, params))
        written[name] = params


def _check_custom_atomtype_conflict(
    name: str,
    custom_fields: tuple[str, ...],
    written: dict[str, tuple[str, int, float, float, str, float, float]],
) -> None:
    """Check whether a custom-molecule atomtype conflicts with an existing one.

    If *name* is already in *written*, compares the key LJ parameters
    (sigma, epsilon).  If they differ, raises ValueError — the user must
    rename the atomtype in their custom molecule to avoid the clash.
    If they match, the duplicate is silently skipped (already defined above).

    Args:
        name: Atomtype name from the custom ITP file.
        custom_fields: 8-element string tuple from parse_itp_atomtypes().
        written: Dict of already-written atomtypes (name → params tuple).

    Raises:
        ValueError: If atomtype name already exists with different parameters.
    """
    if name not in written:
        return  # No conflict — name is new

    # Compare LJ parameters numerically (strings may use different formatting)
    try:
        custom_sigma = float(custom_fields[6])
        custom_epsilon = float(custom_fields[7])
    except (ValueError, IndexError):
        # If we can't parse, be conservative and raise
        raise ValueError(
            f"Custom molecule atomtype '{name}' could not be parsed for "
            f"parameter comparison.  Existing atomtypes with this name have "
            f"already been written.  Please rename the atomtype in your "
            f"custom molecule ITP file to avoid the collision."
        )

    existing_params = written[name]
    existing_sigma = existing_params[5]  # index 5 in (bond_type, anum, mass, charge, ptype, sigma, epsilon)
    existing_epsilon = existing_params[6]

    # Use relative tolerance for floating-point comparison
    if not _lj_params_match(existing_sigma, existing_epsilon,
                            custom_sigma, custom_epsilon):
        raise ValueError(
            f"Atomtype '{name}' is already defined with different LJ "
            f"parameters.  Existing: sigma={existing_sigma:.5e} nm, "
            f"epsilon={existing_epsilon:.5e} kJ/mol.  Custom molecule "
            f"defines: sigma={custom_sigma:.5e} nm, "
            f"epsilon={custom_epsilon:.5e} kJ/mol.  "
            f"Please rename the atomtype in your custom molecule ITP file "
            f"to avoid the conflict."
        )
    # Parameters match — duplicate is harmless, already written above


def _lj_params_match(
    sigma1: float, eps1: float, sigma2: float, eps2: float,
    rtol: float = 1e-4,
) -> bool:
    """Compare two LJ parameter sets with relative tolerance.

    Returns True if both sigma and epsilon values are close enough to be
    considered identical (accounting for rounding in different formats).
    """
    import math
    if sigma1 == 0.0 and sigma2 == 0.0 and eps1 == 0.0 and eps2 == 0.0:
        return True
    if sigma1 == 0.0 or sigma2 == 0.0:
        return sigma1 == sigma2  # Both should be zero
    if eps1 == 0.0 or eps2 == 0.0:
        return eps1 == eps2
    return (math.isclose(sigma1, sigma2, rel_tol=rtol) and
            math.isclose(eps1, eps2, rel_tol=rtol))


def _merge_custom_atomtypes(f, itp_path, written, label):
    """Parse [ atomtypes ] from a custom molecule ITP and merge into the main .top.

    For each parsed atomtype: conflict-check against *written* (raises ValueError
    on LJ-param mismatch), then write the line only if the name is new (dedup) and
    record its params in *written* for future conflict checks. No-op when the ITP
    has no [ atomtypes ] section.

    Args:
        f: Open file handle for the .top [ atomtypes ] block.
        itp_path: Path to the custom molecule .itp file.
        written: Mutable dict name -> params tuple, pre-seeded with water/ion/GAFF2
                 atomtypes. Updated in place.
        label: Comment label for the block (e.g. "custom guest etoh_e2e atom types").
    """
    custom_atomtypes = parse_itp_atomtypes(itp_path)
    if not custom_atomtypes:
        return
    f.write(f"; {label}\n")
    for atomtype in custom_atomtypes:
        if len(atomtype) >= 8:
            at_name = atomtype[0]
            _check_custom_atomtype_conflict(at_name, atomtype, written)
            if at_name not in written:
                f.write(_format_custom_atomtype_line(atomtype))
                try:
                    written[at_name] = (
                        atomtype[1], int(atomtype[2]),
                        float(atomtype[3]), float(atomtype[4]),
                        atomtype[5], float(atomtype[6]),
                        float(atomtype[7]),
                    )
                except (ValueError, IndexError):
                    pass  # Best-effort recording
