---
phase: 020-version-bump-4.5
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - quickice/__init__.py
  - quickice/cli/parser.py
autonomous: true

must_haves:
  truths:
    - "Version string in __init__.py shows 4.5.0"
    - "CLI --version flag displays 4.5.0"
  artifacts:
    - path: "quickice/__init__.py"
      provides: "Package version constant"
      contains: '__version__ = "4.5.0"'
    - path: "quickice/cli/parser.py"
      provides: "CLI version display"
      contains: 'version="%(prog)s 4.5.0"'
  key_links:
    - from: "quickice/__init__.py"
      to: "quickice package version"
      via: "__version__ constant"
---

<objective>
Update version strings from 4.0.0 to 4.5.0 across the codebase.

Purpose: Align code version with README documentation (v4.5) and current milestone status.
Output: Consistent 4.5.0 version across all version references.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md

Current state:
- README.md claims v4.5
- quickice/__init__.py has __version__ = "4.0.0"
- quickice/cli/parser.py has version="%(prog)s 4.0.0"
</context>

<tasks>

<task type="auto">
  <name>Update version strings to 4.5.0</name>
  <files>
    - quickice/__init__.py
    - quickice/cli/parser.py
  </files>
  <action>
Update version strings in two files:

1. **quickice/__init__.py** (line 3):
   - Change: `__version__ = "4.0.0"`
   - To: `__version__ = "4.5.0"`

2. **quickice/cli/parser.py** (line 175):
   - Change: `version="%(prog)s 4.0.0"`
   - To: `version="%(prog)s 4.5.0"`

Use semantic versioning format: 4.5.0 (not 4.5) for consistency.
  </action>
  <verify>
    ```bash
    # Check __init__.py version
    grep -n '__version__ = "4.5.0"' quickice/__init__.py

    # Check CLI parser version
    grep -n 'version="%(prog)s 4.5.0"' quickice/cli/parser.py

    # Verify no old version strings remain
    ! grep -r "4.0.0" quickice/__init__.py quickice/cli/parser.py
    ```
  </verify>
  <done>
Both files updated with consistent 4.5.0 version string. No 4.0.0 references remain in version-related code.
  </done>
</task>

</tasks>

<verification>
1. Grep confirms 4.5.0 in both files
2. No 4.0.0 version strings remain
3. CLI `--version` would display 4.5.0 (verified via grep)
</verification>

<success_criteria>
- [ ] quickice/__init__.py contains `__version__ = "4.5.0"`
- [ ] quickice/cli/parser.py contains `version="%(prog)s 4.5.0"`
- [ ] No 4.0.0 version strings in modified files
</success_criteria>

<output>
After completion, create `.planning/quick/020-version-bump-4.5/020-SUMMARY.md`
</output>
