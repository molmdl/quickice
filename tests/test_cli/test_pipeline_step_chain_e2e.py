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

        return SimpleNamespace(
            pipe=pipe,
            args=args,
            rcs=rcs,
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

    return SimpleNamespace(
        pipe=pipe,
        source_rc=source_rc,
        interface_rc=interface_rc,
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
