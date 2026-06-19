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

from quickice.structure_generation.ion_inserter import AVOGADRO
from quickice.structure_generation.types import WATER_VOLUME_NM3

logger = logging.getLogger(__name__)

MAX_CSV_ROWS = 10000  # Safety limit for positions CSV files


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

        # SEC-04: Reject directory traversal outside working directory
        resolved_path = path.resolve()
        cwd = Path.cwd().resolve()
        if not resolved_path.is_relative_to(cwd):
            raise ValueError(
                f"Positions CSV path resolves outside working directory: "
                f"{resolved_path} is not under {cwd}"
            )

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

                # SEC-05: Reject excessively large CSV files
                if len(positions) > MAX_CSV_ROWS:
                    raise ValueError(
                        f"CSV file exceeds maximum row limit of {MAX_CSV_ROWS}. "
                        f"File has {len(positions)} data rows. "
                        f"Reduce the number of molecules or split the file."
                    )

        return positions, rotations

    # ------------------------------------------------------------------
    # Step stubs — return 1 with progress message; replaced by Plans 05-08
    # ------------------------------------------------------------------

    def _run_source_step(self) -> int:
        """Generate ice candidate or hydrate structure.

        When --hydrate is specified, generates a hydrate structure using
        HydrateStructureGenerator. If --interface is also set, the hydrate
        is converted to a Candidate via to_candidate() for downstream
        interface generation.

        When --interface is specified without --hydrate, generates an ice
        candidate via generate_candidates.

        Returns:
            0 on success, non-zero on failure.
        """
        # Hydrate branch (when --hydrate is specified)
        if getattr(self.args, 'hydrate', False):
            try:
                from quickice.structure_generation.types import HydrateConfig, WATER_ATOMS_PER_MOLECULE
                from quickice.structure_generation.hydrate_generator import HydrateStructureGenerator
            except ImportError as e:
                logger.error("Missing required package: %s", e)
                report_progress(f"Source step failed: missing package — {e}")
                return 1

            try:
                config = HydrateConfig(
                    lattice_type=getattr(self.args, 'lattice_type', 'sI'),
                    guest_type=getattr(self.args, 'guest', 'CH4').lower(),
                    supercell_x=getattr(self.args, 'supercell_x', 1),
                    supercell_y=getattr(self.args, 'supercell_y', 1),
                    supercell_z=getattr(self.args, 'supercell_z', 1),
                    cage_occupancy_small=getattr(self.args, 'cage_occupancy_small', 100.0),
                    cage_occupancy_large=getattr(self.args, 'cage_occupancy_large', 100.0),
                )
                generator = HydrateStructureGenerator()
                self._hydrate_result = generator.generate(config)

                # IMPORTANT: Use guest_count/water_count (NOT the *_nmolecules attrs — those don't exist on HydrateStructure)
                report_progress(
                    f"Generated {config.lattice_type} hydrate with "
                    f"{self._hydrate_result.guest_count} {config.guest_type} guests, "
                    f"{self._hydrate_result.water_count} water molecules"
                )

                # If also --interface: convert hydrate to candidate for interface generation
                if self.args.interface:
                    self._ice_candidate = self._hydrate_result.to_candidate()
                    report_progress("Hydrate converted to ice candidate for interface generation")

            except ValueError as e:
                logger.error("Invalid hydrate configuration: %s", e)
                report_progress(f"Source step failed: bad config — {e}")
                return 1

            return 0  # Skip ice candidate generation below

        # Ice candidate branch (when --interface without --hydrate):
        if self._ice_candidate is None:
            try:
                from quickice.phase_mapping import lookup_phase, UnknownPhaseError
                from quickice.structure_generation import generate_candidates
            except ImportError as e:
                logger.error("Missing required package: %s", e)
                report_progress(f"Source step failed: missing package — {e}")
                return 1

            try:
                phase_info = lookup_phase(self.args.temperature, self.args.pressure)
                nmolecules = self.args.nmolecules or 256
                gen_result = generate_candidates(
                    phase_info,
                    nmolecules=nmolecules,
                    n_candidates=1,
                    base_seed=self.args.seed,
                )
                self._ice_candidate = gen_result.candidates[0]
                report_progress(
                    f"Generated ice candidate ({phase_info['phase_id']})"
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

        Supports two placement modes:
        - random: count from --custom-count or calculated from --custom-concentration
        - custom: positions/rotations parsed from --custom-positions-file CSV

        Returns:
            0 on success, non-zero on failure.
        """
        try:
            from quickice.structure_generation.custom_molecule_inserter import (
                CustomMoleculeInserter,
                InsertionError,
            )
            from quickice.structure_generation.types import CustomMoleculeConfig
        except ImportError as e:
            logger.error("Missing required package: %s", e)
            report_progress(f"Custom step failed: missing package — {e}")
            return 1

        try:
            # Validate input files
            gro_path = Path(self.args.custom_gro)
            itp_path = Path(self.args.custom_itp)

            if not gro_path.exists():
                raise FileNotFoundError(f"GRO file not found: {gro_path}")
            if not itp_path.exists():
                raise FileNotFoundError(f"ITP file not found: {itp_path}")

            # SEC-02: Validate file extensions (case-insensitive)
            if gro_path.suffix.lower() != '.gro':
                report_progress(
                    f"Error: --custom-gro file must have .gro extension, "
                    f"got '{gro_path.suffix}'"
                )
                return 1
            if itp_path.suffix.lower() != '.itp':
                report_progress(
                    f"Error: --custom-itp file must have .itp extension, "
                    f"got '{itp_path.suffix}'"
                )
                return 1

            # SEC-04: Reject directory traversal outside working directory
            resolved_gro = gro_path.resolve()
            resolved_itp = itp_path.resolve()
            cwd = Path.cwd().resolve()
            if not resolved_gro.is_relative_to(cwd):
                report_progress(
                    f"Error: --custom-gro path resolves outside working directory: "
                    f"{resolved_gro} is not under {cwd}"
                )
                return 1
            if not resolved_itp.is_relative_to(cwd):
                report_progress(
                    f"Error: --custom-itp path resolves outside working directory: "
                    f"{resolved_itp} is not under {cwd}"
                )
                return 1

            # Get source structure
            source = self._interface_result
            if source is None:
                raise ValueError(
                    "No interface structure available. "
                    "Run --interface step before custom molecule insertion."
                )

            # Branch on placement mode
            if self.args.custom_placement == "random":
                # Determine molecule count
                custom_count = self.args.custom_count
                custom_concentration = getattr(
                    self.args, 'custom_concentration', None
                )

                if custom_count is None and custom_concentration is not None:
                    # Calculate from concentration
                    water_nmolecules = getattr(source, 'water_nmolecules', 0)
                    liquid_volume_nm3 = water_nmolecules * WATER_VOLUME_NM3
                    count = int(round(
                        custom_concentration * liquid_volume_nm3 * 1e-24
                        * AVOGADRO
                    ))
                elif custom_count is not None:
                    count = custom_count
                else:
                    raise ValueError(
                        "Specify --custom-count or --custom-concentration "
                        "for random placement"
                    )

                config = CustomMoleculeConfig(
                    gro_path=gro_path,
                    itp_path=itp_path,
                    placement_mode="random",
                    molecule_count=count,
                )
                inserter = CustomMoleculeInserter(config, seed=self.args.seed)
                self._custom_result = inserter.place_random(source, count)
                report_progress(
                    f"Custom molecules: placed {count} molecules (random)"
                )

            else:
                # Custom placement — parse CSV
                positions, rotations = self._parse_positions_csv(
                    self.args.custom_positions_file
                )
                config = CustomMoleculeConfig(
                    gro_path=gro_path,
                    itp_path=itp_path,
                    placement_mode="custom",
                    positions=positions,
                    rotations=rotations,
                )
                inserter = CustomMoleculeInserter(config, seed=self.args.seed)
                self._custom_result = inserter.place_custom(
                    source, positions, rotations
                )
                report_progress(
                    f"Custom molecules: placed {len(positions)} molecules "
                    f"(custom positions)"
                )

        except FileNotFoundError as e:
            logger.error("File not found: %s", e)
            report_progress(f"Custom step failed: file not found — {e}")
            return 1
        except ValueError as e:
            logger.error("Invalid configuration: %s", e)
            report_progress(f"Custom step failed: bad config — {e}")
            return 1
        except InsertionError as e:
            logger.error("Insertion failed: %s", e)
            report_progress(f"Custom step failed: insertion error — {e}")
            return 1

        return 0

    def _run_solute_step(self) -> int:
        """Insert solute molecules into the liquid region.

        Source structure is selected via --solute-source (default: interface).
        FIX #7: SoluteInserter(config, seed=args.seed) — NOT SoluteInserter(config).

        Returns:
            0 on success, non-zero on failure.
        """
        try:
            from quickice.structure_generation.solute_inserter import SoluteInserter
            from quickice.structure_generation.types import SoluteConfig
        except ImportError as e:
            logger.error("Missing required package: %s", e)
            report_progress(f"Solute step failed: missing package — {e}")
            return 1

        try:
            # Resolve source structure
            source_name = getattr(self.args, 'solute_source', 'interface')
            source = self._get_source_structure(source_name)

            if source is None:
                raise ValueError(
                    f"No '{source_name}' structure available for solute "
                    f"insertion. Run the prerequisite step first."
                )

            config = SoluteConfig(
                concentration_molar=self.args.solute_concentration,
                solute_type=self.args.solute_type,
            )

            # FIX #7: seed=args.seed — NOT just SoluteInserter(config)
            inserter = SoluteInserter(config, seed=self.args.seed)
            self._solute_result = inserter.insert_solutes(source, config)

            report_progress(
                f"Solute: placed {self._solute_result.n_molecules} "
                f"{config.solute_type} molecules at "
                f"{config.concentration_molar} M (source={source_name})"
            )

        except ValueError as e:
            logger.error("Invalid configuration: %s", e)
            report_progress(f"Solute step failed: bad config — {e}")
            return 1
        except FileNotFoundError as e:
            logger.error("File not found: %s", e)
            report_progress(f"Solute step failed: file not found — {e}")
            return 1

        return 0

    def _run_ion_step(self) -> int:
        """Insert ions for charge screening.

        Supports 3 source modes (--ion-source):
        - interface: use the original InterfaceStructure directly
        - custom: use CustomMoleculeStructure, propagate custom molecule
          attributes to the interface structure with FIX #4 offset
          (ice_atom_count + water_atom_count + guest_atom_count)
        - solute: use SoluteStructure, propagate solute attributes to the
          interface structure, plus custom molecule attributes if present

        Attribute propagation uses duck-typing (setting attributes on
        InterfaceStructure at runtime), mirroring GUI MainWindow._on_insert_ions.

        Returns:
            0 on success, non-zero on failure.
        """
        try:
            from quickice.structure_generation.ion_inserter import insert_ions
            from quickice.structure_generation.types import WATER_ATOMS_PER_MOLECULE
        except ImportError as e:
            logger.error("Missing required package: %s", e)
            report_progress(f"Ion step failed: missing package — {e}")
            return 1

        try:
            # Resolve source mode
            ion_source = getattr(self.args, 'ion_source', 'interface')

            if ion_source == "interface":
                source_for_ions = self._interface_result
                if source_for_ions is None:
                    raise ValueError(
                        "No interface structure available. "
                        "Run --interface step before ion insertion."
                    )

            elif ion_source == "custom":
                source = self._custom_result
                if source is None:
                    raise ValueError(
                        "No custom molecule structure available. "
                        "Run the custom molecule step before using "
                        "--ion-source custom."
                    )

                interface = source.interface_structure
                if interface is None:
                    raise ValueError(
                        "Custom molecule structure does not have an "
                        "associated interface structure."
                    )

                # FIX #4: offset includes guest_atom_count
                # (NOT just ice_atom_count + water_atom_count)
                offset = (
                    interface.ice_atom_count
                    + interface.water_atom_count
                    + interface.guest_atom_count
                )
                interface.custom_molecule_positions = source.positions[offset:]
                interface.custom_molecule_atom_names = source.atom_names[offset:]
                interface.custom_molecule_count = source.custom_molecule_count
                interface.custom_molecule_moleculetype = source.moleculetype_name
                interface.custom_gro_path = source.gro_path
                interface.custom_itp_path = source.itp_path
                source_for_ions = interface

            elif ion_source == "solute":
                source = self._solute_result
                if source is None:
                    raise ValueError(
                        "No solute structure available. "
                        "Run the solute step before using --ion-source solute."
                    )

                interface = source.interface_structure
                if interface is None:
                    raise ValueError(
                        "Solute structure does not have an associated "
                        "interface structure."
                    )

                # Propagate solute attributes to interface structure
                interface.solute_type = source.solute_type
                interface.solute_positions = source.positions
                interface.solute_atom_names = source.atom_names
                interface.solute_n_molecules = source.n_molecules
                interface.solute_molecule_indices = source.molecule_indices
                interface.solute_registry = source.registry

                # Also propagate custom molecule attributes if present
                # (handles Custom → Solute → Ion workflow chain)
                if (hasattr(source, 'custom_molecule_count')
                        and source.custom_molecule_count > 0):
                    if (hasattr(source, 'custom_molecule_positions')
                            and source.custom_molecule_positions is not None):
                        interface.custom_molecule_count = source.custom_molecule_count
                        interface.custom_molecule_atom_count = source.custom_molecule_atom_count
                        interface.custom_molecule_positions = source.custom_molecule_positions
                        interface.custom_molecule_atom_names = source.custom_molecule_atom_names
                        interface.custom_molecule_moleculetype = source.custom_molecule_moleculetype
                        interface.custom_gro_path = source.custom_gro_path
                        interface.custom_itp_path = source.custom_itp_path

                source_for_ions = interface

            else:
                raise ValueError(f"Unknown ion source: {ion_source!r}")

            # Calculate liquid volume from water molecule count
            liquid_volume = getattr(source_for_ions, 'water_nmolecules', 0) * WATER_VOLUME_NM3

            # Insert ions
            self._ion_result = insert_ions(
                source_for_ions,
                concentration_molar=self.args.ion_concentration,
                liquid_volume_nm3=liquid_volume,
                seed=self.args.seed,
            )
            report_progress(
                f"Ion insertion: {self._ion_result.na_count} Na+, "
                f"{self._ion_result.cl_count} Cl-"
            )

        except ValueError as e:
            logger.error("Invalid configuration: %s", e)
            report_progress(f"Ion step failed: bad config — {e}")
            return 1

        return 0

    def _run_export_step(self) -> int:
        """Export GROMACS files for the final structure.

        Selects the most downstream structure available (ion > solute >
        custom > interface > hydrate > ice) and writes GROMACS .gro/.top
        files plus required ITP files.

        Returns:
            0 on success, non-zero on failure.
        """
        try:
            from quickice.output.gromacs_writer import (
                write_gro_file,
                write_top_file,
                write_interface_gro_file,
                write_interface_top_file,
                write_custom_molecule_gro_file,
                write_custom_molecule_top_file,
                write_solute_gro_file,
                write_solute_top_file,
                write_ion_gro_file,
                write_ion_top_file,
            )
            from quickice.cli.itp_helpers import copy_itp_files_for_structure
        except ImportError as e:
            logger.error("Missing required package: %s", e)
            report_progress(f"Export step failed: missing package — {e}")
            return 1

        # Priority order: most downstream wins — FIX #9: hydrate between interface and ice
        if self._ion_result is not None:
            structure, step_name = self._ion_result, "ion"
        elif self._solute_result is not None:
            structure, step_name = self._solute_result, "solute"
        elif self._custom_result is not None:
            structure, step_name = self._custom_result, "custom"
        elif self._interface_result is not None:
            structure, step_name = self._interface_result, "interface"
        elif self._hydrate_result is not None:
            structure, step_name = self._hydrate_result, "hydrate"
        else:
            structure, step_name = self._ice_candidate, "ice"

        if structure is None:
            logger.error("No structure available for export")
            report_progress("Export step failed: no structure to export")
            return 1

        try:
            gro_path = str(self._output_dir / f"{step_name}.gro")
            top_path = str(self._output_dir / f"{step_name}.top")

            # Writer dispatch by step type
            if step_name == "ice":
                write_gro_file(structure, gro_path)
                write_top_file(structure, top_path)
            elif step_name == "hydrate":
                # HydrateStructure → InterfaceStructure-compatible wrapper
                # IMPORTANT: HydrateStructure has guest_count and water_count
                # (NOT guest_nmolecules, water_atom_count, etc.)
                from quickice.structure_generation.types import (
                    InterfaceStructure,
                    WATER_ATOMS_PER_MOLECULE,
                )
                hydrate = structure
                water_atom_count = hydrate.water_count * WATER_ATOMS_PER_MOLECULE
                guest_atom_count = len(hydrate.positions) - water_atom_count
                # Verify atom counts are consistent before creating wrapper
                # (catches bugs where water_count * 4 does not match actual
                # water atoms in positions, which would silently corrupt
                # downstream atom counting)
                assert water_atom_count + guest_atom_count == len(hydrate.positions), \
                    f"Atom count mismatch: water_atom_count({water_atom_count}) + " \
                    f"guest_atom_count({guest_atom_count}) != " \
                    f"total positions({len(hydrate.positions)})"
                guest_nmolecules = hydrate.guest_count
                water_nmolecules = hydrate.water_count
                wrapper = InterfaceStructure(
                    positions=hydrate.positions,
                    atom_names=hydrate.atom_names,
                    cell=hydrate.cell,
                    molecule_index=hydrate.molecule_index,
                    mode="hydrate",
                    report=hydrate.report if hasattr(hydrate, "report") else "",
                    ice_atom_count=0,
                    water_atom_count=water_atom_count,
                    ice_nmolecules=0,
                    water_nmolecules=water_nmolecules,
                    guest_atom_count=guest_atom_count,
                    guest_nmolecules=guest_nmolecules,
                )
                write_interface_gro_file(wrapper, gro_path)
                write_interface_top_file(wrapper, top_path)
            elif step_name == "interface":
                write_interface_gro_file(structure, gro_path)
                write_interface_top_file(structure, top_path)
            elif step_name == "custom":
                write_custom_molecule_gro_file(structure, gro_path)
                write_custom_molecule_top_file(structure, top_path)
            elif step_name == "solute":
                write_solute_gro_file(structure, gro_path)
                write_solute_top_file(structure, top_path)
            elif step_name == "ion":
                write_ion_gro_file(structure, gro_path)
                write_ion_top_file(structure, top_path)

            # Copy ITP files
            itp_files = copy_itp_files_for_structure(
                self._output_dir, structure, step_name
            )

            report_progress(
                f"Exported GROMACS: {step_name}.gro, {step_name}.top, "
                f"{len(itp_files)} ITP files → {self._output_dir}"
            )
        except (OSError, ValueError) as e:
            logger.error("Export failed: %s", e)
            report_progress(f"Export step failed: {e}")
            return 1

        return 0
