"""Tests for the CLI --depol flag (Phase 45-12, closes CLI-03).

This is the ONLY code-change plan in Phase 45 (all other plans are test-only).
The --depol flag threads depolarization mode (strict/optimal, default strict)
from the CLI parser to HydrateConfig.depol_mode in CLIPipeline._run_source_step.

Coverage:
  1. test_depol_arg_parse_defaults_to_strict
     --depol not specified -> defaults to "strict" (preserves pre-change behavior).
  2. test_depol_arg_parse_accepts_optimal
     --depol accepts "optimal" and "strict" choices; argparse rejects invalid
     values BEFORE they reach HydrateConfig.__post_init__ (double safety).
  3. test_depol_threads_to_hydrate_config
     --depol optimal/strict reaches HydrateConfig.depol_mode via
     CLIPipeline._run_source_step -> HydrateConfig(depol_mode=...).

NOTE (Pitfall 1 from 45-RESEARCH.md): GenIce2 2.2.13.1 produces IDENTICAL
output for strict and optimal (Stage34E branches only on "none" vs
anything-else; both -> dipoleOptimizationCycles=1000). These tests assert
the config FIELD is threaded correctly — they do NOT assert strict !=
optimal output (that would be a false-future-proofing bug).

Background:
  - The GUI has a depol combo (hydrate_panel.py:218, strict/optimal, added in
    43-02). The CLI had NO --depol flag — depol_mode always defaulted to
    "strict" (the HydrateConfig default from 43-01).
  - HydrateConfig.__post_init__ validates depol_mode in ("strict", "optimal")
    (types.py:586, added in 43-01). hydrate_generator._run_via_api passes
    config.depol_mode to GenIce2 generate_ice(depol=...) (line 317).
  - This plan adds the argparse flag + threads it. Validation is double:
    argparse rejects invalid choices; __post_init__ rejects anything outside
    the set (defense in depth).
"""
import pytest
from types import SimpleNamespace

from quickice.cli.parser import create_parser
from quickice.cli.pipeline import CLIPipeline


def test_depol_arg_parse_defaults_to_strict():
    """--depol not specified -> defaults to 'strict'.

    The default "strict" preserves byte-identical pre-change behavior: every
    existing HydrateConfig(...) call site that omits depol_mode inherits the
    "strict" dataclass default (43-01), and the CLI now matches that.
    """
    p = create_parser()
    # --temperature/--pressure are required by create_parser(); include them
    # so parse_args succeeds (the plan's snippet omitted them — they are
    # argparse-required, not --depol-specific).
    a = p.parse_args(["--temperature", "270", "--pressure", "1", "--hydrate"])
    assert a.depol == "strict"


def test_depol_arg_parse_accepts_optimal():
    """--depol accepts 'optimal' and 'strict' choices.

    argparse choices=["strict", "optimal"] rejects invalid values (e.g.
    'banana') BEFORE they reach HydrateConfig.__post_init__ — double safety
    per the 43-01 design (QuickIce is the SOLE gatekeeper for depol validity;
    GenIce2 accepts any string silently).
    """
    p = create_parser()
    # --depol optimal
    a = p.parse_args([
        "--temperature", "270", "--pressure", "1",
        "--hydrate", "--depol", "optimal",
    ])
    assert a.depol == "optimal"
    # --depol strict (explicit)
    a = p.parse_args([
        "--temperature", "270", "--pressure", "1",
        "--hydrate", "--depol", "strict",
    ])
    assert a.depol == "strict"


def test_depol_threads_to_hydrate_config():
    """--depol optimal/strict reaches HydrateConfig.depol_mode via _run_source_step.

    Constructs CLIPipeline with a SimpleNamespace args (bypassing argparse),
    runs _run_source_step (which builds HydrateConfig + calls GenIce2), and
    asserts the resulting HydrateStructure.config.depol_mode matches the
    requested mode.

    interface=False is REQUIRED: _run_source_step (pipeline.py:353) accesses
    self.args.interface directly (not getattr) — without it the test raises
    AttributeError.

    Does NOT assert strict != optimal output (Pitfall 1 — GenIce2 2.2.13.1
    produces identical output for both modes). Only asserts the config
    FIELD is threaded correctly.
    """
    # --- optimal ---
    args = SimpleNamespace(
        hydrate=True,
        interface=False,
        depol="optimal",
        lattice_type="sI",
        guest="CH4",
        supercell_x=1,
        supercell_y=1,
        supercell_z=1,
        cage_occupancy_small=100.0,
        cage_occupancy_large=100.0,
        cage_guest=None,
    )
    pipe = CLIPipeline(args=args)
    code = pipe._run_source_step()
    assert code == 0
    assert pipe._hydrate_result.config.depol_mode == "optimal"

    # --- strict (explicit) ---
    args = SimpleNamespace(
        hydrate=True,
        interface=False,
        depol="strict",
        lattice_type="sI",
        guest="CH4",
        supercell_x=1,
        supercell_y=1,
        supercell_z=1,
        cage_occupancy_small=100.0,
        cage_occupancy_large=100.0,
        cage_guest=None,
    )
    pipe = CLIPipeline(args=args)
    code = pipe._run_source_step()
    assert code == 0
    assert pipe._hydrate_result.config.depol_mode == "strict"
