"""Regression tests for scancode Group 9 documentation/citation-label fixes.

Covers:
- CLI #3: the bundled TIP4P-ICE data file uses the hyphen form
  ``tip4p-ice.itp`` and ``quickice/main.py`` must use the same hyphen
  destination filename so the produced file matches the
  ``#include "tip4p-ice.itp"`` line written in the .top files.
- CLI I1: the "TIP4P-ICE" citation label must sit next to DOI
  ``10.1063/1.1931662`` (Abascal 2005, per AGENTS.md), not next to
  ``10.1063/1.2121600`` (TIP4P/2005).
"""
from pathlib import Path

import quickice


REPO_ROOT = Path(quickice.__file__).resolve().parent.parent


def test_tip4p_ice_itp_data_file_exists():
    """CLI #3: the bundled TIP4P-ICE data file is ``tip4p-ice.itp`` (hyphen).

    ``get_tip4p_itp_path()`` returns this file, and both ``main.py`` and
    ``cli/itp_helpers.py`` copy it to the output directory. The destination
    filename must match the ``#include "tip4p-ice.itp"`` line in the
    generated ``.top`` files (see ``gui/export.py:391,1120``).
    """
    data_file = Path(quickice.__file__).parent / "data" / "tip4p-ice.itp"
    assert data_file.exists(), (
        f"Expected bundled TIP4P-ICE data file at {data_file} (hyphen form). "
        "If this file is renamed, update get_tip4p_itp_path() and every "
        "destination filename that must match the .top #include line."
    )


def test_main_py_uses_hyphen_itp_destination():
    """CLI #3: ``quickice/main.py`` must use the hyphen destination filename.

    The pipeline path (``cli/itp_helpers.py:314``) writes ``tip4p-ice.itp``.
    ``main.py`` must use the SAME destination filename so the produced
    file matches the ``#include "tip4p-ice.itp"`` line in the .top file.
    Using the underscore form (``tip4p_ice.itp``) here would produce a
    file GROMACS ``grompp`` cannot find.
    """
    main_py = Path(quickice.__file__).parent / "main.py"
    content = main_py.read_text()
    # The destination filename must be the hyphen form.
    assert '"tip4p-ice.itp"' in content, (
        "main.py must set itp_filename = \"tip4p-ice.itp\" (hyphen) so the "
        "produced file matches the .top #include line. Found no hyphen form."
    )
    # The underscore form must NOT appear as a destination filename literal.
    # (It is OK if it appears in a comment explaining the old bug; guard the
    # check by looking for the assignment pattern.)
    import re
    bad = re.search(r'itp_filename\s*=\s*["\']tip4p_ice\.itp["\']', content)
    assert bad is None, (
        f"main.py still assigns the underscore form at: {bad.group(0)!r}. "
        "Use \"tip4p-ice.itp\" (hyphen) to match the .top #include line."
    )


def test_tip4p_ice_label_on_correct_doi():
    """CLI I1: the 'TIP4P-ICE' citation label must sit next to DOI
    ``10.1063/1.1931662`` (Abascal 2005), per AGENTS.md.

    The TIP4P/2005 label must sit next to DOI ``10.1063/1.2121600`` (which
    self-identifies as TIP4P/2005 by its title). The previous code reversed
    these labels: 'For TIP4P-ICE specifically' was attached to the
    10.1063/1.2121600 (TIP4P/2005) reference.

    This test only checks the LABEL-to-DOI assignment. It does NOT verify
    the paper titles (a separate pre-existing issue: the title on the
    10.1063/1.1931662 line does not match README.md's title for the same
    DOI). Per the plan, CLI I1 swaps labels only and does not touch titles
    or DOIs.
    """
    types_py = (
        Path(quickice.__file__).parent
        / "structure_generation"
        / "types.py"
    )
    lines = types_py.read_text().splitlines()

    # Find the line carrying DOI 10.1063/1.1931662 (TIP4P-ICE per AGENTS.md).
    ice_doi_line = next(
        (i for i, ln in enumerate(lines) if "10.1063/1.1931662" in ln), None
    )
    assert ice_doi_line is not None, (
        "DOI 10.1063/1.1931662 not found in types.py"
    )
    # The label sits 1-2 lines above the DOI line.
    ice_context = "\n".join(lines[max(0, ice_doi_line - 2): ice_doi_line + 1])
    assert "TIP4P-ICE" in ice_context, (
        "The 'TIP4P-ICE' label must be near DOI 10.1063/1.1931662. "
        f"Context:\n{ice_context}"
    )
    assert "TIP4P/2005" not in ice_context, (
        "The 'TIP4P/2005' label must NOT be near DOI 10.1063/1.1931662. "
        f"Context:\n{ice_context}"
    )

    # Find the line carrying DOI 10.1063/1.2121600 (TIP4P/2005).
    f2005_doi_line = next(
        (i for i, ln in enumerate(lines) if "10.1063/1.2121600" in ln), None
    )
    assert f2005_doi_line is not None, (
        "DOI 10.1063/1.2121600 not found in types.py"
    )
    f2005_context = "\n".join(
        lines[max(0, f2005_doi_line - 2): f2005_doi_line + 1]
    )
    assert "TIP4P/2005" in f2005_context, (
        "The 'TIP4P/2005' label must be near DOI 10.1063/1.2121600. "
        f"Context:\n{f2005_context}"
    )
    assert "TIP4P-ICE" not in f2005_context, (
        "The 'TIP4P-ICE' label must NOT be near DOI 10.1063/1.2121600. "
        f"Context:\n{f2005_context}"
    )
