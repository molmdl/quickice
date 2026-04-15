"""Background worker for hydrate structure generation.

This module provides HydrateWorker class for running GenIce2-based hydrate
generation in a background thread, preventing UI freezing during generation.
"""

from PySide6.QtCore import QThread, Signal

from quickice.structure_generation.types import (
    HydrateConfig,
    HydrateStructure,
)


class HydrateWorker(QThread):
    """QThread-based worker for hydrate structure generation.
    
    Runs GenIce2 hydrate generation in a background thread to prevent UI freezing.
    Provides signals for progress updates, completion, and error handling.
    
    Signals:
        progress_updated: Emitted with status message during generation
        generation_complete: Emitted with HydrateStructure on success
        generation_error: Emitted with error message on failure
    
    Usage:
        config = HydrateConfig(lattice_type="sI", guest_type="ch4", ...)
        worker = HydrateWorker(config)
        worker.progress_updated.connect(self.on_progress)
        worker.generation_complete.connect(self.on_complete)
        worker.generation_error.connect(self.on_error)
        worker.start()  # Runs in background thread
    """
    
    # Signals for progress and completion
    progress_updated = Signal(str)  # Status message
    generation_complete = Signal(object)  # HydrateStructure
    generation_error = Signal(str)  # Error message
    
    def __init__(self, config: HydrateConfig, parent=None):
        """Initialize the hydrate generation worker.
        
        Args:
            config: HydrateConfig with lattice, guest, occupancy, supercell settings
            parent: Optional parent QObject
        """
        super().__init__(parent)
        self._config = config
    
    def run(self):
        """Execute hydrate generation in background thread.
        
        This method runs in a separate thread. It imports HydrateStructureGenerator
        internally to avoid blocking the main thread during import operations.
        
        Emits:
            progress_updated: Status messages during generation
            generation_complete: HydrateStructure on success
            generation_error: Error message on failure
        """
        try:
            self.progress_updated.emit("Initializing hydrate generation...")
            
            # Import generator inside run() to avoid blocking main thread
            from quickice.structure_generation.hydrate_generator import HydrateStructureGenerator
            
            # Create generator instance
            generator = HydrateStructureGenerator()
            
            # Emit progress with configuration info
            lattice_info = self._config.get_genice_lattice_name()
            guest_name = self._config.guest_type.upper()
            self.progress_updated.emit(
                f"Generating {self._config.lattice_type} lattice "
                f"({lattice_info}) with {guest_name} guest..."
            )
            
            # Run generation with timeout protection
            result = generator.generate(self._config)
            
            # Emit success
            self.progress_updated.emit(
                f"Structure generated successfully: "
                f"{result.water_count} water molecules, "
                f"{result.guest_count} guest molecules"
            )
            self.generation_complete.emit(result)
            
        except ImportError as e:
            # GenIce2 not available
            error_msg = (
                "Failed to import required module for hydrate generation. "
                f"Error: {e}"
            )
            self.progress_updated.emit(f"Error: {error_msg}")
            self.generation_error.emit(error_msg)
            
        except RuntimeError as e:
            # GenIce2 generation failed
            error_msg = f"Generation failed: {e}"
            self.progress_updated.emit(f"Error: {error_msg}")
            self.generation_error.emit(error_msg)
            
        except ValueError as e:
            # Invalid configuration
            error_msg = f"Invalid configuration: {e}"
            self.progress_updated.emit(f"Error: {error_msg}")
            self.generation_error.emit(error_msg)
            
        except Exception as e:
            # Unexpected error
            error_msg = f"Unexpected error during generation ({type(e).__name__}): {e}"
            self.progress_updated.emit(f"Error: {error_msg}")
            self.generation_error.emit(error_msg)
