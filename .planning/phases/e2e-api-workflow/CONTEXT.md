# E2E API Workflow Test Context for Gap-Filling Planner

## Purpose

This document provides all context needed for a gap-filling planner to create e2e API-level tests for QuickIce v4.5 UAT workflows 2-9. These tests exercise the **actual computation pipeline** (not the GUI), catching logic bugs before human UAT.

## What Already Exists

### Existing Test Infrastructure
- **`tests/test_integration_v35.py`**: CLI-based integration tests (interface generation for all 3 modes, GRO file validation). 11 tests. PASSES.
- **`tests/test_output/`**: 7 files + conftest.py testing GROMACS **export** via mocked QFileDialog. 37 tests. PASSES. These test the GUI export layer with mock dialogs.
- **`tests/test_cli_integration.py`**: CLI argument validation tests. PASSES.
- **30+ unit tests** in `tests/`: Covering individual components (atom ordering, density, filtering, etc.)

### Existing Test Fixtures (`tests/test_output/conftest.py`)
Provides **synthetic** structure fixtures:
- `simple_candidate`: 1-molecule ice Candidate
- `simple_hydrate_structure`: 2 water + 1 CH4
- `simple_interface`: 2 ice + 2 water molecules (VERY small, synthetic)
- `interface_with_ch4_guests`: extends simple_interface with 1 CH4
- `custom_structure`: simple_interface + 1 ethanol (9 atoms)
- `solute_structure`: 1 CH4 solute molecule
- `ion_structure`: 2 water + 1 NA + 1 CL

**Problem**: These fixtures are too small to test real insertion logic (overlap checking, concentration-based counts, water removal). They're fine for export tests but insufficient for pipeline correctness.

## What's Missing (The Gap)

API-level e2e tests that:
1. **Generate real structures** using GenIce (not synthetic fixtures)
2. **Build real interfaces** with actual ice candidates
3. **Insert custom molecules** with real overlap checking and water removal
4. **Insert solutes** from various sources with concentration-based counts
5. **Insert ions** from various sources with charge neutrality
6. **Validate the entire chain**: ice→interface→custom→solute→ion
7. **Verify structural invariants** at each step (atom counts, overlap-free, correct ordering)

These correspond to UAT Workflows 2-9 (~50 API-testable items). The remaining ~13 GUI-only items (tab switching, dropdown rendering, keyboard shortcuts) still need manual testing.

---

## Combination Matrix

### Source Types for Interface

| Source | Phase | Orthogonal? | Interface Modes | Notes |
|--------|-------|-------------|-----------------|-------|
| Ice Ih | ice_ih | Yes | slab, pocket, piece | Most common, baseline |
| Ice Ic | ice_ic | Yes | slab, pocket, piece | Cubic, smaller unit cell |
| Ice III | ice_iii | Yes | slab, pocket, piece | Tetragonal, high pressure |
| Ice VI | ice_vi | Yes | slab, pocket, piece | Tetragonal, double network |
| Ice VII | ice_vii | Yes | slab, pocket, piece | Cubic, double network |
| Ice VIII | ice_viii | Yes | slab, pocket, piece | Ordered Ice VII |
| ~~Ice II~~ | ~~ice_ii~~ | No | **NONE** | Rhombohedral - rejected by interface_builder |
| ~~Ice V~~ | ~~ice_v~~ | No | **NONE** | Triclinic - rejected or fails in slab/pocket |
| Hydrate sI + CH4 | hydrate_sI | Yes | slab, pocket | Has 8 CH4 guests, 46 water |
| Hydrate sI + THF | hydrate_sI | Yes | slab, pocket | Has 8 THF guests, 46 water |
| Hydrate sII + CH4 | hydrate_sII | Yes | slab, pocket | Has 24 CH4 guests, 136 water |
| Hydrate sII + THF | hydrate_sII | Yes | slab, pocket | Has 24 THF guests, 136 water |
| Hydrate sH + CH4 | hydrate_sH | Yes | (not tested) | Small unit cell |
| Hydrate sH + THF | hydrate_sH | Yes | (not tested) | Small unit cell |

### Post-Interface Insertion Combinations

The key dimension is: **what molecules are already present** when you do the next insertion step.

#### Custom Molecule Insertion (from Interface)

| # | Source Interface | Custom Molecule | Unique Issue |
|---|-----------------|-----------------|-------------|
| C1 | Ice Ih interface (no guests) | etoh random | Baseline: simple overlap + water removal |
| C2 | Ice Ih interface (no guests) | etoh custom position | Custom placement: bounds + overlap validation |
| C3 | Hydrate sI+CH4 interface | etoh random | Guest molecules present; custom after guests in ordering |
| C4 | Hydrate sI+THF interface | etoh random | THF guests (13 atoms each); more complex structure |

#### Solute Insertion (from Interface or Custom)

| # | Source | Solute Type | Unique Issue |
|---|--------|------------|-------------|
| S1 | Ice Ih interface | CH4 | Baseline solute insertion |
| S2 | Ice Ih interface | THF | THF has 13 atoms; larger template |
| S3 | Hydrate sI+CH4 interface | CH4 liquid | **CRITICAL**: CH4_H hydrate guests + CH4_L liquid solutes coexist; MoleculetypeRegistry must distinguish |
| S4 | Hydrate sI+THF interface | THF liquid | THF_H hydrate guests + THF_L liquid solutes coexist |
| S5 | Hydrate sI+CH4 interface | THF liquid | Different molecule types in guests vs liquid |
| S6 | Custom (from C1) | CH4 | Custom molecules + solutes; attribute propagation |
| S7 | Custom (from C3) | THF | Custom + guests + solutes; all three molecule types |

#### Ion Insertion (from Interface, Custom, or Solute)

| # | Source | Unique Issue |
|---|--------|-------------|
| I1 | Ice Ih interface | Baseline ion insertion |
| I2 | Hydrate sI+CH4 interface | Ions with hydrate guests present |
| I3 | Custom (from C1) | Custom molecule attributes must propagate through ion |
| I4 | Custom (from C3) | Guests + custom + ions; all types present |
| I5 | Solute (from S1) | **BUG**: SoluteStructure.molecule_index missing → AttributeError. GUI works around by passing solute_structure.interface_structure instead. API test should expose this. |
| I6 | Solute (from S3) | Guests + solutes + ions; plus the bug above |
| I7 | Solute (from S6) | Custom + solutes + ions; attribute propagation chain |

#### Full Chain Combinations

| # | Chain | Unique Issue |
|---|-------|-------------|
| F1 | Ice Ih→Interface(slab)→Custom(random)→Solute(CH4,Custom source)→Ion(Solute source) | Full chain with all 4 insertion steps |
| F2 | Ice Ih→Interface(slab)→Custom(random)→Ion(Custom source) | Short chain skipping solute |
| F3 | Hydrate sI+CH4→Interface(slab)→Solute(CH4,Interface source)→Ion(Solute source) | Hydrate chain with CH4_H+CH4_L coexistence + SoluteStructure bug |
| F4 | Hydrate sI+THF→Interface(slab)→Custom(random)→Solute(THF,Custom source)→Ion(Solute source) | All molecule types: guests+custom+solute+ions |
| F5 | Ice Ih→Interface(pocket)→Custom(random)→Solute(CH4) | Pocket mode chain (different interface structure) |
| F6 | Ice Ih→Interface(slab)→Solute(CH4,Interface source) | No custom → simpler chain |
| F7 | Ice Ih→Interface(slab)→Solute(THF,Interface source)→Ion(Solute source) | THF solute chain |

### Recommended Test Subset (Balanced Coverage)

Not all 7×5×7 = 245 combinations need testing. The following covers all distinct code paths:

| Priority | Combination | Why |
|----------|-------------|-----|
| **P0** | F1 (Ice Ih→slab→custom→solute→ion) | Full chain baseline |
| **P0** | S3 (Hydrate sI+CH4 → CH4 liquid) | CH4_H/CH4_L naming conflict |
| **P0** | I5 (SoluteStructure → IonInserter) | Known bug: AttributeError |
| **P1** | C2 (Custom placement validation) | Bounds + overlap checking |
| **P1** | S2 (Ice interface + THF solute) | 13-atom template |
| **P1** | F3 (Hydrate+CH4→solute→ion) | Guest+solute+ion chain |
| **P1** | I3 (Custom→Ion) | Custom attribute propagation |
| **P2** | S4 (Hydrate+THF → THF liquid) | THF_H/THF_L naming |
| **P2** | S7 (Custom+guests → THF solute) | Three molecule types |
| **P2** | F5 (Pocket→custom→solute) | Pocket mode variant |
| **P2** | F2 (Custom→Ion short chain) | Skip-solute variant |
| **P2** | Ice Ic + piece mode | Piece mode variant |

---

## Known Bugs Found During Research

### BUG 1: SoluteStructure → IonInserter AttributeError (CRITICAL)

**Location**: `quickice/structure_generation/ion_inserter.py:192`
**Trigger**: `IonInserter.replace_water_with_ions(solute_structure, ion_pairs)`
**Error**: `AttributeError: 'SoluteStructure' object has no attribute 'molecule_index'`
**Root cause**: `SoluteStructure` has `molecule_indices` (list of tuples) but NOT `molecule_index` (list of MoleculeIndex). `IonInserter.replace_water_with_ions` checks `structure.molecule_index` first.
**GUI workaround**: `main_window.py:854` passes `solute_structure.interface_structure` (an InterfaceStructure) to ion_inserter, attaching solute info as ad-hoc attributes. This means the **API-level** function `replace_water_with_ions` cannot accept SoluteStructure directly.
**Fix needed**: Either add `molecule_index` to SoluteStructure, or make IonInserter handle SoluteStructure by using `interface_structure.molecule_index`.

### BUG 2: Ice V + slab mode fails

**Location**: `quickice/structure_generation/interface_builder.py` → slab mode
**Trigger**: Ice V (triclinic) candidate + slab InterfaceConfig
**Error**: "Some input data are greater than the size of the periodic box"
**Root cause**: Ice V has triclinic cell with off-diagonal elements. The transformed orthogonal cell is larger than the user-specified box.
**Note**: Non-orthogonal phases (Ice II, V) should be documented as unsupported for interface. Ice V passes validation but fails at generation.

---

## UAT Item Mapping

### Workflow 2: Ice Generation (1 item)
| UAT # | Test | API Function |
|-------|------|-------------|
| 1 | Generate ice structure successfully | `IceStructureGenerator(phase_info, 96).generate_all(1)` |

### Workflow 3: Hydrate Generation (4 items)
| UAT # | Test | API Function |
|-------|------|-------------|
| 1 | Generate hydrate with CH4 guest | `HydrateStructureGenerator().generate(HydrateConfig(lattice_type='sI', guest_type='ch4'))` |
| 2 | Generate hydrate with THF guest | `HydrateStructureGenerator().generate(HydrateConfig(lattice_type='sI', guest_type='thf'))` |
| 3 | Export verify CH4_H/THF_H moleculetype | `structure.to_candidate().metadata['guest_type_counts']` |
| 4 | Export verify .top includes ch4.itp (no _liquid suffix) | Covered by e2e-export-test phase |

### Workflow 4: Interface Generation (3 items)
| UAT # | Test | API Function |
|-------|------|-------------|
| 1 | Ice → Interface flow | `generate_interface(candidate, InterfaceConfig(mode='slab',...))` |
| 2 | Hydrate → Interface flow | `generate_interface(hydrate_candidate, InterfaceConfig(mode='slab',...))` |
| 3 | Interface available for Ion tab | Verify `interface.water_nmolecules > 0` |

Additional interface mode combinations to test:
| Test | API | Combination |
|------|-----|------------|
| Ice Ih + slab | C1 baseline | P0 |
| Ice Ih + pocket | Pocket mode | P2 |
| Ice Ih + piece | Piece mode | P2 |
| Hydrate sI+CH4 + slab | Guest molecules present | P0 |
| Ice II rejection | `InterfaceGenerationError` | P1 |

### Workflow 5: Custom Molecule Upload & Insertion (24 items)

#### 5a. File Upload & Validation (7 items)
| UAT # | Test | API Function |
|-------|------|-------------|
| 1 | Upload valid GRO file | `parse_gro_file(Path('quickice/data/custom/etoh.gro'))` |
| 2 | Upload valid ITP file | `parse_itp_file(Path('quickice/data/custom/etoh.itp'))` → `is_valid` |
| 3 | Atom count mismatch | `validate_custom_molecule(gro_path, itp_info)` → error in `result.errors` |
| 4 | Residue name mismatch (GRO='MOL', ITP='etoh') | `validate_custom_molecule()` → `residue_name_mismatch` check (MOL is generic so mismatch=False) |
| 5 | Upload non-GRO file | `parse_gro_file(Path('non_gro.txt'))` → raises exception |
| 6 | ITP without [atomtypes] | `parse_itp_file()` → `has_atomtypes_section=False`; warning in validation |
| 7 | Real molecule etoh.gro/itp no residue name warning | `validate_custom_molecule()` with etoh files → `is_valid=True` |

#### 5b. Random Placement Mode (4 items)
| UAT # | Test | API Function |
|-------|------|-------------|
| 1 | Random mode molecule count input | `CustomMoleculeConfig(placement_mode='random', molecule_count=10)` |
| 2 | Concentration 1.0M → volume + count preview | `CustomMoleculeInserter.calculate_molecule_count(1.0, liquid_volume_nm3)` |
| 3 | Generate → molecules in liquid region | `inserter.place_random(interface, 5)` → positions within liquid bounds |
| 4 | No visible overlap | Verify all-atom min distance > min_separation for placed molecules |

#### 5c. Custom Placement Mode (10 items, 6 testable)
| UAT # | Test | API Function |
|-------|------|-------------|
| 1 | Custom mode inputs | `CustomMoleculeConfig(placement_mode='custom', positions=[...], rotations=[...])` |
| 2 | Liquid region bounds | `interface.positions[ice_start:ice_start+water_count].min/max` |
| 3 | Validate & Preview | `inserter.validate_single_placement(interface, position, rotation)` |
| 5 | Out-of-bounds position → error | `validate_single_placement()` → `within_bounds=False` |
| 6 | Overlapping position → overlap detected | `validate_single_placement()` → `has_overlap=True` |
| 10 | Validate without interface → error | `validate_single_placement()` with no liquid region → `is_valid=False` |

#### 5d-e. Visualization + Export — GUI-only or covered by e2e-export-test

### Workflow 6: Solute Insertion (15 items, 9 API-testable)

#### 6a. UI Controls (1 testable)
| UAT # | Test | API Function |
|-------|------|-------------|
| 5 | Concentration updates molecule count | `SoluteInserter.calculate_molecule_count(conc, vol)` |

#### 6b. Insertion from Interface Source (3 testable)
| UAT # | Test | API Function |
|-------|------|-------------|
| 1 | Generate solutes from Interface | `SoluteInserter(config).insert_solutes(interface)` |
| 2 | Solutes in liquid phase only | Verify all solute positions within liquid region bounds |
| 4 | No overlap between solutes | Verify pairwise distances > min_separation |

#### 6c. Insertion from Custom Molecule Source (3 testable)
| UAT # | Test | API Function |
|-------|------|-------------|
| 1 | Switch source to Custom Molecule | Pass CustomMoleculeStructure to insert_solutes |
| 3 | Insert solutes uses custom molecule structure | `SoluteInserter.insert_solutes(custom_structure)` |
| 4 | Custom molecule info preserved | Check `solute_result.custom_molecule_count > 0` |

#### 6d. GROMACS Export — covered by e2e-export-test phase

**Additional solute combinations** (not in original UAT but needed):
| Test | Combination | Priority |
|------|-------------|----------|
| Hydrate sI+CH4 interface + CH4 liquid | S3: CH4_H/CH4_L coexistence | P0 |
| Hydrate sI+THF interface + THF liquid | S4: THF_H/THF_L coexistence | P2 |
| Hydrate sI+CH4 interface + THF liquid | S5: Mixed guest+solute | P2 |

### Workflow 7: Ion Insertion (8 items, 3 API-testable)

#### 7a. UI Controls — all GUI-only

#### 7b. Source Behaviors (3 testable)
| UAT # | Test | API Function |
|-------|------|-------------|
| 1 | Interface source | `IonInserter.replace_water_with_ions(interface, ion_pairs)` |
| 2 | Custom Molecule source | Pass CustomMoleculeStructure → `replace_water_with_ions()` |
| 3 | Solute source | **BUG**: Pass SoluteStructure directly → AttributeError (I5) |

### Workflow 8: Complete Workflow Chains (9 items)

#### 8a. Full Chain: Interface → Custom → Solute → Ion (5 items)
| UAT # | Test | API Pipeline |
|-------|------|-------------|
| 1 | Generate interface | `generate_interface(candidate, config)` |
| 2 | Place custom molecules | `CustomMoleculeInserter(config).place_random(interface, 3)` |
| 3 | Select Custom source + insert solutes | `SoluteInserter(config).insert_solutes(custom_structure)` |
| 4 | Select Solute source + insert ions | **BUG**: Need to pass interface_structure with solute attrs, not SoluteStructure directly |
| 5 | Export → all components present | Verify ion_structure has all molecule types |

#### 8b. Short Chain: Interface → Custom → Ion (4 items)
| UAT # | Test | API Pipeline |
|-------|------|-------------|
| 1 | Generate interface | `generate_interface()` |
| 2 | Place custom molecules | `place_random()` |
| 3 | Custom Molecule source + ions | `IonInserter.replace_water_with_ions(custom_structure, ion_pairs)` |
| 4 | Export complete system | Verify structure has ice+water+custom+ions |

---

## Core API Reference

### Ice Generation
```python
from quickice.phase_mapping.lookup import lookup_phase
from quickice.structure_generation.generator import IceStructureGenerator

phase_info = lookup_phase(250, 0.1)
gen = IceStructureGenerator(phase_info, 96)
candidates = gen.generate_all(1)
candidate = candidates[0]  # .positions, .atom_names, .cell, .nmolecules, .phase_id
```

### Hydrate Generation
```python
from quickice.structure_generation.hydrate_generator import HydrateStructureGenerator
from quickice.structure_generation.types import HydrateConfig

gen = HydrateStructureGenerator()
config = HydrateConfig(lattice_type='sI', guest_type='ch4', supercell_x=1, supercell_y=1, supercell_z=1)
structure = gen.generate(config)  # HydrateStructure
candidate = structure.to_candidate()  # For interface generation
```

### Interface Generation
```python
from quickice.structure_generation.interface_builder import generate_interface
from quickice.structure_generation.types import InterfaceConfig

config = InterfaceConfig(mode='slab', box_x=3.0, box_y=3.0, box_z=8.0, seed=42,
                         ice_thickness=2.0, water_thickness=4.0)
interface = generate_interface(candidate, config)
# interface.ice_atom_count, interface.water_atom_count, interface.guest_atom_count
# interface.ice_nmolecules, interface.water_nmolecules, interface.guest_nmolecules
# interface.molecule_index: list[MoleculeIndex]
```

### Custom Molecule Insertion
```python
from quickice.structure_generation.custom_molecule_inserter import CustomMoleculeInserter
from quickice.structure_generation.types import CustomMoleculeConfig
from quickice.structure_generation.molecule_validator import validate_custom_molecule
from quickice.structure_generation.itp_parser import parse_itp_file

# Validation
itp_info = parse_itp_file(Path('quickice/data/custom/etoh.itp'))
result = validate_custom_molecule(Path('quickice/data/custom/etoh.gro'), itp_info)

# Random placement
config = CustomMoleculeConfig(placement_mode='random', gro_path=gro_path, itp_path=itp_path, molecule_count=5)
inserter = CustomMoleculeInserter(config)
custom_structure = inserter.place_random(interface, 5)

# Single placement validation
validation = inserter.validate_single_placement(interface, position=(x,y,z), rotation=(a,b,g))
# .is_valid, .within_bounds, .has_overlap, .min_distance

# Custom placement
custom_structure = inserter.place_custom(interface, positions=[(x,y,z)], rotations=[(a,b,g)])
```

### Solute Insertion
```python
from quickice.structure_generation.solute_inserter import SoluteInserter
from quickice.structure_generation.types import SoluteConfig

config = SoluteConfig(concentration_molar=1.0, solute_type='CH4')
inserter = SoluteInserter(config=config, seed=42)
solute_structure = inserter.insert_solutes(interface, config)
# solute_structure.n_molecules, solute_structure.solute_type
# solute_structure.interface_structure: modified InterfaceStructure
# solute_structure.molecule_indices: list of (start, end) tuples
# NOTE: solute_structure has molecule_indices NOT molecule_index

# From Custom source
solute_from_custom = inserter.insert_solutes(custom_structure, config)
# Preserves custom molecule attributes via custom_molecule_count, etc.
```

### Ion Insertion
```python
from quickice.structure_generation.ion_inserter import IonInserter
from quickice.structure_generation.types import IonConfig

config = IonConfig(concentration_molar=0.15)
inserter = IonInserter(config=config, seed=42)
liquid_volume = interface.water_nmolecules * 0.0299
ion_pairs = inserter.calculate_ion_pairs(0.15, liquid_volume)

# From Interface (works)
ion_result = inserter.replace_water_with_ions(interface, ion_pairs)

# From CustomMoleculeStructure (works - has molecule_index)
ion_from_custom = inserter.replace_water_with_ions(custom_structure, ion_pairs)

# From SoluteStructure (BROKEN - has molecule_indices not molecule_index)
# ion_from_solute = inserter.replace_water_with_ions(solute_structure, ion_pairs)
# WORKAROUND: pass solute_structure.interface_structure with solute attrs attached
interface_for_ions = solute_structure.interface_structure
interface_for_ions.solute_type = solute_structure.solute_type
interface_for_ions.solute_positions = solute_structure.positions
# ... etc
ion_result = inserter.replace_water_with_ions(interface_for_ions, ion_pairs)
```

### Moleculetype Registry
```python
from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry
registry = MoleculetypeRegistry()
registry.register_hydrate_guest('CH4')   # → 'CH4_H'
registry.register_liquid_solute('CH4')  # → 'CH4_L'
registry.register_custom_molecule()     # → 'MOL' (first), 'MOL_1' (collision)
```

---

## Structural Invariants to Verify

### At Each Pipeline Step
1. `positions.shape == (N, 3)` with N > 0
2. `cell.shape == (3, 3)` with positive diagonal
3. `np.all(np.isfinite(positions))` — no NaN/Inf
4. Atom counts sum: `ice + water + guests + custom + solutes == total`
5. Molecule counts consistent: `atom_count / atoms_per_mol == n_molecules`

### After Custom Molecule Insertion
6. Custom molecules center-of-mass within liquid region bounds
7. No custom-ice overlap (all atoms > min_separation from ice)
8. Water removal: `custom.water_atom_count < interface.water_atom_count`
9. Total atoms: `len(custom.positions) == ice + reduced_water + guests + custom_atoms`

### After Solute Insertion
10. Solutes center-of-mass within liquid bounds
11. No solute-solute overlap (pairwise > min_separation)
12. Molecule count: `n_molecules ≈ concentration * volume * NA` (within rounding)
13. Water removal in interface_structure
14. Custom molecule attrs propagated when source was CustomMoleculeStructure
15. MoleculetypeRegistry has `liquid_{solute}` entry

### After Ion Insertion
16. Charge neutrality: `na_count == cl_count`
17. Ion count: `ion_pairs ≈ concentration * volume * NA` (within rounding)
18. Ion positions within water molecule region
19. No ion-ion overlap > MIN_SEPARATION
20. Guest molecule info preserved
21. Custom molecule info preserved
22. Solute info preserved

### Full Chain Invariants
23. Molecule ordering: SOL → hydrate guests → liquid solutes → custom → ions
24. All molecule types present in final structure
25. No atoms lost: sum of all molecule atom counts == total
26. CH4_H ≠ CH4_L when both present (MoleculetypeRegistry distinction)

---

## Test Fixture Strategy

### Use Real Generation (Module-Scoped)
```python
@pytest.fixture(scope="module")
def ice_candidate():
    phase_info = lookup_phase(250, 0.1)
    gen = IceStructureGenerator(phase_info, 96)
    return gen.generate_all(1)[0]

@pytest.fixture(scope="module")
def interface_structure(ice_candidate):
    config = InterfaceConfig(mode='slab', box_x=3.0, box_y=3.0, box_z=8.0,
                             seed=42, ice_thickness=2.0, water_thickness=4.0)
    return generate_interface(ice_candidate, config)
```

Ice generation ~3s, interface ~2s. Module scope amortizes cost. Use function scope only for cheap operations (validation, counts).

---

## Proposed Test Files

| File | Tests | Coverage |
|------|-------|----------|
| `test_e2e_ice_generation.py` | ~5 | Workflow 2 (ice generation + all orthogonal phases) |
| `test_e2e_hydrate_generation.py` | ~8 | Workflow 3 (sI/sII × ch4/thf) |
| `test_e2e_interface_generation.py` | ~10 | Workflow 4 (ice×modes, hydrate→interface, Ice II rejection) |
| `test_e2e_custom_molecule.py` | ~20 | Workflow 5 (validation, random placement, custom placement, edge cases) |
| `test_e2e_solute_insertion.py` | ~15 | Workflow 6 (all S1-S7 combinations) |
| `test_e2e_ion_insertion.py` | ~12 | Workflow 7 (I1-I7 + bug I5 + charge neutrality) |
| `test_e2e_workflow_chains.py` | ~12 | Workflow 8 (F1-F7 chains + invariants) |
| **Total** | **~82** | |

---

## Edge Cases

1. **Zero concentration**: concentration=0 → n_molecules=0, no crash
2. **Very high concentration**: More solutes than water → partial placement
3. **Atom count mismatch**: GRO 10 atoms vs ITP 9 atoms → validation error
4. **Generic residue names**: GRO='MOL' vs ITP='etoh' → no mismatch warning
5. **No [atomtypes] in ITP**: Warning but not blocking
6. **Ice II rejection**: InterfaceGenerationError with clear message
7. **Pocket diameter >= box**: InterfaceGenerationError
8. **Piece mode box too small**: InterfaceGenerationError
9. **Custom placement out of bounds**: within_bounds=False
10. **Custom placement with overlap**: has_overlap=True
11. **THF solute (13 atoms)**: Larger template, more overlap checks
12. **CH4_H + CH4_L coexistence**: Registry must distinguish
13. **Concentration roundtrip**: molecule_count → concentration → molecule_count
14. **SoluteStructure → IonInserter**: AttributeError (BUG)
15. **Empty interface (no water)**: Graceful error

---

## Test Data

| File | Path | Atoms |
|------|------|-------|
| Ethanol GRO | `quickice/data/custom/etoh.gro` | 9 |
| Ethanol ITP | `quickice/data/custom/etoh.itp` | 9, has [atomtypes] |
| CH4 ITP | `quickice/data/ch4.itp` | 5 |
| THF ITP | `quickice/data/thf.itp` | 13 |
| CH4 Hydrate ITP | `quickice/data/ch4_hydrate.itp` | 5 |
| THF Hydrate ITP | `quickice/data/thf_hydrate.itp` | 13 |
| CH4 Liquid ITP | `quickice/data/ch4_liquid.itp` | 5 |
| THF Liquid ITP | `quickice/data/thf_liquid.itp` | 13 |

## Execution

```bash
pytest tests/test_e2e_*.py -v          # ~90s total
pytest tests/test_e2e_*.py -v --durations=20
```
