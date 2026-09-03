"""Tier-B in-process CLI step-wiring chain e2e (Phase 48.3-09, GAP 1).

Drives the REAL ``CLIPipeline`` step methods in sequence on ONE instance:

    _run_source_step -> _run_interface_step -> _run_custom_step
        -> _run_solute_step -> _run_ion_step

Why (research 48.3-RESEARCH-CLI-E2E GAP 1, highest-priority CLI gap): no
existing test drives the full step chain. Subprocess tests
(``test_cli_pipeline.py``) are black-box and never grompp-validate a chain
containing the custom step; the 44.1-20-style cross-tab tests grompp every
export but bypass ALL step methods (direct generator/insert calls). The bug
classes this file pins — arg→config threading regressions (wrong ``getattr``
defaults, ``HydrateConfig``/``InterfaceConfig`` field mismatches), inter-step
attribute propagation breakage, and auto-chain regressions — are invisible to
every existing test.

What is asserted:
  1. Every step returns rc == 0 and populates its ``_<step>_result``
     attribute (the wiring execute() relies on, driven here step by step).
  2. CP-01 duck-typed attribute flow: the solute structure carries the
     custom-molecule attributes (duck-typed from ``CustomMoleculeStructure``)
     and the ion structure carries solute + custom attributes (duck-typed
     through the interface). Duck-typing is the accepted design (CP-01) —
     this file pins it, it does not judge it.
  3. Auto-chain behavior (pipeline.py:659-664 solute, :741-753 ion): with
     ``--solute-source``/``--ion-source`` left at their argparse defaults,
     the solute source is upgraded to 'custom' and the ion source to
     'solute'. Pinned by observable output (exported species content —
     see the export tests) plus the in-process-only log/progress records.
  4. Hydrate→interface variant: ``_run_source_step`` hydrate branch →
     ``to_candidate()`` path → ``_run_interface_step`` (the only source
     path previously touched only by ``test_depol_flag.py``).

Conventions:
  - Args come from the REAL parser path (``get_arguments`` = create_parser +
    parse_args + validate_pipeline_args) so argv-equivalent fields and
    defaults are authentic — the exact thing arg→config threading bugs break.
  - Module-scoped fixtures amortize GenIce2 (~1-2 s per generate here).
  - IN-PROCESS tests CAN point ``pipe._output_dir`` at pytest ``tmp_path``;
    only subprocess ``--output`` cannot (SAFE-05). Custom-step INPUT paths
    are still gated by SEC-04 (pipeline.py:532-547) even in-process, so
    etoh.gro/etoh.itp are staged under ``<cwd>/tmp/`` (gitignored).
  - ``@gmx_skipif`` gates every grompp test; file-consistency and species
    asserts run regardless.
  - No PySide6/VTK imports (AGENTS.md lazy-import rule — CLI path is
    Qt-free).

Species naming note (D1, phase 48.3-02): ``CustomMoleculeInserter`` now
registers the custom molecule under the ITP ``[moleculetype]`` name, so
liquid ethanol appears as ``etoh`` in exported residues and ``[molecules]``
(NOT the legacy ``MOL`` default). Solutes use ``CH4_L``; ions use ``NA``/``CL``.

Runtime budget: ~15-25 s total (chain ~5 s + hydrate variant ~3 s + 5 grompp
runs ~1.5 s each), within the plan's 30-60 s tier-B budget.
"""

import io
import logging
import shutil
import tempfile
from contextlib import redirect_stderr
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.conftest import gmx_skipif
from quickice.cli.parser import get_arguments
from quickice.cli.pipeline import CLIPipeline
from tests.e2e_export_helpers import (
    ETOH_GRO,
    ETOH_ITP,
    MDP_PATH,
    assert_gro_top_consistent,
    assert_itp_completeness,
    parse_gro_residue_names,
    parse_top_molecules,
    run_gmx_grompp,
)


# ══════════════════════════════════════════════════════════════════════════════
# Shared helpers / constants
# ══════════════════════════════════════════════════════════════════════════════

# Slab geometry: 3x3x8 nm box, 2.0 nm ice + 4.0 nm water (the 44.1-20 dims —
# proven to assemble, grompp, and leave room for custom/solute/ion insertion;
# shortest box vector 3.0 nm > 2x rcoulomb=1.0 rule).
SLAB_FLAGS = [
    "--interface", "--mode", "slab",
    "--box-x", "3", "--box-y", "3", "--box-z", "8",
    "--ice-thickness", "2.0", "--water-thickness", "4.0",
]

# (step name, CLIPipeline result attribute) in execution order.
STEP_ATTRS = [
    ("interface", "_interface_result"),
    ("custom", "_custom_result"),
    ("solute", "_solute_result"),
    ("ion", "_ion_result"),
]

CUSTOM_COUNT = 3
ETOH_ATOMS_PER_MOLECULE = 9  # ethanol C2H5OH in etoh.gro


def _make_cwd_tmp_dir(prefix: str) -> Path:
    """Create a temp dir under ``<cwd>/tmp/`` (gitignored).

    SEC-04 gates the custom-step INPUT paths (pipeline.py:532-547) against
    the working directory even for in-process calls, so the etoh input files
    must live under CWD — the same constraint that forces subprocess tests
    to use ``<cwd>/tmp/`` instead of pytest ``tmp_path``.
    """
    tmp_base = Path.cwd() / "tmp"
    tmp_base.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=prefix, dir=str(tmp_base)))


def _stage_custom_inputs(work_dir: Path) -> tuple[Path, Path]:
    """Copy the real etoh.gro/etoh.itp fixtures under ``work_dir`` (under CWD).

    Returns:
        (gro_path, itp_path) — the staged copies, suitable for
        ``--custom-gro``/``--custom-itp`` under the SEC-04 containment check.
    """
    staged_gro = work_dir / "etoh.gro"
    staged_itp = work_dir / "etoh.itp"
    shutil.copy(ETOH_GRO, staged_gro)
    shutil.copy(ETOH_ITP, staged_itp)
    return staged_gro, staged_itp


def _capture_pipeline_output():
    """Install an INFO handler on the pipeline logger (log capture half).

    The auto-chain decisions are logged via ``logger.info`` only
    (pipeline.py:659-664, 741-753) — an in-process-only observable of the
    auto-upgrade decisions that subprocess tests can never see. The
    ``[PROGRESS]`` stderr half is captured separately by the caller via
    ``with redirect_stderr(progress_buf):`` (kept inline so the context
    manager's enter/exit stays balanced — its ``__exit__`` must run exactly
    once per ``__enter__``).

    Returns ``(handler, log_buf, pipeline_logger, orig_level)`` — undo with
    :func:`_release_pipeline_output`.
    """
    log_buf = io.StringIO()
    handler = logging.StreamHandler(log_buf)
    handler.setLevel(logging.INFO)
    pipeline_logger = logging.getLogger("quickice.cli.pipeline")
    orig_level = pipeline_logger.level
    pipeline_logger.addHandler(handler)
    pipeline_logger.setLevel(logging.INFO)
    return handler, log_buf, pipeline_logger, orig_level


def _release_pipeline_output(handler, pipeline_logger, orig_level):
    """Undo :func:`_capture_pipeline_output` (the logging half only)."""
    pipeline_logger.removeHandler(handler)
    pipeline_logger.setLevel(orig_level)


def _export_step(ws, step_name, structure, attr, hydrate=None):
    """44.1-20 ``_assert_step_output`` export pattern, isolated per step.

    Builds a FRESH ``CLIPipeline`` with ``_output_dir`` = ``ws`` and the
    SINGLE ``_<step>_result`` the export priority needs (ion > solute >
    custom > interface > hydrate > ice; ``hydrate`` optionally pre-set for
    the custom-guest cgi threading), then calls ``_run_export_step()``.
    This pins each export branch in isolation with the REAL step-produced
    structure — the thing 44.1-20 deliberately avoided by calling the
    generators directly.

    Args:
        ws: Per-step output directory (created here — ``execute()`` is the
            only caller that mkdirs, ``_run_export_step`` does not).
        step_name: ``"interface"``/``"custom"``/``"solute"``/``"ion"``.
        structure: The step's result structure to export.
        attr: The ``CLIPipeline`` attribute name (e.g. ``"_solute_result"``).
        hydrate: Optional hydrate result (carries ``.config``) to pre-set on
            ``_hydrate_result`` for the cgi-threading path.

    Returns:
        (rc, pipe) — the ``_run_export_step`` return code and the pipe.
    """
    ws.mkdir(parents=True, exist_ok=True)
    pipe = CLIPipeline(args=SimpleNamespace())
    pipe._output_dir = ws
    if hydrate is not None:
        pipe._hydrate_result = hydrate
    setattr(pipe, attr, structure)
    rc = pipe._run_export_step()
    return rc, pipe


def _assert_export_files(ws, step_name):
    """Assert exported files exist + are consistent; return species views.

    Copies ``em.mdp`` in (for the later grompp test), runs
    ``assert_itp_completeness`` + ``assert_gro_top_consistent`` (always-on,
    gmx-free), and returns ``(top_molecules, gro_residues)`` for species
    assertions.
    """
    gro = ws / f"{step_name}.gro"
    top = ws / f"{step_name}.top"
    assert gro.exists(), f"{step_name}.gro not written to {ws}"
    assert top.exists(), f"{step_name}.top not written to {ws}"
    assert (ws / "tip4p-ice.itp").exists(), (
        f"tip4p-ice.itp not staged for the {step_name} export"
    )
    shutil.copy(MDP_PATH, ws / "em.mdp")
    assert_itp_completeness(str(top), ws)
    assert_gro_top_consistent(str(gro), str(top))
    return parse_top_molecules(str(top)), set(parse_gro_residue_names(str(gro)))


# ══════════════════════════════════════════════════════════════════════════════
# Module fixtures — the REAL step chain, run ONCE, amortized across tests
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def step_chain(tmp_path_factory):
    """Module-scoped: drive ONE ``CLIPipeline`` through the full step chain.

    Uses the real parser path (``get_arguments``) with
    ``--solute-source``/``--ion-source`` left at their argparse defaults so
    the auto-chain upgrade logic (pipeline.py:659-664, 741-753) is exercised
    exactly as a user running the full chain without explicit source flags.

    Returns a namespace with:
        pipe      — the pipeline instance after all 5 steps
        args      — the parsed namespace (defaults intact for the pin tests)
        rcs       — {step_name: rc} for all 5 steps in execution order
        exports   — {step_name: SimpleNamespace(ws, rc)} per-step exports
        progress  — captured ``[PROGRESS]`` stderr text
        logs      — captured ``quickice.cli.pipeline`` INFO records
    """
    work_dir = _make_cwd_tmp_dir("pipeline_step_chain_")
    try:
        staged_gro, staged_itp = _stage_custom_inputs(work_dir)
        args = get_arguments([
            "-T", "270", "-P", "0.1",
            *SLAB_FLAGS,
            "--custom-gro", str(staged_gro),
            "--custom-itp", str(staged_itp),
            "--custom-placement", "random",
            "--custom-count", str(CUSTOM_COUNT),
            "--solute-type", "CH4", "--solute-concentration", "0.3",
            "--ion-concentration", "0.15",
            "--seed", "42",
            "--output", str(work_dir / "out"),
        ])
        # Auto-chain preconditions: the source flags stay at their argparse
        # defaults ('interface') — the chain relies on the upgrade logic.
        assert args.solute_source == "interface"
        assert args.ion_source == "interface"

        pipe = CLIPipeline(args=args)
        # In-process: _output_dir may live under pytest tmp (only subprocess
        # --output is SAFE-05-restricted to CWD).
        pipe._output_dir = tmp_path_factory.mktemp("step_chain_main_out")

        handler, log_buf, pl_logger, orig_level = _capture_pipeline_output()
        try:
            with redirect_stderr(io.StringIO()) as progress_buf:
                rcs = {
                    "source": pipe._run_source_step(),
                    "interface": pipe._run_interface_step(),
                    "custom": pipe._run_custom_step(),
                    "solute": pipe._run_solute_step(),
                    "ion": pipe._run_ion_step(),
                }
        finally:
            _release_pipeline_output(handler, pl_logger, orig_level)

        # Per-step exports (44.1-20 _assert_step_output pattern): each step's
        # structure exported via _run_export_step into its own isolated
        # subdir with the priority branch isolated to that single result.
        exports_root = tmp_path_factory.mktemp("step_chain_exports")
        exports = {}
        for step_name, attr in STEP_ATTRS:
            structure = getattr(pipe, attr)
            assert structure is not None, (
                f"chain broke before the {step_name} export: rcs={rcs}"
            )
            export_rc, _ = _export_step(
                exports_root / step_name, step_name, structure, attr
            )
            exports[step_name] = SimpleNamespace(
                ws=exports_root / step_name, rc=export_rc
            )

        # execute()-equivalent final export on the REAL instance: with ALL
        # step results populated, the priority selection (ion > solute >
        # custom > interface) must pick the ion result — what a real full-
        # chain invocation writes as ion.gro/ion.top.
        final_ws = pipe._output_dir
        final_ws.mkdir(parents=True, exist_ok=True)
        final_export_rc = pipe._run_export_step()

        return SimpleNamespace(
            pipe=pipe,
            args=args,
            rcs=rcs,
            exports=exports,
            final_export=SimpleNamespace(ws=final_ws, rc=final_export_rc),
            progress=progress_buf.getvalue(),
            logs=log_buf.getvalue(),
        )
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


@pytest.fixture(scope="module")
def hydrate_variant(tmp_path_factory):
    """Module-scoped: hydrate branch → ``to_candidate()`` → interface step.

    Exercises ``_run_source_step``'s hydrate branch (the only partially
    covered source path — previously touched only by test_depol_flag.py's
    depol threading) followed by ``_run_interface_step`` on the candidate
    produced by ``HydrateStructure.to_candidate()``.

    Returns a namespace with:
        pipe         — the pipeline instance after both steps
        source_rc    — rc of _run_source_step
        interface_rc — rc of _run_interface_step
        export       — SimpleNamespace(ws, rc) interface export (fresh pipe,
                       priority-isolated, CH4_H cage-guest path)
        progress     — captured ``[PROGRESS]`` stderr text
    """
    args = get_arguments([
        "-T", "270", "-P", "0.1",
        "--hydrate", "--lattice-type", "sI", "--guest", "CH4",
        *SLAB_FLAGS,
        "--seed", "42",
        "--output", "output",
    ])
    pipe = CLIPipeline(args=args)
    handler, log_buf, pl_logger, orig_level = _capture_pipeline_output()
    try:
        with redirect_stderr(io.StringIO()) as progress_buf:
            source_rc = pipe._run_source_step()
            interface_rc = pipe._run_interface_step()
    finally:
        _release_pipeline_output(handler, pl_logger, orig_level)

    # Export the hydrate-derived interface (CH4_H cage guests) through
    # _run_export_step — the guest-ITP staging path driven by the REAL
    # source+interface step wiring (44.1-20 drives it from a hand-built slab).
    export_ws = tmp_path_factory.mktemp("hydrate_variant_iface_export")
    export_rc, _ = _export_step(
        export_ws,
        "interface",
        pipe._interface_result,
        "_interface_result",
        hydrate=pipe._hydrate_result,
    )

    return SimpleNamespace(
        pipe=pipe,
        source_rc=source_rc,
        interface_rc=interface_rc,
        export=SimpleNamespace(ws=export_ws, rc=export_rc),
        progress=progress_buf.getvalue(),
        logs=log_buf.getvalue(),
    )


@pytest.fixture()
def custom_inputs():
    """Function-scoped staged etoh inputs under ``<cwd>/tmp/`` (SEC-04)."""
    work_dir = _make_cwd_tmp_dir("pipeline_step_chain_neg_")
    try:
        yield _stage_custom_inputs(work_dir)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


# ══════════════════════════════════════════════════════════════════════════════
# Task 1: sequential step-chain on ONE CLIPipeline instance (GAP 1)
# ══════════════════════════════════════════════════════════════════════════════


class TestSequentialStepChain:
    """The real step wiring: source → interface → custom → solute → ion."""

    def test_all_steps_rc_zero_and_results_populated(self, step_chain):
        """Every step returns rc==0 and populates its ``_<step>_result``.

        This is the core GAP 1 assertion: the hand-offs execute() relies on
        (``self._interface_result`` → custom step, ``self._custom_result`` →
        solute step, ``self._solute_result`` → ion step) actually carry
        populated structures when driven through the real step methods.
        """
        pipe = step_chain.pipe
        for step_name in ("source", "interface", "custom", "solute", "ion"):
            rc = step_chain.rcs[step_name]
            assert rc == 0, f"step {step_name} returned rc={rc} (chain broke)"

        # Source step (interface branch): real GenIce2 ice candidate.
        assert pipe._ice_candidate is not None, (
            "interface-branch source step must populate _ice_candidate"
        )

        iface = pipe._interface_result
        assert iface is not None, "_run_interface_step must populate _interface_result"
        assert iface.ice_nmolecules > 0 and iface.water_nmolecules > 0

        custom = pipe._custom_result
        assert custom is not None, "_run_custom_step must populate _custom_result"
        assert custom.custom_molecule_count == CUSTOM_COUNT
        assert custom.custom_molecule_atom_count == (
            CUSTOM_COUNT * ETOH_ATOMS_PER_MOLECULE
        )

        solute = pipe._solute_result
        assert solute is not None, "_run_solute_step must populate _solute_result"
        assert solute.n_molecules > 0, "0.3 M CH4 in a 36 nm3 water region must place solutes"

        ion = pipe._ion_result
        assert ion is not None, "_run_ion_step must populate _ion_result"
        assert (ion.na_count + ion.cl_count) > 0, (
            "0.15 M NaCl in a 36 nm3 water region must place ions"
        )

    def test_solute_auto_chain_upgrade_pins(self, step_chain):
        """Auto-chain observable (in-process only): default --solute-source
        'interface' is upgraded to 'custom' because ``_custom_result`` exists
        (pipeline.py:659-664 — logged via logger.info, invisible to
        subprocess tests; the report_progress line names the resolved source).

        The structural observable — the custom molecule surviving into the
        exported solute output — is asserted in
        ``test_per_step_export_consistency_and_species``.
        """
        # Precondition: the flag was left at its argparse default.
        assert step_chain.args.solute_source == "interface"
        # The upgrade decision itself (logger.info, pipeline.py:661-664).
        assert (
            "Auto-chaining: --solute-source upgraded from "
            "'interface' to 'custom'" in step_chain.logs
        ), f"auto-chain log record not found in: {step_chain.logs!r}"
        # report_progress names the resolved source (pipeline.py:683-687).
        assert "(source=custom)" in step_chain.progress, (
            f"solute progress line must name the upgraded source; got: "
            f"{step_chain.progress!r}"
        )

    def test_ion_auto_chain_upgrade_pins(self, step_chain):
        """Auto-chain observable (in-process only): default --ion-source
        'interface' is upgraded to 'solute' — the most downstream result
        (pipeline.py:741-753, logger.info only).

        The output observable (custom AND solute species in the exported
        ion.gro) is asserted in ``test_per_step_export_consistency_and_species``.
        """
        assert step_chain.args.ion_source == "interface"
        assert (
            "Auto-chaining: --ion-source upgraded from "
            "'interface' to 'solute'" in step_chain.logs
        ), f"auto-chain log record not found in: {step_chain.logs!r}"

    def test_per_step_export_consistency_and_species(self, step_chain):
        """Per-step exports: file consistency + species content.

        THE auto-chain output observables (impossible to assert in
        subprocess black-box tests):
        - the exported solute output carries the custom molecule
          ('etoh' residue + [molecules] entry) — that IS the
          solute-source auto-upgrade observable (pipeline.py:659-664 logs
          only), and
        - the exported ion output contains BOTH the custom ('etoh') and
          the solute ('CH4_L') species (pipeline.py:741-753 auto-upgrade).
        """
        exports = step_chain.exports
        for step_name, _attr in STEP_ATTRS:
            assert exports[step_name].rc == 0, (
                f"_run_export_step failed for the {step_name} step"
            )
        custom_name = step_chain.pipe._custom_result.moleculetype_name  # "etoh" (D1)

        # 1) Interface export: plain ice-water slab (no cage guests) → SOL only.
        mols, residues = _assert_export_files(exports["interface"].ws, "interface")
        assert "SOL" in mols and "SOL" in residues

        # 2) Custom export: SOL + etoh.
        mols, residues = _assert_export_files(exports["custom"].ws, "custom")
        assert custom_name in mols, f"custom molecule missing from [molecules]: {mols}"
        assert custom_name in residues, (
            f"custom residue missing from custom.gro: {sorted(residues)}"
        )

        # 3) Solute export: SOL + etoh + CH4_L — the custom molecule SURVIVING
        #    the solute step is the auto-upgrade observable.
        mols, residues = _assert_export_files(exports["solute"].ws, "solute")
        assert custom_name in mols and custom_name in residues, (
            f"auto-chain regression: custom molecule dropped from the solute "
            f"export (molecules={mols}, residues={sorted(residues)})"
        )
        assert "CH4_L" in mols and "CH4_L" in residues

        # 4) Ion export: SOL + etoh + CH4_L (+ NA/CL) — BOTH upstream species
        #    survive into the ion output.
        mols, residues = _assert_export_files(exports["ion"].ws, "ion")
        assert custom_name in mols and custom_name in residues, (
            f"auto-chain regression: custom molecule dropped from the ion "
            f"export (molecules={mols}, residues={sorted(residues)})"
        )
        assert "CH4_L" in mols and "CH4_L" in residues
        ion = step_chain.pipe._ion_result
        if ion.na_count > 0:
            assert "NA" in mols and "NA" in residues
        if ion.cl_count > 0:
            assert "CL" in mols and "CL" in residues

        # 5) Final export on the REAL instance (execute()-equivalent): with
        #    ALL results populated, priority (ion > solute > custom >
        #    interface) must select the ion result.
        assert step_chain.final_export.rc == 0
        assert (step_chain.final_export.ws / "ion.gro").exists(), (
            "priority selection must pick the ion result on a fully "
            "populated instance (execute() writes ion.gro/ion.top)"
        )
        assert (step_chain.final_export.ws / "ion.top").exists()

    @gmx_skipif
    def test_per_step_export_grompp(self, step_chain):
        """Every per-step export passes ``gmx grompp`` (rc == 0).

        44.1-20-style per-step grompp validation WITH the real step wiring —
        the subprocess tests grompp only 2 black-box runs and never a chain
        containing the custom step (research GAP 2).
        """
        for step_name, _attr in STEP_ATTRS:
            ws = step_chain.exports[step_name].ws
            rc, stderr = run_gmx_grompp(
                ws, gro_file=f"{step_name}.gro", top_file=f"{step_name}.top"
            )
            assert rc == 0, (
                f"gmx grompp failed for the {step_name} step export:\n{stderr[-800:]}"
            )

    def test_duck_typed_attribute_flow(self, step_chain):
        """CP-01 duck-typing: solute carries custom attrs; ion carries solute+custom.

        The ion step reads these duck-typed attributes off the structures to
        propagate them onto the interface (pipeline.py:810-830) — if the
        solute inserter or the chain stops carrying them, custom molecules
        are silently dropped from the ion export. Duck-typing is the accepted
        design (CP-01); this test pins it.
        """
        pipe = step_chain.pipe
        custom = pipe._custom_result
        solute = pipe._solute_result
        ion = pipe._ion_result

        # D1 (48.3-02): the inserter registers the molecule under the ITP
        # [moleculetype] name — etoh for quickice/data/custom/etoh.itp.
        assert custom.moleculetype_name == "etoh", (
            f"expected D1 moleculetype 'etoh', got {custom.moleculetype_name!r}"
        )

        # Solute structure carries the custom molecule (duck-typed).
        assert solute.custom_molecule_count == custom.custom_molecule_count
        assert solute.custom_molecule_moleculetype == "etoh"
        assert solute.custom_molecule_positions is not None
        assert len(solute.custom_molecule_positions) == (
            CUSTOM_COUNT * ETOH_ATOMS_PER_MOLECULE
        )
        assert solute.interface_structure is not None, (
            "SoluteStructure.interface_structure must be populated for ion chaining"
        )

        # Ion structure carries BOTH solute and custom attributes (duck-typed
        # through the interface; IonInserter copies them onto IonStructure).
        assert ion.solute_type == "CH4"
        assert ion.solute_n_molecules == solute.n_molecules
        assert ion.solute_positions is not None
        assert ion.custom_molecule_count == CUSTOM_COUNT
        assert ion.custom_molecule_atom_count == CUSTOM_COUNT * ETOH_ATOMS_PER_MOLECULE
        assert ion.custom_molecule_moleculetype == "etoh"
        assert ion.custom_molecule_positions is not None


class TestHydrateSourceVariant:
    """Task 1 Test 2: hydrate branch → to_candidate() → interface step."""

    def test_hydrate_source_to_interface_chain(self, hydrate_variant):
        """``_run_source_step`` hydrate branch feeds ``_run_interface_step``.

        Pins the hydrate→interface source path: the hydrate is generated
        (real GenIce2), converted to an ice candidate via ``to_candidate()``
        (pipeline.py:392-394), and the interface step assembles a slab from
        that candidate — with the hydrate's CH4 cage guests surviving into
        the interface structure.
        """
        hv = hydrate_variant
        assert hv.source_rc == 0, "hydrate-branch source step failed"
        assert hv.interface_rc == 0, "interface step off a hydrate candidate failed"

        pipe = hv.pipe
        assert pipe._hydrate_result is not None
        # to_candidate() path: the source step converted the hydrate for
        # downstream interface generation.
        assert pipe._ice_candidate is not None, (
            "hydrate source step with --interface must populate _ice_candidate "
            "via HydrateStructure.to_candidate()"
        )

        iface = pipe._interface_result
        assert iface is not None
        assert iface.ice_nmolecules > 0 and iface.water_nmolecules > 0
        # The sI hydrate's CH4 cage guests survive the to_candidate → slab path.
        assert iface.guest_nmolecules > 0, (
            "hydrate-derived slab must carry cage guests into the interface"
        )

        # Progress observables (verbatim from pipeline.py:385-394).
        assert "Generated sI hydrate" in hv.progress
        assert "Hydrate converted to ice candidate" in hv.progress

    @gmx_skipif
    def test_hydrate_variant_interface_export_grompp(self, hydrate_variant):
        """The hydrate-derived interface export passes ``gmx grompp``.

        The interface export branch (guest ITP staging via the
        ``_detect_guest_type`` fallback, CH4_H residues) driven by the REAL
        ``_run_source_step`` hydrate branch + ``_run_interface_step`` wiring
        — 44.1-20 covers the same export from a hand-built slab instead.
        """
        hv = hydrate_variant
        assert hv.export.rc == 0, "interface export of the hydrate-derived slab failed"
        mols, residues = _assert_export_files(hv.export.ws, "interface")
        assert "SOL" in mols and "SOL" in residues
        assert "CH4_H" in mols, f"CH4_H missing from [molecules]: {mols}"
        assert "CH4_H" in residues, (
            f"CH4_H residue missing from interface.gro: {sorted(residues)}"
        )
        rc, stderr = run_gmx_grompp(
            hv.export.ws, gro_file="interface.gro", top_file="interface.top"
        )
        assert rc == 0, (
            f"gmx grompp failed for the hydrate-variant interface export:\n"
            f"{stderr[-800:]}"
        )


class TestStepOrderingGuard:
    """Negative spot-check: step order is enforced with a clear message."""

    def test_custom_step_before_interface_fails_cleanly(self, custom_inputs, capsys):
        """``_run_custom_step`` without an interface result → rc 1 + clear message.

        The custom step REQUIRES the interface result (pipeline.py:549-555):
        with ``_interface_result`` still None it must fail fast with rc 1 and
        the actionable message read verbatim from pipeline.py:552-555 (not
        invented here): "No interface structure available. Run --interface
        step before custom molecule insertion."
        """
        staged_gro, staged_itp = custom_inputs
        args = get_arguments([
            "-T", "270", "-P", "0.1",
            *SLAB_FLAGS,
            "--custom-gro", str(staged_gro),
            "--custom-itp", str(staged_itp),
            "--custom-placement", "random",
            "--custom-count", "2",
            "--seed", "42",
            "--output", "output",
        ])
        pipe = CLIPipeline(args=args)
        assert pipe._interface_result is None  # the step-ordering precondition

        rc = pipe._run_custom_step()
        assert rc == 1, "custom step before the interface step must fail with rc 1"
        assert pipe._custom_result is None, (
            "a failed custom step must not populate _custom_result"
        )

        err = capsys.readouterr().err
        assert "No interface structure available" in err, (
            f"expected the pipeline.py:552-555 message on stderr, got: {err!r}"
        )
        assert "Run --interface step before custom molecule insertion" in err
