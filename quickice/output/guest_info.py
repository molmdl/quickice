"""Shared custom-guest info builder for GROMACS exporters (GUI + CLI).

Neutral module — no Qt/PySide6/VTK/argparse imports. Both the GUI exporters
(quickice/gui/export.py) and the CLI pipeline (quickice/cli/pipeline.py)
import ``_build_custom_guest_info`` from here.
"""
from pathlib import Path


def _build_custom_guest_info(config) -> list[dict] | None:
    """Build the ``custom_guest_info`` list for the hydrate writers, or ``None``.

    Returns a list of dicts (one per DISTINCT custom guest_type, deduped by
    ``mol_type``) when ``config`` carries any custom cage assignment, else
    ``None`` (built-in guests, or ``config is None``). Dedup by ``mol_type``
    matches the 42-02 generator's ExitStack dedup and the 42-03 writers'
    ``custom_by_moltype`` dict (duplicate ``mol_type`` entries would be
    collapsed anyway — dedup here keeps the list canonical).

    Each dict: ``{'mol_type': a.guest_type, 'residue_name': '{guest_residue_name}_H',
    'itp_path': Path(a.guest_itp_path)}``. Built-in guests (``ch4``/``thf``) are
    excluded — the registry handles them. The Phase 41 legacy single-custom-guest
    path (``HydrateConfig(guest_type='etoh_e2e', ...)``) goes through the 42-01
    ``__post_init__`` shim which populates ``cage_guest_assignments`` for both
    ``small`` and ``large``; the dedup here collapses that to a 1-element list.

    Kept as a module-level function (not a method) so it can be unit-tested in
    isolation without instantiating ``CLIPipeline``. ``Path`` is reused from the
    top-level ``from pathlib import Path`` import.
    """
    if config is None:
        return None
    assignments = getattr(config, "cage_guest_assignments", {}) or {}
    seen_mol_types: set[str] = set()
    out: list[dict] = []
    for assignment in assignments.values():
        if not getattr(assignment, "is_custom_guest", False):
            continue  # built-in ch4/thf handled by the MoleculetypeRegistry
        mol_type = assignment.guest_type
        if mol_type in seen_mol_types:
            continue  # dedup by mol_type (sI small+large both etoh_e2e -> 1 entry)
        seen_mol_types.add(mol_type)
        out.append({
            "mol_type": mol_type,
            "residue_name": f"{assignment.guest_residue_name}_H",
            "itp_path": Path(assignment.guest_itp_path),
        })
    return out or None
