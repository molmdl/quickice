"""E2E triclinic blocking tests through the REAL CLI pipeline and GUI worker.

Plan 45-08: proves that triclinic filled-ice lattices (c0te, c1te) are BLOCKED
at the interface step through the REAL CLI pipeline (``_run_interface_step``
catches ``InterfaceGenerationError`` -> returns 1) and the GUI worker
(``InterfaceGenerationWorker`` catches -> emits ``error`` signal). This closes
the gap where ``test_triclinic_blocking.py`` only tested
``validate_interface_config`` directly.

Triclinic blocking is at the INTERFACE step (``generate_interface`` ->
``validate_interface_config`` -> raises ``InterfaceGenerationError``).
Generation WORKS for c0te/c1te. ``TRICLINIC_HYDRATE_PHASES`` =
``{"hydrate_c0te", "hydrate_c1te"}`` (interface_builder.py:121) is
phase_id-based blocking, NOT the ``is_triclinic`` flag (sH is triclinic but
NOT blocked).

Key paths tested:
- CLI: ``quickice.cli.pipeline.CLIPipeline._run_interface_step`` (pipeline.py
  :421-444) constructs an ``InterfaceConfig`` from ``self.args``, calls
  ``generate_interface``, catches ``InterfaceGenerationError`` -> returns 1.
- GUI: ``quickice.gui.workers.InterfaceGenerationWorker`` (workers.py:146,
  200, 215-218) calls ``generate_interface`` inside ``run()``, catches
  ``InterfaceGenerationError`` -> emits the ``error`` signal.

``InterfaceGenerationWorker`` is a ``QObject`` (NOT ``QThread`` —
workers.py:146), so ``run()`` is called directly (synchronous): it executes
and returns after emitting ``error`` on ``InterfaceGenerationError``. No
``QThread``, ``worker.start()``, ``worker.wait()``, or ``QTest.qWait`` is
needed.
"""

import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

# Add tests/ directory to sys.path for e2e_export_helpers import
sys.path.insert(0, str(Path(__file__).parent))

from quickice.structure_generation.hydrate_generator import (  # noqa: E402
    HydrateStructureGenerator,
)
from quickice.structure_generation.types import (  # noqa: E402
    HydrateConfig,
    InterfaceConfig,
)
from quickice.structure_generation.errors import (  # noqa: E402
    InterfaceGenerationError,
)
from quickice.cli.pipeline import CLIPipeline  # noqa: E402

# TRICLINIC_HYDRATE_PHASES is a local constant inside validate_interface_config
# (interface_builder.py:121), not a module-level importable name. Mirror it
# here for documentation/assertion purposes.
TRICLINIC_HYDRATE_PHASES = {"hydrate_c0te", "hydrate_c1te"}


# ---------------------------------------------------------------------------
# Module-scoped fixture: generate c0te + c1te hydrates ONCE, amortize GenIce2
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def triclinic_hydrates():
    """Build c0te + c1te hydrate chains once per module (amortize GenIce2).

    Triclinic blocking is at the INTERFACE step, not generation — both
    lattices generate successfully. The blocking happens when
    ``generate_interface`` -> ``validate_interface_config`` raises
    ``InterfaceGenerationError`` for ``phase_id`` in
    ``TRICLINIC_HYDRATE_PHASES``.
    """
    chains = {}
    for lattice_type in ("c0te", "c1te"):
        gen = HydrateStructureGenerator()
        config = HydrateConfig(
            lattice_type=lattice_type,
            guest_type="ch4",
            supercell_x=1,
            supercell_y=1,
            supercell_z=1,
        )
        hydrate = gen.generate(config)
        candidate = hydrate.to_candidate()
        chains[lattice_type] = SimpleNamespace(
            hydrate=hydrate,
            candidate=candidate,
            config=config,
        )
    yield chains


# ---------------------------------------------------------------------------
# CLI: _run_interface_step catches InterfaceGenerationError -> returns 1
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lattice_type", ["c0te", "c1te"])
def test_cli_run_interface_step_blocks_triclinic(triclinic_hydrates, lattice_type):
    """CLI ``_run_interface_step`` returns non-zero for triclinic filled ice.

    The CLI pipeline catches ``InterfaceGenerationError`` at pipeline.py:441-444
    and returns 1. This proves blocking works through the REAL CLI pipeline,
    not just ``validate_interface_config`` directly (which is what
    ``test_triclinic_blocking.py`` covers).
    """
    chain = triclinic_hydrates[lattice_type]

    # Construct CLIPipeline with an empty args namespace
    pipe = CLIPipeline(args=SimpleNamespace())

    # Mirror _run_source_step: when --interface is set, the hydrate result is
    # stored and converted to an ice candidate for interface generation
    # (pipeline.py:343-354).
    pipe._hydrate_result = chain.hydrate
    pipe._ice_candidate = chain.candidate

    # Mirror the InterfaceConfig construction in _run_interface_step
    # (pipeline.py:421-431). The candidate's phase_id is "hydrate_c0te" or
    # "hydrate_c1te" — both in TRICLINIC_HYDRATE_PHASES — so
    # validate_interface_config raises InterfaceGenerationError before any
    # mode-specific (slab) checks run.
    pipe.args.mode = "slab"
    pipe.args.box_x = 3.0
    pipe.args.box_y = 3.0
    pipe.args.box_z = 8.0
    pipe.args.ice_thickness = 2.0
    pipe.args.water_thickness = 4.0
    pipe.args.seed = 42
    pipe.args.pocket_diameter = None
    pipe.args.pocket_shape = "sphere"

    # Run the interface step — should catch InterfaceGenerationError -> return 1
    code = pipe._run_interface_step()

    # Blocking: _run_interface_step catches InterfaceGenerationError -> returns 1
    assert code != 0, (
        f"CLI _run_interface_step should return non-zero for triclinic "
        f"{lattice_type} (blocked), got code={code}"
    )
    # No interface was generated
    assert pipe._interface_result is None, (
        f"CLI _interface_result should be None for blocked triclinic "
        f"{lattice_type}, got {pipe._interface_result}"
    )


# ---------------------------------------------------------------------------
# GUI: InterfaceGenerationWorker catches -> emits error signal
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lattice_type", ["c0te", "c1te"])
def test_gui_interface_worker_blocks_triclinic(triclinic_hydrates, lattice_type):
    """GUI ``InterfaceGenerationWorker`` emits error signal for triclinic filled ice.

    The GUI worker (workers.py:146, 200, 215-218) catches
    ``InterfaceGenerationError`` and emits the ``error`` signal.
    ``InterfaceGenerationWorker`` is a ``QObject`` (NOT ``QThread`` —
    workers.py:146), so ``run()`` is called directly (synchronous): it
    executes and returns after emitting ``error`` on
    ``InterfaceGenerationError``. No ``QThread``, ``worker.start()``,
    ``worker.wait()``, or ``QTest.qWait`` is needed.
    """
    # Headless GUI: set offscreen platform if not already set
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    # Lazy import PySide6 inside the test (AGENTS.md: no top-level GUI imports)
    from PySide6.QtWidgets import QApplication

    # Lazy import the GUI worker inside the test (AGENTS.md: lazy imports)
    from quickice.gui.workers import InterfaceGenerationWorker

    # QApplication instance (singleton — reuse if one already exists)
    app = QApplication.instance() or QApplication(sys.argv)

    chain = triclinic_hydrates[lattice_type]
    config = InterfaceConfig(
        mode="slab",
        box_x=3.0,
        box_y=3.0,
        box_z=8.0,
        ice_thickness=2.0,
        water_thickness=4.0,
        seed=42,
    )

    # Construct the worker (QObject, NOT QThread)
    worker = InterfaceGenerationWorker(chain.candidate, config)

    # Collect error signals emitted by the worker. Connect BEFORE calling
    # run() so the signal is captured during the synchronous execution.
    errors = []
    worker.error.connect(lambda msg: errors.append(msg))

    # Call run() directly (synchronous — no QThread needed). run() calls
    # generate_interface -> validate_interface_config -> raises
    # InterfaceGenerationError -> except block emits error signal
    # (workers.py:215-218).
    worker.run()

    # The worker caught InterfaceGenerationError and emitted the error signal
    assert len(errors) > 0, (
        f"GUI InterfaceGenerationWorker should emit error signal for triclinic "
        f"{lattice_type} (blocked), but no error signal was emitted"
    )
    # The error message should mention the triclinic lattice
    error_msg = errors[0]
    assert "triclinic" in error_msg.lower(), (
        f"Error message should contain 'triclinic' for {lattice_type}: "
        f"{error_msg}"
    )
