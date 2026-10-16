"""True-e2e partial-export guard (48.4 hardening, audit Finding 1).

The audit's headline failure: a malformed/broken required ITP staging (e.g.
a custom guest ITP whose source is missing) produced a partial export dir —
``hydrate.gro`` + ``hydrate.top`` + ``tip4p-ice.itp`` written, guest ITP
absent, and rc=0. The failure flows through
``copy_custom_guest_itp`` (already narrow, returns ``None`` by contract
pinned in ``tests/test_cli/test_itp_helpers_custom_guest.py``) and the
caller's ``if itp_name:`` silently skips — so narrowing the four broad
``except Exception`` sites (plan 48.4-01 Task 1) alone does NOT close it.

Task 2 adds a post-staging reconciliation in
``pipeline.py::_run_export_step`` (immediately after
``copy_itp_files_for_structure``, inside the existing ``try:``): every
``#include`` target parsed from the just-written ``{step}.top`` must exist
in the output dir, else ``raise ValueError`` — riding the existing
``except (OSError, ValueError)`` catch at ``pipeline.py:1006`` ->
``logger.error`` + ``report_progress(f"Export step failed: {e}")`` ->
rc=1. One invariant closes EVERY silent-omission path.

RED-first: tests 1-2 were created BEFORE the reconciliation and FAIL on the
pre-fix tree (rc==0, silent partial dir — the audit signature reproduced
live; recorded in 48.4-01-SUMMARY.md). Test 3 passes pre- and post-fix
(over-trigger regression guard).

CLI surface (mirrors ``tests/e2e/solute_ion/test_e2e_cli_zero_ion_export.py``):
``CLIPipeline(args=SimpleNamespace())`` with only ``_hydrate_result`` +
``_output_dir`` set, ``_run_export_step()`` called directly — no Qt/VTK
imports. Module-scoped fixtures amortize the GenIce2 calls.

Fixture mechanics (verified chain, plan 48.4-01 Task 2):

* ``missing_itp_hydrate`` — real sI hydrate with a custom guest
  ``etoh_partial_guard`` whose ``guest_itp_path`` points at a path that does
  NOT exist (named ``etoh.itp`` — the .top's ``#include`` uses
  ``Path(ci["itp_path"]).name``, ``interface_writer.py:842``). Generation
  reads only the ``.gro`` (``build_custom_guest_module``,
  ``custom_guest_bridge.py:71-174`` — no ITP read, no residue-name gate;
  the >3-char check lives in ``validate_custom_guest_files``, the GUI-upload
  validator, never called by generation). The TOP writer tolerates the
  missing file (``_merge_custom_atomtypes`` -> ``parse_itp_atomtypes``
  catches ``(IOError, OSError)`` at ``quickice/output/_itp.py:136``, warns,
  returns ``[]``) but still emits ``#include "etoh.itp"``.
  ``guest_residue_name="MOL"`` — NOT "ETHAN": ETHAN_H (7 chars) trips the
  GRO writer's residue-name guard (``interface_writer.py:383-384``, runs
  BEFORE staging) and would fail with the wrong error.
* ``valid_guest_hydrate`` — same shape with the REAL bundled
  ``quickice/data/custom/etoh.itp`` and 3x3x3 supercell. Precondition
  assert: shortest cell vector > 2 × 1.0 nm (the true grompp PBC rule,
  rcoulomb=rvdw=1.0 in em.mdp; sI a ≈ 1.2 nm -> 3x3x3 ≈ 3.6 nm, clears the
  rule with headroom).
"""

import shutil
from types import SimpleNamespace

import numpy as np
import pytest

from quickice.cli.pipeline import CLIPipeline
from quickice.structure_generation.hydrate_generator import (
    HydrateStructureGenerator,
)
from quickice.structure_generation.types import HydrateConfig

from tests.conftest import gmx_skipif
from tests.e2e_export_helpers import (
    MDP_PATH,
    run_gmx_grompp,
    assert_itp_completeness,
    assert_gro_top_consistent,
)

_GUEST_ATOM_LABELS = ["H", "C", "H", "H", "C", "H", "H", "O", "H"]
_GUEST_ATOM_COUNT = 9
_GUEST_GRO_PATH = "quickice/data/custom/etoh.gro"
_GUEST_ITP_PATH = "quickice/data/custom/etoh.itp"


def _assert_grompp_pbc_precondition(hydrate) -> None:
    """Shortest cell vector must exceed 2 x 1.0 nm (rcoulomb=rvdw=1.0)."""
    shortest = min(float(np.linalg.norm(v)) for v in hydrate.cell)
    assert shortest > 2.0, (
        f"grompp PBC precondition broken: shortest cell vector {shortest:.4f} nm "
        "<= 2 x 1.0 nm cut-off — supercell choice no longer satisfies the box "
        "rule; re-diagnose before touching this fixture"
    )


@pytest.fixture(scope="module")
def missing_itp_hydrate(tmp_path_factory):
    """sI hydrate with a custom etoh guest whose ITP SOURCE does not exist.

    Reproduces the audit's headline scenario deterministically: the .gro is
    real (bundled etoh.gro) so generation, GRO and TOP writing all succeed —
    only the guest ITP staging fails (source missing), which pre-fix yields
    rc=0 with a partial export dir (the audit signature).

    UNIQUE guest_type slug (module convention) to avoid sys.modules key
    collisions with other custom-guest test modules.
    """
    missing_itp = tmp_path_factory.mktemp("missing_guest_itp") / "etoh.itp"
    config = HydrateConfig(
        lattice_type="sI",
        guest_type="etoh_partial_guard",
        guest_residue_name="MOL",
        guest_gro_path=_GUEST_GRO_PATH,
        guest_itp_path=str(missing_itp),
        guest_atom_labels=list(_GUEST_ATOM_LABELS),
        guest_atom_count=_GUEST_ATOM_COUNT,
        supercell_x=1,
        supercell_y=1,
        supercell_z=1,
    )
    return HydrateStructureGenerator().generate(config)


@pytest.fixture(scope="module")
def valid_guest_hydrate():
    """sI hydrate with a custom etoh guest and the REAL bundled ITP (3x3x3).

    Supercell 3x3x3 (sI a ~ 1.2 nm -> ~3.6 nm cell) clears the true grompp
    PBC rule (box must exceed 2 x cut-off = 2.0 nm) with headroom.
    """
    config = HydrateConfig(
        lattice_type="sI",
        guest_type="etoh_partial_guard_ok",
        guest_residue_name="MOL",
        guest_gro_path=_GUEST_GRO_PATH,
        guest_itp_path=_GUEST_ITP_PATH,
        guest_atom_labels=list(_GUEST_ATOM_LABELS),
        guest_atom_count=_GUEST_ATOM_COUNT,
        supercell_x=3,
        supercell_y=3,
        supercell_z=3,
    )
    hydrate = HydrateStructureGenerator().generate(config)
    _assert_grompp_pbc_precondition(hydrate)
    return hydrate


def test_required_guest_itp_missing_source_export_fails(
    missing_itp_hydrate, tmp_path, capsys
):
    """Audit's headline scenario: required guest ITP fails to stage -> rc=1.

    Pre-fix: rc=0 with hydrate.gro + hydrate.top + tip4p-ice.itp written and
    etoh.itp absent — a silent partial export (RED). Post-fix: rc=1 with
    ``[PROGRESS] Export step failed:`` and the missing filename ``etoh.itp``
    on stderr (GREEN). The gro/top still exist (writers run BEFORE staging) —
    the partial export is real; the export now REPORTS failure instead of
    claiming success.
    """
    ws = tmp_path
    pipe = CLIPipeline(args=SimpleNamespace())
    pipe._output_dir = ws
    pipe._hydrate_result = missing_itp_hydrate

    rc = pipe._run_export_step()

    err = capsys.readouterr().err
    assert rc == 1, (
        f"_run_export_step with an unstaged required guest ITP must return 1, "
        f"got {rc} (pre-48.4 silent partial export: rc=0)"
    )
    assert "[PROGRESS] Export step failed:" in err, (
        f"stderr missing the fail-fast progress line:\n{err}"
    )
    assert "etoh.itp" in err, (
        f"stderr must name the missing ITP (etoh.itp):\n{err}"
    )

    # The partial export is real: writers ran before staging.
    assert (ws / "hydrate.gro").exists(), f"hydrate.gro not written in {ws}"
    assert (ws / "hydrate.top").exists(), f"hydrate.top not written in {ws}"
    assert not (ws / "etoh.itp").exists(), (
        "etoh.itp unexpectedly staged — the missing-source repro precondition "
        "is broken; re-diagnose before touching this test"
    )


def test_missing_required_itp_reconciliation_guard(
    valid_guest_hydrate, monkeypatch, tmp_path, capsys
):
    """Reconciliation fires on a silent omission with an INTACT config.

    Isolates the reconciliation from missing-file mechanics: a fully valid
    config (real bundled etoh.itp), with the omission injected purely by
    monkeypatching ``copy_custom_guest_itp`` (called by module-global name at
    itp_helpers.py:328) to return ``None`` — the exact silent-None contract
    the pinned unit tests require. Staging 'succeeds' with no staging log
    noise; only the post-staging #include reconciliation can catch it. The
    .top's ``#include`` names the real bundled file's basename (etoh.itp).
    """
    monkeypatch.setattr(
        "quickice.cli.itp_helpers.copy_custom_guest_itp", lambda *a, **k: None
    )

    ws = tmp_path
    pipe = CLIPipeline(args=SimpleNamespace())
    pipe._output_dir = ws
    pipe._hydrate_result = valid_guest_hydrate

    rc = pipe._run_export_step()

    err = capsys.readouterr().err
    assert rc == 1, (
        f"_run_export_step with a silently-omitted required ITP must return 1, "
        f"got {rc}"
    )
    assert "[PROGRESS] Export step failed:" in err, (
        f"stderr missing the fail-fast progress line:\n{err}"
    )
    assert "etoh.itp" in err, (
        f"stderr must name the omitted ITP (etoh.itp):\n{err}"
    )


@gmx_skipif
def test_valid_custom_guest_export_still_succeeds(valid_guest_hydrate, tmp_path):
    """Over-trigger regression guard: a valid custom-guest export stays rc=0.

    The reconciliation must NOT fire for valid exports (mirrors
    ``test_ion_present_export_keeps_ion_include``): rc=0, every #include'd
    ITP present (``assert_itp_completeness``), gro/top consistent, and
    ``gmx grompp`` rc==0.
    """
    ws = tmp_path
    pipe = CLIPipeline(args=SimpleNamespace())
    pipe._output_dir = ws
    pipe._hydrate_result = valid_guest_hydrate

    rc = pipe._run_export_step()
    assert rc == 0, f"_run_export_step (valid custom-guest hydrate) rc={rc}"

    gro_path = ws / "hydrate.gro"
    top_path = ws / "hydrate.top"
    assert gro_path.exists() and top_path.exists(), (
        f"hydrate export files missing in {ws}"
    )
    assert (ws / "etoh.itp").exists(), f"etoh.itp not staged in {ws}"

    assert_itp_completeness(str(top_path), ws)
    assert_gro_top_consistent(str(gro_path), str(top_path))

    shutil.copy(MDP_PATH, ws / "em.mdp")
    gmx_rc, stderr = run_gmx_grompp(
        ws, gro_file="hydrate.gro", top_file="hydrate.top"
    )
    assert gmx_rc == 0, (
        f"gmx grompp failed for valid custom-guest export:\n{stderr[-1000:]}"
    )
