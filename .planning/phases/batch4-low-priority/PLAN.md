---
phase: batch4-low-priority
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - quickice/structure_generation/types.py
  - quickice/output/gromacs_writer.py
  - quickice/utils/molecule_utils.py
  - quickice/gui/main_window.py
  - quickice/output/gromacs_writer.py
  - quickice/structure_generation/hydrate_generator.py
  - quickice/structure_generation/gromacs_ion_export.py
  - quickice/structure_generation/ion_inserter.py
  - quickice/ranking/scorer.py
  - quickice/ranking/types.py
  - docs/ranking.md
  - quickice/phase_mapping/water_density.py
  - quickice/phase_mapping/ice_ih_density.py
  - quickice/structure_generation/water_filler.py
  - quickice/structure_generation/molecule_validator.py
  - quickice/structure_generation/itp_parser.py
autonomous: true

must_haves:
  truths:
    - "THF atom count is 13 everywhere (C4H8O = 4C + 8H + 1O)"
    - "Debug logging in main_window.py uses logger.debug(), not logger.info()"
    - "Dead MOLECULE_TYPE_INFO imports removed from gromacs_writer.py and hydrate_generator.py"
    - "Ion ITP files include Madrid2019_085 header"
    - "AVOGADRO constant is 6.02214076e23 (CODATA 2017) everywhere"
    - "Ranking citations reference Petrenko & Whitworth (1999)"
    - "Extrapolated IAPWS values are logged at debug level"
    - "Fallback density warnings state actual T/P conditions"
    - "Water template caching is thread-safe via lru_cache"
    - "GenIce2 lazy loading is thread-safe via threading.Lock"
    - "GENERIC_RESIDUE_NAMES includes common PDB generic names"
    - "ITP parser strips BOM and normalizes line endings"
  artifacts:
    - path: "quickice/structure_generation/types.py"
      provides: "Correct THF atom count (13)"
    - path: "quickice/output/gromacs_writer.py"
      provides: "Fixed THF comment, removed dead import"
    - path: "quickice/structure_generation/water_filler.py"
      provides: "Thread-safe template caching"
  key_links:
    - from: "quickice/ranking/scorer.py"
      to: "quickice/structure_generation/solute_inserter.py"
      via: "AVOGADRO constant"
      pattern: "6\\.02214076e23"
---

<objective>
Fix 17 LOW priority issues across the codebase: THF atom count bugs, debug logging
levels, dead imports, missing scientific citations, constant inconsistencies,
suppressed warnings, thread safety, and fragile code.

Purpose: Improve code correctness, scientific accuracy, and robustness.
Output: All 17 issues resolved with precise search-and-replace edits.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<tasks>

<task type="auto">
  <name>Task 1: Fix THF atom counts and formula comments (Issues 21, 22, 23)</name>
  <files>
    quickice/structure_generation/types.py
    quickice/output/gromacs_writer.py
    quickice/utils/molecule_utils.py
  </files>
  <action>
    THF = C4H8O = 4C + 8H + 1O = 13 atoms. Fix ALL occurrences across 3 files.

    === File: quickice/structure_generation/types.py ===

    Edit 1 (line 17) — MOLECULE_TYPE_INFO dict:
      OLD:     "thf":   {"atoms": 12, "res_name": "THF", "description": "Tetrahydrofuran"},
      NEW:     "thf":   {"atoms": 13, "res_name": "THF", "description": "Tetrahydrofuran"},

    Edit 2 (line 30) — MoleculeIndex docstring:
      OLD:     - THF (12 atoms): C4O + 8H
      NEW:     - THF (13 atoms): C4H8O (4C + 8H + 1O)

    Edit 3 (line 87) — GUEST_MOLECULES dict:
      OLD:         "atoms": 12,
      NEW:         "atoms": 13,

    Edit 4 (line 247) — InterfaceStructure docstring:
      OLD:         Guest molecules vary (CH4: 5 atoms, THF: 12 atoms).
      NEW:         Guest molecules vary (CH4: 5 atoms, THF: 13 atoms).

    === File: quickice/output/gromacs_writer.py ===

    Edit 5 (line 841) — THF detection comment:
      OLD:     # THF: C5H8O (5 C, 8 H, 1 O = 14 atoms typically)
      NEW:     # THF: C4H8O (4 C, 8 H, 1 O = 13 atoms)

    === File: quickice/utils/molecule_utils.py ===

    Edit 6 (line 77) — THF comment:
      OLD:     # THF: C5H8O = 14 atoms, but GenIce2 outputs 13 atoms (some versions)
      NEW:     # THF: C4H8O = 13 atoms

    CAVEATS:
    - In types.py line 87, the string `"atoms": 12,` appears in the GUEST_MOLECULES
      dict under "thf". There is also `"atoms": 12` at line 17 under MOLECULE_TYPE_INFO.
      Both must change to 13. Use the surrounding context to make each edit unique.
    - In molecule_utils.py, lines 78-82 already have the correct atom count (13)
      in the code logic — only the comment on line 77 is wrong.
  </action>
  <verify>
    grep -n "atoms.*12\|12.*atoms\|C5H8O\|14 atoms" quickice/structure_generation/types.py quickice/output/gromacs_writer.py quickice/utils/molecule_utils.py
    # Should return NO matches (all 12s → 13, all C5H8O → C4H8O, all 14 atoms → 13 atoms)
  </verify>
  <done>No references to THF having 12 atoms or formula C5H8O remain in any of the 3 files</done>
</task>

<task type="auto">
  <name>Task 2: Fix debug logging, dead imports, and scientific metadata (Issues 24, 25, 26, 27, 28, 29, 30, 31)</name>
  <files>
    quickice/gui/main_window.py
    quickice/output/gromacs_writer.py
    quickice/structure_generation/hydrate_generator.py
    quickice/structure_generation/gromacs_ion_export.py
    quickice/structure_generation/ion_inserter.py
    quickice/ranking/scorer.py
    quickice/ranking/types.py
    docs/ranking.md
  </files>
  <action>
    === Issue 24: Debug logging at logger.info() level ===
    File: quickice/gui/main_window.py

    Change ALL logger.info() calls containing "[Water Count Debug]" to logger.debug().
    There are 9 occurrences. Do NOT change logger.warning() calls (lines 1234, 1240)
    — those indicate real issues and should stay at WARNING level.

    Edit 1 (line 1221):
      OLD:             logger.info(f"[Water Count Debug] Starting water replacement calculation...")
      NEW:             logger.debug(f"[Water Count Debug] Starting water replacement calculation...")

    Edit 2 (line 1222):
      OLD:             logger.info(f"[Water Count Debug] hasattr(_current_interface_result): {hasattr(self, '_current_interface_result')}")
      NEW:             logger.debug(f"[Water Count Debug] hasattr(_current_interface_result): {hasattr(self, '_current_interface_result')}")

    Edit 3 (line 1224):
      OLD:                 logger.info(f"[Water Count Debug] _current_interface_result is None: {self._current_interface_result is None}")
      NEW:                 logger.debug(f"[Water Count Debug] _current_interface_result is None: {self._current_interface_result is None}")

    Edit 4 (line 1228):
      OLD:                 logger.info(f"[Water Count Debug] original_water_count: {original_water_count}")
      NEW:                 logger.debug(f"[Water Count Debug] original_water_count: {original_water_count}")

    Edit 5 (line 1232):
      OLD:                     logger.info(f"[Water Count Debug] modified_water_count: {modified_water_count}")
      NEW:                     logger.debug(f"[Water Count Debug] modified_water_count: {modified_water_count}")

    Edit 6 (line 1237):
      OLD:                 logger.info(f"[Water Count Debug] water_replaced calculation: {original_water_count} - {modified_water_count} = {water_replaced}")
      NEW:                 logger.debug(f"[Water Count Debug] water_replaced calculation: {original_water_count} - {modified_water_count} = {water_replaced}")

    Edit 7 (line 1243):
      OLD:             logger.info(f"[Water Count Debug] Logging success message...")
      NEW:             logger.debug(f"[Water Count Debug] Logging success message...")

    Edit 8 (line 1250):
      OLD:             logger.info(f"[Water Count Debug] Checking if water_replaced > 0: {water_replaced > 0}")
      NEW:             logger.debug(f"[Water Count Debug] Checking if water_replaced > 0: {water_replaced > 0}")

    Edit 9 (line 1252):
      OLD:                 logger.info(f"[Water Count Debug] Logging water replacement message: {water_replaced} waters")
      NEW:                 logger.debug(f"[Water Count Debug] Logging water replacement message: {water_replaced} waters")

    Edit 10 (line 1257):
      OLD:                 logger.info(f"[Water Count Debug] No water replacement message (water_replaced={water_replaced})")
      NEW:                 logger.debug(f"[Water Count Debug] No water replacement message (water_replaced={water_replaced})")

    CAVEAT: Do NOT change the two logger.warning() calls on lines 1234 and 1240.
    Those are legitimate warnings about None values and missing data.

    === Issue 25: Dead import MOLECULE_TYPE_INFO in gromacs_writer.py ===
    File: quickice/output/gromacs_writer.py

    Edit (line 14):
      OLD: from quickice.structure_generation.types import Candidate, InterfaceStructure, IonStructure, MoleculeIndex, MOLECULE_TYPE_INFO
      NEW: from quickice.structure_generation.types import Candidate, InterfaceStructure, IonStructure, MoleculeIndex

    Verified: MOLECULE_TYPE_INFO appears only on the import line — never used in the file body.

    === Issue 26: Dead import MOLECULE_TYPE_INFO in hydrate_generator.py ===
    File: quickice/structure_generation/hydrate_generator.py

    Edit (lines 10-18):
      OLD:
    from quickice.structure_generation.types import (
        HydrateConfig,
        HydrateStructure,
        HydrateLatticeInfo,
        MoleculeIndex,
        MOLECULE_TYPE_INFO,
        HYDRATE_LATTICES,
        GUEST_MOLECULES,
    )
      NEW:
    from quickice.structure_generation.types import (
        HydrateConfig,
        HydrateStructure,
        HydrateLatticeInfo,
        MoleculeIndex,
        HYDRATE_LATTICES,
        GUEST_MOLECULES,
    )

    Verified: MOLECULE_TYPE_INFO appears only on line 15 (the import) — never used.

    === Issue 27: Generated ion.itp lacks Madrid2019_085 header ===
    File: quickice/structure_generation/gromacs_ion_export.py

    Edit (line 40) — add header before [ moleculetype ]:
      OLD:     itp_content = f"""[ moleculetype ]
      NEW:     itp_content = f"""; Madrid2019_085 ion model (Zeron et al., J. Chem. Phys. 2019)
    [ moleculetype ]

    === Issue 28: Ion parameters lack version tracking in output ===
    File: quickice/structure_generation/ion_inserter.py

    Edit (after line 8, before line 10):
      OLD: """
      NEW: """
    # Ion parameters from Madrid2019_085 (Zeron et al., J. Chem. Phys. 2019)

    Wait — that's ambiguous. Insert a comment block AFTER the module docstring.
    The actual edit:

      OLD: # Physical constants
    AVOGADRO = 6.02214076e23  # mol^-1
      NEW: # Ion parameters from Madrid2019_085 (Zeron et al., J. Chem. Phys. 2019)

    # Physical constants
    AVOGADRO = 6.02214076e23  # mol^-1 (CODATA 2017)

    === Issue 29: AVOGADRO constant inconsistency ===
    File: quickice/ranking/scorer.py

    Edit (line 168):
      OLD:     AVOGADRO = 6.022e23  # molecules/mol
      NEW:     AVOGADRO = 6.02214076e23  # molecules/mol (CODATA 2017)

    This matches the value already in ion_inserter.py (6.02214076e23).

    === Issue 30: Missing citations in ranking/types.py ===
    File: quickice/ranking/types.py

    Edit 1 (line 21):
      OLD:     ideal_oo_distance: float = 0.276  # nm - ideal O-O distance in ice (H-bond length)
      NEW:     ideal_oo_distance: float = 0.276  # nm - ideal O-O distance in ice (Petrenko & Whitworth, 1999, Physics of Ice)

    Edit 2 (line 22):
      OLD:     oo_cutoff: float = 0.35  # nm - cutoff for H-bond detection
      NEW:     oo_cutoff: float = 0.35  # nm - cutoff for O-O neighbor detection (common PBC cutoff)

    === Issue 31: Missing citation in docs/ranking.md ===
    File: docs/ranking.md

    Edit (line 31):
      OLD: - `0.276` = Ideal O-O distance in nm (typical hydrogen bond length)
      NEW: - `0.276` = Ideal O-O distance in nm (Petrenko & Whitworth, 1999, Physics of Ice)
  </action>
  <verify>
    # Verify debug logging
    grep -n 'logger\.info.*\[Water Count Debug\]' quickice/gui/main_window.py
    # Should return NO matches

    # Verify dead imports removed
    grep -n "MOLECULE_TYPE_INFO" quickice/output/gromacs_writer.py quickice/structure_generation/hydrate_generator.py
    # Should return NO matches

    # Verify Madrid header
    grep -n "Madrid2019_085" quickice/structure_generation/gromacs_ion_export.py quickice/structure_generation/ion_inserter.py
    # Should find matches in both files

    # Verify AVOGADRO
    grep -n "6.022e23" quickice/ranking/scorer.py
    # Should return NO matches (all should be 6.02214076e23)

    # Verify citations
    grep -n "Petrenko" quickice/ranking/types.py docs/ranking.md
    # Should find matches in both files
  </verify>
  <done>
    - All [Water Count Debug] logger.info() → logger.debug() in main_window.py
    - MOLECULE_TYPE_INFO import removed from gromacs_writer.py and hydrate_generator.py
    - ion.itp includes Madrid2019_085 header
    - ion_inserter.py has source comment
    - AVOGADRO = 6.02214076e23 in scorer.py
    - Petrenko & Whitworth citations in types.py and ranking.md
  </done>
</task>

<task type="auto">
  <name>Task 3: Fix warnings, thread safety, and fragile code (Issues 32, 33, 34, 35, 36, 37)</name>
  <files>
    quickice/phase_mapping/water_density.py
    quickice/phase_mapping/ice_ih_density.py
    quickice/structure_generation/water_filler.py
    quickice/structure_generation/hydrate_generator.py
    quickice/structure_generation/molecule_validator.py
    quickice/structure_generation/itp_parser.py
  </files>
  <action>
    === Issue 32: Suppressed IAPWS extrapolation warnings ===
    File: quickice/phase_mapping/water_density.py

    Add a logger.debug() call AFTER the IAPWS95 call succeeds with extrapolation,
    so developers know when extrapolated values are used. Insert after line 75
    (the water = IAPWS95(...) line) and before line 76 (rho = water.rho):

      OLD:             water = IAPWS95(T=T_K, P=P_MPa)
            rho = water.rho
      NEW:             water = IAPWS95(T=T_K, P=P_MPa)
            logger.debug(f"Using extrapolated IAPWS-95 value at T={T_K:.1f}K, P={P_MPa:.1f}MPa")
            rho = water.rho

    === Issue 33: Fallback density at 273.15K regardless of actual T/P ===
    File: quickice/phase_mapping/ice_ih_density.py

    Improve the warning message on line 74 to state the fallback conditions:

      OLD:         logger.warning(f"Using fallback density for ice Ih at T={T_K}K, P={P_MPa}MPa")
      NEW:         logger.warning(f"Using fallback density {FALLBACK_DENSITY_GCM3} g/cm³ (273.15K, 0.1MPa) for ice Ih at T={T_K}K, P={P_MPa}MPa — IAPWS calculation failed, density is approximate")

    === Issue 34: Module-level mutable cache without thread safety (water_filler.py) ===
    File: quickice/structure_generation/water_filler.py

    Replace the manual module-level cache with @functools.lru_cache(maxsize=1).
    The function load_water_template() takes no arguments and returns a tuple,
    making lru_cache ideal. functools is NOT currently imported.

    Step 1: Add functools import. Insert after line 11 (import math):
      OLD: import math
    from pathlib import Path
      NEW: import math
    from functools import lru_cache
    from pathlib import Path

    Step 2: Remove the module-level cache variable (line 144):
      OLD: # Module-level cache for water template (never changes)
    _water_template_cache: Optional[tuple[np.ndarray, list[str], np.ndarray]] = None
      NEW: # (cached via @lru_cache on load_water_template)

    Step 3: Add @lru_cache decorator and remove manual caching in load_water_template():
      OLD: def load_water_template() -> tuple[np.ndarray, list[str], np.ndarray]:
      """Load the bundled TIP4P water template from tip4p.gro.

      Uses shared gro_parser module. Results are cached at module
      level since the template never changes.
      NEW: @lru_cache(maxsize=1)
    def load_water_template() -> tuple[np.ndarray, list[str], np.ndarray]:
      """Load the bundled TIP4P water template from tip4p.gro.

      Uses shared gro_parser module. Results are cached via
      @lru_cache(maxsize=1) since the template never changes.

    Step 4: Remove the global statement and manual caching logic in the function body:
      OLD:     global _water_template_cache

      if _water_template_cache is not None:
          return _water_template_cache

      # Locate the bundled tip4p.gro file
      NEW:     # Locate the bundled tip4p.gro file

    Step 5: Remove the cache assignment at the end (before the return):
      OLD:     # Cache the result
      _water_template_cache = (positions, atom_names, box_dims)

      return positions, atom_names, box_dims
      NEW:     return positions, atom_names, box_dims

    === Issue 35: Module-level globals without thread safety (hydrate_generator.py) ===
    File: quickice/structure_generation/hydrate_generator.py

    Add threading.Lock to protect the lazy-loading code.

    Step 1: Add threading import. Insert after line 7 (import numpy as np):
      OLD: import numpy as np
    from pathlib import Path
      NEW: import numpy as np
    import threading
    from pathlib import Path

    Step 2: Add module-level lock (after line 30, the existing module-level globals):
      OLD: _lattice_modules_loaded = {}


      class HydrateStructureGenerator:
      NEW: _lattice_modules_loaded = {}

    # Lock for thread-safe lazy loading of GenIce2
    _genice_lock = threading.Lock()


      class HydrateStructureGenerator:

    Step 3: Add lock to _ensure_genice_import method (line 49-51):
      OLD:     def _ensure_genice_import(self):
        """Lazy import of GenIce2 to avoid startup overhead."""
        global _genice_lib, _gromacs_format, _lattice_modules_loaded
        
        if self._genice_lib is None:
      NEW:     def _ensure_genice_import(self):
        """Lazy import of GenIce2 to avoid startup overhead."""
        
        if self._genice_lib is not None:
            return
        
        with _genice_lock:
            # Double-check after acquiring lock
            if self._genice_lib is not None:
                return

    Step 4: Indent the try block body inside the with block (lines 54-72).
    The entire try/except block needs to be indented by 4 more spaces
    since it's now inside the `with _genice_lock:` block.

    Replace the old try block with the indented version:
      OLD:             try:
                import genice2.genice as genice_lib
                from genice2.formats import gromacs
                from genice2.lattices import sI, sII, sH
                from genice2.molecules.tip4p import Molecule as TIP4P
                
                self._genice_lib = genice_lib
                self._gromacs_format = gromacs
                self._lattice_modules = {
                    "sI": sI,
                    "sII": sII,
                    "sH": sH,
                }
                self._water_molecule = TIP4P()
            except ImportError as e:
                raise ImportError(
                    "GenIce2 is required for hydrate generation. "
                    f"Import error: {e}"
                )
      NEW:                 try:
                    import genice2.genice as genice_lib
                    from genice2.formats import gromacs
                    from genice2.lattices import sI, sII, sH
                    from genice2.molecules.tip4p import Molecule as TIP4P
                    
                    self._genice_lib = genice_lib
                    self._gromacs_format = gromacs
                    self._lattice_modules = {
                        "sI": sI,
                        "sII": sII,
                        "sH": sH,
                    }
                    self._water_molecule = TIP4P()
                except ImportError as e:
                    raise ImportError(
                        "GenIce2 is required for hydrate generation. "
                        f"Import error: {e}"
                    )

    Also remove the module-level globals that are no longer needed (lines 28-30)
    since the class uses instance attributes:
      OLD: # Lazy-loaded GenIce2 modules (loaded in _ensure_genice_import)
    _genice_lib = None
    _gromacs_format = None
    _lattice_modules_loaded = {}
      NEW: # Thread-safe lock for GenIce2 lazy loading (loaded in _ensure_genice_import)

    === Issue 36: Hardcoded GENERIC_RESIDUE_NAMES ===
    File: quickice/structure_generation/molecule_validator.py

    Edit (line 18):
      OLD: GENERIC_RESIDUE_NAMES = {"MOL", "UNK", "LIG", "XXX", "RES"}
      NEW: GENERIC_RESIDUE_NAMES = {"MOL", "UNK", "LIG", "XXX", "RES", "DRG", "API", "HET", "UNL", "LIG1", "MOL1"}

    === Issue 37: ITP regex fragile for non-standard formatting ===
    File: quickice/structure_generation/itp_parser.py

    Add BOM stripping and line ending normalization at the start of parse_itp_file(),
    after reading the content (line 60) and before the regex (line 61).

      OLD:     content = filepath.read_text()
        logger.info(f"Parsing ITP file: {filepath.name}")
      NEW:     content = filepath.read_text()
        # Normalize: strip BOM, normalize line endings
        content = content.lstrip('\ufeff')
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        logger.info(f"Parsing ITP file: {filepath.name}")
  </action>
  <verify>
    # Verify extrapolation debug logging
    grep -n "extrapolated IAPWS" quickice/phase_mapping/water_density.py

    # Verify improved warning message
    grep -n "fallback density" quickice/phase_mapping/ice_ih_density.py

    # Verify lru_cache on water template
    grep -n "lru_cache\|_water_template_cache" quickice/structure_generation/water_filler.py
    # Should find @lru_cache and NO _water_template_cache references

    # Verify threading lock
    grep -n "threading\|_genice_lock" quickice/structure_generation/hydrate_generator.py

    # Verify expanded residue names
    grep -n "GENERIC_RESIDUE_NAMES" quickice/structure_generation/molecule_validator.py
    # Should include DRG, API, HET, UNL, LIG1, MOL1

    # Verify BOM stripping
    grep -n "lstrip.*ufeff\|replace.*r.n" quickice/structure_generation/itp_parser.py
  </verify>
  <done>
    - IAPWS extrapolation values logged at debug level
    - Ice Ih fallback warning includes actual conditions and "approximate" note
    - Water template cached via @lru_cache (thread-safe)
    - GenIce2 lazy loading protected by threading.Lock with double-check pattern
    - GENERIC_RESIDUE_NAMES expanded with 6 additional PDB generic names
    - ITP parser strips BOM and normalizes line endings before parsing
  </done>
</task>

</tasks>

<verification>
Run all verification commands from each task:
1. grep -n "atoms.*12\|C5H8O\|14 atoms" quickice/structure_generation/types.py quickice/output/gromacs_writer.py quickice/utils/molecule_utils.py
2. grep -n 'logger\.info.*\[Water Count Debug\]' quickice/gui/main_window.py
3. grep -n "MOLECULE_TYPE_INFO" quickice/output/gromacs_writer.py quickice/structure_generation/hydrate_generator.py
4. grep -n "Madrid2019_085" quickice/structure_generation/gromacs_ion_export.py quickice/structure_generation/ion_inserter.py
5. grep -n "6.022e23" quickice/ranking/scorer.py
6. grep -n "Petrenko" quickice/ranking/types.py docs/ranking.md
7. grep -n "extrapolated IAPWS" quickice/phase_mapping/water_density.py
8. grep -n "fallback density" quickice/phase_mapping/ice_ih_density.py
9. grep -n "lru_cache" quickice/structure_generation/water_filler.py
10. grep -n "threading\|_genice_lock" quickice/structure_generation/hydrate_generator.py
11. grep -n "GENERIC_RESIDUE_NAMES" quickice/structure_generation/molecule_validator.py
12. grep -n "lstrip.*ufeff\|replace.*r.n" quickice/structure_generation/itp_parser.py

Also run: python -c "import quickice" to verify no import errors.
</verification>

<success_criteria>
All 17 LOW priority issues resolved:
- THF atom count = 13 everywhere (4 occurrences in types.py, 1 in gromacs_writer.py, 1 in molecule_utils.py)
- 10 logger.info("[Water Count Debug]") → logger.debug() in main_window.py
- 2 dead MOLECULE_TYPE_INFO imports removed
- Madrid2019_085 header added to ion.itp generation
- Source comment added to ion_inserter.py
- AVOGADRO = 6.02214076e23 in scorer.py (matches CODATA 2017)
- Petrenko & Whitworth citations in types.py and ranking.md
- IAPWS extrapolation logged at debug level
- Ice Ih fallback warning improved with conditions
- Water template caching uses @lru_cache (thread-safe)
- GenIce2 lazy loading uses threading.Lock (thread-safe)
- GENERIC_RESIDUE_NAMES expanded with DRG, API, HET, UNL, LIG1, MOL1
- ITP parser strips BOM and normalizes line endings
</success_criteria>

<output>
After completion, create `.planning/phases/batch4-low-priority/01-SUMMARY.md`
</output>
