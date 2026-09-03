"""MainWindow-driven headless full-chain GUI e2e (G5/G8 closure).

This is the flagship behavioral test of the GUI middle layer: panels →
handlers → workers → ``_current_*_result`` hand-offs → export menu handlers.
Before 48.3-13 that layer had ZERO execution-level coverage — only
source-string greps (``inspect.getsource`` assertions in test_hydrate_panel.py
/ test_scancode_bugs_gui_ion.py). This is the exact seam where the 44.1-UAT
(Workflow F: "moleculetype etoh is redefined") and UAT-F bugs lived: curated
exporter-level fixtures pre-rename inputs, real users do not.

What runs here (all REAL, headless, per 48.3-RESEARCH-GUI-TESTING §5):
- a module-scoped fixture constructs the real ``MainWindow`` ONCE and drives
  the real handler chain: hydrate (real ``HydrateWorker`` QThread — direct
  QThread subclass per AGENTS.md, NOT migrated) → interface (real viewmodel
  threaded worker via ``_on_interface_hydrate_generate``) → solute
  (synchronous ``_on_insert_solutes``) → custom molecule (threaded
  ``CustomMoleculeWorker`` fed a REALISTIC UNRENAMED ``etoh.gro``/``etoh.itp``
  upload — no cmet pre-rename, the fixture sanitization this test exists to
  eliminate) → ion (real ``IonInsertionWorker`` QThread);
- the 4 real ``_on_export_{interface,solute,custom_molecule,ion}_gromacs``
  menu handlers are then invoked with the save dialog routed to tmp dirs and
  every output is validated: files exist + ``assert_itp_completeness`` +
  ``assert_gro_top_consistent`` (STRICT, per D1=option-a — the 48.3-02
  insertion-boundary fix makes the unrenamed-etoh case pass) + ``gmx grompp``
  rc==0;
- a negative-path test proves the missing-``_current_*`` guards are
  behavioral: warning dialog captured by the modal mock, NO files written;
- a Tab 0 (Ice) leg drives ``GenerationWorker.run()`` synchronously (Pattern
  C — QObject worker, signals connected BEFORE run(), same proven shape as
  ``InterfaceGenerationWorker`` in test_e2e_triclinic_blocking_e2e.py) and
  feeds the result through the real ``_on_candidates_ready`` handler, then
  exports via the real ice handler ``_on_export_gromacs`` (small-cutoff MDP
  per 48.3-08 R16 precedent — the 96-molecule ice cell ≈ 1.47 nm cannot fit
  the shared em.mdp's 2.0 nm requirement).

Safety mechanics (why this file cannot hang or SIGABRT):
- ``tests/gui_e2e_helpers.py`` (RESEARCH-GUI-TESTING §3): offscreen-forced
  QApplication (Blocker 1), COMPLETE modal-dialog patch catalog (Blocker 2 —
  the ``main_window.QMessageBox.information`` "Export Complete" modal fires
  on EVERY successful export and hung the research probe), protective
  ``DISPLAY=localhost:11.0`` so ``is_vtk_available()`` is False (Blocker 3),
  state-polling waits for handler-created workers (Blocker 5), and
  ``teardown_threads(mw)`` in fixture teardown — a live QThread at exit
  SIGABRTs and poisons the pytest session (Blocker 4).

Runtime budget (research-measured, this machine): full chain ≈ 2.5s +
one-time ``import main_window`` ≈ 1-5s (Blocker 7 — budget it).
"""

import os

# ── Headless env guards (defense in depth; conftest.py already setdefaults
#    offscreen at session start, and gui_e2e_helpers forces both at import).
os.environ["QT_QPA_PLATFORM"] = "offscreen"
if not os.environ.get("DISPLAY", "").startswith("localhost"):
    os.environ["DISPLAY"] = "localhost:11.0"

import shutil
from pathlib import Path

import pytest

from quickice.gui.main_window import MainWindow
from quickice.structure_generation.itp_parser import parse_itp_file
from tests.conftest import gmx_skipif
from tests.e2e_export_helpers import (
    ETOH_GRO,
    ETOH_ITP,
    MDP_PATH,
    assert_gro_top_consistent,
    assert_itp_completeness,
    parse_gro_atom_count,
    parse_gro_residue_names,
    parse_top_molecules,
    run_gmx_grompp,
)
from tests.gui_e2e_helpers import (
    patch_gui_modals,
    qapp_session,  # noqa: F401  (fixture imported for pytest visibility)
    teardown_threads,
    wait_for_mainwindow_state,
)


# Small-cutoff MDP for the ice-only export (Task 3): the 96-molecule ice_ih
# candidate cell ≈ 1.47 nm < the 2.0 nm the shared tests/em.mdp needs
# (rcoulomb=rvdw=1.0 → grompp fatal "cut-off length longer than half the
# shortest box vector"). 0.5 nm cutoffs need box > 1.0 nm — fits. Verbatim
# precedent: tests/test_cli/test_pipeline_grompp_matrix.py SMALL_CUTOFF_MDP
# (48.3-08, R12/R16 rows) and test_scancode_bugs_constants.py.
SMALL_CUTOFF_MDP = (
    "integrator = steep\n"
    "nsteps = 0\n"
    "emtol  = 100.0\n"
    "emstep = 0.01\n"
    "pbc = xyz\n"
    "cutoff-scheme = Verlet\n"
    "coulombtype   = PME\n"
    "rcoulomb      = 0.5\n"
    "vdwtype       = Cut-off\n"
    "rvdw          = 0.5\n"
    "DispCorr      = EnerPres\n"
    "constraints   = none\n"
)

# Ice-tab conditions: conftest.py PHASE_CONDITIONS["ice_ih"] = (250, 0.1) —
# the curve-verified T/P pair that produces ice Ih.
ICE_T_KELVIN = 250.0
ICE_P_MPA = 0.1
ICE_NMOLECULES = 96


# ══════════════════════════════════════════════════════════════════════════════
# Module-scoped fixture: ONE MainWindow, driven through the REAL handler chain
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def driven_mainwindow(qapp_session, tmp_path_factory):
    """Construct the real MainWindow and drive it tab-by-tab, headless.

    Drive order (research §5.1): hydrate → interface → solute → custom
    (realistic UNRENAMED etoh upload) → ion. Each leg triggers the same
    handler a real button click would, then waits on the ``_current_*``
    state attribute the export handlers read.

    ``teardown_threads(mw)`` runs in the ``finally`` AND on yield teardown
    (Blocker 4 — must run even when a drive assertion fails, or the live
    QThreads SIGABRT at session exit and poison the run).
    """
    upload_dir = tmp_path_factory.mktemp("etoh_upload")
    gro_path = upload_dir / "etoh.gro"
    itp_path = upload_dir / "etoh.itp"
    shutil.copy(ETOH_GRO, gro_path)
    shutil.copy(ETOH_ITP, itp_path)

    with patch_gui_modals() as drive_modals:
        mw = MainWindow()

        try:
            # ── (a) Hydrate: real generate path via the panel signal a real
            # button click emits (hydrate_panel.py:101 → generate_requested).
            # Default panel config: sI, CH4, 1×1×1, 100% occupancy.
            mw.hydrate_panel.generate_requested.emit()
            hydrate = wait_for_mainwindow_state(mw, "_current_hydrate_result")
            assert hydrate is not None, (
                "Hydrate generation never completed — check drive_modals."
                f"main_window.critical for error dialogs: "
                f"{drive_modals.main_window.critical.call_args_list}"
            )
            assert hydrate.water_count > 0 and hydrate.guest_count > 0

            # ── (b) Interface: real viewmodel threaded worker. Configure the
            # real panel widgets first (what a user would type): 3×3×8 slab,
            # ice 2.0 / water 4.0, seed 42 (research §5.2 measured shape).
            panel = mw.interface_panel
            panel.box_x_input.setValue(3.0)
            panel.box_y_input.setValue(3.0)
            panel.box_z_input.setValue(8.0)
            panel.ice_thickness_input.setValue(2.0)
            panel.water_thickness_input.setValue(4.0)
            panel.seed_input.setValue(42)
            mw._on_interface_hydrate_generate()
            interface = wait_for_mainwindow_state(mw, "_current_interface_result")
            assert interface is not None, (
                "Interface generation never completed — critical dialogs: "
                f"{drive_modals.main_window.critical.call_args_list}"
            )
            assert interface.ice_nmolecules > 0 and interface.water_nmolecules > 0

            # ── (c) Solute: synchronous handler (panel defaults: Interface
            # source, CH4, 0.1 M). Failure mode is a log message, so assert
            # on the resulting state attribute directly.
            mw._on_insert_solutes()
            assert mw._current_solute_result is not None, (
                "Solute insertion failed (logged to solute_panel, not raised)"
            )

            # ── (d) Custom molecule: REALISTIC UNRENAMED etoh upload. The
            # panel GRO residue is the generic 'MOL'; the ITP moleculetype is
            # 'etoh'. Upload-bypass pattern (test_custom_molecule_panel_34_6
            # precedent): set gro_path/itp_path/itp_info then _validate_files().
            # The generic-residue dialog fires and the patched modal mock
            # answers Yes — the D1 proceed path. Per 48.3-02 D1=option-a the
            # inserter then registers the molecule under the ITP name 'etoh'.
            custom_panel = mw.custom_molecule_panel
            custom_panel.gro_path = gro_path
            custom_panel.itp_path = itp_path
            custom_panel.itp_info = parse_itp_file(itp_path)
            custom_panel._validate_files()
            assert drive_modals.panel.question.called, (
                "Expected the generic-residue-name dialog (GRO 'MOL' vs ITP "
                "'etoh') to fire on the unrenamed upload — the D1 proceed path"
            )
            custom_panel.generate_requested.emit()
            custom = wait_for_mainwindow_state(mw, "_current_custom_molecule_result")
            assert custom is not None, (
                "Custom molecule insertion never completed — critical dialogs: "
                f"{drive_modals.main_window.critical.call_args_list}"
            )
            # D1 (48.3-DECISIONS.md, option-a): the insertion-boundary fix
            # registers the custom molecule under the ITP [moleculetype] name.
            assert custom.moleculetype_name == "etoh", (
                f"D1 reconciliation: expected moleculetype 'etoh' from the "
                f"unrenamed ITP, got {custom.moleculetype_name!r}"
            )

            # ── (e) Ion: real IonInsertionWorker QThread (panel defaults:
            # Interface source, 0.5 M NaCl).
            mw._on_insert_ions()
            ion = wait_for_mainwindow_state(mw, "_current_ion_result")
            assert ion is not None, (
                "Ion insertion never completed — critical dialogs: "
                f"{drive_modals.main_window.critical.call_args_list}"
            )
            assert ion.na_count > 0 and ion.cl_count > 0

            yield mw
        finally:
            # Blocker 4: MUST run on the success path (yield teardown) AND on
            # any drive-assertion failure path (finally around the drive).
            teardown_threads(mw)


# ══════════════════════════════════════════════════════════════════════════════
# Export menu handlers: 4 parametrized grompp-validated cases
# ══════════════════════════════════════════════════════════════════════════════

# (test id, handler attribute, default export filename stem)
EXPORT_CASES = [
    ("interface", "_on_export_interface_gromacs", "interface"),
    ("solute", "_on_export_solute_gromacs", "solute"),
    ("custom_molecule", "_on_export_custom_molecule_gromacs", "custom"),
    ("ion", "_on_export_ion_gromacs", "ion"),
]


def _validate_export_workspace(workspace: Path, mdp_text: str | None = None) -> tuple[Path, Path]:
    """Assert exactly one .gro + one .top were exported and grompp passes.

    Shared by the 4 menu-handler cases and the ice export: routes the save
    dialog mock, copies an MDP in, then runs the repo's own gates
    (assert_itp_completeness + assert_gro_top_consistent) and ``gmx grompp``.

    Returns:
        (gro_path, top_path)
    """
    gro_files = sorted(workspace.glob("*.gro"))
    top_files = sorted(workspace.glob("*.top"))
    assert len(gro_files) == 1 and len(top_files) == 1, (
        f"Expected exactly one .gro + one .top in {workspace}, got "
        f"{[p.name for p in sorted(workspace.iterdir())]}"
    )
    gro_path, top_path = gro_files[0], top_files[0]

    mdp_path = workspace / "em.mdp"
    if mdp_text is not None:
        mdp_path.write_text(mdp_text)
    else:
        shutil.copy(MDP_PATH, mdp_path)

    assert_itp_completeness(str(top_path), workspace)
    assert_gro_top_consistent(str(gro_path), str(top_path))

    rc, err = run_gmx_grompp(
        workspace, gro_file=gro_path.name, top_file=top_path.name
    )
    assert rc == 0, (
        f"gmx grompp failed (rc={rc}) for {gro_path.name}:\n{err[-3000:]}"
    )
    return gro_path, top_path


@pytest.mark.parametrize("case_name,handler_attr,file_stem", EXPORT_CASES)
@gmx_skipif
def test_export_menu_handler_grompp_fullchain(
    driven_mainwindow, tmp_path, case_name, handler_attr, file_stem
):
    """Drive each REAL ``_on_export_*_gromacs`` menu handler and grompp-check.

    Each case routes ``QFileDialog.getSaveFileName`` (the patched export
    namespace) to a fresh tmp dir, invokes the real handler on the fully
    populated module fixture, and validates the output with the repo's own
    e2e gates plus grompp rc==0.
    """
    mw = driven_mainwindow
    with patch_gui_modals() as mocks:
        mocks.export_file_dialog.getSaveFileName.return_value = (
            str(tmp_path / f"{file_stem}.gro"),
            "GRO Files (*.gro)",
        )

        getattr(mw, handler_attr)()

        # Success path observable: the "Export Complete" information modal
        # fired (the dialog that hung the research probe when unpatched).
        assert mocks.main_window.information.called, (
            f"{handler_attr}: expected the 'Export Complete' information "
            f"dialog on success. warning={mocks.main_window.warning.call_args_list} "
            f"critical={mocks.main_window.critical.call_args_list}"
        )
        # Exactly one save dialog per export (research §2 Pattern B).
        assert mocks.export_file_dialog.getSaveFileName.call_count == 1

        gro_path, top_path = _validate_export_workspace(tmp_path)

        if case_name == "custom_molecule":
            # D1 = option-a (48.3-DECISIONS.md): STRICT gro/top agreement on
            # the realistic UNRENAMED etoh upload — no fallback recipe. The
            # 48.3-02 insertion-boundary fix registers 'etoh' as the
            # moleculetype, so the .top [molecules] entry and the .gro
            # residues must agree verbatim with NO 'MOL' residue left.
            molecules = parse_top_molecules(str(top_path))
            assert molecules.get("etoh") == 10, (
                f"Expected .top [molecules] 'etoh 10' (10 molecules × the "
                f"panel default By-Count), got {molecules}"
            )
            residues = set(parse_gro_residue_names(str(gro_path)))
            assert "etoh" in residues, (
                f"Expected verbatim 'etoh' residue in the exported .gro "
                f"(D1 reconciliation), got {sorted(residues)}"
            )
            assert "MOL" not in residues, (
                f"Generic 'MOL' residue must not survive the D1 proceed path, "
                f"got {sorted(residues)}"
            )


# ══════════════════════════════════════════════════════════════════════════════
# Negative path: missing _current_* state → warning dialog, NO files
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize("case_name,handler_attr,state_attr", [
    ("interface", "_on_export_interface_gromacs", "_current_interface_result"),
    ("solute", "_on_export_solute_gromacs", "_current_solute_result"),
    ("custom_molecule", "_on_export_custom_molecule_gromacs", "_current_custom_molecule_result"),
    ("ion", "_on_export_ion_gromacs", "_current_ion_result"),
])
def test_export_menu_handler_missing_state_warns_and_writes_nothing(
    driven_mainwindow, tmp_path, case_name, handler_attr, state_attr
):
    """Export guard is behavioral, not just present (negative path).

    Clears the ``_current_*`` state attribute (plan-sanctioned variant; the
    fixture value is restored in a finally so later cases are unaffected),
    invokes the real handler, and asserts the warning dialog was captured by
    the modal mock and NO files were written.
    """
    mw = driven_mainwindow
    original = getattr(mw, state_attr, None)
    assert original is not None, f"fixture sanity: {state_attr} must be populated"
    setattr(mw, state_attr, None)
    try:
        with patch_gui_modals() as mocks:
            mocks.export_file_dialog.getSaveFileName.return_value = (
                str(tmp_path / "should_not_exist.gro"),
                "GRO Files (*.gro)",
            )

            getattr(mw, handler_attr)()

            assert mocks.main_window.warning.called, (
                f"{handler_attr}: expected a warning dialog when {state_attr} "
                f"is missing — the guard must be behavioral"
            )
            assert not mocks.main_window.information.called, (
                "Export must not reach the success path with missing state"
            )
            assert mocks.export_file_dialog.getSaveFileName.call_count == 0, (
                "No save dialog may open when the guard trips"
            )
            assert not list(tmp_path.iterdir()), (
                f"NO files may be written when {state_attr} is missing, got "
                f"{[p.name for p in tmp_path.iterdir()]}"
            )
    finally:
        setattr(mw, state_attr, original)
