# Architecture: Pre-built Small Molecules for GROMACS

**Project:** QuickIce — Pre-built small molecule library + AMBER→GROMACS converter
**Researched:** 2026-06-12
**Confidence:** HIGH (based on direct codebase analysis of all integration points)

---

## 1. Component Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                        PHASE 1: Converter                           │
│                                                                      │
│  phenix/geostd     ┌─────────────────────┐     ┌───────────────┐    │
│  .mol2 + .frcmod ──► amber_to_gromacs()  ├────► .gro + .itp    │    │
│                     │  (pure Python)      │     │  (GROMACS)    │    │
│  gaff2.dat ────────►│  numpy + networkx   │     │               │    │
│  (bundled params)   └─────────────────────┘     └──────┬────────┘    │
│                                                             │         │
└─────────────────────────────────────────────────────────────┼─────────┘
                                                              │
                        ┌─────────────────────────────────────┘
                        ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     PHASE 2: Molecule Bundle                        │
│                                                                      │
│  quickice/data/molecules/                                           │
│  ├── index.json              ← molecule metadata (search/filter)    │
│  ├── gases/                                                          │
│  │   ├── ch4.gro + ch4.itp   ← replaces quickice/data/ch4.itp     │
│  │   ├── n2.gro + n2.itp     ← manually created                    │
│  │   └── xe.gro + xe.itp     ← manually created                    │
│  ├── solvents/                                                        │
│  │   ├── etoh.gro + etoh.itp ← replaces quickice/data/custom/      │
│  │   └── dms.gro + dms.itp                                           │
│  ├── hydrate_guests/                                                  │
│  │   └── ... (curated from geostd)                                   │
│  ├── alkanes/                                                          │
│  │   └── ... (ethane, propane, ...)                                   │
│  └── drug_like/                                                        │
│      └── ... (small drug molecules)                                   │
│                                                                      │
│  NOTE: .itp files use COMMENTED [atomtypes] convention              │
│  (matching ch4.itp, thf.itp, ch4_hydrate.itp)                       │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     PHASE 3: GUI Integration                        │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐      │
│  │  CustomMoleculePanel (existing, modified)                 │      │
│  │                                                            │      │
│  │  ┌─────────────────────────┐  ┌────────────────────────┐  │      │
│  │  │ File Upload Group        │  │ Molecule Library Group  │  │      │
│  │  │                         │  │  (NEW)                  │  │      │
│  │  │ [Upload .gro] [Upload   │  │ [Search...] ──────┐    │  │      │
│  │  │  .itp]                 │  │ Category: [All ▾]  │    │  │      │
│  │  └─────────────────────────┘  │ ┌─────────────────┤    │  │      │
│  │                                │ │ QListView        │    │  │      │
│  │  OR: Select from library ────►│ │ (filtered)       │    │  │      │
│  │                                │ └─────────────────┘    │  │      │
│  │                                │ [Preview] [Select]     │  │      │
│  │                                └────────────────────────┘  │      │
│  │                                                            │      │
│  │  → Selected molecule sets gro_path + itp_path             │      │
│  │  → Existing validation + placement flow UNCHANGED         │      │
│  └────────────────────────────────────────────────────────────┘      │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────────────┐
│                   PHASE 4: Export Pipeline                          │
│                                                                      │
│  CustomMoleculeGROMACSExporter (existing, UNCHANGED)               │
│  ├── write_custom_molecule_gro_file()                               │
│  ├── write_custom_molecule_top_file()                               │
│  │   ├── parse_itp_atomtypes() → extracts atom types from ITP      │
│  │   └── deduplication (Bug 3 fix pattern)                         │
│  ├── comment_out_atomtypes_in_itp() → on ITP copy to output dir     │
│  └── copy tip4p-ice.itp, guest.itp to output dir                    │
│                                                                      │
│  Pre-built .itp files already have atomtypes commented              │
│  → parse_itp_atomtypes() returns empty                               │
│  → SOLUTION: Bundled ITPs use ACTIVE [atomtypes] (like etoh.itp)    │
│     and comment_out_atomtypes_in_itp() handles the rest             │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 2. File Organization

### 2.1 New Directory Structure

```
quickice/
├── converters/                          # NEW PACKAGE
│   ├── __init__.py
│   ├── amber_to_gromacs.py              # Core converter (~1200 LOC)
│   ├── mol2_parser.py                   # MOL2 file parser (~200 LOC)
│   ├── frcmod_parser.py                 # FRCMOD file parser (~150 LOC)
│   ├── gaff2_params.py                  # Bundled GAFF2 parameter table (~300 LOC)
│   ├── gromacs_writer.py                # GRO/ITP writer (local, not the export one) (~250 LOC)
│   ├── converters.py                    # CLI batch converter script (~100 LOC)
│   └── README.md                        # Converter usage docs
│
├── data/
│   ├── molecules/                        # NEW: Pre-built molecule bundle
│   │   ├── index.json                    # Molecule library index
│   │   ├── ATTRIBUTION.md               # BSD-3-Clause + citation notice
│   │   ├── gases/
│   │   │   ├── ch4.gro
│   │   │   ├── ch4.itp
│   │   │   ├── n2.gro
│   │   │   ├── n2.itp
│   │   │   ├── xe.gro
│   │   │   ├── xe.itp
│   │   │   ├── ar.gro
│   │   │   ├── ar.itp
│   │   │   └── kr.gro + kr.itp
│   │   ├── solvents/
│   │   │   ├── etoh.gro + etoh.itp
│   │   │   ├── dms.gro + dms.itp
│   │   │   └── ...
│   │   ├── hydrate_guests/
│   │   │   └── ... (curated from geostd)
│   │   ├── alkanes/
│   │   │   └── ...
│   │   └── drug_like/
│   │       └── ...
│   │
│   ├── ch4.itp              # KEEP (backward compat — symlink or copy from molecules/gases/)
│   ├── thf.itp              # KEEP (backward compat)
│   ├── ch4_hydrate.itp      # KEEP (hydrate-specific ITP, different moleculetype name)
│   ├── thf_hydrate.itp      # KEEP
│   ├── ch4_liquid.itp       # KEEP (solute-specific ITP)
│   ├── thf_liquid.itp       # KEEP
│   ├── tip4p-ice.itp        # KEEP (water model)
│   ├── tip4p.gro            # KEEP (water template)
│   └── custom/              # KEEP (example custom molecule directory)
│
├── gui/
│   ├── custom_molecule_panel.py         # MODIFY: add library browse
│   ├── molecule_library_dialog.py       # NEW: search/filter dialog (~300 LOC)
│   ├── molecule_library_model.py        # NEW: Qt model for filtered list (~150 LOC)
│   └── ...
│
├── structure_generation/
│   ├── molecule_library.py              # NEW: programmatic library access (~200 LOC)
│   ├── types.py                         # MODIFY: add library molecule dataclass
│   └── ...                              # (existing modules unchanged)
│
└── output/
    └── gromacs_writer.py                # MINOR: add library-aware atomtype lookup
```

### 2.2 Rationale for `converters/` Package (NOT `structure_generation/`)

The converter is a **build-time tool**, not a runtime dependency:
- Used offline to generate the molecule bundle from phenix geostd sources
- The GUI and structure generation pipeline only consume the pre-built `.gro`/`.itp` files
- Separating it avoids circular conceptual dependencies
- Can be tested independently
- Can be invoked from CLI: `python -m quickice.converters --source geostd/ --output data/molecules/`

### 2.3 Rationale for `data/molecules/` (Bundled with Install)

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| Bundled in `data/molecules/` | Zero network dependency, instant access, simple `import quickice` path resolution, matches existing `data/tip4p.gro` pattern | ~1-2 MB package bloat | **RECOMMENDED** |
| On-demand download | Smaller install | Network dependency, cache management complexity, UX friction | Rejected |
| User-side cache | Flexible | Requires download infrastructure, stale cache issues | Rejected |

**Recommendation:** Bundle with install. 1-2 MB is negligible. The existing codebase already uses `Path(quickice.__file__).parent / "data"` for runtime data access — just extend this to `data/molecules/`.

---

## 3. Data Model

### 3.1 Molecule Library Index (`index.json`)

```json
{
  "version": 1,
  "description": "QuickIce pre-built small molecule library for GROMACS",
  "source": "phenix geostd (BSD-3-Clause) + manual creation",
  "molecules": {
    "ch4": {
      "name": "Methane",
      "formula": "CH₄",
      "molecular_weight": 16.04,
      "smiles": "C",
      "category": "gases",
      "atom_count": 5,
      "source": "manual",
      "pdb_code": null,
      "residue_name": "CH4",
      "atom_types": ["c3", "hc", "hc", "hc", "hc"],
      "penalty_score": 0,
      "notes": "Standard hydrate guest molecule"
    },
    "etoh": {
      "name": "Ethanol",
      "formula": "C₂H₆O",
      "molecular_weight": 46.07,
      "smiles": "CCO",
      "category": "solvents",
      "atom_count": 9,
      "source": "geostd",
      "pdb_code": "EOH",
      "residue_name": "MOL",
      "atom_types": ["hc", "c3", "hc", "hc", "c3", "h1", "h1", "oh", "ho"],
      "penalty_score": 0,
      "notes": "Common solvent/co-solute"
    },
    "n2": {
      "name": "Dinitrogen",
      "formula": "N₂",
      "molecular_weight": 28.01,
      "smiles": "N#N",
      "category": "gases",
      "atom_count": 2,
      "source": "manual",
      "pdb_code": null,
      "residue_name": "N2",
      "atom_types": ["n2", "n2"],
      "penalty_score": 0,
      "notes": "Simple gas, absent from geostd"
    }
  }
}
```

**Why JSON over Python dict or YAML:**

| Format | Load Time | Tool Access | Editability | Verdict |
|--------|-----------|-------------|-------------|---------|
| Python dict literal | Fastest (import) | No external tools | Poor | Rejected — hard to maintain 150 entries |
| JSON | Fast (`json.loads`) | jq, python, JS | OK | **RECOMMENDED** |
| YAML | Slow (PyYAML dep) | yq | Best | Rejected — adds dependency, slow for 150 entries |
| SQLite | Fast queries | sqlite3 CLI | Poor | Rejected — overkill for 150 entries, binary file |

**JSON rationale:**
- 150 entries × ~200 bytes = ~30 KB index — `json.loads()` is <1ms
- No additional dependency (stdlib `json`)
- Can be validated with JSON Schema
- Works with `jq`, Python, JavaScript, any text tool
- Compatible with Qt model (QJsonDocument → QVariantMap)

### 3.2 Molecule Library Dataclass

```python
@dataclass
class MoleculeLibraryEntry:
    """Single molecule entry from the pre-built library.
    
    Attributes:
        code: Short identifier (e.g., "ch4", "etoh", "n2") — matches filename stem
        name: Human-readable name (e.g., "Methane", "Ethanol")
        formula: Chemical formula with subscripts (e.g., "CH₄", "C₂H₆O")
        molecular_weight: Molecular weight in g/mol
        smiles: SMILES string for structure representation
        category: Category for filtering (e.g., "gases", "solvents", "hydrate_guests")
        atom_count: Number of atoms in molecule
        source: Data provenance ("geostd" or "manual")
        pdb_code: PDB Chemical Component Dictionary code (null if manual)
        residue_name: Default residue name in ITP file
        atom_types: List of GAFF2 atom type names
        penalty_score: Conversion penalty score (0=perfect, >6=needs review)
        notes: Additional notes
    """
    code: str
    name: str
    formula: str
    molecular_weight: float
    smiles: str
    category: str
    atom_count: int
    source: str
    pdb_code: str | None
    residue_name: str
    atom_types: list[str]
    penalty_score: int
    notes: str = ""
```

### 3.3 Category Taxonomy

```python
MOLECULE_CATEGORIES = {
    "gases": {
        "display_name": "Simple Gases",
        "description": "Small gas molecules (hydrate guests, atmosphere)",
        "examples": "CH₄, N₂, Xe, Ar, Kr, CO₂, H₂, O₂",
    },
    "solvents": {
        "display_name": "Solvents",
        "description": "Common laboratory solvents",
        "examples": "Ethanol, DMSO, Acetone, THF",
    },
    "hydrate_guests": {
        "display_name": "Hydrate Guests",
        "description": "Molecules known to occupy hydrate cages",
        "examples": "Ethane, Propane, Cyclopentane, TBT",
    },
    "alkanes": {
        "display_name": "Alkanes",
        "description": "Linear and cyclic alkanes",
        "examples": "Ethane, Propane, Butane, Cyclohexane",
    },
    "amino_acid_fragments": {
        "display_name": "Amino Acid Fragments",
        "description": "Small fragments from amino acids",
        "examples": "Acetate, Methylammonium, Imidazole",
    },
    "drug_like": {
        "display_name": "Drug-like Molecules",
        "description": "Small drug molecules",
        "examples": "Aspirin, Ibuprofen, Caffeine",
    },
    "ions": {
        "display_name": "Ions",
        "description": "Monoatomic and polyatomic ions",
        "examples": "Na⁺, Cl⁻, SO₄²⁻",
    },
}
```

---

## 4. ITP Convention: CRITICAL DESIGN DECISION

### 4.1 The Two-Conventions Problem

The existing codebase has **two ITP conventions**:

| File | [atomtypes] Convention | Used By |
|------|----------------------|---------|
| `ch4.itp` | **Commented out** | gromacs_writer (hardcoded atomtypes in .top) |
| `thf.itp` | **Commented out** | gromacs_writer (hardcoded atomtypes in .top) |
| `ch4_hydrate.itp` | **Commented out** | gromacs_writer (hardcoded atomtypes in .top) |
| `etoh.itp` | **Active/inline** | gromacs_writer → `parse_itp_atomtypes()` extracts and merges |
| `etoh.top` | **Active/inline** | Standalone test topology |

### 4.2 The Export Pipeline's Atomtype Handling

The export pipeline (`write_custom_molecule_top_file()`) already handles this duality:

1. **If ITP has active `[atomtypes]`**: `parse_itp_atomtypes()` extracts them, merges into `.top` with deduplication
2. **If ITP has commented `[atomtypes]`**: `parse_itp_atomtypes()` returns empty, falls back to hardcoded types
3. **When copying ITP to output dir**: `comment_out_atomtypes_in_itp()` always comments them out

### 4.3 Recommendation: ACTIVE `[atomtypes]` in Bundled ITPs

**All new bundled ITPs should use ACTIVE `[atomtypes]` sections** (like `etoh.itp`).

**Rationale:**

1. **Self-describing**: Each ITP carries its own atomtype definitions — no hardcoded lookup table needed
2. **Scalability**: With 100-150 molecules using 30+ GAFF2 atom types, maintaining a hardcoded table in `gromacs_writer.py` is unsustainable
3. **Existing pipeline already handles it**: `parse_itp_atomtypes()` + deduplication (Bug 3 fix) + `comment_out_atomtypes_in_itp()` work correctly
4. **No changes to export code**: The `write_custom_molecule_top_file()` path already extracts and deduplicates

**Example bundled ITP (new convention):**

```itp
; Created by QuickIce AMBER→GROMACS converter from phenix geostd
; Source: geostd/EOH (BSD-3-Clause)
; Conversion penalty: 0 (clean)

[ atomtypes ]
; name   at.num      mass       charge   ptype     sigma (nm)    epsilon (kJ/mol)
hc           1     1.007941    0.000000    A      2.600177E-01    8.702720E-02
c3           6    12.010736    0.000000    A      3.397710E-01    4.510352E-01
h1           1     1.007941    0.000000    A      2.421997E-01    8.702720E-02
oh           8    15.999405    0.000000    A      3.242871E-01    3.891120E-01
ho           1     1.007941    0.000000    A      5.379246E-02    1.966480E-02

[ moleculetype ]
; name          nrexcl
etoh       3

[ atoms ]
;  Index   type   residue  resname   atom         cgnr     charge       mass
     1     hc         1      MOL     H              1    0.05772791    1.007941
...
```

### 4.4 Migration Path for Existing ITPs

The existing `ch4.itp`, `thf.itp` files with commented atomtypes can stay as-is for backward compatibility. The `gromacs_writer.py` hardcoded atomtype table for CH4/THF still works. Over time, migrate to active atomtypes when convenient.

**No breaking changes required.**

---

## 5. Converter Architecture

### 5.1 API Design

```python
def amber_to_gromacs(
    mol2_path: Path,
    frcmod_path: Path | None = None,
    gaff2_params: dict | None = None,
    residue_name: str | None = None,
    penalty_threshold: float = 10.0,
) -> ConversionResult:
    """Convert AMBER format molecule to GROMACS format.
    
    Pure Python converter. Uses only numpy, networkx, and stdlib.
    
    Args:
        mol2_path: Path to AMBER .mol2 file (must have @<TRIPOS>ATOM section)
        frcmod_path: Path to AMBER .frcmod file (overrides for specific params).
                     If None, uses only GAFF2 defaults from bundled table.
        gaff2_params: Pre-loaded GAFF2 parameter dict. If None, loads default.
        residue_name: Override residue name in output. If None, uses mol2 residue.
        penalty_threshold: Max allowed penalty score. Raises if exceeded.
    
    Returns:
        ConversionResult with gro_content, itp_content, atomtypes_content,
        metadata (penalty scores, warnings, atom types used)
    
    Raises:
        ConversionError: On missing parameters (ATTN entries) or 
                         penalty exceeding threshold
        ValueError: On invalid mol2/frcmod format
    
    Dependencies:
        - numpy: matrix math for GRO coordinates
        - networkx: graph traversal for 1-4 pairs generation
        - stdlib: file I/O, string parsing
    """
```

### 5.2 ConversionResult Dataclass

```python
@dataclass
class ConversionResult:
    """Result of AMBER→GROMACS conversion.
    
    Attributes:
        gro_content: String content for .gro file (GROMACS coordinates)
        itp_content: String content for .itp file (molecule topology)
        atomtypes_content: String content for [atomtypes] section
        molecule_name: Molecule name from [moleculetype] section
        residue_name: Residue name used in output
        atom_types: List of GAFF2 atom type names used
        atom_count: Number of atoms
        penalty_score: Maximum penalty score across all parameters
        warnings: List of non-fatal warnings (e.g., "missing dihedral")
        missing_params: List of (param_type, atom_types) tuples for ATTENTION entries
    """
    gro_content: str
    itp_content: str
    atomtypes_content: str
    molecule_name: str
    residue_name: str
    atom_types: list[str]
    atom_count: int
    penalty_score: float
    warnings: list[str]
    missing_params: list[tuple[str, str]]
```

### 5.3 Module Decomposition

```
quickice/converters/
├── amber_to_gromacs.py     # Main entry point + orchestration
│   ├── amber_to_gromacs()  # Top-level function
│   ├── _convert_bonds()    # Bond parameter lookup + unit conversion
│   ├── _convert_angles()   # Angle parameter lookup + unit conversion  
│   ├── _convert_dihedrals()# Dihedral parameter lookup + multi-term handling
│   ├── _convert_impropers()# Improper parameter lookup + wildcard expansion
│   ├── _generate_pairs()   # 1-4 pair generation using networkx
│   └── _compute_penalty()  # Penalty score calculation
│
├── mol2_parser.py          # AMBER MOL2 file parser
│   ├── parse_mol2_file()   # Returns MOL2Data dataclass
│   └── MOL2Data            # positions, atom_names, atom_types, bonds, etc.
│
├── frcmod_parser.py        # AMBER FRCMOD file parser  
│   ├── parse_frcmod_file() # Returns FRCMODData dataclass
│   └── FRCMODData           # overrides for bonds, angles, dihedrals, impropers
│
├── gaff2_params.py         # Bundled GAFF2 parameter table
│   ├── GAFF2_BONDS: dict   # {(type1, type2): (r0_nm, k_kj)}
│   ├── GAFF2_ANGLES: dict  # {(type1, type2, type3): (a0_deg, k_kj)}
│   ├── GAFF2_DIHEDRALS: dict  # {(type1, type2, type3, type4): [(phase, kd, pn), ...]}
│   ├── GAFF2_IMPROPERS: dict  # {(type1, type2, type3, type4): (phase, kd, pn)}
│   ├── GAFF2_ATOMTYPES: dict  # {type_name: (at_num, mass, sigma_nm, epsilon_kj)}
│   └── load_gaff2_params() # Returns combined dict
│
├── gromacs_writer.py       # GRO/ITP string writers (local to converter)
│   ├── write_gro_string()  # Positions + atom_names → GRO format string
│   ├── write_itp_string()  # Topology sections → ITP format string
│   └── write_atomtypes_string() # Atom type definitions → string
│
└── converters.py           # CLI batch converter
    └── main()              # argparse + batch conversion loop
```

### 5.4 GAFF2 Parameter Table Design

**Storage format: Python dict literal in `gaff2_params.py`**

**Rationale over alternatives:**

| Format | Load Time | Maintainability | Verdict |
|--------|-----------|----------------|---------|
| Python dict literal | Fastest (import) | Good (IDE support) | **RECOMMENDED** |
| JSON file | Fast | Good | Rejected — adds I/O, same structure |
| Text parsing at runtime | Slow | Poor | Rejected — fragile |
| Hardcoded in converter | Fast | Poor coupling | Rejected — mixes data and logic |

**Structure:**

```python
# quickice/converters/gaff2_params.py

# Bond parameters: AMBER atom types → (r0 in Å, k in kcal/mol/Å²)
# Conversion: r0_nm = r0_angstrom / 10, k_kj = k_kcal * 4184 * 100
GAFF2_BONDS: dict[tuple[str, str], tuple[float, float]] = {
    ("c3", "hc"): (1.0962, 342.0),    # C-H aliphatic
    ("c3", "c3"): (1.5354, 227.1),    # C-C single
    ("c3", "oh"): (1.4242, 283.3),    # C-O alcohol
    ("oh", "ho"): (0.9725, 533.2),    # O-H alcohol
    ("c5", "os"): (1.4346, 274.1),    # C-O ether
    # ... ~200 entries total from gaff2.dat
}

# Angle parameters: AMBER atom types → (a0 in degrees, k in kcal/mol/rad²)
# Conversion: k_kj = k_kcal * 4184
GAFF2_ANGLES: dict[tuple[str, str, str], tuple[float, float]] = {
    ("hc", "c3", "hc"): (107.73, 71.57),    # H-C-H
    ("c3", "c3", "hc"): (109.68, 86.45),    # C-C-H
    ("c3", "c3", "oh"): (109.66, 153.81),   # C-C-O
    # ... ~300 entries total
}

# Dihedral parameters: multi-term dihedrals
# Each entry is a list of (phase_deg, kd_kcal, pn) tuples
# GROMACS convention: func type 9, each term becomes separate line
GAFF2_DIHEDRALS: dict[tuple[str, ...], list[tuple[float, float, int]]] = {
    ("X", "c3", "c3", "X"): [(0.0, 0.1551, 3)],   # X-c3-c3-X (single term)
    ("hc", "c3", "c3", "oh"): [(0.0, 0.0897, 3)],  # hc-c3-c3-oh
    # ... ~500 entries total
}

# Atom type LJ parameters: sigma in nm, epsilon in kJ/mol
# Pre-converted from AMBER (Rmin/2 → sigma, ε → epsilon)
GAFF2_ATOMTYPES: dict[str, tuple[int, float, float, float]] = {
    # type: (atomic_number, mass_gmol, sigma_nm, epsilon_kjmol)
    "c3":  (6, 12.010736, 3.39771e-01, 4.51035e-01),
    "hc":  (1, 1.007941,  2.60018e-01, 8.70272e-02),
    "oh":  (8, 15.999405, 3.24287e-01, 3.89112e-01),
    "ho":  (1, 1.007941,  5.37925e-02, 1.96648e-02),
    # ... ~70 entries total
}
```

### 5.5 Unit Conversion Constants

```python
# AMBER → GROMACS unit conversions
AMBER_TO_GROMACS = {
    "length": 0.1,          # Å → nm (divide by 10)
    "bond_k": 4184 * 100,  # kcal/mol/Å² → kJ/mol/nm² (× 4184 × 100)
    "angle_k": 4184,        # kcal/mol/rad² → kJ/mol/rad² (× 4184)
    "dihedral_k": 4184,     # kcal/mol → kJ/mol (× 4184)
    "improper_k": 4184,     # kcal/mol → kJ/mol (× 4184)
    "lJ_epsilon": 4.184,    # kcal/mol → kJ/mol (× 4.184)
    "lJ_Rmin_to_sigma": 2**(1/6) * 2,  # Rmin/2 → sigma conversion factor
}
```

### 5.6 Pairs Generation (1-4 Interactions)

**Algorithm using networkx:**

```python
def _generate_pairs(bonds: list[tuple[int, int]], n_atoms: int) -> list[tuple[int, int]]:
    """Generate 1-4 pair list from bond connectivity.
    
    Uses networkx to find shortest paths. A 1-4 pair is two atoms
    separated by exactly 3 bonds (path length 4), excluding those
    that are also 1-2 (bonded) or 1-3 (angle).
    
    Args:
        bonds: List of (atom_i, atom_j) bond pairs (0-indexed)
        n_atoms: Total number of atoms
    
    Returns:
        List of (atom_i, atom_j) 1-4 pairs
    """
    import networkx as nx
    
    G = nx.Graph()
    G.add_nodes_from(range(n_atoms))
    G.add_edges_from(bonds)
    
    pairs = []
    for node in range(n_atoms):
        # Get all nodes at distance 3 (exactly 3 bonds away)
        for target in nx.single_source_shortest_path_length(G, node, cutoff=3):
            if nx.shortest_path_length(G, node, target) == 3 and node < target:
                pairs.append((node + 1, target + 1))  # 1-indexed for GROMACS
    
    return sorted(pairs)
```

### 5.7 Dihedral Multi-Term Convention

**AMBER convention:** Single dihedral with multiple terms (func type 9 in GROMACS):
```
; In .itp: each term is a separate line with same atom indices
    1   2   5   6    9    0.000    0.65084    3   ; X-c3-c3-X term 1
    1   2   5   6    9    0.000    0.15510    1   ; X-c3-c3-X term 2
```

**Wildcard matching:** `X` in AMBER matches any atom type. Must expand to all matching type quadruplets in the molecule.

```python
def _expand_wildcard_dihedral(
    dihedral_key: tuple[str, ...],
    molecule_atom_types: list[str]
) -> list[tuple[str, ...]]:
    """Expand AMBER wildcard dihedrals (X) to concrete type quadruplets.
    
    AMBER uses 'X' as wildcard in dihedrals like (X, c3, c3, X).
    This means any atom type is valid in the X positions.
    GROMACS requires explicit type quadruplets.
    
    Returns only quadruplets that actually appear in the molecule.
    """
    expanded = []
    for i, t1 in enumerate(molecule_atom_types):
        for j, t2 in enumerate(molecule_atom_types):
            for k, t3 in enumerate(molecule_atom_types):
                for l, t4 in enumerate(molecule_atom_types):
                    if (dihedral_key[0] in ('X', t1) and
                        dihedral_key[1] in ('X', t2) and
                        dihedral_key[2] in ('X', t3) and
                        dihedral_key[3] in ('X', t4)):
                        expanded.append((t1, t2, t3, t4))
    # Deduplicate
    return list(set(expanded))
```

### 5.8 Error Handling Strategy

```python
class ConversionError(Exception):
    """Raised when conversion cannot proceed.
    
    Attributes:
        message: Human-readable error
        missing_params: List of missing parameter descriptions
        penalty_score: Total penalty score
    """
    def __init__(self, message: str, missing_params: list[str] = None, 
                 penalty_score: float = 0.0):
        self.missing_params = missing_params or []
        self.penalty_score = penalty_score
        super().__init__(message)
```

**Penalty score handling:**
- Score 0: Perfect match (all params found in GAFF2 defaults)
- Score 1-6: Good (minor deviations, common for complex molecules)
- Score 7-10: Review recommended (some params approximated)
- Score >10: Likely problematic (missing critical parameters)

**"ATTN" entries:** Parameters marked `ATTN` in AMBER output indicate completely missing force field terms. These should:
1. Raise `ConversionError` if `penalty_threshold` is exceeded
2. Be logged as `missing_params` in `ConversionResult`
3. Be written as comments in the ITP file with `; ATTENTION: missing parameter` markers

---

## 6. GUI Integration

### 6.1 Molecule Library Dialog

**New file:** `quickice/gui/molecule_library_dialog.py`

```
┌──────────────────────────────────────────────────────────────┐
│  Molecule Library                                    [X]     │
├──────────────────────────────────────────────────────────────┤
│  Search: [________________________]                          │
│                                                              │
│  Category: [All Categories  ▾]                               │
│                                                              │
│  ┌────────────┬──────────┬─────────┬────────┬────────┐       │
│  │ Name       │ Formula  │ Atoms   │ MW     │ Source│       │
│  ├────────────┼──────────┼─────────┼────────┼────────┤       │
│  │ Methane    │ CH₄      │ 5       │ 16.04  │ manual│       │
│  │ Ethanol    │ C₂H₆O   │ 9       │ 46.07  │geostd │       │
│  │ Dinitrogen │ N₂       │ 2       │ 28.01  │ manual│       │
│  │ ...        │ ...      │ ...     │ ...    │ ...   │       │
│  └────────────┴──────────┴─────────┴────────┴────────┘       │
│                                                              │
│  ┌─ Preview ──────────────────────────────────────────┐      │
│  │  Molecule: Ethanol (etoh)                          │      │
│  │  Formula: C₂H₆O    MW: 46.07 g/mol               │      │
│  │  SMILES: CCO                                      │      │
│  │  Atom types: hc, c3, hc, hc, c3, h1, h1, oh, ho  │      │
│  │  Category: solvents                               │      │
│  │  Source: geostd (PDB: EOH)                        │      │
│  │  Penalty: 0 (clean)                               │      │
│  └────────────────────────────────────────────────────┘      │
│                                                              │
│              [Select]  [Cancel]                              │
└──────────────────────────────────────────────────────────────┘
```

### 6.2 Integration with CustomMoleculePanel

**Modified flow in `custom_molecule_panel.py`:**

```python
# In _create_file_upload_group(), add "or Browse Library" link:

def _create_file_upload_group(self) -> QGroupBox:
    group = QGroupBox("Molecule Source")
    layout = QVBoxLayout()
    
    # Source mode selector (NEW)
    source_row = QHBoxLayout()
    self.source_mode_combo = QComboBox()
    self.source_mode_combo.addItems(["Upload Files", "Browse Library"])
    self.source_mode_combo.setToolTip(
        "Select molecule source:\n"
        "• Upload Files — Manually provide .gro and .itp files\n"
        "• Browse Library — Select from pre-built molecule library"
    )
    source_row.addWidget(self.source_mode_combo)
    source_row.addStretch()
    layout.addLayout(source_row)
    
    # Upload widgets (shown when "Upload Files" selected)
    self.upload_widget = self._create_upload_widgets()
    layout.addWidget(self.upload_widget)
    
    # Library browse widgets (shown when "Browse Library" selected)
    self.library_widget = self._create_library_widgets()
    self.library_widget.setVisible(False)
    layout.addWidget(self.library_widget)
    
    group.setLayout(layout)
    return group

def _create_library_widgets(self) -> QWidget:
    """Create library browse/search widget."""
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    
    # Browse button
    browse_row = QHBoxLayout()
    self.library_browse_button = QPushButton("Browse Molecule Library")
    self.library_browse_button.setToolTip(
        "Browse pre-built molecules for GROMACS\n"
        "Includes: gases, solvents, hydrate guests, alkanes, etc."
    )
    browse_row.addWidget(self.library_browse_button)
    browse_row.addStretch()
    layout.addLayout(browse_row)
    
    # Selected molecule info (hidden initially)
    self.library_info_widget = QWidget()
    info_layout = QFormLayout(self.library_info_widget)
    info_layout.setContentsMargins(0, 0, 0, 0)
    self.library_info_widget.setVisible(False)
    
    self.library_name_label = QLabel("--")
    self.library_formula_label = QLabel("--")
    self.library_atoms_label = QLabel("--")
    
    info_layout.addRow("Name:", self.library_name_label)
    info_layout.addRow("Formula:", self.library_formula_label)
    info_layout.addRow("Atoms:", self.library_atoms_label)
    layout.addWidget(self.library_info_widget)
    
    return widget

def _on_source_mode_changed(self, mode: str):
    """Handle source mode switching (Upload Files vs Browse Library)."""
    is_upload = (mode == "Upload Files")
    self.upload_widget.setVisible(is_upload)
    self.library_widget.setVisible(not is_upload)
    self.log_message(f"Switched to {mode} mode")
```

### 6.3 Signal/Slot Connections

```python
def _setup_connections(self):
    # ... existing connections ...
    
    # NEW: Source mode switching
    self.source_mode_combo.currentTextChanged.connect(self._on_source_mode_changed)
    
    # NEW: Library browse button
    self.library_browse_button.clicked.connect(self._browse_library)

def _browse_library(self):
    """Open molecule library dialog and handle selection."""
    from quickice.gui.molecule_library_dialog import MoleculeLibraryDialog
    
    dialog = MoleculeLibraryDialog(self)
    if dialog.exec() == QDialog.Accepted:
        selected = dialog.get_selected_molecule()
        if selected:
            self._load_library_molecule(selected)

def _load_library_molecule(self, entry: MoleculeLibraryEntry):
    """Load a molecule from the library into the panel.
    
    Sets gro_path and itp_path to bundled file paths,
    then triggers the existing validation flow.
    """
    from quickice.structure_generation.molecule_library import get_molecule_paths
    
    gro_path, itp_path = get_molecule_paths(entry.code)
    
    # Set paths (same as manual upload, but from bundled files)
    self.gro_path = gro_path
    self.itp_path = itp_path
    
    # Update status labels
    self.gro_status.setText(f"Library: {entry.name} ({gro_path.name})")
    self.gro_status.setStyleSheet("color: green;")
    self.itp_status.setText(f"Library: {entry.name} ({itp_path.name})")
    self.itp_status.setStyleSheet("color: green;")
    
    # Update library info
    self.library_name_label.setText(entry.name)
    self.library_formula_label.setText(entry.formula)
    self.library_atoms_label.setText(f"{entry.atom_count} atoms")
    self.library_info_widget.setVisible(True)
    
    # Trigger validation (reuses existing flow)
    try:
        from quickice.structure_generation.itp_parser import parse_itp_file
        self.itp_info = parse_itp_file(itp_path)
        self._validate_files()
    except Exception as e:
        self.itp_status.setText(f"Error: {e}")
        self.itp_status.setStyleSheet("color: red;")
    
    self.log_message(f"Selected from library: {entry.name} ({entry.formula})")
```

### 6.4 MoleculeLibraryDialog Implementation

```python
class MoleculeLibraryDialog(QDialog):
    """Dialog for browsing and selecting pre-built molecules.
    
    Features:
    - Text search by name, formula, SMILES, PDB code
    - Category filter dropdown
    - Sortable QTableView with QSortFilterProxyModel
    - Preview panel showing selected molecule details
    - Double-click or Select button to confirm
    
    Signals: None (modal dialog, returns selection via get_selected_molecule())
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Molecule Library")
        self.setMinimumSize(700, 500)
        self._selected_code = None
        self._setup_ui()
        self._load_library()
    
    def get_selected_molecule(self) -> MoleculeLibraryEntry | None:
        """Return the selected molecule entry after dialog closes."""
        if self._selected_code is None:
            return None
        return self._library.get_molecule(self._selected_code)
```

### 6.5 CustomMoleculeConfig Compatibility

**No changes needed to CustomMoleculeConfig.** The existing dataclass already has `gro_path: Path` and `itp_path: Path` fields. When a library molecule is selected, these simply point to the bundled files instead of user-uploaded files. The downstream `CustomMoleculeInserter`, `CustomMoleculeWorker`, and export pipeline all work with `Path` objects regardless of source.

**This is the key architectural insight:** The library feature is a *source selection* mechanism, not a new pipeline. Everything after file selection remains unchanged.

---

## 7. Programmatic Library Access

**New file:** `quickice/structure_generation/molecule_library.py`

```python
"""Programmatic access to the pre-built molecule library.

Provides functions to:
- Load the molecule library index
- Search/filter molecules by name, category, formula, SMILES
- Get file paths for specific molecules
- Validate molecule availability
"""

import json
import logging
from pathlib import Path
from typing import Optional

from quickice.structure_generation.types import MoleculeLibraryEntry

logger = logging.getLogger(__name__)

# Lazy-loaded library index
_library_cache: dict | None = None


def _get_data_dir() -> Path:
    """Get the molecule library data directory.
    
    Uses the same pattern as existing code:
        Path(quickice.__file__).parent / "data" / "molecules"
    """
    import quickice
    return Path(quickice.__file__).parent / "data" / "molecules"


def _load_index() -> dict:
    """Load and cache the molecule library index from index.json.
    
    Returns:
        Parsed JSON dict with 'molecules' key
    """
    global _library_cache
    if _library_cache is not None:
        return _library_cache
    
    index_path = _get_data_dir() / "index.json"
    if not index_path.exists():
        raise FileNotFoundError(
            f"Molecule library index not found: {index_path}\n"
            "The pre-built molecule library may not be installed."
        )
    
    with open(index_path, 'r') as f:
        _library_cache = json.load(f)
    
    logger.info(f"Loaded molecule library: {len(_library_cache.get('molecules', {}))} entries")
    return _library_cache


def get_all_molecules() -> list[MoleculeLibraryEntry]:
    """Get all molecules in the library.
    
    Returns:
        List of MoleculeLibraryEntry objects
    """
    index = _load_index()
    return [
        MoleculeLibraryEntry(code=code, **data)
        for code, data in index.get('molecules', {}).items()
    ]


def search_molecules(
    query: str = "",
    category: str | None = None,
    max_atoms: int | None = None,
    min_atoms: int | None = None,
) -> list[MoleculeLibraryEntry]:
    """Search molecules with optional filters.
    
    Args:
        query: Search term (matches name, formula, SMILES, PDB code)
        category: Filter by category (e.g., "gases", "solvents")
        max_atoms: Maximum atom count filter
        min_atoms: Minimum atom count filter
    
    Returns:
        Filtered list of MoleculeLibraryEntry objects
    """
    molecules = get_all_molecules()
    
    if query:
        query_lower = query.lower()
        molecules = [
            m for m in molecules
            if (query_lower in m.name.lower() or
                query_lower in m.formula.lower() or
                query_lower in m.smiles.lower() or
                (m.pdb_code and query_lower in m.pdb_code.lower()) or
                query_lower in m.code.lower())
        ]
    
    if category:
        molecules = [m for m in molecules if m.category == category]
    
    if max_atoms is not None:
        molecules = [m for m in molecules if m.atom_count <= max_atoms]
    
    if min_atoms is not None:
        molecules = [m for m in molecules if m.atom_count >= min_atoms]
    
    return molecules


def get_molecule_paths(code: str) -> tuple[Path, Path]:
    """Get .gro and .itp file paths for a molecule.
    
    Args:
        code: Molecule code (e.g., "ch4", "etoh", "n2")
    
    Returns:
        Tuple of (gro_path, itp_path)
    
    Raises:
        KeyError: If molecule code not in library
        FileNotFoundError: If files not found on disk
    """
    index = _load_index()
    molecules = index.get('molecules', {})
    
    if code not in molecules:
        raise KeyError(f"Molecule '{code}' not found in library")
    
    data = molecules[code]
    category = data['category']
    data_dir = _get_data_dir()
    
    gro_path = data_dir / category / f"{code}.gro"
    itp_path = data_dir / category / f"{code}.itp"
    
    if not gro_path.exists():
        raise FileNotFoundError(f"GRO file not found: {gro_path}")
    if not itp_path.exists():
        raise FileNotFoundError(f"ITP file not found: {itp_path}")
    
    return gro_path, itp_path


def get_molecule(code: str) -> MoleculeLibraryEntry:
    """Get a single molecule by code.
    
    Args:
        code: Molecule code (e.g., "ch4", "etoh")
    
    Returns:
        MoleculeLibraryEntry
    
    Raises:
        KeyError: If molecule code not found
    """
    index = _load_index()
    molecules = index.get('molecules', {})
    
    if code not in molecules:
        raise KeyError(f"Molecule '{code}' not found in library")
    
    return MoleculeLibraryEntry(code=code, **molecules[code])


def get_categories() -> list[dict]:
    """Get available molecule categories.
    
    Returns:
        List of category dicts with 'name', 'display_name', 'description'
    """
    return list(MOLECULE_CATEGORIES.values())
```

---

## 8. Export Pipeline Integration

### 8.1 Existing Flow (Unchanged)

The existing `CustomMoleculeGROMACSExporter.export_custom_molecule_gromacs()` flow:

1. User clicks "Export GROMACS"
2. File dialog for `.gro` path
3. `write_custom_molecule_gro_file()` → `.gro` file
4. `write_custom_molecule_top_file()` → `.top` file with atomtypes
5. `comment_out_atomtypes_in_itp()` → copies ITP with atomtypes commented
6. Copy `tip4p-ice.itp`, guest `.itp` to output dir

### 8.2 How Pre-built Molecules Fit In

**No changes needed to the export pipeline.** When a library molecule is selected:

1. `self.gro_path` points to `quickice/data/molecules/solvents/etoh.gro`
2. `self.itp_path` points to `quickice/data/molecules/solvents/etoh.itp`
3. `CustomMoleculeConfig(gro_path=..., itp_path=...)` — same as manual upload
4. Export pipeline reads these paths, processes identically

**One subtle issue:** The export pipeline copies the ITP file to the output directory:
```python
# In CustomMoleculeGROMACSExporter.export_custom_molecule_gromacs():
itp_content = custom_structure.itp_path.read_text()
modified_content = comment_out_atomtypes_in_itp(itp_content)
custom_itp_dest = path.with_name(custom_structure.itp_path.name)
custom_itp_dest.write_text(modified_content)
```

This works perfectly for bundled ITPs with active `[atomtypes]` — `comment_out_atomtypes_in_itp()` comments them out in the copy, while the original in `data/molecules/` keeps them active for the next use.

### 8.3 Atomtype Deduplication

The existing `write_custom_molecule_top_file()` already deduplicates atomtypes:

```python
# Track written atomtype names for deduplication (Bug 3 fix)
_written_atomtypes = {"OW_ice", "HW_ice", "MW"}
# ...
if custom_structure.itp_path and custom_structure.itp_path.exists():
    custom_atomtypes = parse_itp_atomtypes(custom_structure.itp_path)
    if custom_atomtypes:
        for atomtype in custom_atomtypes:
            if len(atomtype) >= 8 and atomtype[0] not in _written_atomtypes:
                f.write(f"{atomtype[0]:<8s} ...")
                _written_atomtypes.add(atomtype[0])
```

**This handles all GAFF2 atom types across molecules correctly.** If CH4 (c3, hc) and ethanol (c3, hc, h1, oh, ho) are both present, the dedup prevents writing `c3` and `hc` twice.

### 8.4 Future: Multi-Molecule Support

Currently, only one custom molecule type can be inserted at a time. A future enhancement would allow selecting multiple molecule types. The architecture supports this because:

1. `MoleculetypeRegistry.register_custom_molecule()` already handles unique naming
2. `write_custom_molecule_top_file()` already handles multiple `[atomtypes]` sets
3. `index.json` is searchable for multiple selections

---

## 9. Dependency Analysis

### 9.1 New Dependencies

| Package | Version | Purpose | Already in QuickIce? |
|---------|---------|---------|---------------------|
| networkx | ≥2.6 | 1-4 pair generation in converter | YES (requirements.txt) |
| numpy | ≥1.20 | Matrix math in converter | YES |
| json | stdlib | Library index parsing | YES |

**No new external dependencies required.** The converter uses only what QuickIce already has.

### 9.2 What Existing Code Changes

| Module | Change Type | Scope | Risk |
|--------|------------|-------|------|
| `custom_molecule_panel.py` | **MODIFY** | Add source mode combo, library browse button, `_browse_library()`, `_load_library_molecule()` | LOW — additive changes only |
| `types.py` | **MODIFY** | Add `MoleculeLibraryEntry` dataclass | LOW — new dataclass, no existing changes |
| `gromacs_writer.py` | **NONE** | No changes needed (export pipeline handles both conventions) | NONE |
| `custom_molecule_inserter.py` | **NONE** | Works with Path objects regardless of source | NONE |
| `custom_molecule_worker.py` | **NONE** | Passes through config unchanged | NONE |
| `itp_parser.py` | **NONE** | Already handles both atomtypes conventions | NONE |
| `gro_parser.py` | **NONE** | Already handles any valid GRO file | NONE |
| `molecule_validator.py` | **NONE** | Works with any valid GRO/ITP pair | NONE |
| `moleculetype_registry.py` | **NONE** | Handles any molecule name | NONE |

### 9.3 Purely Additive (New Code)

| Module | LOC (est.) | Purpose |
|--------|------------|---------|
| `converters/amber_to_gromacs.py` | ~1200 | Core converter |
| `converters/mol2_parser.py` | ~200 | MOL2 parsing |
| `converters/frcmod_parser.py` | ~150 | FRCMOD parsing |
| `converters/gaff2_params.py` | ~300 | Parameter table |
| `converters/gromacs_writer.py` | ~250 | GRO/ITP string writing |
| `converters/converters.py` | ~100 | CLI batch tool |
| `structure_generation/molecule_library.py` | ~200 | Library access API |
| `gui/molecule_library_dialog.py` | ~300 | Search/browse dialog |
| `gui/molecule_library_model.py` | ~150 | Qt model for list |
| `data/molecules/index.json` | ~100 | Library index |
| `data/molecules/ATTRIBUTION.md` | ~30 | License attribution |

**Total new code: ~2830 LOC** (converter ~2000, library access ~200, GUI ~450)

---

## 10. Phased Implementation Sequence

### Phase 1: Converter Core (No GUI impact)

**Goal:** Build the AMBER→GROMACS converter that can produce GRO/ITP files from phenix geostd sources.

**Deliverables:**
1. `quickice/converters/` package with all converter modules
2. `gaff2_params.py` with complete parameter table
3. CLI batch converter (`converters.py`)
4. Unit tests for converter (mol2 parsing, frcmod parsing, unit conversion, pair generation, dihedral multi-term)
5. Integration test: convert 10 geostd molecules, verify against Sobtop output

**Validation:** Run converter on full geostd set, verify 82% clean conversion rate.

**No changes to existing QuickIce code.**

### Phase 2: Molecule Bundle (Data-only, no code changes)

**Goal:** Create the curated molecule bundle and library index.

**Deliverables:**
1. Convert ~100-150 geostd molecules using the converter from Phase 1
2. Manually create ~15 molecules absent from geostd (N2, Xe, Ar, Kr, etc.)
3. `index.json` with metadata for all molecules
4. `ATTRIBUTION.md` with BSD-3-Clause attribution + citations
5. Place all files in `quickice/data/molecules/` directory structure
6. Verify all bundled ITPs parse correctly with existing `parse_itp_file()`
7. Verify all bundled GRO files parse correctly with existing `parse_gro_file()`

**Validation:** Load each molecule through the existing CustomMoleculePanel upload flow (manual test).

**No changes to existing QuickIce code.**

### Phase 3: Programmatic Library Access (Backend, no GUI yet)

**Goal:** Add `MoleculeLibraryEntry` dataclass and `molecule_library.py` module.

**Deliverables:**
1. `MoleculeLibraryEntry` dataclass in `types.py`
2. `molecule_library.py` with `get_all_molecules()`, `search_molecules()`, `get_molecule_paths()`
3. Unit tests for library access functions
4. Verify `get_molecule_paths()` returns valid paths for all entries in `index.json`

**Changes to existing code:**
- `types.py`: Add `MoleculeLibraryEntry` dataclass (additive, no modification of existing types)

### Phase 4: GUI Integration (User-facing feature)

**Goal:** Add "Browse Library" option to CustomMoleculePanel.

**Deliverables:**
1. `molecule_library_dialog.py` — search/filter dialog
2. `molecule_library_model.py` — Qt model for filtered molecule list
3. Modify `custom_molecule_panel.py` — add source mode selector, library browse button
4. Signal/slot connections: source mode toggle, browse button → dialog → selection → `_load_library_molecule()`
5. Verify selected library molecules flow through validation + placement correctly
6. Manual test: select CH4 from library, insert into interface, export GROMACS

**Changes to existing code:**
- `custom_molecule_panel.py`: Add source mode combo, library browse button, `_browse_library()`, `_load_library_molecule()`, modify `_create_file_upload_group()`

**Risk mitigation:** The "Upload Files" mode is unchanged. If library code breaks, users can still manually upload files. Feature is **additive and reversible**.

### Phase 5: Polish & Edge Cases

**Goal:** Handle edge cases, improve UX, add preview.

**Deliverables:**
1. Preview selected molecule in 3D viewer (reuse `create_custom_molecule_actor()`)
2. Handle molecules with penalty > 6 (show warning badge in library dialog)
3. Handle molecules with missing params (ATTN entries — show in red)
4. Category icons in library dialog
5. Recently used molecules quick-access
6. Ensure BSD-3-Clause attribution appears in exported .top file comments
7. Full end-to-end E2E test: select from library → insert → export → validate with `gmx grompp`

---

## 11. Critical Design Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Where files live | Bundled in `data/molecules/` | ~1-2 MB, instant access, no network dependency, matches existing pattern |
| Index format | JSON | 30 KB, <1ms load, stdlib only, tool-accessible |
| ITP convention | Active `[atomtypes]` | Self-describing, scales to 150 molecules, existing dedup code handles it |
| Converter deps | numpy + networkx + stdlib only | Already in requirements.txt, no new dependencies |
| GUI approach | Source mode selector (Upload vs Library) | Non-breaking: "Upload Files" unchanged, library is additive |
| Config compatibility | None — `CustomMoleculeConfig` unchanged | Library selection just sets `gro_path`/`itp_path` to bundled paths |
| Export pipeline | No changes needed | `comment_out_atomtypes_in_itp()` + dedup already handles active atomtypes |
| Atomtype conflicts | Dedup in `write_custom_molecule_top_file()` | Bug 3 fix pattern already exists, works for any GAFF2 types |
| GRO format | Single-molecule coordinate file | Matches existing `etoh.gro` pattern, feeds into `CustomMoleculeInserter` |
| Backward compat | Keep existing `data/ch4.itp` etc. | Hydrate-specific ITPs (`ch4_hydrate.itp`) have different moleculetype names |

---

## 12. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| GAFF2 parameter gaps cause conversion failures for specific molecules | MEDIUM | LOW | Penalty scoring + manual review for score > 6; Phase 2 validation catches these |
| Atomtype name collision with future force field types | LOW | LOW | Dedup in gromacs_writer already handles; GAFF2 names (c3, hc, os) are well-established |
| index.json grows too large for fast search | VERY LOW | LOW | 150 entries × 200 bytes = 30 KB; `json.loads` is <1ms; could add caching if needed |
| Library molecule doesn't work with existing validation | LOW | MEDIUM | Phase 2 validates each molecule through existing upload flow |
| PDB code collision (25% of codes are complex ligands) | MEDIUM | MEDIUM | Curated bundle with human review; `penalty_score` field flags problematic molecules |
| Breaking change to custom_molecule_panel.py | LOW | HIGH | Source mode selector is additive; "Upload Files" path completely unchanged |
| networkx not available in minimal install | VERY LOW | LOW | Already in requirements.txt; converter is optional (only for building the bundle) |

---

## 13. Sources

All findings are based on direct analysis of the QuickIce codebase (confidence: HIGH):

- `quickice/gui/custom_molecule_panel.py` — GUI panel structure, signal/slot patterns
- `quickice/gui/custom_molecule_worker.py` — Background worker pattern
- `quickice/gui/custom_molecule_viewer.py` — VTK 3D viewer integration
- `quickice/structure_generation/types.py` — Dataclass patterns, CustomMoleculeConfig
- `quickice/structure_generation/custom_molecule_inserter.py` — Insertion pipeline
- `quickice/structure_generation/itp_parser.py` — ITP parsing expectations
- `quickice/structure_generation/gro_parser.py` — GRO parsing expectations
- `quickice/structure_generation/moleculetype_registry.py` — Moleculetype naming
- `quickice/structure_generation/molecule_validator.py` — Validation flow
- `quickice/output/gromacs_writer.py` — Export pipeline, atomtype handling, dedup
- `quickice/gui/export.py` — GROMACS exporter classes
- `quickice/data/ch4.itp`, `thf.itp` — Commented atomtypes convention
- `quickice/data/custom/etoh.itp` — Active atomtypes convention
- `quickice/data/ch4_hydrate.itp` — Hydrate-specific moleculetype naming
