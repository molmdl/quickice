"""Shared custom-guest info builder for GROMACS exporters (GUI + CLI).

Neutral module — no Qt/PySide6/VTK/argparse imports. Both the GUI exporters
(quickice/gui/export.py) and the CLI pipeline (quickice/cli/pipeline.py)
import ``_build_custom_guest_info`` and ``_stage_hydrate_guest_itps`` from here.
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


def _bundled_hydrate_guest_itp_path(guest_type: str) -> Path:
    """Resolve the path to the bundled ``{guest_type}_hydrate.itp`` data file.

    Mirrors :func:`quickice.output.gromacs_writer.get_tip4p_itp_path`'s lookup
    pattern (package data dir, with a project-root fallback for development /
    editable installs). Inlined here rather than imported from
    :mod:`quickice.gui.export` / :mod:`quickice.gui.hydrate_export` to keep this
    module Qt-free (those GUI modules import PySide6 at load). The two GUI
    copies are candidates for future consolidation onto this neutral helper.

    Args:
        guest_type: Built-in guest slug (``"ch4"`` / ``"thf"``).

    Returns:
        Path to the bundled ``{guest_type}_hydrate.itp``.

    Raises:
        FileNotFoundError: If no hydrate ``.itp`` exists for ``guest_type``.
    """
    import quickice
    package_dir = Path(quickice.__file__).parent
    itp_path = package_dir / "data" / f"{guest_type}_hydrate.itp"
    if itp_path.exists():
        return itp_path
    # Fallback to project root (for development / editable installs).
    # __file__ is quickice/output/guest_info.py -> .parent.parent = quickice/.
    fallback = Path(__file__).parent.parent / "data" / f"{guest_type}_hydrate.itp"
    if fallback.exists():
        return fallback
    raise FileNotFoundError(f"No hydrate .itp file found for guest type: {guest_type}")


def _detect_builtin_guest_type(structure, detect_from_atoms) -> str | None:
    """Detect the built-in guest type from a structure (neutral mirror).

    Mirrors :func:`quickice.gui.export._detect_guest_type_from_structure` but
    lives in this neutral module (the GUI version imports PySide6 at load, so
    it cannot be imported here). ``detect_from_atoms`` is
    :func:`quickice.output.gromacs_writer.detect_guest_type_from_atoms`
    (passed in so the caller controls the lazy import).

    Detection order (matches the GUI version):
    1. Scan ``structure.molecule_index`` for ``mol_type == "guest"`` entries and
       detect the type from the first guest molecule's atom names.
    2. Heuristic fallback on ``guest_atom_count`` / ``guest_nmolecules``
       (>=10 atoms/guest -> ``"thf"``, else ``"ch4"``).

    Args:
        structure: Any structure with ``molecule_index``, ``atom_names``,
            ``guest_nmolecules`` and ``guest_atom_count`` attributes, or None.
        detect_from_atoms: :func:`detect_guest_type_from_atoms` (lazy-imported
            by the caller to keep this module's top level light).

    Returns:
        Guest type string (``"ch4"`` / ``"thf"`` / ...) or None if no guest
        detected (or ``structure is None``).
    """
    if structure is None:
        return None
    molecule_index = getattr(structure, "molecule_index", None)
    atom_names = getattr(structure, "atom_names", None)
    guest_count = (
        sum(1 for m in molecule_index if m.mol_type == "guest")
        if molecule_index else 0
    )
    guest_atom_count = getattr(structure, "guest_atom_count", 0)
    if guest_count > 0 and guest_atom_count > 0 and atom_names is not None:
        for mol in molecule_index:
            if mol.mol_type == "guest":
                mol_atom_names = atom_names[mol.start_idx:mol.start_idx + mol.count]
                guest_type = detect_from_atoms(mol_atom_names)
                if guest_type:
                    return guest_type
    guest_nmolecules = getattr(structure, "guest_nmolecules", 0)
    if guest_atom_count > 0 and guest_nmolecules > 0:
        atoms_per_guest = guest_atom_count // guest_nmolecules
        return "thf" if atoms_per_guest >= 10 else "ch4"
    return None


def _detect_builtin_guest_types(structure, detect_from_atoms) -> list:
    """Detect ALL distinct built-in guest types in a structure (plural).

    Phase 45-15 plural counterpart of :func:`_detect_builtin_guest_type` for
    MIXED built-in hydrates (CH4 in small + THF in large cages). Walks the
    ``mol_type == "guest"`` entries of ``structure.molecule_index``, detects
    each molecule's type from its atom-name slice, and returns the ordered
    deduped list of distinct types (first-appearance order).

    Reliable for built-in ch4/thf because each molecule_index entry carries
    the CORRECT per-molecule count (post Phase 45-15 ion-inserter fix), so
    the slice is exactly one molecule — no neighbor contamination.

    Falls back to the singular heuristic
    (``guest_atom_count // guest_nmolecules >= 10`` -> ``"thf"`` else
    ``"ch4"``) when no molecule_index is available, returning a 1-element
    list (the single-guest case). Returns ``[]`` if no guest is detected.

    Args:
        structure: Any structure with ``molecule_index``, ``atom_names``,
            ``guest_nmolecules`` and ``guest_atom_count`` attributes, or None.
        detect_from_atoms: :func:`detect_guest_type_from_atoms` (lazy-imported
            by the caller to keep this module's top level light).

    Returns:
        Ordered list of distinct guest type strings (e.g. ``["ch4", "thf"]``).
    """
    if structure is None:
        return []
    molecule_index = getattr(structure, "molecule_index", None)
    atom_names = getattr(structure, "atom_names", None)
    guest_atom_count = getattr(structure, "guest_atom_count", 0)
    found: list = []
    if molecule_index and atom_names is not None:
        for mol in molecule_index:
            if getattr(mol, "mol_type", None) != "guest":
                continue
            names = atom_names[mol.start_idx:mol.start_idx + mol.count]
            gtype = detect_from_atoms(names)
            if gtype and gtype not in found:
                found.append(gtype)
    if found:
        return found
    # Fallback: single-guest heuristic (no molecule_index / no guest entries).
    single = _detect_builtin_guest_type(structure, detect_from_atoms)
    return [single] if single else []


def _stage_hydrate_guest_itps(
    output_dir,
    hydrate_config,
    structure,
    guest_atom_count=None,
    guest_nmolecules=None,
):
    """Stage hydrate-guest ITPs for any interface-derived exporter (interface,
    solute, custom-molecule, ion). Config-driven — safe for the interface path.

    Mirrors ``hydrate_export.py:253-359`` (42-08) but drives from the hydrate
    config (not the structure's ``molecule_index``, which interface-derived
    structures don't carry the same way as the hydrate structure). Safe for the
    interface path because you cannot change the interface without regenerating
    from the hydrate (no 42-08-style desync possible) — see 44.1-RESEARCH §5
    Option A.

    Replaces the broken ``_detect_guest_type_from_structure`` (returns None for
    custom) + ``shutil.copy({guest_type}_hydrate.itp)`` (FileNotFoundError for
    custom) pattern duplicated 4x in ``quickice/gui/export.py``. All 4 GUI
    exporters (interface / solute / custom-molecule / ion) and the CLI export
    branches call this helper to stage guest ITPs in a config-driven way.

    Args:
        output_dir: Directory (``Path`` or ``str``) to stage ITP files into.
        hydrate_config: :class:`HydrateConfig` | None. None (or a config with
            only built-in cage assignments) -> built-in path (no custom
            guests); a config with custom ``cage_guest_assignments`` -> custom
            path (transform + write each custom ITP with the ``_H`` suffix).
        structure: The structure being exported (``InterfaceStructure`` /
            ``SoluteStructure`` / ``CustomMoleculeStructure`` / ``IonStructure``).
            Used for the presence gate (``guest_atom_count`` / ``guest_nmolecules``
            attrs) and for built-in ``guest_type`` detection when
            ``hydrate_config`` is None. May be None (tests / config-only calls)
            — then gating falls back to the explicit kwargs and built-in
            detection falls back to the config's ``cage_guest_assignments``.
        guest_atom_count: Explicit total guest atom count (overrides
            ``structure.guest_atom_count`` when provided). Threaded through the
            interface modes (plans 05/06/07) because the structure's heuristic
            attrs can be wrong for custom guests.
        guest_nmolecules: Explicit guest molecule count (overrides
            ``structure.guest_nmolecules`` when provided).

    Returns:
        ``(custom_guest_info, itp_files)`` where:
        - ``custom_guest_info``: ``list[dict]`` for the gro/top writers'
          ``custom_guest_info`` kwarg, or ``None`` for the no-guest and built-in
          paths (the writers treat ``None`` and ``[]`` identically via
          ``for ci in (custom_guest_info or [])``).
        - ``itp_files``: ``dict[str, str]`` of staged ITP file names -> their
          staged full paths, for the exporter to report / log.

    ``guest_atom_count`` / ``guest_nmolecules`` gate presence: if the structure
    has no guest atoms (e.g. ion-only export with no hydrate guests), returns
    ``(None, {})`` without staging any guest ITPs.

    Raises:
        FileNotFoundError: If a custom guest's ITP path (from the config) does
            not exist on disk, or the built-in ``{guest_type}_hydrate.itp`` data
            file cannot be resolved.
    """
    import shutil
    # Lazy import: gromacs_writer is a large module; keep guest_info.py's top
    # level light (AGENTS.md: no heavy module-level deps in output/). Both
    # primitives come from the same neutral output module (no Qt cross-import).
    from quickice.output.gromacs_writer import (
        detect_guest_type_from_atoms,
        transform_guest_itp,
    )

    output_dir = Path(output_dir)

    # Resolve the presence gate. Explicit kwargs override the structure's attrs
    # (the interface-mode pattern from plans 05/06/07: guest_atom_count is
    # threaded explicitly because the structure's heuristic attrs can be wrong
    # for custom guests). When neither is provided, fall back to the structure.
    if guest_atom_count is None:
        guest_atom_count = (
            getattr(structure, "guest_atom_count", 0) if structure else 0
        )
    if guest_nmolecules is None:
        guest_nmolecules = (
            getattr(structure, "guest_nmolecules", 0) if structure else 0
        )

    # Regression fix (CustomMoleculeStructure chain, exposed by the 44.1-11
    # solute-exporter wiring): when guest_nmolecules=0 but molecule_index has
    # guest entries (and guest_atom_count > 0), recover the guest molecule
    # count from molecule_index. This mirrors the old
    # _detect_guest_type_from_structure (quickice/gui/export.py) which used
    # molecule_index as the PRIMARY source — a workflow chain that passes
    # through CustomMoleculeStructure (which historically lacked
    # guest_nmolecules) can leave interface_structure.guest_nmolecules=0 even
    # though molecule_index has guest entries and guest_atom_count > 0.
    # Without this recovery the presence gate below short-circuits, the guest
    # ITP is NOT staged, yet the writer still #includes it (guest_count is
    # computed from molecule_index) -> grompp "File not found". Safe for the
    # interface path (assemble_slab produces an EMPTY molecule_index for
    # custom guests, so this recovery doesn't trigger) and the no-guest path
    # (molecule_index has no guest entries -> no recovery -> gate
    # short-circuits as before). Rule 1 deviation (bug fix), tracked in
    # 44.1-11-SUMMARY.
    if (
        guest_nmolecules <= 0
        and guest_atom_count > 0
        and structure is not None
    ):
        _mi = getattr(structure, "molecule_index", None)
        if _mi:
            _mi_guest_count = sum(
                1 for m in _mi if getattr(m, "mol_type", "") == "guest"
            )
            if _mi_guest_count > 0:
                guest_nmolecules = _mi_guest_count

    # Gate: no guests -> nothing to stage (e.g. ion-only export, ice-only
    # interface). Return the no-op result so the exporter skips guest ITP
    # staging entirely. Both counts must be positive: atom_count==0 means no
    # guest atoms; nmolecules==0 means no guest molecules.
    if guest_atom_count <= 0 or guest_nmolecules <= 0:
        return None, {}

    # Build custom_guest_info from the hydrate config (config-driven Option A
    # from 44.1-RESEARCH §5). None -> built-in path; list[dict] -> custom path.
    # _build_custom_guest_info excludes built-in ch4/thf (the registry handles
    # them) and dedups by mol_type (sI small+large same etoh_e2e -> 1 entry).
    custom_guest_info = _build_custom_guest_info(hydrate_config)

    itp_files: dict[str, str] = {}

    if custom_guest_info is not None:
        # Custom path: transform + write each custom guest ITP to output_dir
        # with the _H suffix applied (mirror hydrate_export.py:353-359).
        # Do NOT reimplement transform_guest_itp (AGENTS.md) — import and reuse
        # it; it already preserves comb-rule=2 (Step 1 only comments out
        # [atomtypes], never touches [defaults]).
        for ci in custom_guest_info:
            src_itp_path = Path(ci["itp_path"])
            if not src_itp_path.exists():
                raise FileNotFoundError(
                    f"Custom guest ITP not found: {src_itp_path}"
                )
            # ci["residue_name"] is already "{base}_H" (e.g. "MOL_H"); the
            # transform takes the BASE name and appends suffix="_H" -> "MOL_H".
            # removesuffix("_H") recovers the base (e.g. "MOL") — this mirrors
            # hydrate_export.py passing descriptor.guest_residue_name (base)
            # to transform_guest_itp.
            base_resname = ci["residue_name"].removesuffix("_H")
            itp_content = src_itp_path.read_text()
            transformed = transform_guest_itp(
                itp_content, base_resname, suffix="_H"
            )
            dest_name = src_itp_path.name
            dest_path = output_dir / dest_name
            dest_path.write_text(transformed)
            itp_files[dest_name] = str(dest_path)
    else:
        # Built-in path: detect ALL distinct built-in guest_types and copy
        # each bundled {guest_type}_hydrate.itp (mirror export.py:181-187
        # built-in path, extended in Phase 45-15 for mixed hydrates).
        # Phase 45-15: a mixed built-in hydrate (CH4 in small + THF in large
        # cages) needs BOTH ch4_hydrate.itp and thf_hydrate.itp staged — the
        # old single-_detect_builtin_guest_type call staged only the FIRST
        # detected type, so thf_hydrate.itp was missing and grompp would fail
        # on the #include "thf_hydrate.itp" the writer now emits.
        # Detection tries the structure first (matches existing export.py
        # behavior for real exports where the structure carries ch4/thf
        # molecule_index entries), then falls back to the config's
        # cage_guest_assignments (config-driven — handles the structure=None
        # test case and the IonStructure which has no interface_structure ref).
        guest_types = _detect_builtin_guest_types(
            structure, detect_guest_type_from_atoms
        )
        if not guest_types and hydrate_config is not None:
            for assignment in (
                getattr(hydrate_config, "cage_guest_assignments", {}) or {}
            ).values():
                if not getattr(assignment, "is_custom_guest", False):
                    if assignment.guest_type not in guest_types:
                        guest_types.append(assignment.guest_type)
        if not guest_types:
            # No built-in guest detected — nothing to stage.
            return None, {}
        # The bundled _hydrate.itp is pre-transformed (moleculetype "CH4_H",
        # [atoms] resname "CH4_H"); shutil.copy is the same as the existing
        # export.py built-in path (transform_guest_itp would be idempotent here
        # but the copy matches the existing behavior exactly).
        for guest_type in guest_types:
            src_itp_path = _bundled_hydrate_guest_itp_path(guest_type)
            dest_name = f"{guest_type}_hydrate.itp"
            dest_path = output_dir / dest_name
            shutil.copy(src_itp_path, dest_path)
            itp_files[dest_name] = str(dest_path)

    return custom_guest_info, itp_files
