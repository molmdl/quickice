# E2E GROMACS Export Test - Research

**Researched:** 2026-05-22
**Domain:** GROMACS export pipeline (6 tab exporters, writer functions, data structures)
**Confidence:** HIGH

## Summary

This research traces the complete GROMACS export chain across all 6 tab exporters in QuickIce. Each exporter follows a consistent pattern: (1) show QFileDialog for save path, (2) call writer functions from `gromacs_writer.py` to write .gro/.top files, (3) copy/modify .itp files to the output directory, (4) handle errors via QMessageBox. The key complexity lies in the chain dependencies (Tab 3→2, Tab 4→2, Tab 5→4) and the varying structure dataclasses each exporter requires.

The writer functions in `gromacs_writer.py` (2557 lines) are pure I/O functions with no GUI dependencies — they can be tested independently. The exporter classes in `gui/export.py` (927 lines) and `gui/hydrate_export.py` (192 lines) are the GUI integration points that need QFileDialog/QMessageBox mocking.

**Primary recommendation:** Test the writer functions directly (no mocking needed), then test the exporter classes by mocking only `QFileDialog.getSaveFileName` (return a tmpdir path) and `QMessageBox` (suppress dialogs). Build structure fixtures incrementally following the chain dependency order.

---

## Exporter 1: GROMACSExporter (Tab 0 — Ice)

- **Class:** `GROMACSExporter` (export.py line 688)
- **Entry point:** `export_gromacs(self, ranked_candidate: RankedCandidate, T: float, P: float) -> bool`
- **Required structure:** `RankedCandidate` (wraps `Candidate`)

### Structure Fields Used
| Field | From | Required? | Notes |
|-------|------|-----------|-------|
| `candidate.phase_id` | Candidate | Yes | Used for default filename and .top system name |
| `candidate.nmolecules` | Candidate | Yes | Controls .gro atom count and .top molecule count |
| `candidate.positions` | Candidate | Yes | (N, 3) array in nm — O, H, H per molecule |
| `candidate.atom_names` | Candidate | Yes | ["O", "H", "H", ...] |
| `candidate.cell` | Candidate | Yes | (3, 3) row vectors in nm |
| `rank` | RankedCandidate | Yes | For default filename |

### Writer Functions Called
```python
write_gro_file(candidate, filepath)           # line 426 gromacs_writer.py
write_top_file(candidate, filepath)            # line 512 gromacs_writer.py
get_tip4p_itp_path()                           # line 570 gromacs_writer.py
```

### ITP Files Copied
- `tip4p-ice.itp` — via `shutil.copy(itp_source, itp_path)` where `itp_path = path.with_name(path.stem + '.itp')`

**NOTE:** The ITP destination filename uses the .gro stem, NOT "tip4p-ice.itp". E.g., `ice_ih_195K_1.36MPa_c5.itp`.

### Output Files
- `{stem}.gro` — coordinates
- `{stem}.top` — topology
- `{stem}.itp` — tip4p-ice.itp copy

### QMessageBox Calls
1. `QMessageBox.critical(self.parent, "Export Error", ...)` — on any exception (line 766)

### QFileDialog Calls
1. `QFileDialog.getSaveFileName(self.parent, "Export for GROMACS", default_name, "GRO Files (*.gro);;All Files (*)", "GRO Files (*.gro)")` — returns (filepath, selected_filter); empty filepath = user cancelled

### Minimum Mock Data Needed
```python
candidate = Candidate(
    positions=np.array([[0.1, 0.1, 0.1], [0.15, 0.12, 0.1], [0.08, 0.12, 0.1]]),  # 1 molecule
    atom_names=["O", "H", "H"],
    cell=np.array([[0.9, 0.0, 0.0], [0.0, 0.78, 0.0], [0.0, 0.0, 0.72]]),
    nmolecules=1,
    phase_id="ice_ih",
    seed=42,
    metadata={}
)
ranked = RankedCandidate(candidate=candidate, energy_score=0.0, density_score=0.0, diversity_score=0.0, rank=1)
```

---

## Exporter 2: HydrateGROMACSExporter (Tab 1 — Hydrate)

- **Class:** `HydrateGROMACSExporter` (hydrate_export.py line 71)
- **Entry point:** `export_hydrate(self, structure: HydrateStructure, config: HydrateConfig) -> bool`

### Required Structures
1. `HydrateStructure`
2. `HydrateConfig`

### Structure Fields Used

**From HydrateStructure:**
| Field | Required? | Notes |
|-------|-----------|-------|
| `positions` | Yes | (N_atoms, 3) in nm |
| `atom_names` | Yes | List of atom name strings |
| `cell` | Yes | (3, 3) row vectors |
| `molecule_index` | Yes | List of MoleculeIndex |
| `config` | Yes | Used for filename and ITP lookup |
| `lattice_info` | Yes | For `.to_candidate()` |
| `report` | No | Not used in export |
| `guest_count` | No | Not used in export |
| `water_count` | No | Not used in export |

**From HydrateConfig:**
| Field | Required? | Notes |
|-------|-----------|-------|
| `lattice_type` | Yes | "sI", "sII", "sH" — for filename |
| `guest_type` | Yes | "ch4" or "thf" — for ITP lookup and registry |
| `supercell_x/y/z` | Yes | For filename |

### Writer Functions Called
```python
write_multi_molecule_gro_file(positions, molecule_index, cell, filepath, title, atom_names)  # line 1046
write_multi_molecule_top_file(molecule_index, filepath, system_name, itp_files, registry)     # line 1143
get_tip4p_itp_path()                                                                            # line 570
```

### ITP Files Copied
- `tip4p-ice.itp` — always
- `{guest_type}_hydrate.itp` — always (e.g., `ch4_hydrate.itp`, `thf_hydrate.itp`)

### MoleculetypeRegistry Usage
```python
registry = MoleculetypeRegistry()
registry.register_hydrate_guest(config.guest_type.upper())  # Returns "CH4_H" or "THF_H"
```
The registry is passed to `write_multi_molecule_top_file` for molecule naming.

### Output Files
- `{stem}.gro` — coordinates
- `{stem}.top` — topology
- `tip4p-ice.itp` — water topology
- `{guest_type}_hydrate.itp` — guest topology

### QMessageBox Calls
1. `QMessageBox.critical(self.parent, "Export Error", ...)` — on any exception (line 187)

### QFileDialog Calls
1. `QFileDialog.getSaveFileName(self.parent, "Export Hydrate for GROMACS", default_name, ...)` — returns (filepath, selected_filter)

### ITP Path Resolution
`_get_hydrate_guest_itp_path(guest_type)` — searches in:
1. `quickice/data/{guest_type}_hydrate.itp` (package dir)
2. `quickice/data/{guest_type}_hydrate.itp` (relative to export.py's parent.parent)
3. Raises `FileNotFoundError` if not found

### Minimum Mock Data Needed
```python
config = HydrateConfig(lattice_type="sI", guest_type="ch4", supercell_x=1, supercell_y=1, supercell_z=1)

molecule_index = [
    MoleculeIndex(start_idx=0, count=4, mol_type="water"),
    MoleculeIndex(start_idx=4, count=5, mol_type="ch4"),
]
structure = HydrateStructure(
    positions=np.array([...]),  # 9 atoms (4 water + 5 CH4)
    atom_names=["OW","HW1","HW2","MW","C","H","H","H","H"],
    cell=np.eye(3) * 2.0,
    molecule_index=molecule_index,
    config=config,
    lattice_info=HydrateLatticeInfo.from_lattice_type("sI"),
    report="test",
    guest_count=1,
    water_count=1,
)
```

---

## Exporter 3: InterfaceGROMACSExporter (Tab 2 — Interface)

- **Class:** `InterfaceGROMACSExporter` (export.py line 824)
- **Entry point:** `export_interface_gromacs(self, interface_structure: InterfaceStructure) -> bool`

### Required Structure
`InterfaceStructure`

### Structure Fields Used
| Field | Required? | Notes |
|-------|-----------|-------|
| `positions` | Yes | (N_atoms, 3) in nm — ice + water + guests |
| `atom_names` | Yes | Used for guest type detection |
| `cell` | Yes | (3, 3) row vectors |
| `ice_atom_count` | Yes | Marks ice/water boundary |
| `water_atom_count` | Yes | Marks water/guest boundary |
| `ice_nmolecules` | Yes | For .gro/.top output |
| `water_nmolecules` | Yes | For .gro/.top output |
| `mode` | Yes | "slab", "pocket", "piece" — for filename |
| `guest_atom_count` | Yes | Conditional: guests section |
| `guest_nmolecules` | Yes | Conditional: guests section |
| `molecule_index` | Yes | For molecule-aware wrapping |
| `report` | No | Not used in export |

### Writer Functions Called
```python
write_interface_gro_file(iface, filepath)   # line 606 gromacs_writer.py
write_interface_top_file(iface, filepath)    # line 938 gromacs_writer.py
get_tip4p_itp_path()                          # line 570
detect_guest_type_from_atoms(atom_names)      # line 885
```

### ITP Files Copied
- `tip4p-ice.itp` — always
- `{guest_type}_hydrate.itp` — conditional on `guest_nmolecules > 0 AND guest_atom_count > 0`

### Output Files
- `{stem}.gro`, `{stem}.top`, `tip4p-ice.itp`, optionally `{guest_type}_hydrate.itp`

### QMessageBox Calls
1. `QMessageBox.warning(self.parent, "Missing Guest ITP", ...)` — if `_get_hydrate_guest_itp_path` raises FileNotFoundError (line 915)
2. `QMessageBox.critical(self.parent, "Export Error", ...)` — on any exception (line 926)

### QFileDialog Calls
1. `QFileDialog.getSaveFileName(self.parent, "Export Interface for GROMACS", default_name, ...)`

### Guest Type Detection Logic (CRITICAL)
The exporter detects guest type from atom names using two methods:
1. **Primary:** `detect_guest_type_from_atoms(guest_atom_names)` — analyzes atom composition
2. **Via molecule_index:** Loops through `molecule_index` entries with `mol_type == "guest"`, extracts atom names, calls `detect_guest_type_from_atoms`
3. **Fallback heuristic:** `atoms_per_guest >= 10` → "thf", else "ch4"

**IMPORTANT:** The code first checks `molecule_index` for guest entries (line 902-907 in InterfaceGROMACSExporter) but the writer functions use the atom_names-based detection. The exporter also uses the `ice_atom_count + water_atom_count` offset to get guest atom names.

### Minimum Mock Data Needed
```python
# Simple ice+water interface (no guests)
iface = InterfaceStructure(
    positions=np.zeros((14, 3)),  # 2 ice (6 atoms) + 2 water (8 atoms)
    atom_names=["O","H","H","O","H","H","OW","HW1","HW2","MW","OW","HW1","HW2","MW"],
    cell=np.eye(3) * 3.0,
    ice_atom_count=6,
    water_atom_count=8,
    ice_nmolecules=2,
    water_nmolecules=2,
    mode="slab",
    report="test",
    guest_atom_count=0,
    molecule_index=[
        MoleculeIndex(0, 3, "ice"), MoleculeIndex(3, 3, "ice"),
        MoleculeIndex(6, 4, "water"), MoleculeIndex(10, 4, "water"),
    ],
    guest_nmolecules=0,
)
```

---

## Exporter 4: CustomMoleculeGROMACSExporter (Tab 3)

- **Class:** `CustomMoleculeGROMACSExporter` (export.py line 160)
- **Entry point:** `export_custom_molecule_gromacs(self, custom_structure) -> bool`

### Required Structure
`CustomMoleculeStructure`

### Structure Fields Used
| Field | Required? | Notes |
|-------|-----------|-------|
| `positions` | Yes | ALL atoms (ice + water + custom) |
| `atom_names` | Yes | ALL atom names |
| `cell` | Yes | (3, 3) row vectors |
| `molecule_index` | Yes | For ordering and wrapping |
| `ice_atom_count` | Yes | For guest detection offset |
| `water_atom_count` | Yes | For guest detection offset |
| `guest_atom_count` | Yes | Conditional: guest ITP |
| `moleculetype_name` | Yes | For filename, residue name |
| `custom_molecule_count` | Yes | For filename |
| `itp_path` | Yes | **Path object** — must exist for reading and copying |
| `custom_molecule_atom_count` | No | Not directly used by exporter (used by writer) |
| `config` | No | Not used in export |
| `gro_path` | No | Not used in export |
| `residue_name` | No | Not used in export |
| `interface_structure` | No | Not directly accessed by exporter (but used by writer indirectly) |

### Writer Functions Called
```python
write_custom_molecule_gro_file(custom_structure, filepath)   # line 1841 gromacs_writer.py
write_custom_molecule_top_file(custom_structure, filepath)    # line 1989 gromacs_writer.py
comment_out_atomtypes_in_itp(itp_content)                      # line 310
get_tip4p_itp_path()                                            # line 570
detect_guest_type_from_atoms(atom_names)                        # line 885
```

### ITP Files — Modified, Not Simply Copied
- **Custom .itp:** Read from `custom_structure.itp_path`, modified via `comment_out_atomtypes_in_itp()`, then written to output dir. **The atomtypes section is commented out because types are defined in the main .top file.**
- `tip4p-ice.itp` — always copied
- `{guest_type}_hydrate.itp` — conditional on guests present

### Output Files
- `{stem}.gro`, `{stem}.top`, `tip4p-ice.itp`, `{custom_itp_name}`, optionally `{guest_type}_hydrate.itp`

### QMessageBox Calls
1. `QMessageBox.warning(self.parent, "Missing Guest ITP", ...)` — if guest ITP not found (line 248)
2. `QMessageBox.critical(self.parent, "Export Error", ...)` — on any exception (line 260)

### QFileDialog Calls
1. `QFileDialog.getSaveFileName(self.parent, "Export Custom Molecule System for GROMACS", default_name, ...)`

### Minimum Mock Data Needed
```python
# Need a real .itp file for custom_structure.itp_path
# Use quickice/data/custom/etoh.itp as test fixture

itp_path = Path("quickice/data/custom/etoh.itp")  # Must exist!
custom = CustomMoleculeStructure(
    positions=np.zeros((17, 3)),  # 4 ice (12) + 4 water (4) + 1 custom (1) ... adjust counts
    atom_names=["O","H","H","OW","HW1","HW2","MW","C1","H1"],  # abbreviated
    cell=np.eye(3) * 3.0,
    molecule_index=[...],
    ice_atom_count=3,  # 1 ice molecule
    water_atom_count=4,  # 1 water molecule
    custom_molecule_atom_count=5,  # custom atoms
    moleculetype_name="ETOH",
    custom_molecule_count=1,
    itp_path=itp_path,  # CRITICAL: must be a real Path to an existing .itp
)
```

**IMPORTANT:** `custom_structure.itp_path.read_text()` is called directly (line 221), so `itp_path` must point to an existing, readable file. Use `quickice/data/custom/etoh.itp` or create a temp .itp.

---

## Exporter 5: SoluteGROMACSExporter (Tab 4)

- **Class:** `SoluteGROMACSExporter` (export.py line 26)
- **Entry point:** `export_solute_gromacs(self, solute_structure: SoluteStructure) -> bool`

### Required Structure
`SoluteStructure`

### Structure Fields Used
| Field | Required? | Notes |
|-------|-----------|-------|
| `solute_type` | Yes | "CH4" or "THF" — for filename, ITP lookup |
| `n_molecules` | Yes | For filename |
| `positions` | Yes | Solute atom positions |
| `atom_names` | Yes | Solute atom names |
| `cell` | Yes | Box vectors |
| `molecule_indices` | Yes | List of (start, end) tuples |
| `registry` | Yes | MoleculetypeRegistry with CH4_L/THF_L registered |
| `interface_structure` | Yes | **CRITICAL** — accessed for `guest_nmolecules`, `guest_atom_count`, `molecule_index`, `atom_names` |
| `custom_molecule_count` | Yes | Conditional: custom ITP |
| `custom_molecule_positions` | Yes | Conditional: custom ITP |
| `custom_itp_path` | Yes | Conditional: custom ITP (must exist if custom molecules present) |
| `custom_molecule_moleculetype` | Yes | Conditional: custom molecule naming |

### Writer Functions Called
```python
write_solute_gro_file(solute_structure, filepath)    # line 2100 gromacs_writer.py
write_solute_top_file(solute_structure, filepath)     # line 2376 gromacs_writer.py
get_tip4p_itp_path()                                   # line 570
comment_out_atomtypes_in_itp(itp_content)               # line 310
detect_guest_type_from_atoms(atom_names)                # line 885
```

### ITP Files — Conditional Logic
- `tip4p-ice.itp` — always
- `{solute_type}_liquid.itp` — if file exists in `quickice/data/`, modified with atomtypes commented out
- `{guest_type}_hydrate.itp` — if `interface.guest_nmolecules > 0 AND interface.guest_atom_count > 0`
- Custom `.itp` — if `custom_molecule_count > 0 AND custom_molecule_positions is not None AND custom_itp_path exists`

### Output Files
- `{stem}.gro`, `{stem}.top`, `tip4p-ice.itp`, `{solute_type}_liquid.itp`, optionally `{guest_type}_hydrate.itp`, optionally custom `.itp`

### QMessageBox Calls
1. `QMessageBox.warning(self.parent, "Missing Guest ITP", ...)` — if guest ITP not found (line 120)
2. `QMessageBox.critical(self.parent, "Export Error", ...)` — on any exception (line 154)

### QFileDialog Calls
1. `QFileDialog.getSaveFileName(self.parent, "Export Solutes for GROMACS", default_name, ...)`

### Key Detail: InterfaceStructure Access Pattern
The exporter accesses the INNER interface via `solute_structure.interface_structure`:
```python
interface = solute_structure.interface_structure
if interface.guest_nmolecules > 0 and interface.guest_atom_count > 0:
    # ... guest detection using interface.molecule_index, interface.atom_names
```
The writer functions (`write_solute_gro_file`, `write_solute_top_file`) also access `solute_structure.interface_structure` for positions, molecule_index, and cell.

### Minimum Mock Data Needed
```python
# First build an InterfaceStructure (see Tab 2 section)
iface = InterfaceStructure(...)

registry = MoleculetypeRegistry()
registry.register_liquid_solute("CH4")  # Returns "CH4_L"

solute = SoluteStructure(
    positions=np.array([[0.5, 0.5, 0.5], [0.55, 0.5, 0.5], [0.45, 0.5, 0.5], [0.55, 0.45, 0.5], [0.45, 0.45, 0.5]]),
    atom_names=["C", "H", "H", "H", "H"],
    cell=iface.cell,
    solute_type="CH4",
    n_molecules=1,
    molecule_indices=[(0, 5)],
    registry=registry,
    interface_structure=iface,  # CRITICAL
)
```

---

## Exporter 6: IonGROMACSExporter (Tab 5)

- **Class:** `IonGROMACSExporter` (export.py line 266)
- **Entry point:** `export_ion_gromacs(self, ion_structure: IonStructure) -> bool`

### Required Structure
`IonStructure`

### Structure Fields Used
| Field | Required? | Notes |
|-------|-----------|-------|
| `na_count` | Yes | For filename, ion.itp, .top |
| `cl_count` | Yes | For filename, ion.itp, .top |
| `positions` | Yes | Water + ion positions |
| `atom_names` | Yes | All atom names |
| `cell` | Yes | Box vectors |
| `molecule_index` | Yes | For ordering and wrapping |
| `report` | No | Not used in export |
| `guest_nmolecules` | Yes | Conditional: guest ITP |
| `guest_atom_count` | Yes | Conditional: guest ITP |
| `solute_n_molecules` | Yes | Conditional: solute ITP |
| `solute_type` | Yes | Conditional: solute ITP |
| `solute_positions` | Yes | Conditional: solute writing |
| `solute_atom_names` | Yes | Conditional: solute writing |
| `solute_molecule_indices` | Yes | Conditional: solute ordering |
| `solute_registry` | Yes | Conditional: solute naming |
| `custom_molecule_count` | Yes | Conditional: custom ITP |
| `custom_molecule_positions` | Yes | Conditional: custom writing |
| `custom_molecule_atom_names` | Yes | Conditional: custom writing |
| `custom_molecule_moleculetype` | Yes | Conditional: custom naming |
| `custom_itp_path` | Yes | Conditional: custom ITP |

### Writer Functions Called
```python
write_ion_gro_file(ion_structure, filepath)   # line 1299 gromacs_writer.py
write_ion_top_file(ion_structure, filepath)    # line 1624 gromacs_writer.py
get_tip4p_itp_path()                            # line 570
comment_out_atomtypes_in_itp(itp_content)        # line 310
detect_guest_type_from_atoms(atom_names)          # line 885
write_ion_itp(ion_itp_path, na_count, cl_count)  # from gromacs_ion_export.py line 81
```

### ITP Files — Most Complex of All Exporters
- `tip4p-ice.itp` — always
- `ion.itp` — **GENERATED** (not copied!) via `write_ion_itp()` from `quickice.structure_generation.gromacs_ion_export`
- `{guest_type}_hydrate.itp` — conditional on guests
- `{solute_type}_liquid.itp` — conditional on solutes, modified with atomtypes commented
- Custom `.itp` — conditional on custom molecules, modified with atomtypes commented

### Output Files
- `{stem}.gro`, `{stem}.top`, `tip4p-ice.itp`, `ion.itp`, optionally `{guest_type}_hydrate.itp`, optionally `{solute_type}_liquid.itp`, optionally custom `.itp`

### QMessageBox Calls
1. `QMessageBox.warning(self.parent, "Missing Guest ITP", ...)` — if guest ITP not found (line 368)
2. `QMessageBox.critical(self.parent, "Export Error", ...)` — on any exception (line 411)

### QFileDialog Calls
1. `QFileDialog.getSaveFileName(self.parent, "Export Ions for GROMACS", default_name, ...)`

### Minimum Mock Data Needed
```python
ion = IonStructure(
    positions=np.zeros((10, 3)),  # 2 water (8 atoms) + 1 NA + 1 CL
    atom_names=["OW","HW1","HW2","MW","OW","HW1","HW2","MW","NA","CL"],
    cell=np.eye(3) * 3.0,
    molecule_index=[
        MoleculeIndex(0, 4, "water"),
        MoleculeIndex(4, 4, "water"),
        MoleculeIndex(8, 1, "na"),
        MoleculeIndex(9, 1, "cl"),
    ],
    na_count=1,
    cl_count=1,
    report="test",
    # All optional fields default to 0/None/empty
)
```

---

## Chain Dependencies

```
Tab 0 (Ice) ──────────── standalone (needs Candidate/RankedCandidate only)
Tab 1 (Hydrate) ──────── standalone (needs HydrateStructure + HydrateConfig)
Tab 2 (Interface) ────── standalone (needs InterfaceStructure)
Tab 3 (Custom Molecule) → needs InterfaceStructure from Tab 2
                            (stored as custom_structure.interface_structure)
Tab 4 (Solute) ────────→ needs InterfaceStructure from Tab 2
                            (stored as solute_structure.interface_structure)
                            + may carry CustomMoleculeStructure fields from Tab 3
Tab 5 (Ion) ────────────→ needs IonStructure which carries forward:
                            - guest info (from InterfaceStructure/Tab 2)
                            - solute info (from SoluteStructure/Tab 4)
                            - custom molecule info (from CustomMoleculeStructure/Tab 3)
```

### Recommended Test Build Order
1. **Tab 0** — simplest: just Candidate
2. **Tab 1** — simple: HydrateStructure + HydrateConfig
3. **Tab 2** — builds on nothing but is prerequisite for 3, 4
4. **Tab 3** — needs InterfaceStructure fixture from Tab 2
5. **Tab 4** — needs InterfaceStructure fixture from Tab 2 + registry
6. **Tab 5** — most complex: IonStructure with all optional fields

---

## External Dependencies to Mock

### QFileDialog
- **What:** `QFileDialog.getSaveFileName(parent, title, default_name, filters, selected_filter)` returns `(filepath_str, selected_filter_str)`
- **When to mock:** Every exporter calls this. Empty string = user cancelled.
- **How to mock:**
  ```python
  from unittest.mock import patch
  with patch('quickice.gui.export.QFileDialog.getSaveFileName') as mock_dialog:
      mock_dialog.return_value = (str(tmpdir / "test.gro"), "GRO Files (*.gro)")
      exporter.export_gromacs(ranked_candidate, T=195, P=1.36)
  ```
- **Important:** The mock path string must be the full path to the .gro file. The exporter derives .top and .itp paths from the stem.

### QMessageBox
- **What:** `QMessageBox.critical()`, `QMessageBox.warning()`, `QMessageBox.question()`
- **When to mock:** On error paths and overwrite prompts
- **How to mock:**
  ```python
  with patch('quickice.gui.export.QMessageBox') as mock_mb:
      exporter.export_gromacs(ranked_candidate, T=195, P=1.36)
  ```
  Or just let it be a no-op (PySide6 may need a QApplication).
- **Simpler approach:** Mock QMessageBox to be a no-op, since we're testing file output, not dialog behavior.

### GenIce2
- **Availability:** Required at runtime for structure generation, NOT needed for export testing
- **What to mock:** Nothing — export tests use pre-built structure fixtures, not generation

### IAPWS
- **Availability:** Used for density calculations in generation, NOT needed for export testing
- **What to mock:** Nothing — export tests use pre-built structure fixtures

### File I/O
- **Approach:** Use `tempfile.TemporaryDirectory()` as the output directory
- **Pattern from existing tests:**
  ```python
  with tempfile.TemporaryDirectory() as tmpdir:
      output_path = Path(tmpdir) / "test.gro"
      # ... write and verify
  ```
- **Note:** `get_tip4p_itp_path()` and `_get_hydrate_guest_itp_path()` look for ITP files in the package data directory. These must exist for the exporters to work. They DO exist in `quickice/data/`.

### Data Files Required (must exist in quickice/data/)
| File | Used By |
|------|---------|
| `tip4p-ice.itp` | ALL exporters |
| `ch4_hydrate.itp` | Interface, CustomMolecule, Solute, Ion (when guests are CH4) |
| `thf_hydrate.itp` | Interface, CustomMolecule, Solute, Ion (when guests are THF) |
| `ch4_liquid.itp` | Solute, Ion (when solutes are CH4) |
| `thf_liquid.itp` | Solute, Ion (when solutes are THF) |
| `custom/etoh.itp` | CustomMolecule test fixture |
| `custom/etoh.gro` | CustomMolecule test fixture |

All these files exist in `quickice/data/` (verified).

---

## Existing Test Patterns

### Pattern 1: Direct Writer Testing (test_pdb_writer.py, test_molecule_wrapping.py)
```python
# No mocking needed — writer functions are pure I/O
with tempfile.NamedTemporaryFile(mode='w', suffix='.gro', delete=False) as f:
    filepath = f.name
try:
    write_gro_file(candidate, filepath)
    assert Path(filepath).exists()
    # ... verify content
finally:
    Path(filepath).unlink(missing_ok=True)
```

### Pattern 2: Structure Fixture Construction (test_output/test_validator.py)
```python
@pytest.fixture
def ice_ih_candidate():
    cell = np.array([...])
    positions = np.array([...])
    atom_names = ['O', 'H', 'H', ...]
    return Candidate(positions=positions, atom_names=atom_names, cell=cell,
                     nmolecules=4, phase_id='ice_ih', seed=1000, metadata={})
```

### Pattern 3: MoleculeIndex Construction (test_gromacs_molecule_ordering.py)
```python
molecule_index = []
idx = 0
for i in range(10):
    molecule_index.append(MoleculeIndex(start_idx=idx, count=4, mol_type='water'))
    idx += 4
for i in range(5):
    molecule_index.append(MoleculeIndex(start_idx=idx, count=5, mol_type='ch4'))
    idx += 5
```

### Pattern 4: Mock Interface Construction (test_custom_molecule_panel_34_6.py)
```python
def _create_mock_interface(self) -> InterfaceStructure:
    # Creates simple mock with ice + water
    return InterfaceStructure(
        positions=np.zeros((22, 3)),
        atom_names=[...],
        cell=np.eye(3) * 3.0,
        ice_atom_count=12,
        water_atom_count=8,
        ice_nmolecules=4,
        water_nmolecules=2,
        mode="slab",
        report="test",
        ...
    )
```

### Key Observation: No Existing Export Tests
There are **ZERO** existing tests for the exporter CLASSES (GROMACSExporter, InterfaceGROMACSExporter, etc.). Existing tests only cover:
- Writer functions (gromacs_writer) directly
- Molecule ordering in GRO files
- ITP bundling
- PDB writing

The exporter classes with their QFileDialog/QMessageBox interactions are completely untested.

---

## Recommended Test Structure

### File Organization
```
tests/
├── test_output/
│   ├── test_gromacs_writer.py          # EXISTING — writer function tests
│   ├── test_gromacs_export_ice.py       # NEW — Tab 0 GROMACSExporter
│   ├── test_gromacs_export_hydrate.py   # NEW — Tab 1 HydrateGROMACSExporter
│   ├── test_gromacs_export_interface.py # NEW — Tab 2 InterfaceGROMACSExporter
│   ├── test_gromacs_export_custom.py    # NEW — Tab 3 CustomMoleculeGROMACSExporter
│   ├── test_gromacs_export_solute.py    # NEW — Tab 4 SoluteGROMACSExporter
│   ├── test_gromacs_export_ion.py       # NEW — Tab 5 IonGROMACSExporter
│   └── conftest.py                      # NEW — shared fixtures
```

### Suggested Test Ordering (incremental dependency)
1. `test_gromacs_export_ice.py` — simplest, validates mock pattern
2. `test_gromacs_export_hydrate.py` — validates MoleculetypeRegistry pattern
3. `test_gromacs_export_interface.py` — validates guest detection
4. `test_gromacs_export_custom.py` — validates ITP modification
5. `test_gromacs_export_solute.py` — validates interface_structure access
6. `test_gromacs_export_ion.py` — most complex, validates all paths

### Suggested Fixture Design (conftest.py)
```python
import pytest
import numpy as np
from pathlib import Path
from unittest.mock import patch
from quickice.structure_generation.types import (
    Candidate, InterfaceStructure, HydrateStructure, HydrateConfig,
    HydrateLatticeInfo, MoleculeIndex, IonStructure, SoluteStructure,
    CustomMoleculeStructure
)
from quickice.ranking.types import RankedCandidate

# ─── Basic structures ───

@pytest.fixture
def simple_candidate():
    """1-molecule ice candidate (3 atoms: O, H, H)."""
    return Candidate(
        positions=np.array([[0.1, 0.1, 0.1], [0.15, 0.12, 0.1], [0.08, 0.12, 0.1]]),
        atom_names=["O", "H", "H"],
        cell=np.array([[0.9, 0.0, 0.0], [0.0, 0.78, 0.0], [0.0, 0.0, 0.72]]),
        nmolecules=1,
        phase_id="ice_ih",
        seed=42,
        metadata={},
    )

@pytest.fixture
def ranked_candidate(simple_candidate):
    return RankedCandidate(
        candidate=simple_candidate,
        energy_score=0.0, density_score=0.0, diversity_score=0.0, rank=1
    )

@pytest.fixture
def simple_interface():
    """2 ice + 2 water molecules, no guests."""
    ...

@pytest.fixture
def interface_with_guests():
    """2 ice + 2 water + 1 CH4 guest."""
    ...

# ─── QFileDialog mock ───

@pytest.fixture
def mock_save_dialog(tmp_path):
    """Returns a fixture that mocks QFileDialog.getSaveFileName to save in tmp_path."""
    def _mock(exporter_method, structure, filename="test.gro", **kwargs):
        save_path = str(tmp_path / filename)
        with patch('quickice.gui.export.QFileDialog.getSaveFileName',
                   return_value=(save_path, "GRO Files (*.gro)")):
            with patch('quickice.gui.export.QMessageBox'):
                return exporter_method(structure, **kwargs)
    return _mock

# Alternative: fixture for hydrate_export.py module path
@pytest.fixture
def mock_hydrate_save_dialog(tmp_path):
    def _mock(exporter, structure, config, filename="test.gro"):
        save_path = str(tmp_path / filename)
        with patch('quickice.gui.hydrate_export.QFileDialog.getSaveFileName',
                   return_value=(save_path, "GRO Files (*.gro)")):
            with patch('quickice.gui.hydrate_export.QMessageBox'):
                return exporter.export_hydrate(structure, config)
    return _mock
```

### Test Template per Exporter
```python
class TestIceGROMACSExporter:
    """Test GROMACSExporter (Tab 0)."""
    
    def test_export_creates_gro_top_itp(self, ranked_candidate, tmp_path):
        """Test that export creates all 3 expected files."""
        from quickice.gui.export import GROMACSExporter
        
        exporter = GROMACSExporter(parent_widget=None)
        save_path = str(tmp_path / "ice_test.gro")
        
        with patch('quickice.gui.export.QFileDialog.getSaveFileName',
                   return_value=(save_path, "GRO Files (*.gro)")):
            with patch('quickice.gui.export.QMessageBox'):
                result = exporter.export_gromacs(ranked_candidate, T=195, P=1.36)
        
        assert result is True
        assert (tmp_path / "ice_test.gro").exists()
        assert (tmp_path / "ice_test.top").exists()
        assert (tmp_path / "ice_test.itp").exists()
    
    def test_export_cancelled(self, ranked_candidate):
        """Test that cancelled dialog returns False."""
        with patch('quickice.gui.export.QFileDialog.getSaveFileName',
                   return_value=("", "")):
            exporter = GROMACSExporter(parent_widget=None)
            result = exporter.export_gromacs(ranked_candidate, T=195, P=1.36)
            assert result is False
    
    def test_gro_file_has_correct_atom_count(self, ranked_candidate, tmp_path):
        """Test that .gro file has nmolecules * 4 atoms (TIP4P-ICE)."""
        ...
    
    def test_top_file_has_molecules_section(self, ranked_candidate, tmp_path):
        """Test that .top file has [molecules] section with SOL count."""
        ...
```

---

## Risk Areas

### 1. QFileDialog Mock Path (MEDIUM RISK)
The `QFileDialog.getSaveFileName` is imported from `PySide6.QtWidgets` and used in `quickice.gui.export`. The mock must patch the **module-level reference**, not the PySide6 class. Use:
```python
patch('quickice.gui.export.QFileDialog.getSaveFileName', ...)
```
NOT:
```python
patch('PySide6.QtWidgets.QFileDialog.getSaveFileName', ...)  # WRONG
```

### 2. Hydrate Exporter is in a Separate Module (MEDIUM RISK)
`HydrateGROMACSExporter` is in `quickice.gui.hydrate_export`, not `quickice.gui.export`. So the mock path is different:
```python
patch('quickice.gui.hydrate_export.QFileDialog.getSaveFileName', ...)
patch('quickice.gui.hydrate_export.QMessageBox', ...)
```

### 3. ITP File Existence (HIGH RISK)
Multiple ITP files must exist in `quickice/data/` for the exporters to work:
- `tip4p-ice.itp` — used by ALL exporters
- `ch4_hydrate.itp`, `thf_hydrate.itp` — used when guests present
- `ch4_liquid.itp`, `thf_liquid.itp` — used when solutes present

If these are missing, `_get_hydrate_guest_itp_path()` raises `FileNotFoundError`, which triggers `QMessageBox.warning` but **does NOT abort the export** — the exporter continues, leaving the .top file referencing a missing .itp.

### 4. SoluteStructure.interface_structure is Required (HIGH RISK)
`write_solute_gro_file` and `write_solute_top_file` both access `solute_structure.interface_structure` for:
- `interface.molecule_index` — for SOL/guest counting and wrapping
- `interface.positions` — for coordinate writing
- `interface.cell` — for box vectors
- `interface.atom_names` — for guest type detection

If `interface_structure` is `None`, the export will crash with `AttributeError`.

### 5. Ice Atom Normalization (3→4 atoms) (MEDIUM RISK)
Ice molecules stored as 3 atoms (O, H, H) are expanded to 4 atoms (OW, HW1, HW2, MW) at export time. The MW virtual site position is computed using `compute_mw_position()`. Tests must account for this expansion when checking atom counts in .gro files:
- Input: `nmol * 3` atoms
- Output: `nmol * 4` atoms

### 6. CustomMoleculeStructure.itp_path Must Exist (MEDIUM RISK)
`custom_structure.itp_path.read_text()` is called directly (line 221 of export.py). If `itp_path` is `None` or points to a nonexistent file, the export crashes. For testing, either:
- Use `quickice/data/custom/etoh.itp` (exists in the repo)
- Create a temporary .itp file in the test

### 7. comment_out_atomtypes_in_itp Modifies ITP Content (LOW RISK)
The `comment_out_atomtypes_in_itp()` function is applied to custom .itp and solute .itp files before writing. This means the output .itp files are NOT identical to the source — the `[atomtypes]` section is commented out. Tests must verify the modified content, not the original.

### 8. Ion ITP is Generated, Not Copied (LOW RISK)
`IonGROMACSExporter` generates `ion.itp` via `write_ion_itp()`, unlike all other .itp files which are copied or modified copies. The generated file contains NA and CL moleculetype sections with Madrid2019 parameters.

### 9. GRO Format Number Wrapping (LOW RISK)
For systems with >99999 atoms, atom and residue numbers wrap at 100000 (GROMACS convention). For test fixtures with small systems, this won't be an issue, but it's worth noting for large-scale tests.

### 10. Triclinic Cell Vectors in .gro/.top (LOW RISK)
Box vectors are written in GROMACS triclinic format (9 values) even for orthogonal cells. The .gro file has `cell[0,0] cell[1,1] cell[2,2] cell[0,1] cell[0,2] cell[1,0] cell[1,2] cell[2,0] cell[2,1]`. For orthogonal cells, off-diagonal elements are 0.

---

## Writer Function Summary (for reference)

| Function | Signature | Writes To | Input Structure |
|----------|-----------|-----------|-----------------|
| `write_gro_file` | `(candidate, filepath)` | .gro | Candidate |
| `write_top_file` | `(candidate, filepath)` | .top | Candidate |
| `write_interface_gro_file` | `(iface, filepath)` | .gro | InterfaceStructure |
| `write_interface_top_file` | `(iface, filepath)` | .top | InterfaceStructure |
| `write_multi_molecule_gro_file` | `(positions, molecule_index, cell, filepath, title, atom_names)` | .gro | Raw data |
| `write_multi_molecule_top_file` | `(molecule_index, filepath, system_name, itp_files, registry)` | .top | Raw data |
| `write_ion_gro_file` | `(ion_structure, filepath)` | .gro | IonStructure |
| `write_ion_top_file` | `(ion_structure, filepath)` | .top | IonStructure |
| `write_custom_molecule_gro_file` | `(custom_structure, filepath)` | .gro | CustomMoleculeStructure |
| `write_custom_molecule_top_file` | `(custom_structure, filepath)` | .top | CustomMoleculeStructure |
| `write_solute_gro_file` | `(solute_structure, filepath)` | .gro | SoluteStructure |
| `write_solute_top_file` | `(solute_structure, filepath)` | .top | SoluteStructure |
| `write_ion_itp` | `(output_path, na_count, cl_count)` | ion.itp | Raw counts |

## Sources

### Primary (HIGH confidence)
- `quickice/gui/export.py` — 927 lines, all 5 non-hydrate exporters read directly
- `quickice/gui/hydrate_export.py` — 192 lines, hydrate exporter read directly
- `quickice/structure_generation/types.py` — 718 lines, all dataclasses read directly
- `quickice/output/gromacs_writer.py` — 2557 lines, all writer functions read directly
- `quickice/structure_generation/gromacs_ion_export.py` — 163 lines, ion ITP generation read directly
- `quickice/structure_generation/moleculetype_registry.py` — 166 lines, registry read directly
- `quickice/ranking/types.py` — 58 lines, RankedCandidate read directly
- `quickice/data/` — verified all .itp files exist

### Secondary (MEDIUM confidence)
- `tests/test_output/test_pdb_writer.py` — existing test patterns for writer testing
- `tests/test_output/test_molecule_wrapping.py` — existing test patterns for molecule index
- `tests/test_gromacs_molecule_ordering.py` — existing test patterns for GRO parsing
- `tests/test_custom_molecule.py` — existing mock interface construction pattern
- `tests/test_custom_molecule_panel_34_6.py` — existing mock interface construction pattern

## Metadata

**Confidence breakdown:**
- Exporter class tracing: HIGH — all source files read directly, line numbers documented
- Writer function signatures: HIGH — all 13 writer functions traced from source
- Data structure fields: HIGH — all dataclasses read from source with field analysis
- Chain dependencies: HIGH — verified by reading code paths
- External dependencies: HIGH — verified data files exist, GenIce2/IAPWS not needed
- Mock patterns: MEDIUM — inferred from codebase patterns, no existing export test examples
- Risk areas: MEDIUM — based on code analysis, some edge cases may be undiscovered

**Research date:** 2026-05-22
**Valid until:** 2026-06-22 (30 days — stable codebase)
