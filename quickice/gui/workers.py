"""Background workers for QuickIce GUI.

This module provides QThread-based workers for running computationally
intensive operations in background threads, preventing UI freezing.
"""

from PySide6.QtCore import QObject, Signal, QThread
from dataclasses import dataclass
from typing import Optional, Any


@dataclass
class GenerationResult:
    """Result from generation worker.
    
    Attributes:
        success: Whether generation completed successfully
        result: The ranking result (RankedCandidate list) on success
        error: Error message on failure
    """
    success: bool
    result: Optional[Any] = None  # The ranked result
    error: Optional[str] = None


class GenerationWorker(QObject):
    """Worker for running ice structure generation in background thread.
    
    Uses the worker-object pattern (QObject with run method, NOT subclassing QThread).
    This allows proper signal/slot connections and cancellation support.
    
    Signals:
        progress: Emitted with percentage (0-100)
        status: Emitted with status message
        finished: Emitted with GenerationResult on completion
        error: Emitted with error message on failure
        cancelled: Emitted when cancellation is confirmed
    
    Usage:
        worker = GenerationWorker(temperature=300, pressure=1, nmolecules=96)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        thread.start()
    """
    
    # Signals for progress updates
    progress = Signal(int)      # 0-100 percentage
    status = Signal(str)        # Status message
    finished = Signal(object)   # GenerationResult
    error = Signal(str)         # Error message
    cancelled = Signal()         # Cancellation confirmed
    
    def __init__(self, temperature: float, pressure: float, nmolecules: int):
        """Initialize the generation worker.
        
        Args:
            temperature: Temperature in Kelvin (0-500)
            pressure: Pressure in MPa (0-10000)
            nmolecules: Number of water molecules (4-216)
        """
        super().__init__()
        self._temperature = temperature
        self._pressure = pressure  # in MPa (no conversion needed)
        self._nmolecules = nmolecules
        self._is_cancelled = False
    
    def run(self):
        """Execute generation - runs in separate thread.
        
        This method imports modules internally to avoid blocking the main thread
        during import operations. Pressure is already in MPa (no conversion needed).
        """
        try:
            # Check for cancellation at start
            if QThread.currentThread().isInterruptionRequested():
                self.cancelled.emit()
                return
            
            # Pressure is already in MPa (no conversion needed)
            pressure_mpa = self._pressure
            
            self.status.emit("Looking up ice phase...")
            self.progress.emit(10)
            
            # Phase lookup - import inside run() to avoid blocking main thread
            from quickice.phase_mapping import lookup_phase
            phase_info = lookup_phase(self._temperature, pressure_mpa)
            self.progress.emit(20)
            
            # Check for cancellation after phase lookup
            if QThread.currentThread().isInterruptionRequested():
                self.cancelled.emit()
                return
            
            self.status.emit("Generating candidates...")
            
            # Generate candidates - import inside run()
            from quickice.structure_generation import generate_candidates
            gen_result = generate_candidates(
                phase_info=phase_info,
                nmolecules=self._nmolecules,
                n_candidates=10
            )
            self.progress.emit(60)
            
            # Check for cancellation after candidate generation
            if QThread.currentThread().isInterruptionRequested():
                self.cancelled.emit()
                return
            
            self.status.emit("Ranking candidates...")
            
            # Ranking - import inside run()
            from quickice.ranking import rank_candidates
            ranking_result = rank_candidates(candidates=gen_result.candidates)
            self.progress.emit(90)
            
            self.status.emit("Complete")
            self.progress.emit(100)
            
            result = GenerationResult(success=True, result=ranking_result)
            self.finished.emit(result)
            
        except Exception as e:
            error_result = GenerationResult(success=False, error=str(e))
            self.error.emit(str(e))
            self.finished.emit(error_result)


@dataclass
class InterfaceGenerationResult:
    """Result from interface generation worker.
    
    Attributes:
        success: Whether generation completed successfully
        result: The InterfaceStructure on success
        error: Error message on failure
    """
    success: bool
    result: Optional[Any] = None  # InterfaceStructure on success
    error: Optional[str] = None


class InterfaceGenerationWorker(QObject):
    """Worker for running interface structure generation in background thread.
    
    Follows the same pattern as GenerationWorker: QObject with run method,
    NOT subclassing QThread. Imports inside run() for thread safety.
    
    Signals:
        progress: Emitted with percentage (0-100)
        status: Emitted with status message
        finished: Emitted with InterfaceGenerationResult on completion
        error: Emitted with error message on failure
        cancelled: Emitted when cancellation is confirmed
    
    Usage:
        worker = InterfaceGenerationWorker(candidate, config)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        thread.start()
    """
    
    progress = Signal(int)
    status = Signal(str)
    finished = Signal(object)   # InterfaceGenerationResult
    error = Signal(str)
    cancelled = Signal()
    
    def __init__(self, candidate, config):
        """Initialize the interface generation worker.
        
        Args:
            candidate: Candidate object from Tab 1
            config: InterfaceConfig with generation parameters
        """
        super().__init__()
        self._candidate = candidate
        self._config = config
    
    def run(self):
        """Execute interface generation - runs in separate thread.
        
        Imports inside run() to avoid blocking main thread.
        """
        try:
            if QThread.currentThread().isInterruptionRequested():
                self.cancelled.emit()
                return
            
            self.status.emit("Validating configuration...")
            self.progress.emit(10)
            
            # Import inside run() for thread safety
            from quickice.structure_generation import generate_interface
            from quickice.structure_generation.errors import InterfaceGenerationError
            
            self.status.emit("Generating interface structure...")
            self.progress.emit(30)
            
            # Run generation
            result = generate_interface(self._candidate, self._config)
            
            self.progress.emit(90)
            self.status.emit("Complete")
            self.progress.emit(100)
            
            gen_result = InterfaceGenerationResult(success=True, result=result)
            self.finished.emit(gen_result)
            
        except InterfaceGenerationError as e:
            error_result = InterfaceGenerationResult(success=False, error=str(e))
            self.error.emit(str(e))
            self.finished.emit(error_result)
        except Exception as e:
            error_result = InterfaceGenerationResult(
                success=False, 
                error=f"Interface generation failed ({type(e).__name__}): {e}"
            )
            self.error.emit(error_result.error)
            self.finished.emit(error_result)
