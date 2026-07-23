"""Hydrate structure generation via GenIce2.

Provides HydrateStructureGenerator class for creating hydrate structures
with configurable lattice type, guest molecules, and cage occupancy.
"""

import logging
import numpy as np
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

from quickice.structure_generation.types import (
    HydrateConfig,
    HydrateStructure,
    HydrateLatticeInfo,
    MoleculeIndex,
    WATER_ATOMS_PER_MOLECULE,
    GuestDescriptor,
    HYDRATE_LATTICES,
    GUEST_MOLECULES,
)

# Map from our lattice type names to GenIce2 lattice modules
_LATTICE_MODULES = {
    "sI": "sI",
    "sII": "sII",
    "sH": "sH",
    "c0te": "c0te",
    "c1te": "c1te",
    "c2te": "c2te",
    "ice1hte": "ice1hte",
    "sTprime": "sTprime",
    "16": "16",
    "17": "17",
}

# Thread-safe lock for GenIce2 lazy loading (loaded in _ensure_genice_import)
_genice_lock = threading.Lock()


class HydrateStructureGenerator:
    """Generator for hydrate structures using GenIce2.

    Supports 10 hydrate lattice types with configurable guest molecules
    (CH4, THF) and cage occupancy:
    - sI, sII, sH: Standard clathrate hydrates
    - c0te, c1te, c2te, ice1hte: Filled ice structures (Teeratchanan 2015)
    - sTprime: Filled ice sT' (Smirnov 2013) — water-only
    - 16: Ice XVI (empty sII framework)
    - 17: Ice XVII (ultralow density) — water-only

    Numeric module names (16, 17) are loaded via safe_import at generation
    time, not pre-imported, since Python syntax forbids `from X import 16`.

    Note: GenIce2 supports additional guest types (CO2, H2), but these are not
    exposed in QuickIce's GUEST_MOLECULES configuration.
    """
    
    def __init__(self):
        """Initialize the generator."""
        self._genice_lib = None
        self._gromacs_format = None
        self._lattice_modules = {}
    
    def _ensure_genice_import(self):
        """Lazy import of GenIce2 to avoid startup overhead."""
        
        if self._genice_lib is not None:
            return
        
        with _genice_lock:
            # Double-check after acquiring lock
            if self._genice_lib is not None:
                return

            try:
                import genice2.genice as genice_lib
                from genice2.formats import gromacs
                from genice2.lattices import sI, sII, sH, c0te, c1te, c2te, ice1hte, sTprime
                from genice2.molecules.tip4p import Molecule as TIP4P
                
                self._genice_lib = genice_lib
                self._gromacs_format = gromacs
                self._lattice_modules = {
                    "sI": sI,
                    "sII": sII,
                    "sH": sH,
                    "c0te": c0te,
                    "c1te": c1te,
                    "c2te": c2te,
                    "ice1hte": ice1hte,
                    "sTprime": sTprime,
                    # "16" and "17" loaded via safe_import at runtime (numeric names can't be imported)
                }
                self._water_molecule = TIP4P()
            except ImportError as e:
                raise ImportError(
                    "GenIce2 is required for hydrate generation. "
                    f"Import error: {e}"
                )
    
    def generate(self, config: HydrateConfig) -> HydrateStructure:
        """Generate hydrate structure with given configuration.

        For custom guests (``config.is_custom_guest`` is True), builds a
        synthetic GenIce2 ``Molecule`` plugin module on the main thread,
        registers it in ``sys.modules`` for the duration of the
        ``_run_via_api`` call (so GenIce2's ``safe_import('molecule',
        <guest_type>)`` finds it), and cleans up afterward via the
        ``custom_guest_module`` context manager (try/finally). Built-in
        guests (ch4, thf) skip the injection and use the existing path.

        Args:
            config: HydrateConfig with lattice, guest, occupancy, supercell

        Returns:
            HydrateStructure with positions, cell, and molecule_index

        Raises:
            ImportError: If GenIce2 is not available
            ValueError: If configuration is invalid
        """
        self._ensure_genice_import()

        # Get GenIce2 lattice name from config
        lattice_name = config.get_genice_lattice_name()

        # Generate structure using GenIce2 Python API (not CLI).
        # For custom guests, the synthetic Molecule module must be registered
        # in sys.modules BEFORE ice.generate_ice(...) runs (Stage7 calls
        # safe_import('molecule', guest_type) which returns the cached entry).
        # _build_molecule_index and HydrateStructure construction happen AFTER
        # the context manager exits — they don't need the module, only
        # generate_ice does. Cleanup always runs (ExitStack finally) to prevent
        # stale module pollution (success criteria #5).
        #
        # Phase 42 mixed occupancy: one custom guest may be assigned to multiple
        # cage keys (the legacy single-custom-guest path synthesizes the SAME
        # guest_type for small+large via the 42-01 shim). custom_guest_module
        # asserts the sys.modules key is absent, so dedup by guest_type and
        # register ONE module per DISTINCT custom guest type. ExitStack
        # guarantees cleanup on exception (Pitfall 5 — thread-safety / no leak).
        custom_by_type: dict = {}
        for _cage_key, _assignment in config.cage_guest_assignments.items():
            if _assignment.is_custom_guest and _assignment.guest_type not in custom_by_type:
                custom_by_type[_assignment.guest_type] = _assignment

        if custom_by_type:
            # Lazy import per AGENTS.md (GenIce2/bridge stay lazy; no
            # top-level import of custom_guest_bridge). This branch only runs
            # when at least one custom guest is assigned, so built-in-only
            # generation is unaffected.
            from contextlib import ExitStack
            from quickice.structure_generation.custom_guest_bridge import (
                build_custom_guest_module,
                custom_guest_module,
            )

            # Build the synthetic Molecule modules on the MAIN thread (the
            # caller's thread). Thread-safe per v4.7 decision: register
            # before any HydrateWorker exists, cleanup after it joins.
            # _run_via_api routes each cage_key's assignment through parse_guest
            # via the cage_guest_assignments loop, so the only requirement is
            # that sys.modules["genice2.molecules.<guest_type>"] is populated
            # before ice.generate_ice(...) runs — which the ExitStack guarantees.
            with ExitStack() as stack:
                for _assignment in custom_by_type.values():
                    module = build_custom_guest_module(
                        _assignment.guest_gro_path,
                        _assignment.guest_type,
                        _assignment.guest_residue_name,
                    )
                    stack.enter_context(
                        custom_guest_module(_assignment.guest_type, module)
                    )
                positions, cell, atom_names, residue_names, residue_seq_nums = (
                    self._run_via_api(lattice_name, config)
                )
        else:
            positions, cell, atom_names, residue_names, residue_seq_nums = (
                self._run_via_api(lattice_name, config)
            )
        
        # Build molecule index (positions from genice2 are already complete molecules)
        # NOTE: Do NOT wrap positions. GenIce2 outputs complete molecules, and wrapping
        # by cell index causes molecules to be split when atoms span multiple periodic
        # images. VTK's vtkMoleculeMapper handles positions outside [0,L) correctly
        # using the lattice setting. This matches genice2 CLI behavior.
        molecule_index = self._build_molecule_index(atom_names, positions, residue_names, residue_seq_nums, config=config)
        
        # Get lattice info
        lattice_info = HydrateLatticeInfo.from_lattice_type(config.lattice_type)
        
        # Count water and guest molecules separately
        # Guest = any molecule that is not water (ch4, thf, na, cl, etc.)
        water_count = sum(1 for m in molecule_index if m.mol_type == "water")
        guest_count = sum(1 for m in molecule_index if m.mol_type != "water")
        
        report = self._generate_report(config, water_count, guest_count)
        
        # Phase 42 mixed cage occupancy: build one GuestDescriptor per cage
        # assignment (one per cage key). The legacy single-guest fields above
        # (guest_name/guest_atom_labels/guest_atom_count/guest_itp_path) remain
        # the "primary guest" (first non-water assignment) for backward compat
        # (Pitfall 7); guest_descriptors carries the full per-cage picture.
        guest_descriptors: list[GuestDescriptor] = []
        for _cage_key, _assignment in config.cage_guest_assignments.items():
            if _assignment.guest_type in GUEST_MOLECULES:
                _gname = GUEST_MOLECULES[_assignment.guest_type]["name"]
            else:
                _gname = _assignment.guest_residue_name or _assignment.guest_type
            guest_descriptors.append(GuestDescriptor(
                mol_type=_assignment.guest_type,
                cage_key=_cage_key,
                guest_name=_gname,
                guest_residue_name=_assignment.guest_residue_name,
                is_custom=_assignment.is_custom_guest,
                atom_labels=list(_assignment.guest_atom_labels),
                atom_count=_assignment.guest_atom_count,
            ))
        
        return HydrateStructure(
            positions=positions,
            atom_names=atom_names,
            cell=cell,
            molecule_index=molecule_index,
            config=config,
            lattice_info=lattice_info,
            report=report,
            guest_count=guest_count,
            water_count=water_count,
            guest_name=config.guest_name,
            guest_atom_labels=config.guest_atom_labels,
            guest_atom_count=config.guest_atom_count,
            guest_itp_path=config.guest_itp_path,
            guest_descriptors=guest_descriptors,
        )
    
    def _run_via_api(self, lattice_name: str, config: HydrateConfig) -> tuple:
        """Run GenIce2 via Python API.
        
        Uses GenIce2 Python API directly instead of CLI subprocess,
        which ensures compatibility with PyInstaller bundled executables.
        
        Args:
            lattice_name: GenIce2 lattice name (e.g., "CS1", "CS2", "DOH")
            config: HydrateConfig with lattice, guest, occupancy, supercell
            
        Returns:
            Tuple of (positions, cell, atom_names, residue_names, residue_seq_nums)
        """
        from genice2.genice import GenIce
        from genice2.plugin import safe_import
        from genice2.valueparser import parse_guest
        from collections import defaultdict
        
        try:
            # Load lattice module
            lattice = safe_import('lattice', lattice_name).Lattice()
            
            # Build supercell matrix
            supercell_matrix = np.diag([
                config.supercell_x,
                config.supercell_y,
                config.supercell_z
            ])
            
            # Create GenIce instance with supercell
            ice = GenIce(lattice, reshape=supercell_matrix)
            
            # Load TIP4P water model (4-point: OW, HW1, HW2, MW)
            water = safe_import('molecule', 'tip4p').Molecule()
            
            # Load GROMACS formatter
            formatter = safe_import('format', 'gromacs').Format()
            
            # Build guests dictionary from config
            # Format: {"12": {"ch4": 0.5}, "Ne1": {"ch4": 1.0}}
            guests = defaultdict(dict)
            
            # Phase 42 mixed occupancy: iterate cage_guest_assignments and
            # route each cage key through parse_guest with the per-assignment
            # guest_type and occupancy. Each cage_key maps to a DISTINCT
            # cage_id via cage_type_map, so parse_guest's "Cage type already
            # specified" assert never fires for valid configs (Pitfall 2).
            # Do NOT use the "+" multi-guest-in-one-cage syntax (different
            # feature). Do NOT call parse_guest twice with the same cage_id.
            lattice_entry = HYDRATE_LATTICES[config.lattice_type]
            cage_type_map = lattice_entry.get("cage_type_map", {})
            is_water_only = lattice_entry.get("is_water_only", False)

            if not is_water_only:
                for cage_key, assignment in config.cage_guest_assignments.items():
                    if cage_key not in cage_type_map:
                        logger.warning(
                            "cage_key %r not in cage_type_map for %s; skipping",
                            cage_key, config.lattice_type,
                        )
                        continue
                    if assignment.occupancy <= 0:
                        continue
                    cage_id = cage_type_map[cage_key]
                    guest_name = assignment.guest_type  # built-in "ch4"/"thf" or custom slug
                    frac = assignment.occupancy / 100.0
                    if frac >= 1.0:
                        guest_spec = f"{cage_id}={guest_name}"
                    else:
                        guest_spec = f"{cage_id}={guest_name}*{frac}"
                    parse_guest(guests, guest_spec)  # asserts cagetype not already in guests
            
            # Generate hydrate structure using GenIce API
            gro_string = ice.generate_ice(
                formatter=formatter,
                water=water,
                guests=guests,
                depol=config.depol_mode
            )
            
            # Parse GRO format result
            return self._parse_gro_result(gro_string)
        
        except Exception as e:
            raise RuntimeError(
                f"GenIce2 failed to generate structure: {e}"
            ) from e
    
    def _parse_gro_result(self, gro_string: str) -> tuple:
        """Parse GRO format string from GenIce2."""
        lines = gro_string.strip().split('\n')
        
        # Skip title and atom count lines
        # GRO format: title, atom_count, atom_lines, box
        
        try:
            n_atoms = int(lines[1].strip())
        except (IndexError, ValueError):
            raise RuntimeError("Invalid GRO format from GenIce2")
        
        # Parse atom lines (lines 2 to n_atoms+1)
        positions = []
        atom_names = []
        residue_names = []  # Track residue names for guest molecule identification
        residue_seq_nums = []  # Track residue sequence numbers for molecule grouping
        
        for i in range(2, min(2 + n_atoms, len(lines))):
            line = lines[i]
            if not line.strip():
                continue
            if len(line) < 44:
                logger.warning("Dropping short GRO line %d: length %d < 44 chars", i+1, len(line))
                continue
            
            # GRO format fixed-width columns
            # Columns 0-5: residue sequence number (right-aligned)
            # Columns 5-10: residue name
            # Columns 10-15: atom name
            # Columns 20-28, 28-36, 36-44: x, y, z in nm
            # Example: "    1ICE      OW    1   1.065   0.370   0.004"
            #           ^5  ^10     ^15
            
            # Extract residue sequence number (columns 0-5) for grouping molecules
            try:
                residue_seq = int(line[0:5].strip())
            except ValueError:
                residue_seq = i  # Fallback to line index
            residue_seq_nums.append(residue_seq)
            
            # Extract residue name from columns 5-10 (needed for THF identification)
            residue_name = line[5:10].strip()
            residue_names.append(residue_name)
            
            # Extract atom name from columns 10-15 (correct for GRO format)
            atom_name = line[10:15].strip()
            if atom_name:
                atom_names.append(atom_name)
            
            # Extract positions (columns 20-28, 28-36, 36-44) - in nm
            try:
                x = float(line[20:28])
                y = float(line[28:36])
                z = float(line[36:44])
                positions.append([x, y, z])
            except (IndexError, ValueError) as e:
                logger.warning("Failed to parse coordinates from GRO line %d: %s", i+1, e)
        
        positions = np.array(positions, dtype=np.float64)
        
        # Parse box vectors from the last line matching the GRO box-line format
        # (exactly 3 floats for orthorhombic, or 9 floats for triclinic — all
        # numeric). Scan backwards from the end so trailing blank/whitespace
        # lines and any trailing non-box lines are skipped. This replaces a
        # fragile earlier loop that skipped lines whose first char was not a
        # digit and relied on the ``box_line = lines[-1]`` fallback, which
        # (a) broke when the input had trailing blank/whitespace lines (the
        # fallback picked a blank line) and (b) silently returned a 10 nm
        # default box for malformed input because ``_parse_box_line`` falls
        # back to ``np.eye(3) * 10.0`` when given <3 values. Standard GenIce2
        # output (box line is the final line, 3 or 9 numeric values) parses
        # identically to before.
        box_line = None
        for line in reversed(lines):
            values = line.split()
            if len(values) in (3, 9):
                try:
                    [float(v) for v in values]
                except ValueError:
                    continue
                box_line = line
                break
        
        if box_line is None:
            raise ValueError(
                "Invalid GRO format: no box-vector line found "
                "(expected a final line with 3 or 9 numeric box values)"
            )
        
        cell = self._parse_box_line(box_line)
        
        # NOTE: Do NOT wrap positions here!
        # Wrapping must happen in generate() with molecule grouping (line 103).
        # If we wrap here individually, molecules spanning boundaries will be
        # split across the cell before molecule_index is built, causing atoms
        # to be missing from rendered molecules.
        
        return positions, cell, atom_names, residue_names, residue_seq_nums
    
    def _parse_box_line(self, line: str) -> np.ndarray:
        """Parse box vector line from GRO file."""
        values = line.split()
        if len(values) >= 9:
            # Triclinic: v1(x) v2(y) v3(z) v1(y) v1(z) v2(x) v2(z) v3(x) v3(y)
            v1x = float(values[0])
            v2y = float(values[1])
            v3z = float(values[2])
            v1y = float(values[3]) if len(values) > 3 else 0.0
            v1z = float(values[4]) if len(values) > 4 else 0.0
            v2x = float(values[5]) if len(values) > 5 else 0.0
            v2z = float(values[6]) if len(values) > 6 else 0.0
            v3x = float(values[7]) if len(values) > 7 else 0.0
            v3y = float(values[8]) if len(values) > 8 else 0.0
            
            cell = np.array([
                [v1x, v1y, v1z],
                [v2x, v2y, v2z],
                [v3x, v3y, v3z],
            ], dtype=np.float64)
        elif len(values) >= 3:
            # Orthorhombic: just v1(x), v2(y), v3(z)
            cell = np.diag([float(v) for v in values[:3]])
        else:
            cell = np.eye(3) * 10.0  # Default 10nm box
        
        return cell
    
    def _wrap_positions_to_cell(self, positions: np.ndarray, cell: np.ndarray, molecule_index: list = None) -> np.ndarray:
        """Wrap atom positions into the unit cell using periodic boundary conditions.
        
        Ensures all positions are within [0, L) for each dimension, where L is
        the box length along that dimension. This handles cases where GenIce2
        outputs atoms with negative coordinates or slightly outside the box.
        
        IMPORTANT: Wraps by molecule (not individually) to keep molecules intact
        across boundaries. ALL atoms in a molecule are wrapped by the same shift
        vector, chosen to place atoms in the primary cell [0, L) when possible.
        
        Strategy:
        1. If all atoms are in the same cell (or primary cell), wrap all to primary cell
        2. If atoms span multiple cells, wrap to the mode (most common) cell
        
        Args:
            positions: (N, 3) array of atom positions in nm
            cell: (3, 3) cell matrix (orthorhombic or triclinic)
            molecule_index: List of MoleculeIndex entries for grouping atoms by molecule
        
        Returns:
            (N, 3) array of wrapped positions in [0, L) range
        """
        if molecule_index is None:
            # Fall back to individual wrapping (legacy behavior)
            return self._wrap_positions_individual(positions, cell)
        
        # Wrap by molecule (keep molecules intact)
        wrapped = positions.copy()
        
        # Determine if cell is orthorhombic
        is_orthorhombic = np.allclose(cell - np.diag(np.diag(cell)), 0)
        
        from collections import Counter
        
        if is_orthorhombic:
            L = np.diag(cell)
            
            for mol in molecule_index:
                start = mol.start_idx
                end = start + mol.count
                mol_positions = positions[start:end]
                
                # Compute the integer cell index for each atom
                cell_indices = np.floor(mol_positions / L).astype(int)
                
                # Check if all atoms are in the same cell
                unique_cells = set(tuple(idx) for idx in cell_indices)
                
                if len(unique_cells) == 1:
                    # All atoms in same cell - wrap to primary cell (0, 0, 0)
                    current_cell = np.array(list(unique_cells)[0])
                    shift = -current_cell * L
                    wrapped[start:end] = mol_positions + shift
                else:
                    # Atoms span multiple cells - wrap to mode cell
                    # But prefer primary cell if it's the mode
                    cell_tuples = [tuple(idx) for idx in cell_indices]
                    counter = Counter(cell_tuples)
                    most_common = counter.most_common()
                    max_count = most_common[0][1]
                    mode_candidates = [idx for idx, count in most_common if count == max_count]
                    
                    if (0, 0, 0) in mode_candidates:
                        mode_index = np.array((0, 0, 0))
                    else:
                        mode_index = np.array(mode_candidates[0])
                    
                    # Vectorized: compute shifts for all atoms at once
                    shifts = (mode_index - cell_indices) * L
                    wrapped[start:start + mol.count] = mol_positions + shifts
        else:
            # Triclinic cell - use fractional coordinates
            cell_inv = np.linalg.inv(cell)
            
            for mol in molecule_index:
                start = mol.start_idx
                end = start + mol.count
                mol_positions = positions[start:end]
                
                # Convert to fractional coordinates
                frac = mol_positions @ cell_inv
                
                # Compute the integer cell index for each atom in fractional space
                cell_indices = np.floor(frac).astype(int)
                
                # Check if all atoms are in the same cell
                unique_cells = set(tuple(idx) for idx in cell_indices)
                
                if len(unique_cells) == 1:
                    # All atoms in same cell - wrap to primary cell (0, 0, 0)
                    current_cell = np.array(list(unique_cells)[0])
                    shift_frac = -current_cell
                    # Vectorized: apply shift to all atoms at once
                    frac_wrapped = frac + shift_frac
                    frac_wrapped = frac_wrapped - np.floor(frac_wrapped)
                    wrapped[start:start + mol.count] = frac_wrapped @ cell
                else:
                    # Atoms span multiple cells - wrap to mode cell
                    cell_tuples = [tuple(idx) for idx in cell_indices]
                    counter = Counter(cell_tuples)
                    most_common = counter.most_common()
                    max_count = most_common[0][1]
                    mode_candidates = [idx for idx, count in most_common if count == max_count]
                    
                    if (0, 0, 0) in mode_candidates:
                        mode_index = np.array((0, 0, 0))
                    else:
                        mode_index = np.array(mode_candidates[0])
                    
                    # Vectorized: compute shifts for all atoms at once
                    shifts_frac = mode_index - cell_indices
                    frac_wrapped = frac + shifts_frac
                    frac_wrapped = frac_wrapped - np.floor(frac_wrapped)
                    wrapped[start:start + mol.count] = frac_wrapped @ cell
        
        return wrapped
    
    def _wrap_positions_individual(self, positions: np.ndarray, cell: np.ndarray) -> np.ndarray:
        """Wrap individual atom positions into the unit cell (legacy behavior).
        
        Args:
            positions: (N, 3) array of atom positions in nm
            cell: (3, 3) cell matrix (orthorhombic or triclinic)
        
        Returns:
            (N, 3) array of wrapped positions in [0, L) range
        """
        # For orthorhombic cells (diagonal matrix), use simple modulo
        # For non-orthogonal cells, convert to fractional coordinates, wrap, convert back
        if np.allclose(cell - np.diag(np.diag(cell)), 0):
            # Orthorhombic: cell is diagonal
            # Get box lengths from diagonal
            L = np.diag(cell)
            # Wrap each dimension using modulo (handles negative values too)
            wrapped = positions % L
            # Handle any positions that ended up at exactly L (should be 0)
            wrapped = np.where(wrapped < 0, 0.0, wrapped)
            wrapped = np.where(wrapped >= L, L - 1e-10, wrapped)
            return wrapped
        else:
            # Triclinic cell: use fractional coordinate wrapping
            # Convert to fractional coordinates
            cell_inv = np.linalg.inv(cell)
            frac = positions @ cell_inv
            # Wrap to [0, 1)
            frac = frac - np.floor(frac)
            # Convert back to Cartesian
            return frac @ cell
    
    def _build_molecule_index(self, atom_names: list[str], positions: np.ndarray, residue_names: list[str] = None, residue_seq_nums: list[int] = None, config: HydrateConfig | None = None) -> list[MoleculeIndex]:
        """Build molecule index from atom names.
        
        Groups atoms by molecule type based on atom naming patterns and residue names.
        When a HydrateConfig is provided, uses metadata-driven guest identification
        (guest_atom_labels, guest_atom_count, guest_type) instead of hardcoded patterns.
        
        Metadata-driven path (config provided):
        - Guest residue grouping: residue_name == guest_type.upper() → group by seq num
        - Guest atom-label matching: atom_names[i:i+count] == guest_atom_labels → guest
        - Guest is checked BEFORE water to prevent misidentification (e.g., THF "O" as water)
        - Water, ions, unknown handled as usual
        
        Pattern-matching path (config=None):
        - Backward-compatible hardcoded pattern matching (unchanged)
        
        Handles:
        - TIP4P water: OW, HW1, HW2, MW (4 atoms)
        - 3-site water: O, H, H (3 atoms)
        - Guest molecules: via metadata (config) or hardcoded patterns (config=None)
        - Ions: Na, Cl (1 atom each)
        
        Args:
            atom_names: List of atom names from GRO file
            positions: Array of positions (for length reference)
            residue_names: List of residue names from GRO file (for guest identification)
            residue_seq_nums: List of residue sequence numbers (for grouping molecules)
            config: Optional HydrateConfig with guest metadata for metadata-driven identification
        """
        molecule_index = []
        i = 0
        
        # Default empty residue_names if not provided
        if residue_names is None:
            residue_names = [""] * len(atom_names)
        
        # Default empty residue_seq_nums if not provided
        if residue_seq_nums is None:
            residue_seq_nums = list(range(len(atom_names)))
        
        # ── Metadata-driven path ──────────────────────────────────────
        if config is not None:
            # Build residue_name -> mol_type map from ALL cage assignments
            # (multi-guest). Built-ins: residue == guest_type.upper()
            # (ch4 -> "CH4"). Custom: residue == guest_residue_name (the
            # Molecule.name_ GenIce2 writes, e.g. "MOL").
            resname_to_moltype: dict[str, str] = {}
            # Keep the single-guest atom-label fallback path working: track
            # the PRIMARY (first) assignment's labels/count/guest_type for the
            # atom-signature fallback (backward compat for configs with a
            # single guest). For multi-guest the residue-grouping path is
            # authoritative (GenIce2 writes per-guest residue names).
            guest_atom_labels = config.guest_atom_labels
            guest_atom_count = config.guest_atom_count
            guest_type = config.guest_type  # primary (first assignment) for fallback
            guest_signature = guest_atom_labels[0] if guest_atom_labels else None
            for _cage_key, _assignment in config.cage_guest_assignments.items():
                if _assignment.guest_type in GUEST_MOLECULES:
                    _res_name = _assignment.guest_type.upper()  # ch4 -> "CH4"
                else:
                    _res_name = _assignment.guest_residue_name or _assignment.guest_type.upper()
                resname_to_moltype[_res_name] = _assignment.guest_type
            
            while i < len(atom_names):
                atom = atom_names[i]
                residue = residue_names[i] if i < len(residue_names) else ""
                
                # 1. Check guest by residue grouping (preferred for GenIce2 output).
                # Multi-guest: look up the residue name in resname_to_moltype
                # (built from ALL cage assignments) to get the per-type mol_type.
                if residue in resname_to_moltype and residue_seq_nums is not None:
                    guest_seq = residue_seq_nums[i]
                    guest_start = i
                    guest_count = 0
                    j = i
                    while j < len(residue_seq_nums) and residue_seq_nums[j] == guest_seq:
                        guest_count += 1
                        j += 1
                    mol_type = resname_to_moltype[residue]
                    molecule_index.append(MoleculeIndex(guest_start, guest_count, mol_type))
                    i = j
                    continue
                
                # 2. Check guest by atom-label sequence matching
                if (guest_signature is not None
                        and atom == guest_signature
                        and i + guest_atom_count <= len(atom_names)
                        and atom_names[i:i + guest_atom_count] == guest_atom_labels):
                    molecule_index.append(MoleculeIndex(i, guest_atom_count, guest_type))
                    i += guest_atom_count
                    continue
                
                # 3. Check for water (TIP4P: OW, HW1, HW2, MW)
                if atom == "OW" and i + 3 < len(atom_names):
                    next_atoms = atom_names[i:i+WATER_ATOMS_PER_MOLECULE]
                    if next_atoms[1] == "HW1" and next_atoms[2] == "HW2" and next_atoms[3] == "MW":
                        molecule_index.append(MoleculeIndex(i, WATER_ATOMS_PER_MOLECULE, "water"))
                        i += WATER_ATOMS_PER_MOLECULE
                        continue
                
                # 4. Check for 3-site water (O, H, H)
                #    Safe now because guest was already checked above —
                #    guest "O" (e.g., THF oxygen) won't reach here
                if atom == "O" and i + 2 < len(atom_names):
                    if atom_names[i+1] == "H" and atom_names[i+2] == "H":
                        molecule_index.append(MoleculeIndex(i, 3, "water"))
                        i += 3
                        continue
                
                # 5. Check for ions
                if atom in ["NA", "Na"]:
                    molecule_index.append(MoleculeIndex(i, 1, "na"))
                    i += 1
                    continue
                
                if atom in ["CL", "Cl"]:
                    molecule_index.append(MoleculeIndex(i, 1, "cl"))
                    i += 1
                    continue
                
                # 6. Unknown atom type
                logger.warning(
                    "Unknown atom type '%s' at index %d in hydrate candidate; "
                    "this may indicate an unsupported guest type. "
                    "Tracking as single-atom 'unknown' molecule.",
                    atom, i
                )
                molecule_index.append(MoleculeIndex(i, 1, "unknown"))
                i += 1
            
            return molecule_index
        
        # ── Pattern-matching path (config=None, backward compat) ──────
        while i < len(atom_names):
            atom = atom_names[i]
            residue = residue_names[i] if i < len(residue_names) else ""
            
            # Check for THF first (using residue name from GenIce2)
            # THF from GenIce2 has residue "THF" with 13 atoms: O, CA, CA, CB, CB, + 8H
            # Each THF molecule has a unique residue sequence number
            if residue == "THF":
                # Find all atoms with the same residue sequence number (same THF molecule)
                thf_seq = residue_seq_nums[i]
                thf_start = i
                thf_count = 0
                j = i
                while j < len(residue_seq_nums) and residue_seq_nums[j] == thf_seq:
                    thf_count += 1
                    j += 1
                molecule_index.append(MoleculeIndex(thf_start, thf_count, "thf"))
                i = j
                continue
            
            # Check for guest molecules (unique atom types)
            if atom == "Me":
                # United-atom methane (Me)
                molecule_index.append(MoleculeIndex(i, 1, "ch4"))
                i += 1
                continue
            
            # Check for all-atom methane (C followed by H atoms)
            # Be careful not to match THF carbon atoms (CA, CB)
            if atom == "C" and i + 4 < len(atom_names):
                # Make sure this is actually methane (C followed by 4 H atoms)
                # Check that residue is not THF (which uses CA, CB naming)
                next_atoms = atom_names[i+1:i+5]
                if all(a == "H" for a in next_atoms):
                    molecule_index.append(MoleculeIndex(i, 5, "ch4"))
                    i += 5
                    continue
            
            # Check for water (TIP4P: OW, HW1, HW2, MW)
            if atom == "OW" and i + 3 < len(atom_names):
                next_atoms = atom_names[i:i+WATER_ATOMS_PER_MOLECULE]
                if next_atoms[1] == "HW1" and next_atoms[2] == "HW2" and next_atoms[3] == "MW":
                    molecule_index.append(MoleculeIndex(i, WATER_ATOMS_PER_MOLECULE, "water"))
                    i += WATER_ATOMS_PER_MOLECULE
                    continue
            
            # Check for 3-site water (O, H, H)
            if atom == "O" and i + 2 < len(atom_names):
                # Make sure this isn't THF oxygen (THF has residue "THF")
                if atom_names[i+1] == "H" and atom_names[i+2] == "H" and residue != "THF":
                    molecule_index.append(MoleculeIndex(i, 3, "water"))
                    i += 3
                    continue
            
            # Check for ions
            if atom in ["NA", "Na"]:
                molecule_index.append(MoleculeIndex(i, 1, "na"))
                i += 1
                continue
            
            if atom in ["CL", "Cl"]:
                molecule_index.append(MoleculeIndex(i, 1, "cl"))
                i += 1
                continue
            
            # Unknown atom type - track as single-atom "unknown" molecule with warning
            logger.warning(
                "Unknown atom type '%s' at index %d in hydrate candidate; "
                "this may indicate an unsupported guest type. "
                "Tracking as single-atom 'unknown' molecule.",
                atom, i
            )
            molecule_index.append(MoleculeIndex(i, 1, "unknown"))
            i += 1
        
        return molecule_index
    
    def _generate_report(self, config: HydrateConfig, water_count: int, guest_count: int) -> str:
        """Generate human-readable report."""
        lattice_entry = HYDRATE_LATTICES[config.lattice_type]
        is_water_only = lattice_entry.get("is_water_only", False)

        lines = [
            f"Generated {config.lattice_type} hydrate structure",
            f"  Lattice: {config.lattice_type} ({config.get_genice_lattice_name()})",
        ]

        if is_water_only:
            lines.append(f"  Water-only lattice — no guest placement")
        elif config.is_custom_guest:
            # Custom guests are not in GUEST_MOLECULES; use guest_name
            # (which defaults to guest_residue_name per 40-03) and include
            # the residue name for traceability. Avoids KeyError on
            # GUEST_MOLECULES[config.guest_type].
            lines.extend([
                f"  Guest: {config.guest_name} (custom, residue={config.guest_residue_name})",
                f"  Small cage occupancy: {config.cage_occupancy_small}%",
                f"  Large cage occupancy: {config.cage_occupancy_large}%",
            ])
        else:
            lines.extend([
                f"  Guest: {GUEST_MOLECULES[config.guest_type]['name']}",
                f"  Small cage occupancy: {config.cage_occupancy_small}%",
                f"  Large cage occupancy: {config.cage_occupancy_large}%",
            ])

        lines.extend([
            f"  Supercell: {config.supercell_x} × {config.supercell_y} × {config.supercell_z}",
            f"  Water molecules: {water_count}",
        ])

        if not is_water_only:
            lines.append(f"  Guest molecules: {guest_count}")

        return "\n".join(lines)