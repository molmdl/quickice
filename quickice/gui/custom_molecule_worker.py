"""Background worker for custom molecule validation and insertion.

This module provides the CustomMoleculeWorker class for running custom molecule
insertion in a background thread, preventing UI freezing during:
- GRO file parsing
- Placement execution (random or custom)
- Overlap checking (for random mode)
"""

import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal, QThread

logger = logging.getLogger(__name__)


class CustomMoleculeWorker(QObject):
    """Worker for running custom molecule insertion in background thread.
    
    Follows the same pattern as InterfaceGenerationWorker: QObject with run method,
    NOT subclassing QThread. Imports inside run() for thread safety.
    
    Signals:
        progress: Emitted with percentage (0-100)
        status: Emitted with status message
        finished: Emitted with CustomMoleculeStructure on completion
        error: Emitted with error message on failure
        cancelled: Emitted when cancellation is confirmed
    
    Usage:
        worker = CustomMoleculeWorker(config, structure, gro_path, itp_path)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        thread.start()
    """
    
    progress = Signal(int)
    status = Signal(str)
    finished = Signal(object)  # CustomMoleculeStructure
    error = Signal(str)
    cancelled = Signal()
    
    def __init__(
        self,
        config,
        structure,
        gro_path: Path,
        itp_path: Path
    ):
        """Initialize the custom molecule worker.
        
        Args:
            config: CustomMoleculeConfig with placement settings
            structure: InterfaceStructure (ice + water) to insert into
            gro_path: Path to custom molecule .gro file
            itp_path: Path to custom molecule .itp file
        """
        super().__init__()
        self._config = config
        self._structure = structure
        self._gro_path = gro_path
        self._itp_path = itp_path
    
    def run(self):
        """Execute custom molecule insertion - runs in separate thread.
        
        Imports inside run() to avoid blocking main thread.
        """
        try:
            # Check for cancellation
            if QThread.currentThread().isInterruptionRequested():
                self.cancelled.emit()
                return
            
            self.status.emit("Loading custom molecule...")
            self.progress.emit(10)
            
            # Import inside run() for thread safety
            from quickice.structure_generation.custom_molecule_inserter import (
                CustomMoleculeInserter,
                InsertionError
            )
            from quickice.structure_generation.gro_parser import parse_gro_file
            
            # Parse GRO file to get template
            template_positions, template_atom_names, template_cell = parse_gro_file(
                self._gro_path
            )
            
            self.progress.emit(20)
            self.status.emit("Initializing placement...")
            
            # Create inserter
            inserter = CustomMoleculeInserter(self._config)
            
            self.progress.emit(40)
            
            # Execute placement based on mode
            if self._config.placement_mode == "random":
                self.status.emit("Placing molecules randomly...")
                result = inserter.place_random(
                    self._structure,
                    self._config.molecule_count
                )
            else:  # custom mode
                self.status.emit("Placing molecules at specified positions...")
                result = inserter.place_custom(
                    self._structure,
                    self._config.positions,
                    self._config.rotations
                )
            
            self.progress.emit(90)
            self.status.emit("Complete")
            self.progress.emit(100)
            
            logger.info(f"Custom molecule insertion complete: {result.custom_molecule_count} molecules")
            self.finished.emit(result)
            
        except InsertionError as e:
            error_msg = f"Insertion failed after {e.attempts} attempts: {e.message}"
            logger.error(error_msg)
            self.error.emit(error_msg)
            
        except Exception as e:
            error_msg = f"Custom molecule insertion failed ({type(e).__name__}): {e}"
            logger.error(error_msg, exc_info=True)
            self.error.emit(error_msg)
