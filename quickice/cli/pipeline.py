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
from quickice.output.guest_info import _build_custom_guest_info  # noqa: F401 (re-exported for backward compat)

logger = logging.getLogger(__name__)

MAX_CSV_ROWS = 10000  # Safety limit for positions CSV files


def report_progress(message: str) -> None:
    """Print a progress message to stderr for CLI feedback.

    Args:
        message: Progress description to display.
    """
    print(f"[PROGRESS] {message}", file=sys.stderr)


def _parse_cage_guest_args(args, lattice_type: str) -> dict:
    """Parse ``args.cage_guest`` (list of ``"KEY=GUEST:OCC"`` strings) into a
    ``dict[str, CageGuestAssignment]`` keyed by cage type map key.

    Returns an empty dict when ``args.cage_guest`` is ``None``/empty (the
    ``HydrateConfig.__post_init__`` legacy shim then synthesizes
    ``cage_guest_assignments`` from ``--guest``/``--cage-occupancy-small/large``).

    Raises:
        ValueError: on malformed input (bad key, non-built-in guest, bad
            occupancy, out-of-range occupancy, duplicate cage key, or cage key
            not present in the lattice's ``cage_type_map``). The CLI source step
            catches ``ValueError`` and reports a clear error to the user.
    """
    specs = getattr(args, "cage_guest", None)
    if not specs:
        return {}
    # Lazy import to keep pipeline.py importable without structure_generation
    # being fully loaded (matches the existing _run_source_step pattern).
    from quickice.structure_generation.types import (
        CageGuestAssignment,
        HYDRATE_LATTICES,
    )
    if lattice_type not in HYDRATE_LATTICES:
        raise ValueError(f"Unknown lattice type: {lattice_type!r}")
    cmap = HYDRATE_LATTICES[lattice_type].get("cage_type_map", {})
    out: dict = {}
    for spec in specs:
        key, _, rest = spec.partition("=")
        if not key or not rest:
            raise ValueError(
                f"invalid spec {spec!r}: expected 'KEY=GUEST:OCC' "
                f"(e.g. small=CH4:60)"
            )
        guest, _, occ_str = rest.partition(":")
        if not guest:
            raise ValueError(
                f"invalid spec {spec!r}: missing GUEST (expected 'KEY=GUEST:OCC')"
            )
        guest_lower = guest.lower()
        # CLI surface is built-in-only for v4.7 (per plan; full custom-guest CLI
        # requiring --custom-guest-gro/--custom-guest-itp is deferred). The GUI
        # already supports custom-guest mixed occupancy via the explicit API.
        if guest_lower not in ("ch4", "thf"):
            raise ValueError(
                f"invalid spec {spec!r}: GUEST {guest!r} is not a built-in CH4 or "
                f"THF. Custom-guest CLI support is deferred (use the GUI for "
                f"custom-guest mixed occupancy)."
            )
        try:
            occ = float(occ_str) if occ_str else 100.0
        except ValueError:
            raise ValueError(
                f"invalid spec {spec!r}: OCC {occ_str!r} is not a number"
            )
        if not (0.0 <= occ <= 100.0):
            raise ValueError(
                f"invalid spec {spec!r}: OCC must be 0-100, got {occ}"
            )
        if key not in cmap:
            valid = ", ".join(sorted(cmap.keys())) or "(none for this lattice)"
            raise ValueError(
                f"invalid spec {spec!r}: cage key {key!r} not valid for lattice "
                f"{lattice_type!r} (valid keys: {valid})"
            )
        if key in out:
            raise ValueError(
                f"duplicate --cage-guest key {key!r}: each cage key may be "
                f"assigned at most once"
            )
        out[key] = CageGuestAssignment(guest_type=guest_lower, occupancy=occ)
    return out


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
                logger.info(
                    "Output directory %s already contains files and "
                    "--no-overwrite was specified; skipping",
                    self._output_dir,
                )
                report_progress("Output directory not empty; --no-overwrite set")
                return 0

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
                # Phase 42 mixed cage occupancy: build cage_guest_assignments
                # from --cage-guest (repeatable KEY=GUEST:OCC) when supplied;
                # else fall back to the legacy --guest/--cage-occupancy-small/large
                # fields (the HydrateConfig.__post_init__ shim synthesizes
                # cage_guest_assignments from them when the dict is empty).
                lattice_type = getattr(self.args, 'lattice_type', 'sI')
                cage_guest_assignments: dict = {}
                if getattr(self.args, 'cage_guest', None):
                    try:
                        cage_guest_assignments = _parse_cage_guest_args(
                            self.args, lattice_type
                        )
                    except ValueError as e:
                        report_progress(f"Source step failed: bad --cage-guest — {e}")
                        return 1
                config = HydrateConfig(
                    lattice_type=lattice_type,
                    cage_guest_assignments=cage_guest_assignments,
                    guest_type=getattr(self.args, 'guest', 'CH4').lower(),
                    supercell_x=getattr(self.args, 'supercell_x', 1),
                    supercell_y=getattr(self.args, 'supercell_y', 1),
                    supercell_z=getattr(self.args, 'supercell_z', 1),
                    cage_occupancy_small=getattr(self.args, 'cage_occupancy_small', 100.0),
                    cage_occupancy_large=getattr(self.args, 'cage_occupancy_large', 100.0),
                    depol_mode=getattr(self.args, 'depol', 'strict'),
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

        Auto-chaining: When --solute-source is the default ('interface') and
        custom molecules were placed in a previous step, the source is
        automatically upgraded to 'custom' so that custom molecule attributes
        are preserved through the solute→ion workflow.

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

            # Auto-chain: upgrade 'interface' to 'custom' when custom molecules
            # were placed in a previous pipeline step.  This ensures custom
            # molecule attributes are carried forward into SoluteStructure so
            # that the ion step can propagate them further.
            if source_name == 'interface' and self._custom_result is not None:
                source_name = 'custom'
                logger.info(
                    "Auto-chaining: --solute-source upgraded from "
                    "'interface' to 'custom' (custom molecules detected)"
                )

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

        Auto-chaining: When --ion-source is the default ('interface') and
        upstream steps produced more downstream results, the source is
        automatically upgraded to the most downstream available result
        (solute > custom > interface).  This prevents silent data loss
        where custom molecules and solutes are dropped from the output
        because the raw InterfaceStructure lacks those attributes.

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

            # Auto-chain: upgrade 'interface' to the most downstream result
            # available.  When the user runs the full chain
            # (interface→custom→solute→ion) without explicitly setting
            # --ion-source, the default 'interface' would drop ALL upstream
            # custom/solute data.  Auto-chaining prevents this silent data loss.
            if ion_source == 'interface':
                if self._solute_result is not None:
                    ion_source = 'solute'
                    logger.info(
                        "Auto-chaining: --ion-source upgraded from "
                        "'interface' to 'solute' (solute step detected)"
                    )
                elif self._custom_result is not None:
                    ion_source = 'custom'
                    logger.info(
                        "Auto-chaining: --ion-source upgraded from "
                        "'interface' to 'custom' (custom molecules detected)"
                    )

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
                interface.custom_molecule_atom_count = source.custom_molecule_atom_count
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

            # Build custom_guest_info from the persisted hydrate config (plan 44.1-17).
            # self._hydrate_result carries .config (HydrateConfig) when the source
            # step generated a hydrate; None for plain-ice CLI runs -> cgi=None ->
            # built-in path (custom_guest_info=None) byte-identical to pre-44.1-17.
            # The hydrate branch below keeps its own local custom_guest_info (the
            # working reference); this threads cgi to the other 4 branches.
            hydrate_config = getattr(self._hydrate_result, "config", None)
            cgi = _build_custom_guest_info(hydrate_config)

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
                # Thread custom-guest metadata (mol_type, residue_name, itp_path)
                # to the writers — None for all-built-in hydrate guests (ch4/thf),
                # or a list of dicts (one per distinct custom guest_type, deduped
                # by mol_type) when --cage-guest supplies a custom guest. The
                # ITP copy itself is handled by copy_itp_files_for_structure
                # (plan 41-07 custom branch) below — unchanged here.
                custom_guest_info = _build_custom_guest_info(getattr(hydrate, "config", None))
                write_interface_gro_file(wrapper, gro_path, custom_guest_info=custom_guest_info)
                write_interface_top_file(wrapper, top_path, custom_guest_info=custom_guest_info)
            elif step_name == "interface":
                write_interface_gro_file(structure, gro_path, custom_guest_info=cgi)
                write_interface_top_file(structure, top_path, custom_guest_info=cgi)
            elif step_name == "custom":
                write_custom_molecule_gro_file(structure, gro_path, custom_guest_info=cgi)
                write_custom_molecule_top_file(structure, top_path, custom_guest_info=cgi)
            elif step_name == "solute":
                write_solute_gro_file(structure, gro_path, custom_guest_info=cgi)
                write_solute_top_file(structure, top_path, custom_guest_info=cgi)
            elif step_name == "ion":
                write_ion_gro_file(structure, gro_path, custom_guest_info=cgi)
                write_ion_top_file(structure, top_path, custom_guest_info=cgi)

            # Copy ITP files
            itp_files = copy_itp_files_for_structure(
                self._output_dir, structure, step_name, hydrate_config=hydrate_config
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
