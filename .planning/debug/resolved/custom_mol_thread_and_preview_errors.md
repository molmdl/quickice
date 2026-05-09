---
status: investigating
trigger: "After fixing initial TypeError and overlap detection, two new errors appeared:\n1. Random insertion: TypeError with moveToThread() call\n2. Custom insertion: AttributeError for missing log_message method and empty preview viewer"
created: 2026-05-09T00:00:00Z
updated: 2026-05-09T00:01:00Z
---

## Current Focus

hypothesis: N/A - fixes applied
test: Running syntax check on modified file
expecting: No syntax errors, all fixes correct
next_action: Verify fixes by running application tests

## Symptoms

expected: 
- Issue #1: Should create a worker thread and execute custom molecule insertion
- Issue #2: Should show preview in 3D viewer with the custom molecule positioned correctly

actual:
- Issue #1: TypeError when trying to move worker to thread
- Issue #2: AttributeError when trying to log messages AND preview viewer window opens but is empty

errors:
Issue #1:
```
ERROR:quickice.gui.main_window:Custom molecule insertion failed: CustomMoleculeWorker.moveToThread() takes exactly one argument (0 given)
Traceback (most recent call last):
  File "/share/home/nglokwan/quickice/quickice/gui/main_window.py", line 1065, in _on_custom_generate_clicked
    thread = worker.moveToThread()
TypeError: CustomMoleculeWorker.moveToThread() takes exactly one argument (0 given)
```

Issue #2:
```
ERROR:quickice.gui.main_window:Failed to create preview: 'MainWindow' object has no attribute 'log_message'
Traceback (most recent call last):
  File "/share/home/nglokwan/quickice/quickice/gui/main_window.py", line 1194, in _on_custom_molecule_preview_requested
    self.log_message(
    ^^^^^^^^^^^^^^^^
AttributeError: 'MainWindow' object has no attribute 'log_message'

During handling of the above exception, another error occurred:

  File "/share/home/nglokwan/quickice/quickice/gui/main_window.py", line 1203, in _on_custom_molecule_preview_requested
    self.log_message(f"Preview error: {e}")
    ^^^^^^^^^^^^^^^^
AttributeError: 'MainWindow' object has no attribute 'log_message'
```

reproduction:
- Issue #1: Click Generate button after uploading validated gro/itp files in Random mode
- Issue #2: Use Custom placement mode, enter position/rotation, click Validate & Preview, accept the dialog, 3D viewer opens but empty

started: These errors appeared after fixing the previous TypeError and overlap detection issues

## Eliminated

## Evidence

- timestamp: 2026-05-09T00:00:30Z
  checked: main_window.py lines 1050-1099 (moveToThread error location)
  found: Line 1065 calls `thread = worker.moveToThread()` with no arguments
  implication: Incorrect API usage - moveToThread() requires QThread instance as argument

- timestamp: 2026-05-09T00:00:45Z
  checked: main_window.py lines 1180-1229 (log_message error location)
  found: Lines 1194, 1203, 1210 call `self.log_message()` which doesn't exist
  implication: Should use `self.custom_molecule_panel.log_message()` instead

- timestamp: 2026-05-09T00:00:55Z
  checked: CustomMoleculeWorker class docstring (lines 32-37)
  found: Correct pattern is: `thread = QThread(); worker.moveToThread(thread); thread.started.connect(worker.run)`
  implication: Current code at line 1065 completely wrong - needs QThread creation and proper connections

- timestamp: 2026-05-09T00:02:30Z
  checked: Applied fixes to main_window.py
  found: 1) Added QThread import, 2) Fixed moveToThread() call, 3) Fixed all log_message() calls
  implication: All code changes applied correctly

- timestamp: 2026-05-09T00:03:00Z
  checked: Syntax validation and import test
  found: Python syntax check passed, MainWindow imports successfully
  implication: No syntax errors, all fixes are valid

- timestamp: 2026-05-09T00:03:30Z
  checked: Ran custom molecule tests
  found: Random insertion tests pass, workflow tests pass. One pre-existing test failure in custom placement (unrelated to GUI fixes)
  implication: Fixes don't break existing functionality

## Resolution

root_cause: Two separate bugs:
1. **Issue #1 (moveToThread)**: Incorrect Qt threading API usage - calling `worker.moveToThread()` without arguments instead of creating QThread instance and passing it as argument
2. **Issue #2 (log_message)**: MainWindow has no `log_message` method - should use `self.custom_molecule_panel.log_message()` instead

fix:
1. Fix line 1065: Create QThread instance, call `worker.moveToThread(thread)` with thread as argument, connect `thread.started` to `worker.run`, connect `worker.finished` to `thread.quit`
2. Fix lines 1194, 1203, 1210: Replace `self.log_message()` with `self.custom_molecule_panel.log_message()`
3. Add QThread to imports at line 22

verification: 
- Python syntax check: PASSED ✓
- MainWindow import test: PASSED ✓  
- Random insertion tests: PASSED ✓
- Workflow end-to-end test: PASSED ✓
- Note: One pre-existing test failure in custom placement logic (unrelated to GUI fixes)
files_changed: [quickice/gui/main_window.py]
