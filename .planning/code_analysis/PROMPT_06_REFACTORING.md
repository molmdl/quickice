# Prompt 6: Code Refactoring

**Workflow:** `/gsd-plan-phase`
**Priority:** LOW (Future)
**Estimated time:** 8-16 hours

---

## Instructions

Start a new session, then run:
```
/gsd-plan-phase
```

Paste this prompt when asked:

---

## Prompt

Phase: Code Refactoring

### Goals

Reduce large file complexity, remove deprecated patterns, and add missing CLI features.

---

### Task 1: Refactor gromacs_writer.py

**Current state:** 1559 lines - difficult to navigate and maintain
**Target:** Split into smaller, focused modules

**Proposed structure:**
```
quickice/output/
├── gromacs_writer.py      # Main orchestrator (200 lines)
├── gro_writer.py          # GRO file writing (300 lines)
├── top_writer.py          # TOP file writing (300 lines)
├── ion_writer.py          # Ion-specific exports (200 lines)
├── hydrate_writer.py      # Hydrate-specific exports (200 lines)
├── molecule_utils.py      # Molecule counting, wrapping (200 lines)
└── itp_generator.py       # ITP file generation (150 lines)
```

**Approach:**
1. Identify distinct responsibilities in current file
2. Extract each to dedicated module
3. Update imports in gromacs_writer.py
4. Ensure backward compatibility (public API unchanged)
5. Add tests for each module

---

### Task 2: Refactor main_window.py

**Current state:** 1317 lines - complex GUI state management
**Target:** Split into smaller components

**Proposed structure:**
```
quickice/gui/
├── main_window.py         # Main window orchestration (300 lines)
├── result_manager.py      # Result storage and retrieval (200 lines)
├── export_handler.py      # Export routing logic (200 lines)
├── tab_controller.py      # Tab switching logic (150 lines)
└── worker_manager.py      # Background worker management (150 lines)
```

**Approach:**
1. Separate result storage into ResultManager class
2. Extract export routing to ExportHandler
3. Move tab logic to TabController
4. Keep main_window.py as coordinator
5. Test GUI thoroughly after refactoring

---

### Task 3: Refactor phase_diagram.py

**Current state:** 1132 lines - many polygon building functions
**Target:** Modularize phase polygon builders

**Proposed structure:**
```
quickice/output/
├── phase_diagram.py       # Main diagram renderer (200 lines)
├── phase_polygons/
│   ├── __init__.py
│   ├── base.py            # Base polygon class (100 lines)
│   ├── ice_polymorphs.py  # Ice phase polygons (300 lines)
│   ├── liquid.py          # Liquid water polygon (150 lines)
│   └── boundaries.py      # Boundary curves (200 lines)
```

**Approach:**
1. Create base class for phase polygons
2. Extract each phase polygon builder to dedicated class
3. Use registry pattern for phase polygon lookup
4. Maintain same output format

---

### Task 4: Remove Deprecated atoms_per_molecule Heuristic

**Current state:** Heuristic inference emits DeprecationWarning
**File:** `quickice/structure_generation/water_filler.py:335-359`

**Approach:**
1. Make `atoms_per_molecule` parameter required (no default)
2. Update all callers to pass explicit value
3. Remove heuristic code
4. Update documentation

**Breaking change:** This will require updating any code that relied on heuristic

---

### Task 5: Add CLI Support for Hydrate Generation

**Current state:** Hydrate generation only available in GUI
**Target:** Full CLI support with all options

**Files to update:**
- `quickice/cli/parser.py` - Add hydrate arguments
- `quickice/main.py` - Add hydrate workflow

**CLI arguments to add:**
```python
hydrate_group = parser.add_argument_group('Hydrate Generation')
hydrate_group.add_argument('--hydrate', action='store_true',
                           help='Generate clathrate hydrate structure')
hydrate_group.add_argument('--lattice-type', choices=['sI', 'sII', 'sH'],
                           default='sI', help='Hydrate lattice type')
hydrate_group.add_argument('--guest', choices=['ch4', 'thf', 'co2', 'h2'],
                           default='ch4', help='Guest molecule type')
hydrate_group.add_argument('--guest-concentration', type=float,
                           default=1.0, help='Guest cage occupancy (0-1)')
hydrate_group.add_argument('--hydrate-molecules', type=int,
                           default=1000, help='Number of water molecules')
```

**Implementation:**
1. Add argument parsing in parser.py
2. Add hydrate generation branch in main.py
3. Handle hydrate-specific export
4. Add tests for CLI hydrate generation

---

### Task 6: Add CLI Support for Ion Insertion

**Current state:** Ion insertion only available in GUI
**Target:** Full CLI support with all options

**Files to update:**
- `quickice/cli/parser.py` - Add ion arguments
- `quickice/main.py` - Add ion insertion workflow

**CLI arguments to add:**
```python
ion_group = parser.add_argument_group('Ion Insertion')
ion_group.add_argument('--insert-ions', action='store_true',
                       help='Insert Na+/Cl- ions into structure')
ion_group.add_argument('--ion-concentration', type=float,
                       default=0.15, help='Ion concentration (mol/L)')
ion_group.add_argument('--ion-seed', type=int,
                       help='Random seed for ion placement')
```

**Implementation:**
1. Add argument parsing in parser.py
2. Add ion insertion branch in main.py
3. Handle ion-specific export (additional .itp files)
4. Add tests for CLI ion insertion

---

### Task 7: Add Progress Reporting for CLI

**Current state:** No progress indication during long CLI operations
**Target:** Progress bars and status messages

**Implementation:**
```python
# In quickice/main.py
from tqdm import tqdm

def generate_with_progress(config, phase_info):
    print(f"Generating {phase_info['name']} structure...")
    print(f"  Temperature: {config.temperature} K")
    print(f"  Pressure: {config.pressure} MPa")
    print(f"  Molecules: {config.nmolecules}")
    
    # For large molecule counts, show progress
    if config.nmolecules > 10000:
        with tqdm(total=100, desc="Generating") as pbar:
            # Hook into generation progress
            result = generator.generate(config, 
                progress_callback=lambda p: pbar.update(int(p * 100)))
    else:
        result = generator.generate(config)
    
    print(f"Generated {result.n_atoms} atoms")
    return result
```

---

## Testing Requirements

### For each refactoring task:

1. **Unit tests:** Ensure all extracted modules have tests
2. **Integration tests:** Verify end-to-end workflows still work
3. **GUI tests:** Manually test all GUI features
4. **CLI tests:** Test all CLI modes and options

### Specific test coverage needed:

- [ ] gromacs_writer module tests (each export type)
- [ ] GUI result manager tests
- [ ] GUI export handler tests
- [ ] Phase polygon builder tests
- [ ] CLI hydrate generation tests
- [ ] CLI ion insertion tests
- [ ] Progress reporting tests

---

## References

- `.planning/codebase/CONCERNS.md` - Large file complexity, missing CLI features
- `.planning/codebase/ARCHITECTURE.md` - Current structure
- `.planning/codebase/TESTING.md` - Test patterns

---

## Success Criteria

- [ ] No files exceed 500 lines
- [ ] All modules have single responsibility
- [ ] Deprecated heuristic removed
- [ ] CLI supports hydrate generation
- [ ] CLI supports ion insertion
- [ ] CLI shows progress for long operations
- [ ] All existing tests pass
- [ ] New tests for refactored modules
- [ ] GUI functionality unchanged
- [ ] CLI functionality extended
