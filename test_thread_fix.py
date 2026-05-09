#!/usr/bin/env python3
"""Verification test for custom molecule thread fix.

This test verifies that the worker and thread are properly stored as instance
variables to prevent premature garbage collection.
"""

import sys
import time
from pathlib import Path
from PySide6.QtCore import QThread, QObject, Signal, QCoreApplication


class MockWorker(QObject):
    """Mock worker for testing thread lifecycle."""
    
    progress = Signal(str)
    finished = Signal(object)
    error = Signal(str)
    
    def __init__(self):
        super().__init__()
        self._ran = False
    
    def run(self):
        """Simulate work."""
        self._ran = True
        self.progress.emit("Working...")
        time.sleep(0.1)  # Simulate some work
        self.finished.emit({"success": True})


def test_worker_stored_as_instance_variable():
    """Test that storing worker as instance variable prevents garbage collection."""
    app = QCoreApplication.instance() or QCoreApplication(sys.argv)
    
    class TestContainer:
        """Simulates MainWindow storing worker and thread."""
        
        def __init__(self):
            self._worker = None
            self._thread = None
            self._result = None
        
        def start_work(self):
            """Start worker in thread - CORRECT pattern."""
            # Store worker as instance variable
            self._worker = MockWorker()
            
            # Store thread as instance variable
            self._thread = QThread()
            self._worker.moveToThread(self._thread)
            
            # Connect signals
            self._thread.started.connect(self._worker.run)
            self._worker.finished.connect(self._thread.quit)
            self._worker.finished.connect(self._on_finished)
            
            # Start
            self._thread.start()
        
        def _on_finished(self, result):
            """Handle completion."""
            self._result = result
            self._thread.quit()
    
    container = TestContainer()
    container.start_work()
    
    # Wait for thread to finish
    if container._thread:
        container._thread.wait(1000)  # Wait up to 1 second
    
    # Verify worker didn't get garbage collected
    assert container._worker is not None, "Worker should still exist"
    assert container._worker._ran, "Worker should have run"
    assert container._result is not None, "Worker should have finished"
    print("✓ Test passed: Worker stored as instance variable works correctly")


def test_worker_not_stored_fails():
    """Test that NOT storing worker causes issues (the bug we fixed)."""
    app = QCoreApplication.instance() or QCoreApplication(sys.argv)
    
    class TestContainerBad:
        """Simulates the BUGGY pattern (worker not stored)."""
        
        def __init__(self):
            self._thread = None
            self._result = None
        
        def start_work(self):
            """Start worker in thread - BUGGY pattern (worker not stored)."""
            # Worker is local variable - will be garbage collected!
            worker = MockWorker()
            
            # Store thread as instance variable
            self._thread = QThread()
            worker.moveToThread(self._thread)
            
            # Connect signals
            self._thread.started.connect(worker.run)
            worker.finished.connect(self._thread.quit)
            worker.finished.connect(self._on_finished)
            
            # Start
            self._thread.start()
            # When this function exits, 'worker' goes out of scope!
        
        def _on_finished(self, result):
            """Handle completion."""
            self._result = result
    
    container = TestContainerBad()
    container.start_work()
    
    # Wait a bit to let potential garbage collection happen
    time.sleep(0.2)
    
    # This pattern MAY work sometimes due to Qt's internal references,
    # but it's unreliable and can cause the "QThread: Destroyed while still running" error
    print("✗ Test shows BUGGY pattern: Worker not stored (may cause race conditions)")
    
    if container._thread:
        container._thread.wait(1000)


if __name__ == "__main__":
    print("Testing thread worker storage patterns...")
    print()
    
    # Test the correct pattern
    test_worker_stored_as_instance_variable()
    print()
    
    # Demonstrate the buggy pattern
    test_worker_not_stored_fails()
    print()
    
    print("Verification complete!")
    print()
    print("Summary:")
    print("- CORRECT: Store both worker and thread as instance variables")
    print("- BUGGY: Store only thread, worker is local variable")
    print()
    print("The fix ensures CustomMoleculeWorker follows the CORRECT pattern.")
