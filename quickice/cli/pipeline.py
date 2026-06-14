"""CLI pipeline for QuickIce v4.5.

Orchestrates the ice → interface → custom → solute → ion → export
workflow via ordered step execution with fail-fast semantics.

No GUI imports — this module works without PySide6/VTK.
"""

import argparse
import csv
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def report_progress(message: str) -> None:
    """Print a progress message to stderr for CLI feedback.

    Args:
        message: Progress description to display.
    """
    print(f"[PROGRESS] {message}", file=sys.stderr)


class CLIPipeline:
    """CLI pipeline orchestrator for QuickIce v4.5 generation workflows.

    Runs ordered steps (source → interface → custom → solute → ion → export)
    with fail-fast semantics: the first failing step stops execution and
    returns a non-zero exit code.

    Args:
        args: Parsed and validated argparse.Namespace from parser.py.
    """

    def __init__(self, args: argparse.Namespace):
        self.args = args
        self._interface_result = None
        self._hydrate_result = None
        self._custom_result = None
        self._solute_result = None
        self._ion_result = None
        self._ice_candidate = None
        self._output_dir = None

    def execute(self) -> int:
        """Execute the pipeline steps in order with fail-fast semantics.

        Returns:
            0 on success, non-zero on failure (1 for stubs, other codes
            for real implementation errors).
        """
        # Step 0: Create output directory
        try:
            output_path = Path(self.args.output).resolve()
            output_path.mkdir(parents=True, exist_ok=True)
            self._output_dir = output_path
        except OSError as e:
            logger.error("Failed to create output directory: %s", e)
            return 1

        # Step 0b: Check --no-overwrite
        if getattr(self.args, 'no_overwrite', False):
            # Check if output files already exist
            existing_files = list(self._output_dir.glob("*"))
            if existing_files:
                logger.error(
                    "Output directory %s already contains files and "
                    "--no-overwrite was specified",
                    self._output_dir,
                )
                report_progress("Output directory not empty; --no-overwrite set")
                return 1

        # Step 1: Source step (hydrate or ice generation)
        if self.args.interface or getattr(self.args, 'hydrate', False):
            result = self._run_source_step()
            if result != 0:
                return result

        # Step 2: Interface step
        if self.args.interface:
            result = self._run_interface_step()
            if result != 0:
                return result

        # Step 3: Custom molecule step
        if getattr(self.args, 'custom_gro', None):
            result = self._run_custom_step()
            if result != 0:
                return result

        # Step 4: Solute step
        if getattr(self.args, 'solute_type', None):
            result = self._run_solute_step()
            if result != 0:
                return result

        # Step 5: Ion step
        if getattr(self.args, 'ion_concentration', None):
            result = self._run_ion_step()
            if result != 0:
                return result

        # Step 6: Export step
        return self._run_export_step()

    def _get_source_structure(self, source_name: str):
        """Return a stored structure by source name.

        Maps source name strings to the corresponding stored result
        from a previous pipeline step.

        Args:
            source_name: One of 'interface', 'custom', 'solute'.

        Returns:
            The stored structure object, or None if not yet computed.

        Raises:
            ValueError: If source_name is not a recognized source.
        """
        source_map = {
            "interface": self._interface_result,
            "custom": self._custom_result,
            "solute": self._solute_result,
        }
        if source_name not in source_map:
            raise ValueError(
                f"Unknown source name: {source_name!r}. "
                f"Must be one of: {', '.join(source_map)}"
            )
        return source_map[source_name]

    @staticmethod
    def _parse_positions_csv(
        filepath: str,
    ) -> tuple[list[tuple], list[tuple]]:
        """Parse a CSV file of custom molecule positions and rotations.

        Each row has 6 columns: x, y, z, alpha, beta, gamma (Euler ZXZ
        convention). Lines starting with '#' and blank rows are skipped.

        Args:
            filepath: Path to the CSV file.

        Returns:
            Tuple of (positions, rotations) where:
              - positions: list of (x, y, z) float tuples
              - rotations: list of (alpha, beta, gamma) float tuples

        Raises:
            FileNotFoundError: If the CSV file does not exist.
            ValueError: If a row has wrong column count or non-numeric values.
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Positions CSV file not found: {filepath}")

        positions: list[tuple] = []
        rotations: list[tuple] = []

        with open(path, newline="") as f:
            reader = csv.reader(f)
            for line_num, row in enumerate(reader, start=1):
                # Skip comment lines (starting with #) and blank rows
                stripped = [cell.strip() for cell in row]
                if not stripped or stripped[0].startswith("#"):
                    continue

                if len(row) != 6:
                    raise ValueError(
                        f"Row {line_num} has {len(row)} columns, expected 6 "
                        f"(x, y, z, alpha, beta, gamma): {row}"
                    )

                try:
                    values = [float(v) for v in row]
                except (ValueError, TypeError) as e:
                    raise ValueError(
                        f"Row {line_num} contains non-numeric value: {row}"
                    ) from e

                positions.append(tuple(values[:3]))   # (x, y, z)
                rotations.append(tuple(values[3:]))    # (alpha, beta, gamma)

        return positions, rotations

    # ------------------------------------------------------------------
    # Step stubs — return 1 with progress message; replaced by Plans 05-08
    # ------------------------------------------------------------------

    def _run_source_step(self) -> int:
        """Generate ice candidate or hydrate structure.

        The hydrate branch (when --hydrate is specified) will be added
        by Plan 06. This implementation handles the ice candidate path
        only (when --interface is specified without --hydrate).

        Returns:
            0 on success, non-zero on failure.
        """
        # [Hydrate branch added by Plan 06 — if getattr(self.args, 'hydrate', False): ...]

        # Ice candidate branch (when --interface without --hydrate):
        if self._ice_candidate is None:  # Not set by hydrate branch
            try:
                from quickice.phase_mapping import lookup_phase, UnknownPhaseError
                from quickice.structure_generation import generate_candidates
            except ImportError as e:
                logger.error("Missing required package: %s", e)
                report_progress(f"Source step failed: missing package — {e}")
                return 1

            try:
                phase_info = lookup_phase(self.args.temperature, self.args.pressure)
                nmolecules = getattr(self.args, 'nmolecules', 256)
                gen_result = generate_candidates(
                    phase_info,
                    nmolecules=nmolecules,
                    n_candidates=1,
                    base_seed=self.args.seed,
                )
                self._ice_candidate = gen_result.candidates[0]
                report_progress(
                    f"Generated ice candidate ({phase_info.phase_id})"
                )
            except UnknownPhaseError as e:
                logger.error("Unknown phase at given T/P: %s", e)
                report_progress(f"Source step failed: unknown phase — {e}")
                return 1
            except ValueError as e:
                logger.error("Invalid configuration: %s", e)
                report_progress(f"Source step failed: bad config — {e}")
                return 1

        return 0

    def _run_interface_step(self) -> int:
        """Generate ice-water interface structure.

        Creates an InterfaceConfig from CLI arguments and calls
        generate_interface() with the previously generated ice candidate.

        Returns:
            0 on success, non-zero on failure.
        """
        try:
            from quickice.structure_generation.types import InterfaceConfig
            from quickice.structure_generation.interface_builder import (
                generate_interface,
            )
            from quickice.structure_generation.errors import (
                InterfaceGenerationError,
            )
        except ImportError as e:
            logger.error("Missing required package: %s", e)
            report_progress(f"Interface step failed: missing package — {e}")
            return 1

        try:
            config = InterfaceConfig(
                mode=self.args.mode,
                box_x=self.args.box_x,
                box_y=self.args.box_y,
                box_z=self.args.box_z,
                ice_thickness=self.args.ice_thickness,
                water_thickness=self.args.water_thickness,
                pocket_diameter=getattr(self.args, 'pocket_diameter', None),
                pocket_shape=getattr(self.args, 'pocket_shape', 'sphere'),
                seed=self.args.seed,
            )
            self._interface_result = generate_interface(
                self._ice_candidate, config
            )
            report_progress(
                f"Interface: {self._interface_result.ice_nmolecules} ice + "
                f"{self._interface_result.water_nmolecules} water molecules"
            )
            if self._interface_result.report:
                print(self._interface_result.report, file=sys.stderr)
        except InterfaceGenerationError as e:
            logger.error("Interface generation failed: %s", e)
            report_progress(f"Interface step failed: {e}")
            return 1

        return 0

    def _run_custom_step(self) -> int:
        """Insert custom molecules into the liquid region.

        Returns:
            0 on success, non-zero on failure.
        """
        report_progress("Custom molecule step: not yet implemented")
        return 1

    def _run_solute_step(self) -> int:
        """Insert solute molecules into the liquid region.

        Returns:
            0 on success, non-zero on failure.
        """
        report_progress("Solute step: not yet implemented")
        return 1

    def _run_ion_step(self) -> int:
        """Insert ions for charge screening.

        Returns:
            0 on success, non-zero on failure.
        """
        report_progress("Ion step: not yet implemented")
        return 1

    def _run_export_step(self) -> int:
        """Export GROMACS files for the final structure.

        Returns:
            0 on success, non-zero on failure.
        """
        report_progress("Export step: not yet implemented")
        return 1
