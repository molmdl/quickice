"""Regression test for scancode issue C1: missing ``logger`` in piece.py.

``quickice/structure_generation/modes/piece.py`` used ``logger.warning(...)``
at its bounds-check branch (``assemble_piece`` → ``if atoms_per_mol >
len(centered_ice_positions)``) but never imported ``logging`` nor defined a
module-level ``logger``. The branch therefore raised ``NameError`` instead of
emitting a warning — the only real crash in the C1 issue class.

The fix mirrors ``quickice/structure_generation/solute_inserter.py`` (which
already has ``import logging`` + ``logger = logging.getLogger(__name__)``):
add ``import logging`` before ``import numpy as np`` and define
``logger = logging.getLogger(__name__)`` after the import block.

These tests are the required regression floor (per the 20260723 fix plan):
  * ``test_piece_module_has_logger`` — the module exposes a ``logger`` that is
    a real ``logging.Logger`` (proves the import + getLogger lines landed).
  * ``test_piece_logger_warning_no_nameerror`` — calling ``piece.logger.warning``
    does not raise ``NameError`` (the exact C1 failure mode).
  * ``test_piece_logger_warning_emits_via_caplog`` (optional, lightweight) —
    the warning is emitted under the expected logger name, proving the wiring
    without driving the full ``assemble_piece`` flow (which would need heavy
    GenIce2 fixtures or fragile monkeypatching to hit the branch condition).
"""

import logging

import pytest

from quickice.structure_generation.modes import piece


def test_piece_module_has_logger():
    """piece.py exposes a module-level ``logger`` that is a real logging.Logger.

    This proves both the ``import logging`` line and the
    ``logger = logging.getLogger(__name__)`` line landed (issue C1 fix).
    """
    assert isinstance(piece.logger, logging.Logger)


def test_piece_logger_warning_no_nameerror():
    """Calling ``piece.logger.warning`` does not raise NameError.

    Pre-fix, ``logger`` was referenced at the bounds-check branch but never
    bound, so any execution of that branch raised ``NameError: name 'logger'
    is not defined``. This test exercises the exact symbol the branch uses.
    """
    # Should not raise NameError (the C1 failure mode) nor any other exception.
    piece.logger.warning("regression test: piece.logger is bound")


def test_piece_logger_warning_emits_via_caplog(caplog):
    """Optional (lightweight): the warning is emitted under the piece logger name.

    A stronger version of the no-NameError test: the warning lands on the
    ``quickice.structure_generation.modes.piece`` logger (the same logger the
    ``assemble_piece`` bounds-check branch references at piece.py:~361), so any
    future code reaching that branch will emit a captured warning rather than
    ``NameError``. This avoids the heavy GenIce2 fixtures / fragile
    monkeypatching that driving ``assemble_piece`` directly would require.
    """
    expected_logger_name = "quickice.structure_generation.modes.piece"
    assert piece.logger.name == expected_logger_name

    with caplog.at_level(logging.WARNING, logger=expected_logger_name):
        piece.logger.warning("caplog regression check")

    assert any(
        "caplog regression check" in record.getMessage()
        and record.name == expected_logger_name
        and record.levelno == logging.WARNING
        for record in caplog.records
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
