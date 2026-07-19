"""Regression tests for scancode Group 9 documentation/citation-label fixes.

Covers:
- CLI #3: the bundled TIP4P-ICE data file uses the hyphen form
  ``tip4p-ice.itp`` and ``quickice/main.py`` must use the same hyphen
  destination filename so the produced file matches the
  ``#include "tip4p-ice.itp"`` line written in the .top files.
- CLI I1: the "TIP4P-ICE" citation label must sit next to DOI
  ``10.1063/1.1931662`` (Abascal 2005, per AGENTS.md), not next to
  ``10.1063/1.2121687`` (TIP4P/2005).
- Item 2 (follow-up): the TIP4P-ICE paper TITLE on the
  ``10.1063/1.1931662`` line in ``types.py`` must match README.md's
  title for the same DOI (verified via doi.org to be "A potential
  model for the study of ices and amorphous water: TIP4P/Ice").
- Item 3 (follow-up): the TIP4P/2005 DOI in ``types.py`` must be
  ``10.1063/1.2121687`` (the old ``10.1063/1.2121600`` returns 404
  from both doi.org and Crossref; the new DOI was verified via
  doi.org to resolve to "A general purpose model for the condensed
  phases of water: TIP4P/2005" by Abascal & Vega 2005).
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

    The TIP4P/2005 label must sit next to DOI ``10.1063/1.2121687`` (which
    self-identifies as TIP4P/2005 by its title). The previous code reversed
    these labels: 'For TIP4P-ICE specifically' was attached to the
    10.1063/1.2121600 (TIP4P/2005) reference.

    This test only checks the LABEL-to-DOI assignment. It does NOT verify
    the paper titles (a separate follow-up issue, Item 2: the title on
    the 10.1063/1.1931662 line was wrong and is now fixed to match
    README.md's title for the same DOI). Per the plan, CLI I1 swaps labels
    only and does not touch titles or DOIs. (Item 3 subsequently corrected
    the TIP4P/2005 DOI from the 404 10.1063/1.2121600 to the verified
    10.1063/1.2121687; this test was updated to track the new DOI.)
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

    # Find the line carrying DOI 10.1063/1.2121687 (TIP4P/2005).
    # Item 3 follow-up: the old DOI 10.1063/1.2121600 returns 404 from both
    # doi.org and Crossref; the verified DOI for "A general purpose model
    # for the condensed phases of water: TIP4P/2005" (Abascal & Vega 2005,
    # J. Chem. Phys. 123, 234505) is 10.1063/1.2121687.
    f2005_doi_line = next(
        (i for i, ln in enumerate(lines) if "10.1063/1.2121687" in ln), None
    )
    assert f2005_doi_line is not None, (
        "DOI 10.1063/1.2121687 not found in types.py"
    )
    f2005_context = "\n".join(
        lines[max(0, f2005_doi_line - 2): f2005_doi_line + 1]
    )
    assert "TIP4P/2005" in f2005_context, (
        "The 'TIP4P/2005' label must be near DOI 10.1063/1.2121687. "
        f"Context:\n{f2005_context}"
    )
    assert "TIP4P-ICE" not in f2005_context, (
        "The 'TIP4P-ICE' label must NOT be near DOI 10.1063/1.2121687. "
        f"Context:\n{f2005_context}"
    )


def test_tip4p_2005_doi_resolves():
    """Item 3 (follow-up): the TIP4P/2005 DOI in ``types.py`` must be
    ``10.1063/1.2121687`` (the verified DOI for "A general purpose model
    for the condensed phases of water: TIP4P/2005" by Abascal & Vega 2005,
    J. Chem. Phys. 123, 234505).

    The old DOI ``10.1063/1.2121600`` returns 404 from both doi.org AND
    Crossref — it is wrong. The user verified ``10.1063/1.2121687`` via
    doi.org (resolves to the TIP4P/2005 paper, matching the existing
    title/author/journal in types.py:36-38). The TIP4P/2005 reference is
    an informational comment (not used by code), so the fix is in-place
    DOI correction, not removal.
    """
    types_py = (
        Path(quickice.__file__).parent
        / "structure_generation"
        / "types.py"
    )
    content = types_py.read_text()

    # The old (404) DOI must NOT be present.
    old_doi = "10.1063/1.2121600"
    assert old_doi not in content, (
        f"types.py must not carry the broken (404) TIP4P/2005 DOI {old_doi!r}. "
        "Use 10.1063/1.2121687 (verified via doi.org)."
    )

    # The new (verified) DOI must be present.
    new_doi = "10.1063/1.2121687"
    assert new_doi in content, (
        f"types.py must carry the verified TIP4P/2005 DOI {new_doi!r}."
    )

    # The TIP4P/2005 reference must still be present (Item 3 keeps the
    # reference, only corrects the DOI).
    assert "TIP4P/2005" in content, (
        "The TIP4P/2005 informational reference must remain in types.py "
        "(Item 3 corrects the DOI in-place, does not remove the reference)."
    )
    assert (
        "A general purpose model for the condensed phases of water: TIP4P/2005"
        in content
    ), (
        "The TIP4P/2005 paper title must remain in types.py."
    )


def test_tip4p_ice_paper_title_matches_readme():
    """Item 2 (follow-up): the TIP4P-ICE paper TITLE on the
    ``10.1063/1.1931662`` line in ``types.py`` must match README.md's
    title for the same DOI.

    The old title in ``types.py:33`` was "A potential model for the
    phase diagram of TIP4P water" — that title belongs to a DIFFERENT
    paper (the original TIP4P paper, Abascal & Vega 2005 is NOT "phase
    diagram of TIP4P water"). The actual title for DOI 10.1063/1.1931662
    (verified via doi.org) is "A potential model for the study of ices
    and amorphous water: TIP4P/Ice" — which already appears in
    ``README.md:237``. This test guards against the title regressing.
    """
    types_py = (
        Path(quickice.__file__).parent
        / "structure_generation"
        / "types.py"
    )
    readme_md = (
        Path(quickice.__file__).parent.parent / "README.md"
    )

    types_content = types_py.read_text()
    readme_content = readme_md.read_text()

    # The correct title (verified via doi.org for 10.1063/1.1931662 and
    # already present in README.md:237).
    correct_title = "A potential model for the study of ices and amorphous water: TIP4P/Ice"

    # README must contain the correct title (canonical source).
    assert correct_title in readme_content, (
        f"README.md must contain the canonical TIP4P-ICE title "
        f"{correct_title!r}"
    )

    # The wrong title must NOT appear in types.py.
    wrong_title = "A potential model for the phase diagram of TIP4P water"
    assert wrong_title not in types_content, (
        f"types.py must not carry the wrong TIP4P-ICE title "
        f"{wrong_title!r} — the actual title for DOI 10.1063/1.1931662 "
        f"is {correct_title!r}."
    )

    # The correct title must appear in types.py near the
    # 10.1063/1.1931662 DOI line.
    types_lines = types_content.splitlines()
    ice_doi_line = next(
        (i for i, ln in enumerate(types_lines) if "10.1063/1.1931662" in ln),
        None,
    )
    assert ice_doi_line is not None, (
        "DOI 10.1063/1.1931662 not found in types.py"
    )
    # Title sits 1-2 lines above the DOI line.
    ice_context = "\n".join(
        types_lines[max(0, ice_doi_line - 2): ice_doi_line + 1]
    )
    assert correct_title in ice_context, (
        f"types.py must carry the canonical TIP4P-ICE title "
        f"{correct_title!r} near DOI 10.1063/1.1931662. "
        f"Context:\n{ice_context}"
    )
