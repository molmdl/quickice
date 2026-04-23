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
    
    # Interface generation signals (Tab 2)
    interface_generation_started = Signal()
    interface_generation_progress = Signal(int)
    interface_generation_status = Signal(str)
    interface_generation_complete = Signal(object)  # InterfaceStructure
    interface_generation_error = Signal(str)
    interface_generation_cancelled = Signal()
    interface_ui_enabled_changed = Signal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: Optional[GenerationWorker] = None
        self._thread: Optional[QThread] = None
        self._is_generating = False
        self._last_ranking_result: Optional[RankingResult] = None
        
        # Interface generation state (Tab 2)
        self._interface_worker = None  # InterfaceGenerationWorker
        self._interface_thread: Optional[QThread] = None
        self._is_interface_generating = False
        self._last_interface_result = None  # Stores InterfaceStructure
    
    def start_generation(self, temperature: float, pressure: float, nmolecules: int):
        """Start ice structure generation in background thread.
        
        Args:
            temperature: Temperature in Kelvin (0-500)
            pressure: Pressure in MPa (0-10000)
            nmolecules: Number of molecules (4-216)
        """
        # Clean up any existing thread
        # Use timeout to prevent UI freeze during long operations
        if self._thread and self._thread.isRunning():
            self._thread.requestInterruption()
            self._thread.quit()
            # Wait with timeout to avoid blocking UI thread
            # Thread will finish naturally via signal handlers if timeout expires
            self._thread.wait(100)  # 100ms timeout
        
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
        # Use timeout to prevent UI freeze during long operations
        if self._thread and self._thread.isRunning():
            self._thread.requestInterruption()
            self._thread.quit()
            # Wait with timeout to avoid blocking UI thread
            self._thread.wait(100)  # 100ms timeout
        
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
    
    # === Interface Generation Methods (Tab 2) ===
    
    def start_interface_generation(self, candidate, config):
        """Start interface structure generation in background thread.
        
        Args:
            candidate: Candidate object from Tab 1
            config: InterfaceConfig with generation parameters
        """
        # Import here to avoid circular imports
        from quickice.gui.workers import InterfaceGenerationWorker
        
        # Clean up any existing thread
        # Use timeout to prevent UI freeze during long operations
        if self._interface_thread and self._interface_thread.isRunning():
            self._interface_thread.requestInterruption()
            self._interface_thread.quit()
            # Wait with timeout to avoid blocking UI thread
            self._interface_thread.wait(100)  # 100ms timeout
        
        # Create worker
        self._interface_worker = InterfaceGenerationWorker(candidate, config)
        
        # Create thread
        self._interface_thread = QThread()
        self._interface_worker.moveToThread(self._interface_thread)
        
        # Connect signals
        self._interface_thread.started.connect(self._interface_worker.run)
        self._interface_worker.progress.connect(self._on_interface_progress)
        self._interface_worker.status.connect(self._on_interface_status)
        self._interface_worker.finished.connect(self._on_interface_finished)
        self._interface_worker.error.connect(self._on_interface_error)
        self._interface_worker.cancelled.connect(self._on_interface_cancelled)
        
        # Cleanup
        self._interface_thread.finished.connect(self._interface_worker.deleteLater)
        self._interface_thread.finished.connect(self._interface_thread.deleteLater)
        
        # Update state
        self._is_interface_generating = True
        self.interface_ui_enabled_changed.emit(False)
        self.interface_generation_started.emit()
        
        # Start thread
        self._interface_thread.start()
    
    def cancel_interface_generation(self):
        """Cancel running interface generation."""
        # Use timeout to prevent UI freeze during long operations
        if self._interface_thread and self._interface_thread.isRunning():
            self._interface_thread.requestInterruption()
            self._interface_thread.quit()
            # Wait with timeout to avoid blocking UI thread
            self._interface_thread.wait(100)  # 100ms timeout
        
        self._is_interface_generating = False
        self.interface_ui_enabled_changed.emit(True)
        self.interface_generation_cancelled.emit()
    
    def get_last_interface_result(self):
        """Get the most recent interface generation result.
        
        Returns:
            The last InterfaceStructure from generation, or None.
        """
        return self._last_interface_result
    
    def is_interface_generating(self) -> bool:
        """Check if interface generation is in progress."""
        return self._is_interface_generating
    
    # === Interface Worker signal handlers ===
    
    @Slot(int)
    def _on_interface_progress(self, value: int):
        self.interface_generation_progress.emit(value)
    
    @Slot(str)
    def _on_interface_status(self, text: str):
        self.interface_generation_status.emit(text)
    
    @Slot(object)
    def _on_interface_finished(self, result):
        print(f"[DEBUG viewmodel.py] _on_interface_finished() called - success={result.success}")
        self._is_interface_generating = False
        self.interface_ui_enabled_changed.emit(True)
        
        if result.success:
            print(f"[DEBUG viewmodel.py] Emitting interface_generation_complete signal")
            self._last_interface_result = result.result
            self.interface_generation_complete.emit(result.result)
            print("[DEBUG viewmodel.py] interface_generation_complete signal emitted!")
        else:
            print(f"[DEBUG viewmodel.py] Emitting interface_generation_error signal: {result.error}")
            self.interface_generation_error.emit(result.error or "Unknown error")
    
    @Slot(str)
    def _on_interface_error(self, error_msg: str):
        self._is_interface_generating = False
        self.interface_ui_enabled_changed.emit(True)
        self.interface_generation_error.emit(error_msg)
    
    @Slot()
    def _on_interface_cancelled(self):
        self._is_interface_generating = False
        self.interface_ui_enabled_changed.emit(True)
        self.interface_generation_cancelled.emit()
