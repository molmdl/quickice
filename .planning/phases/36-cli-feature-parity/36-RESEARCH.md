# Phase 36: CLI Feature Parity - Research

**Researched:** 2026-06-14
**Domain:** CLI architecture for multi-step scientific workflows (internal codebase focus)
**Confidence:** HIGH

## Summary

This research investigates how to bring the CLI to feature parity with the GUI, which supports 6 tabs (Ice, Hydrate, Interface, Custom Molecule, Solute, Ion) with workflow chaining (Interface→Custom→Solute→Ion), source selection dropdowns, and complete system export. The current CLI only supports Ice generation + ranking + PDB/GROMACS export, and Interface generation (slab/pocket/piece) + GROMACS export.

The CLI must support a **pipeline workflow** where each step's output feeds the next step, but without the GUI's in-memory state passing. The right architecture is **Approach A: Linear flags with sequential execution** — add `--hydrate`, `--custom-gro`/`--custom-itp`, `--solute-type`/`--solute-concentration`, `--ion-concentration`, and `--ion-source`/`--solute-source` flags that define a pipeline executed in order. This avoids subcommand refactoring complexity while preserving the exact backend API call patterns the GUI already uses. The key challenge is representing source selection (which prior step's structure to use) — solved by making the pipeline implicit: if you specify `--solute-type` after `--custom-gro`, the solute step uses the custom molecule output as source.

**Primary recommendation:** Extend the existing argparse linear-flag pattern with pipeline-ordered flag groups. Each flag group triggers a step in the Interface→Custom→Solute→Ion pipeline. Source selection is implicit from flag ordering, not explicit dropdowns.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| argparse | stdlib | CLI argument parsing | Already established in parser.py (252 lines) |
| logging | stdlib | Progress reporting | Already used throughout codebase |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tqdm | optional | Progress bars for long operations | Only if available; graceful fallback |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| argparse linear flags | click subcommands | Subcommands = cleaner but requires full parser refactor, breaks backwards compat |
| argparse linear flags | pipeline state files (pickle/JSON) | Most flexible but adds file management, serialization complexity |

**Installation:**
```bash
# No new dependencies needed - argparse is stdlib
# Optional: pip install tqdm  (progress bars)
```

## Architecture Patterns

### Recommended Project Structure
```
quickice/
├── cli/
│   ├── parser.py          # Extended with hydrate/solute/custom/ion flag groups
│   └── pipeline.py        # NEW: Pipeline executor - orchestrates step sequence
├── main.py                # Updated to use pipeline executor
└── structure_generation/  # Unchanged - backend modules called by pipeline
```

### Pattern 1: Linear Flag Pipeline (RECOMMENDED)

**What:** Add sequential flag groups to argparse. Each group represents one step. Steps execute in order: Interface→Custom→Solute→Ion. Source selection is implicit from which prior steps ran.

**When to use:** This is the primary CLI workflow pattern.

**Example:**
```python
# Source: Current parser.py pattern + extension
def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(...)
    
    # === Core parameters (existing) ===
    parser.add_argument("--temperature", "-T", ...)
    parser.add_argument("--pressure", "-P", ...)
    parser.add_argument("--nmolecules", "-N", ...)
    parser.add_argument("--output", "-o", ...)
    parser.add_argument("--gromacs", "-g", ...)
    parser.add_argument("--seed", ...)
    
    # === Interface generation (existing) ===
    interface_group = parser.add_argument_group('interface generation')
    interface_group.add_argument("--interface", action="store_true")
    interface_group.add_argument("--mode", choices=["slab", "pocket", "piece"])
    interface_group.add_argument("--box-x", "--box-y", "--box-z")
    interface_group.add_argument("--ice-thickness", "--water-thickness")
    interface_group.add_argument("--pocket-diameter", "--pocket-shape")
    
    # === Hydrate generation (NEW) ===
    hydrate_group = parser.add_argument_group('hydrate generation')
    hydrate_group.add_argument("--hydrate", action="store_true")
    hydrate_group.add_argument("--lattice-type", choices=["sI", "sII", "sH"])
    hydrate_group.add_argument("--guest", choices=["CH4", "THF"])
    hydrate_group.add_argument("--supercell-x", "--supercell-y", "--supercell-z", type=int)
    hydrate_group.add_argument("--cage-occupancy-small", "--cage-occupancy-large", type=float)
    
    # === Custom molecule insertion (NEW) ===
    custom_group = parser.add_argument_group('custom molecule insertion')
    custom_group.add_argument("--custom-gro", type=str, help="Path to .gro file")
    custom_group.add_argument("--custom-itp", type=str, help="Path to .itp file")
    custom_group.add_argument("--custom-placement", choices=["random", "custom"])
    custom_group.add_argument("--custom-count", type=int, help="Molecule count (random mode)")
    custom_group.add_argument("--custom-concentration", type=float, help="mol/L (random mode)")
    
    # === Solute insertion (NEW) ===
    solute_group = parser.add_argument_group('solute insertion')
    solute_group.add_argument("--solute-type", choices=["CH4", "THF"])
    solute_group.add_argument("--solute-concentration", type=float, help="mol/L")
    solute_group.add_argument("--solute-source", choices=["interface", "custom"],
                               default="interface", help="Source structure for solute")
    
    # === Ion insertion (NEW) ===
    ion_group = parser.add_argument_group('ion insertion')
    ion_group.add_argument("--ion-concentration", type=float, help="NaCl mol/L")
    ion_group.add_argument("--ion-source", choices=["interface", "custom", "solute"],
                            default="interface", help="Source structure for ions")
    
    return parser
```

### Pattern 2: Pipeline Executor (NEW module)

**What:** A `pipeline.py` module that executes steps in sequence, passing results between steps (mirroring GUI's in-memory state passing).

**When to use:** The core orchestration logic that replaces main.py's monolithic flow.

**Example:**
```python
# Source: Derived from GUI MainWindow._on_insert_solutes(), _on_insert_ions() patterns
class CLIPipeline:
    """Orchestrates multi-step structure generation pipeline."""
    
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self._interface_result = None
        self._hydrate_result = None
        self._custom_result = None
        self._solute_result = None
        self._ion_result = None
    
    def execute(self) -> int:
        """Run all requested pipeline steps in order."""
        # Step 1: Generate ice or hydrate (source for interface)
        if self.args.interface or self.args.hydrate:
            self._run_source_step()
        
        # Step 2: Interface generation (if --interface)
        if self.args.interface:
            self._run_interface_step()
        
        # Step 3: Custom molecule insertion (if --custom-gro)
        if self.args.custom_gro:
            self._run_custom_step()
        
        # Step 4: Solute insertion (if --solute-type)
        if self.args.solute_type:
            self._run_solute_step()
        
        # Step 5: Ion insertion (if --ion-concentration)
        if self.args.ion_concentration:
            self._run_ion_step()
        
        # Step 6: Export
        self._run_export_step()
        return 0
    
    def _get_source_structure(self, source_name: str):
        """Get structure by source name (mirrors GUI source dropdown logic)."""
        if source_name == "interface":
            return self._interface_result
        elif source_name == "custom":
            return self._custom_result
        elif source_name == "solute":
            return self._solute_result
        raise ValueError(f"Unknown source: {source_name}")
```

### Pattern 3: Progress Reporting to stderr

**What:** Print progress to stderr (separate from stdout for piping), following the GUI's log panel pattern.

**When to use:** All long-running operations.

**Example:**
```python
# Source: Derived from Quick Task 015 pattern + existing main.py print() style
def report_progress(message: str):
    """Display progress message to stderr (keeps stdout clean for piping)."""
    print(f"[PROGRESS] {message}", file=sys.stderr)
```

### Anti-Patterns to Avoid
- **Subcommand refactor:** Do NOT convert to `quickice generate ice`, `quickice insert-solute`, etc. The existing argparse pattern works, users expect `python quickice.py -T 300 -P 100`, and subcommands break this.
- **State file persistence:** Do NOT serialize intermediate structures to pickle/JSON between steps. The pipeline runs in a single process — pass objects in memory like the GUI does.
- **Custom placement position CLI:** Do NOT try to replicate the GUI's table-based position editor on the CLI. For custom placement mode, use a CSV file input instead of individual flags.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Solute insertion | Custom placement loop | `SoluteInserter.insert_solutes()` | 891 lines of overlap checking, KDTree, water replacement |
| Custom molecule placement | Custom insertion logic | `CustomMoleculeInserter.place_random()` / `.place_custom()` | 949 lines of template loading, rotation, overlap checking |
| Ion insertion | Custom ion placement | `IonInserter.replace_water_with_ions()` | 585 lines of charge neutrality, overlap checking |
| GROMACS export | Custom .gro/.top writer | `write_ion_gro_file()`, `write_solute_gro_file()`, etc. | 2500+ lines of format handling, MW computation, wrapping |
| Hydrate generation | Custom lattice builder | `HydrateGenerator.generate()` | Full GenIce2 integration |
| Source structure passing | Custom structure combiner | Existing interface_structure attribute pattern | Structures already carry `interface_structure` for chaining |

**Key insight:** The backend modules already support the full Interface→Custom→Solute→Ion pipeline through their data structures (each output type carries an `interface_structure` reference). The CLI just needs to wire the same calls the GUI makes.

## Complete CLI vs GUI Feature Gap Matrix

### Currently Supported in CLI
| Feature | CLI Flag | GUI Tab | Status |
|---------|----------|---------|--------|
| Ice generation | `--temperature`, `--pressure`, `--nmolecules` | Tab 0 (Ice) | ✅ EXISTS |
| Phase lookup | Automatic | Tab 0 | ✅ EXISTS |
| Candidate ranking | Automatic (10 candidates) | Tab 0 | ✅ EXISTS |
| GROMACS export (ice) | `--gromacs`, `--candidate` | File menu | ✅ EXISTS |
| PDB export | Automatic | File menu | ✅ EXISTS |
| Phase diagram | `--no-diagram` to disable | Tab 0 left | ✅ EXISTS |
| Interface generation | `--interface`, `--mode` | Tab 2 | ✅ EXISTS |
| Slab mode | `--ice-thickness`, `--water-thickness` | Tab 2 | ✅ EXISTS |
| Pocket mode | `--pocket-diameter`, `--pocket-shape` | Tab 2 | ✅ EXISTS |
| Piece mode | `--mode piece` | Tab 2 | ✅ EXISTS |
| Random seed | `--seed` | Tab 2 | ✅ EXISTS |
| GROMACS export (interface) | Automatic with `--interface` | File menu | ✅ EXISTS |
| Box dimensions | `--box-x`, `--box-y`, `--box-z` | Tab 2 | ✅ EXISTS |

### NOT Supported in CLI (GAP)
| Feature | GUI Tab | CLI Equivalent Needed | Priority |
|---------|---------|---------------------|----------|
| Hydrate generation | Tab 1 (Hydrate) | `--hydrate`, `--lattice-type`, `--guest` | HIGH |
| Custom molecule insertion | Tab 3 (Custom) | `--custom-gro`, `--custom-itp`, `--custom-placement`, `--custom-count` | HIGH |
| Solute insertion | Tab 4 (Solute) | `--solute-type`, `--solute-concentration` | HIGH |
| Ion insertion | Tab 5 (Ion) | `--ion-concentration` | HIGH |
| Source selection (ion) | Tab 5 dropdown | `--ion-source {interface,custom,solute}` | HIGH |
| Source selection (solute) | Tab 4 dropdown | `--solute-source {interface,custom}` | MEDIUM |
| Custom placement positions | Tab 3 position table | CSV file input `--custom-positions-file` | MEDIUM |
| Hydrate supercell | Tab 1 controls | `--supercell-x/y/z` | MEDIUM |
| Cage occupancy | Tab 1 controls | `--cage-occupancy-small/large` | MEDIUM |
| GROMACS export (hydrate) | File menu | Auto with `--hydrate` | HIGH |
| GROMACS export (custom) | File menu | Auto with `--custom-gro` | HIGH |
| GROMACS export (solute) | File menu | Auto with `--solute-type` | HIGH |
| GROMACS export (ion) | File menu | Auto with `--ion-concentration` | HIGH |
| Complete system export | Each tab exports full system | Auto at pipeline end | HIGH |
| Progress reporting | Log panel + progress bar | stderr messages | MEDIUM |
| Concentration input mode | Tab 3 "By Count/By Concentration" | `--custom-count` OR `--custom-concentration` | MEDIUM |

### GUI-Only Features (SKIP for CLI)
| Feature | GUI Tab | Why Skip | CLI Alternative |
|---------|---------|----------|----------------|
| 3D preview/rendering | All tabs | VTK-dependent, no headless mode | N/A |
| Placement validation preview | Tab 3 | VTK preview is GUI-only | Bounds check + overlap check still run (backend logic) |
| Keyboard shortcuts | All | Interactive-only | `--help` suffices |
| Help tooltips | All | Interactive-only | `--help` suffices |
| Residue name mismatch dialog | Tab 3 | Interactive dialog | Auto-accept ITP residue name (no user to ask) |
| Previous molecule clearing dialog | Tab 3 | Interactive dialog | Auto-clear on each run |
| Charge warning | Tab 5 | GUI label | Print warning to stderr |
| File overwrite prompt | main.py | Interactive | `--force` flag or auto-overwrite |

## Updated CLI Requirements (Superseding Stale CLI-01 to CLI-05)

The original CLI-01 through CLI-05 were written BEFORE phases 34.1-34.8 inserted ion source dropdowns, solute source dropdowns, complete system export, separate liquid solute ITP files, and placement validation. Here are the UPDATED requirements:

### CLI-01: Hydrate Generation
- **`--hydrate`** flag triggers hydrate generation mode
- **`--lattice-type`** selects sI, sII, or sH (default: sI)
- **`--guest`** selects CH4 or THF (default: CH4)
- **`--supercell-x/y/z`** for supercell dimensions (default: 1)
- **`--cage-occupancy-small`** and **`--cage-occupancy-large`** (default: 100.0)
- Hydrate can be used as source for interface generation (same as GUI: "Use in Interface →")
- GROMACS export auto-generated with `--hydrate`

### CLI-02: Solute Insertion
- **`--solute-type`** selects CH4 or THF
- **`--solute-concentration`** in mol/L (required with `--solute-type`)
- **`--solute-source`** selects interface or custom (default: interface)
  - "interface" = use interface structure from `--interface` step
  - "custom" = use custom molecule structure from `--custom-gro` step
- Uses **liquid solute ITP files** (CH4_LIQUID, THF_LIQUID) — NOT hydrate ITP (Phase 34.2)
- Complete system export: ice + water + custom (if any) + solutes

### CLI-03: Custom Molecule Insertion
- **`--custom-gro`** path to .gro file (required for custom molecule)
- **`--custom-itp`** path to .itp file (required for custom molecule)
- **`--custom-placement`** selects "random" or "custom" (default: random)
- **`--custom-count`** molecule count for random mode
- **`--custom-concentration`** concentration in mol/L (alternative to --custom-count)
- **`--custom-positions-file`** CSV file for custom mode (position + rotation per line)
- Placement validation bounds checking runs (backend logic, no VTK preview)
- Complete system export: ice + water + custom molecules

### CLI-04: Ion Insertion
- **`--ion-concentration`** NaCl concentration in mol/L (required for ions)
- **`--ion-source`** selects interface, custom, or solute (default: interface)
  - "interface" = use interface structure directly
  - "custom" = use custom molecule structure (carries interface + custom molecules)
  - "solute" = use solute structure (carries interface + custom + solutes)
- Charge neutrality maintained automatically (same as GUI)
- Complete system export: ice + water + guests + custom + solutes + ions

### CLI-05: Progress Reporting
- Progress messages printed to **stderr** (separate from stdout for piping)
- Key progress points: generation start, molecule count, insertion count, export
- Optional tqdm progress bar if installed
- Final summary: atom counts, molecule counts, file paths

### CLI-06: Pipeline Workflow (NEW — not in original requirements)
- Steps execute in order: Source (ice/hydrate) → Interface → Custom → Solute → Ion → Export
- Each step's output is stored in memory for the next step
- Source selection flags (--ion-source, --solute-source) determine which prior step's structure to use
- Full pipeline: `python quickice.py -T 270 -P 0.1 --interface --mode slab --box-x 3 --box-y 3 --box-z 5 --ice-thickness 1.5 --water-thickness 2.0 --solute-type CH4 --solute-concentration 0.5 --ion-concentration 0.15 --gromacs -o output`

### CLI-07: Complete System Export (NEW — from Phase 34.6)
- Each pipeline step produces a "complete system" (ice + water + own molecules)
- Export automatically selects the most downstream structure available:
  - With ions → export ion structure (most complete)
  - With solutes (no ions) → export solute structure
  - With custom (no solutes/ions) → export custom structure
  - With only interface → export interface structure
- All GROMACS files (.gro + .top + .itp files) copied to output directory

## Inserter/Exporter API Signatures for CLI Wiring

### SoluteInserter (solute_inserter.py)
```python
class SoluteInserter:
    def __init__(self, config: SoluteConfig | None = None, seed: int | None = None)
    def insert_solutes(self, structure: InterfaceStructure, config: SoluteConfig | None = None) -> SoluteStructure

# Convenience function:
def insert_solutes(structure: InterfaceStructure, concentration_molar: float, 
                   solute_type: str = "CH4", seed: int | None = None) -> SoluteStructure
```
- **Input:** InterfaceStructure or CustomMoleculeStructure (carries interface_structure attribute)
- **Output:** SoluteStructure with `.interface_structure` carrying modified InterfaceStructure
- **Key:** SoluteStructure carries `custom_molecule_*` attributes for pipeline chaining

### CustomMoleculeInserter (custom_molecule_inserter.py)
```python
class CustomMoleculeInserter:
    def __init__(self, config: CustomMoleculeConfig, registry: MoleculetypeRegistry | None = None, seed: int | None = None)
    def place_random(self, structure: InterfaceStructure, n_molecules: int) -> CustomMoleculeStructure
    def place_custom(self, structure: InterfaceStructure, 
                     positions: list[tuple[float,float,float]], 
                     rotations: list[tuple[float,float,float]]) -> CustomMoleculeStructure
    @staticmethod
    def calculate_molecule_count(concentration_molar: float, liquid_volume_nm3: float) -> int
    @staticmethod
    def calculate_concentration(molecule_count: int, liquid_volume_nm3: float) -> float
```
- **Input:** InterfaceStructure
- **Output:** CustomMoleculeStructure with `.interface_structure` for downstream use
- **Key:** CustomMoleculeStructure has `.moleculetype_name`, `.gro_path`, `.itp_path` for export

### IonInserter (ion_inserter.py)
```python
class IonInserter:
    def __init__(self, config: IonConfig | None = None, seed: int | None = None)
    def calculate_ion_pairs(self, concentration_molar: float, liquid_volume_nm3: float) -> int
    def replace_water_with_ions(self, structure: IonStructure, ion_pairs: int) -> IonStructure

# Convenience function:
def insert_ions(structure, concentration_molar: float, 
                liquid_volume_nm3: float | None = None, seed: int | None = None) -> IonStructure
```
- **Input:** IonStructure (but actually accepts InterfaceStructure via duck typing)
- **Key for source selection:** When source is "solute", must add solute attributes to interface:
  ```python
  interface.solute_type = solute_structure.solute_type
  interface.solute_positions = solute_structure.positions
  interface.solute_atom_names = solute_structure.atom_names
  interface.solute_n_molecules = solute_structure.n_molecules
  interface.solute_molecule_indices = solute_structure.molecule_indices
  interface.solute_registry = solute_structure.registry
  ```
  (This is exactly what the GUI does in MainWindow._on_insert_ions lines 864-871)

### HydrateGenerator (hydrate_generator.py)
```python
class HydrateGenerator:
    def __init__(self, config: HydrateConfig)
    def generate(self) -> HydrateStructure
```
- **Input:** HydrateConfig
- **Output:** HydrateStructure with `.to_candidate()` method for interface use

### GROMACS Export Functions (gromacs_writer.py)
| Function | Input Type | When CLI Uses It |
|----------|-----------|-----------------|
| `write_interface_gro_file(iface, filepath)` | InterfaceStructure | Interface-only pipeline |
| `write_interface_top_file(iface, filepath)` | InterfaceStructure | Interface-only pipeline |
| `write_custom_molecule_gro_file(custom, filepath)` | CustomMoleculeStructure | Custom step present |
| `write_custom_molecule_top_file(custom, filepath)` | CustomMoleculeStructure | Custom step present |
| `write_solute_gro_file(solute, filepath)` | SoluteStructure | Solute step present |
| `write_solute_top_file(solute, filepath)` | SoluteStructure | Solute step present |
| `write_ion_gro_file(ion, filepath)` | IonStructure | Ion step present |
| `write_ion_top_file(ion, filepath)` | IonStructure | Ion step present |

## Quick Tasks 013-015 Disposition

### Quick Task 013: CLI Hydrate Support
- **Status:** PLANNED but NEVER EXECUTED (no SUMMARY file)
- **Plan validity:** Still valid — `--hydrate`, `--lattice-type`, `--guest` flags are correct
- **Discrepancies:** Plan references `HydrateGenerator` class directly but doesn't mention supercell or cage occupancy controls
- **Decision:** **ABSORB into Phase 36** — the plan's task is a subset of Phase 36's CLI-01

### Quick Task 014: CLI Ion Support
- **Status:** PLANNED but NEVER EXECUTED (no SUMMARY file)
- **Plan validity:** Partially valid — `--insert-ions` and `--ion-concentration` are correct
- **Discrepancies:** Plan references `--cation` and `--anion` flags which don't match the GUI (GUI only supports NaCl, no other ion types). Plan doesn't mention source selection (`--ion-source`), which is critical post-Phase 34.1
- **Decision:** **ABSORB into Phase 36** — the plan's task is a subset of Phase 36's CLI-04, but source selection must be added

### Quick Task 015: CLI Progress Reporting
- **Status:** PLANNED but NEVER EXECUTED (no SUMMARY file)
- **Plan validity:** Still valid — stderr progress messages are the right approach
- **Discrepancies:** Plan suggests optional `tqdm` — still a good idea. Plan uses `[PROGRESS]` prefix — fine
- **Decision:** **ABSORB into Phase 36** — the plan's approach is directly reusable for CLI-05

### Summary
All three Quick Tasks are **absorbed into Phase 36** as subsets. Their plans provide useful patterns but are incomplete for v4.5 requirements (missing source selection, custom molecule, complete system export).

## Architecture Approach Evaluation

### Approach A: Linear Flags (RECOMMENDED)

**How it works:** Add flag groups to existing argparse parser. Steps execute sequentially. Source selection is implicit from flag ordering + explicit `--ion-source`/`--solute-source` flags.

**Pros:**
- Backwards compatible — existing `python quickice.py -T 300 -P 100 -N 256` still works
- Follows established parser.py pattern (argument groups)
- Simple to understand — one command does everything
- No new dependencies or architectural patterns
- Matches scientific CLI conventions (GROMACS gmx, LAMMPS)

**Cons:**
- Long command lines for full pipeline
- Flag validation logic gets complex (mutual dependencies)
- No way to "re-run just the solute step" without re-running everything

**Source selection expressiveness:** HIGH — `--ion-source` flag explicitly names which prior step to use

**Chaining support:** HIGH — pipeline executor stores intermediate results in memory

**Complexity:** LOW — extends existing pattern, no new modules beyond pipeline.py

### Approach B: Subcommands

**How it works:** `quickice generate ice`, `quickice insert-solute`, `quickice export`

**Pros:**
- Clean separation of concerns
- Each subcommand is independently testable
- Can re-run individual steps

**Cons:**
- **BREAKS backwards compatibility** — existing `python quickice.py -T 300` would break
- Major parser refactor (parser.py rewrite from scratch)
- Users need to chain commands manually or use pipes
- State must be persisted between subcommands (file serialization)
- Goes against v4.5_prompt.md guidance: "treat as quicktask or numbered phase" (implies incremental, not refactor)

**Source selection expressiveness:** MEDIUM — each subcommand takes an input file

**Chaining support:** LOW — requires file serialization between steps

**Complexity:** HIGH — full parser rewrite, serialization format design

### Approach C: Pipeline with State Files

**How it works:** Each step outputs a pickle/JSON state file, next step reads it

**Pros:**
- Most flexible — can skip steps, re-run steps, inspect intermediate state
- Enables HPC workflow managers (Snakemake, Nextflow)
- State files are persistent (can inspect/debug)

**Cons:**
- Adds serialization complexity — all structure types must be serializable
- numpy arrays don't JSON-serialize natively (need custom encoder)
- File management (temp files, cleanup, naming conventions)
- Over-engineering for current needs — single-process pipeline is sufficient
- Performance overhead (disk I/O for large position arrays)

**Source selection expressiveness:** HIGH — state files are named/explicit

**Chaining support:** HIGH — any step can read any prior state file

**Complexity:** HIGH — serialization, file management, error handling

### Decision: Approach A

Linear flags with pipeline executor is the clear winner because:
1. Backwards compatible (existing CLI works unchanged)
2. Follows established pattern (argument groups in parser.py)
3. Backend modules already support in-memory chaining (interface_structure attribute)
4. Simple implementation (extend parser + add pipeline.py)
5. No serialization needed (single-process pipeline)

## Common Pitfalls

### Pitfall 1: Source Structure Attribute Propagation
**What goes wrong:** When inserting solutes from a custom molecule source, the custom molecule attributes must be manually attached to the interface structure before passing to `insert_ions()`. The GUI does this explicitly (lines 864-871 of main_window.py).
**Why it happens:** The backend inserters use duck typing — they read `.solute_type`, `.solute_positions` etc. from the input structure. These aren't automatically set.
**How to avoid:** In the pipeline executor, after each step, explicitly copy attributes to the source structure before the next step, exactly mirroring the GUI's MainWindow code.
**Warning signs:** Ion export missing solute lines in .top file; custom molecule atoms missing from final .gro.

### Pitfall 2: Liquid Volume Calculation for Ion/Solute Count
**What goes wrong:** Using total cell volume instead of liquid water volume to calculate molecule counts, resulting in way too many solutes/ions.
**Why it happens:** The convenience functions `insert_ions()` and `insert_solutes()` both accept `liquid_volume_nm3` parameter but can fall back to total cell volume if not provided.
**How to avoid:** Always calculate liquid volume as `water_nmolecules * 0.0299` from the source structure's water molecule count, matching the GUI pattern (main_window.py line 627).
**Warning signs:** Solute/ion counts orders of magnitude too high for the liquid region.

### Pitfall 3: Missing ITP File Copying
**What goes wrong:** GROMACS export produces .gro and .top files but doesn't copy the required .itp files (tip4p-ice.itp, ch4_hydrate.itp, thf_hydrate.itp, custom.itp, ion.itp, etc.) to the output directory. The .top uses `#include "filename.itp"` which requires the file to be in the same directory.
**Why it happens:** The existing interface export (main.py line 152) copies tip4p_ice.itp but doesn't handle the full set of ITP files needed for multi-molecule systems.
**How to avoid:** After writing .gro/.top, copy ALL referenced .itp files to the output directory. Use `get_tip4p_itp_path()` pattern. For custom molecules, copy the user-provided .itp file. For liquid solutes, copy from `quickice/data/` (e.g., `ch4_liquid.itp`, `thf_liquid.itp`).
**Warning signs:** GROMACS grompp fails with "File not found" for .itp includes.

### Pitfall 4: Custom Placement Mode Without Positions
**What goes wrong:** User specifies `--custom-placement custom` but provides no position data, or provides position count that doesn't match rotation count.
**Why it happens:** The GUI has a position table editor with validation. The CLI needs a different input mechanism.
**How to avoid:** Require `--custom-positions-file` (CSV) for custom placement mode. Validate that CSV has 6 columns (x,y,z,alpha,beta,gamma) and at least 1 row. If random mode, require `--custom-count` or `--custom-concentration`.
**Warning signs:** CustomMoleculeConfig validation errors; missing position data.

### Pitfall 5: Flag Mutual Exclusivity Validation
**What goes wrong:** User provides conflicting flags (e.g., `--interface` without `--mode`, or `--solute-type` without `--interface` as prerequisite).
**Why it happens:** argparse doesn't natively handle conditional dependencies between flag groups well.
**How to avoid:** Add a `validate_pipeline_args()` function (like existing `validate_interface_args()`) that checks:
- `--solute-type` requires `--interface` (or `--hydrate + --interface`)
- `--custom-gro` requires `--interface`
- `--ion-concentration` requires `--interface`
- `--interface` requires `--mode`, `--box-x/y/z`
- `--hydrate` cannot be combined with `--nmolecules` for ice generation
**Warning signs:** Inexplicable errors from backend modules receiving None inputs.

### Pitfall 6: Ice Candidate Selection for Interface
**What goes wrong:** The GUI lets users pick from ranked candidates (dropdown). The CLI just generates 1 candidate for interface mode (main.py line 105-106). But the hydrate→interface path needs the hydrate structure, not a random ice candidate.
**Why it happens:** Two source paths: ice candidate from generation, or hydrate from hydrate generation. The GUI handles both via dropdown + "Use in Interface" button.
**How to avoid:** When `--hydrate` and `--interface` are both specified, use `hydrate.to_candidate()` as the source (mirrors GUI `_on_interface_hydrate_generate`). When only `--interface`, use ice candidate generation (existing path).
**Warning signs:** Interface uses wrong source structure; hydrate guest molecules lost.

## Code Examples

### Full Pipeline CLI Invocation
```bash
# Source: Derived from GUI workflow patterns
# Complete pipeline: Interface → Solute → Ion with export
python quickice.py \
  -T 270 -P 0.1 \
  --interface --mode slab \
  --box-x 3.0 --box-y 3.0 --box-z 5.0 \
  --ice-thickness 1.5 --water-thickness 2.0 \
  --seed 42 \
  --solute-type CH4 --solute-concentration 0.5 \
  --ion-concentration 0.15 --ion-source solute \
  --gromacs -o output_dir
```

### Custom Molecule Pipeline
```bash
# Interface → Custom Molecule → Solute → Ion
python quickice.py \
  -T 250 -P 0.1 \
  --interface --mode pocket \
  --box-x 4.0 --box-y 4.0 --box-z 4.0 \
  --pocket-diameter 2.0 \
  --custom-gro my_molecule.gro --custom-itp my_molecule.itp \
  --custom-count 5 \
  --solute-type THF --solute-concentration 0.3 --solute-source custom \
  --ion-concentration 0.5 --ion-source solute \
  --gromacs -o output_dir
```

### Hydrate + Interface Pipeline
```bash
# Hydrate → Interface → Ion
python quickice.py \
  -T 270 -P 10.0 \
  --hydrate --lattice-type sI --guest THF \
  --interface --mode piece \
  --box-x 3.0 --box-y 3.0 --box-z 5.0 \
  --ion-concentration 0.6 --ion-source interface \
  --gromacs -o output_dir
```

### Source Selection Logic (mirrors GUI MainWindow._on_insert_ions)
```python
# Source: Derived from quickice/gui/main_window.py lines 820-929
def _run_ion_step(self):
    """Insert ions using selected source structure."""
    from quickice.structure_generation.ion_inserter import insert_ions
    
    source_name = self.args.ion_source
    source = self._get_source_structure(source_name)
    
    if source is None:
        print(f"Error: No {source_name} structure available for ion insertion", file=sys.stderr)
        return
    
    # For solute source: attach solute attributes to interface (mirrors GUI)
    if source_name == "solute":
        interface = source.interface_structure
        interface.solute_type = source.solute_type
        interface.solute_positions = source.positions
        interface.solute_atom_names = source.atom_names
        interface.solute_n_molecules = source.n_molecules
        interface.solute_molecule_indices = source.molecule_indices
        interface.solute_registry = source.registry
        source_for_ions = interface
    elif source_name == "custom":
        interface = source.interface_structure
        # Attach custom molecule attributes (mirrors GUI)
        interface.custom_molecule_positions = source.positions[interface.ice_atom_count + interface.water_atom_count:]
        interface.custom_molecule_atom_names = source.atom_names[interface.ice_atom_count + interface.water_atom_count:]
        interface.custom_molecule_count = source.custom_molecule_count
        interface.custom_molecule_moleculetype = source.moleculetype_name
        interface.custom_gro_path = source.gro_path
        interface.custom_itp_path = source.itp_path
        source_for_ions = interface
    else:
        source_for_ions = source
    
    # Calculate liquid volume
    liquid_volume = source_for_ions.water_nmolecules * 0.0299
    
    # Insert ions
    ion_structure = insert_ions(
        source_for_ions,
        self.args.ion_concentration,
        liquid_volume
    )
    
    self._ion_result = ion_structure
    report_progress(f"Ion insertion: {ion_structure.na_count} Na+, {ion_structure.cl_count} Cl-")
```

### Solute Insertion with Source Selection (mirrors GUI MainWindow._on_insert_solutes)
```python
# Source: Derived from quickice/gui/main_window.py lines 982-1088
def _run_solute_step(self):
    """Insert solutes using selected source structure."""
    from quickice.structure_generation.solute_inserter import SoluteInserter
    from quickice.structure_generation.types import SoluteConfig
    
    source_name = self.args.solute_source
    source = self._get_source_structure(source_name)
    
    if source is None:
        print(f"Error: No {source_name} structure available for solute insertion", file=sys.stderr)
        return
    
    config = SoluteConfig(
        concentration_molar=self.args.solute_concentration,
        solute_type=self.args.solute_type
    )
    
    inserter = SoluteInserter(config)
    solute_structure = inserter.insert_solutes(source, config)
    
    self._solute_result = solute_structure
    report_progress(f"Solute insertion: {solute_structure.n_molecules} {config.solute_type} molecules")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Ice-only CLI | Ice + Interface CLI | v3.5 | CLI supports 2 modes |
| No source selection | Source dropdowns (Ion, Solute) | v4.5 Phase 34.1/34.4 | CLI needs `--ion-source`, `--solute-source` |
| Ice candidate only for interface | Hydrate→candidate path | v4.0 | CLI needs `--hydrate + --interface` support |
| Tab-per-tab export | Complete system export | v4.5 Phase 34.6 | CLI auto-exports most complete structure |
| Hydrate ITP for solutes | Separate liquid solute ITP (CH4_L, THF_L) | v4.5 Phase 34.2 | CLI must use liquid ITP, not hydrate ITP |

**Deprecated/outdated:**
- Quick Task 013's `--cation`/`--anion` flags: GUI only supports NaCl, no ion type selection needed
- CLI-01 through CLI-05 from REQUIREMENTS.md: Superseded by updated requirements above (missing source selection, custom molecule, complete system export)

## Open Questions

1. **Custom placement CSV format**
   - What we know: GUI uses a table with (X, Y, Z, α, β, γ) per row
   - What's unclear: Should CLI use CSV file or command-line JSON? CSV is simpler and more scientific-tool-friendly
   - Recommendation: Use CSV file with `--custom-positions-file` flag. Header row optional. 6 columns: x,y,z,alpha,beta,gamma

2. **Overwrite behavior**
   - What we know: GUI has a dialog; current CLI has `check_output_file()` with stdin prompt
   - What's unclear: CLI with stdin prompts breaks scripting/piping. Should we default to overwrite?
   - Recommendation: Default to overwrite. Add `--no-overwrite` flag that errors if files exist.

3. **Multiple custom molecule types**
   - What we know: GUI only supports one custom molecule at a time (single .gro/.itp pair)
   - What's unclear: CLI users may want to insert two different custom molecules
   - Recommendation: Defer to future phase. Single `--custom-gro`/`--custom-itp` pair matches GUI.

## Sources

### Primary (HIGH confidence)
- `quickice/cli/parser.py` — Current CLI argument structure (252 lines, fully read)
- `quickice/main.py` — Current CLI workflow (288 lines, fully read)
- `quickice/structure_generation/types.py` — All data structures (722 lines, fully read)
- `quickice/structure_generation/solute_inserter.py` — SoluteInserter API (891 lines, fully read)
- `quickice/structure_generation/custom_molecule_inserter.py` — CustomMoleculeInserter API (949 lines, fully read)
- `quickice/structure_generation/ion_inserter.py` — IonInserter API (585 lines, fully read)
- `quickice/output/gromacs_writer.py` — All export functions (2508+ lines, fully read)
- `quickice/gui/main_window.py` — GUI workflow patterns (1125+ lines, fully read)
- `quickice/gui/ion_panel.py` — Ion source selection (549 lines, fully read)
- `quickice/gui/solute_panel.py` — Solute source selection (471 lines, fully read)
- `quickice/gui/custom_molecule_panel.py` — Custom molecule UI (1228+ lines, fully read)
- `quickice/gui/constants.py` — Tab structure (28 lines, fully read)

### Secondary (MEDIUM confidence)
- `.planning/quick/013-add-cli-hydrate-support/013-PLAN.md` — Valid but incomplete (117 lines)
- `.planning/quick/014-add-cli-ion-support/014-PLAN.md` — Partially valid (119 lines)
- `.planning/quick/015-add-cli-progress-reporting/015-PLAN.md` — Valid (117 lines)
- `.planning/REQUIREMENTS.md` — CLI-01 to CLI-05 (superseded)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — argparse is established, no new deps needed
- Architecture: HIGH — derived from direct analysis of existing code and GUI patterns
- Pitfalls: HIGH — identified from reading actual GUI code that handles these cases
- API signatures: HIGH — read all inserter and exporter source code directly
- Updated requirements: HIGH — derived from ROADMAP + phases 34.1-34.8 + GUI analysis

**Research date:** 2026-06-14
**Valid until:** 2026-07-14 (stable — based on internal codebase analysis, not external library versions)
