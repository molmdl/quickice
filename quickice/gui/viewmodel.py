"""ViewModel layer for QuickIce GUI.

This module provides the MVVM ViewModel that orchestrates the worker thread
and manages UI state, bridging the View and Model layers.
"""

from PySide6.QtCore import QObject, Signal, QThread, Slot
from typing import Optional

from quickice.gui.workers import GenerationWorker, GenerationResult
from quickice.ranking.types import RankingResult


class MainViewModel(QObject):
    """ViewModel for managing UI state and worker thread.
    
    Follows MVVM pattern:
    - View calls start_generation() on ViewModel
    - ViewModel creates Worker and moves it to QThread
    - Worker emits signals -> ViewModel forwards to View
    - View updates based on ViewModel signals
    """
    
    # Signals for UI updates (View connects to these)
    generation_started = Signal()           # Emitted when generation starts
    generation_progress = Signal(int)       # Progress percentage (0-100)
    generation_status = Signal(str)        # Status message
    generation_complete = Signal(object)    # Emitted with result on success
    generation_error = Signal(str)          # Emitted with error message
    generation_cancelled = Signal()         # Emitted when cancelled
    
    # UI state signals
    ui_enabled_changed = Signal(bool)       # True = UI enabled, False = generating
    
    # Viewer state signals (Phase 10)
    ranked_candidates_ready = Signal(object)  # Emitted with RankingResult
    generation_log = Signal(str)               # Streaming log messages
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: Optional[GenerationWorker] = None
        self._thread: Optional[QThread] = None
        self._is_generating = False
        self._last_ranking_result: Optional[RankingResult] = None
    
    def start_generation(self, temperature: float, pressure: float, nmolecules: int):
        """Start ice structure generation in background thread.
        
        Args:
            temperature: Temperature in Kelvin (0-500)
            pressure: Pressure in MPa (0-10000)
            nmolecules: Number of molecules (4-216)
        """
        # Clean up any existing thread
        if self._thread and self._thread.isRunning():
            self._thread.requestInterruption()
            self._thread.quit()
            self._thread.wait()
        
        # Create worker
        self._worker = GenerationWorker(temperature, pressure, nmolecules)
        
        # Create thread
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        
        # Connect worker signals to ViewModel slots
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.status.connect(self._on_status)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.cancelled.connect(self._on_cancelled)
        
        # Cleanup on thread finish
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        
        # Update state
        self._is_generating = True
        self.ui_enabled_changed.emit(False)  # Disable UI
        self.generation_started.emit()
        
        # Start thread
        self._thread.start()
    
    def cancel_generation(self):
        """Cancel running generation."""
        if self._thread and self._thread.isRunning():
            self._thread.requestInterruption()
            self._thread.quit()
            self._thread.wait()
        
        self._is_generating = False
        self.ui_enabled_changed.emit(True)  # Re-enable UI
        self.generation_cancelled.emit()
    
    def is_generating(self) -> bool:
        """Check if generation is in progress."""
        return self._is_generating
    
    # === Worker signal handlers ===
    
    @Slot(int)
    def _on_progress(self, value: int):
        """Handle worker progress signal."""
        self.generation_progress.emit(value)
    
    @Slot(str)
    def _on_status(self, text: str):
        """Handle worker status signal."""
        self.generation_status.emit(text)
    
    @Slot(object)
    def _on_finished(self, result: GenerationResult):
        """Handle worker finished signal."""
        self._is_generating = False
        self.ui_enabled_changed.emit(True)  # Re-enable UI
        
        if result.success:
            # Store the ranking result for viewer access
            self._last_ranking_result = result.result
            # Emit generation_complete for backward compatibility
            self.generation_complete.emit(result.result)
            # Emit ranked_candidates_ready for viewer
            self.ranked_candidates_ready.emit(result.result)
        else:
            self.generation_error.emit(result.error or "Unknown error")
    
    @Slot(str)
    def _on_error(self, error_msg: str):
        """Handle worker error signal."""
        self._is_generating = False
        self.ui_enabled_changed.emit(True)  # Re-enable UI
        self.generation_error.emit(error_msg)
    
    @Slot()
    def _on_cancelled(self):
        """Handle worker cancelled signal."""
        self._is_generating = False
        self.ui_enabled_changed.emit(True)  # Re-enable UI
        self.generation_cancelled.emit()
    
    def get_last_ranking_result(self) -> Optional[RankingResult]:
        """Get the most recent ranking result.
        
        Returns:
            The last RankingResult from generation, or None if no generation
            has completed successfully yet.
        """
        return self._last_ranking_result
