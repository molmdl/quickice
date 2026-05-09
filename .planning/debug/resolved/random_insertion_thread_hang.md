---
status: resolved
trigger: "Random insertion appears to hang - log shows \"running\" but nothing happens, and there's a QThread warning about thread being destroyed while still running"
created: 2026-05-09T00:00:00Z
updated: 2026-05-09T00:06:00Z
---

## Current Focus

hypothesis: CONFIRMED - Worker object is being garbage collected because it's not stored as an instance variable
test: Compare all worker creation patterns in codebase
expecting: All other workers are stored as instance variables, only CustomMoleculeWorker is not
next_action: Implement fix by storing worker as instance variable

## Eliminated

## Evidence

- timestamp: 2026-05-09T00:01:00Z
  checked: main_window.py lines 1057-1079 (_on_custom_generate_clicked method)
  found: Worker is created as local variable, moved to thread, but worker is NOT stored as instance variable. Only thread is stored at line 1076.
  implication: Worker object may be garbage collected when function exits, causing thread to have no worker to run

- timestamp: 2026-05-09T00:01:30Z
  checked: viewmodel.py lines 79-83 (start_generation method)
  found: Both worker and thread are stored as instance variables (self._worker and self._thread)
  implication: This is the correct pattern - both worker and thread must be kept alive

- timestamp: 2026-05-09T00:02:00Z
  checked: main_window.py __init__ method (lines 59-114)
  found: No initialization of self._custom_worker_thread or self._custom_worker
  implication: These variables are created on-the-fly but worker is not persisted

- timestamp: 2026-05-09T00:03:00Z
  checked: All worker creation patterns in codebase (grep for "worker = .*Worker\(")
  found: 
    - viewmodel.py line 79: self._worker = GenerationWorker(...) ✓ STORED
    - viewmodel.py line 194: self._interface_worker = InterfaceGenerationWorker(...) ✓ STORED
    - main_window.py line 749: self._hydrate_worker = HydrateWorker(...) ✓ STORED
    - main_window.py line 1057: worker = CustomMoleculeWorker(...) ✗ NOT STORED
  implication: CustomMoleculeWorker is the ONLY worker not stored as instance variable - this is the bug

- timestamp: 2026-05-09T00:03:30Z
  checked: HydrateWorker pattern (main_window.py line 749)
  found: HydrateWorker subclasses QThread directly, so storing it keeps both worker and thread alive
  implication: Different pattern from worker-object pattern used by CustomMoleculeWorker

## Resolution

root_cause: CustomMoleculeWorker object is created as a local variable and not stored as an instance attribute. When _on_custom_generate_clicked() exits, the Python wrapper for the worker goes out of scope and gets garbage collected, even though the worker has been moved to the thread. This causes the thread to have no valid worker to execute, resulting in the Qt warning "QThread: Destroyed while thread '' is still running" and the apparent hang.
fix: Store both worker and thread as instance variables (self._custom_worker and self._custom_worker_thread) to prevent garbage collection. Updated cleanup in _on_custom_finished to properly delete both worker and thread.
verification: Created test_thread_fix.py that demonstrates the bug (worker not stored causes "QThread: Destroyed while thread '' is still running" error and crash). The fix follows the correct pattern used in viewmodel.py for all other workers. All existing custom molecule panel tests pass.
files_changed: [/share/home/nglokwan/quickice/quickice/gui/main_window.py]
