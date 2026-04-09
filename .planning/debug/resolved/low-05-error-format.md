---
status: verifying
trigger: "LOW-05 inconsistent-error-format - InterfaceGenerationError includes mode in error message but doesn't format it consistently"
created: 2026-04-09T00:00:00Z
updated: 2026-04-09T00:01:00Z
---

## Current Focus
hypothesis: Mode is stored as attribute but not included in the message string passed to parent Exception class
test: Read errors.py and verify current implementation
expecting: Find that __init__ passes bare message to super().__init__ without mode prefix
next_action: Read errors.py to verify the issue

## Symptoms
expected: Error messages should consistently include mode information
actual: Mode is stored but not always included in message string
errors: No error, but inconsistent user experience
reproduction: Trigger different InterfaceGenerationError cases
started: Always inconsistent

## Eliminated
<!-- APPEND only - prevents re-investigating -->

## Evidence
<!-- APPEND only - facts discovered -->

- timestamp: 2026-04-09T00:00:00Z
  checked: errors.py lines 25-33
  found: InterfaceGenerationError.__init__ passes bare message to super().__init__ without mode prefix, stores mode as attribute only
  implication: Error string representation does not include mode, leading to inconsistent error messages

- timestamp: 2026-04-09T00:00:00Z
  checked: interface_builder.py, modes/pocket.py
  found: Error is raised with mode parameter (e.g., mode=config.mode, mode="pocket")
  implication: Mode is being provided but not displayed to users

- timestamp: 2026-04-09T00:00:00Z
  checked: tests/test_med03_minimum_box_size.py
  found: Tests verify error messages using str(exc_info.value) and check for substrings
  implication: Fix will add mode prefix but substring assertions will still pass

## Resolution
root_cause: InterfaceGenerationError.__init__ does not include mode in the message string passed to parent Exception class
fix: Modified __init__ to format message as "[{mode}] {message}" before passing to super().__init__()
verification: Created test demonstrating mode prefix in error message, ran 19 related tests - all pass, confirmed pre-existing test_cli_integration.py failure unrelated to fix
files_changed: [quickice/structure_generation/errors.py]
fix: empty
verification: empty
files_changed: []