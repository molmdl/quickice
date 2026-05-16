# Deep Verification: build_molecule_index() Usage

**Analysis Date:** 2026-05-16
**Function:** `build_molecule_index()`
**Location:** `quickice/utils/molecule_utils.py` (lines 111-180, 70 lines)

---

## 1. Function Definition

**Location:** `quickice/utils/molecule_utils.py:111-180`

**Signature:**
```python
def build_molecule_index(atom_names: list[str], residue_names: list[str] | None = None) -> list:
```

**Purpose:** 
Builds a list of `MoleculeIndex` objects by grouping atoms into molecules based on:
- Residue names (CH4, THF, CO2, H2 for guests)
- Atom name patterns (OW, HW1, HW2, MW for TIP4P water)
- Ion detection (NA, CL)

**Returns:** List of `MoleculeIndex(start_idx, count, mol_type)` objects

---

## 2. All Imports from `utils/molecule_utils.py`

**Total imports found:** 3 files

| File | Import |
|------|--------|
| `quickice/structure_generation/modes/pocket.py:16` | `from quickice.utils.molecule_utils import count_guest_atoms` |
| `quickice/structure_generation/modes/slab.py:16` | `from quickice.utils.molecule_utils import count_guest_atoms` |
| `quickice/structure_generation/modes/piece.py:15` | `from quickice.utils.molecule_utils import count_guest_atoms` |

**Imports of `build_molecule_index`:** NONE

---

## 3. Files Checked for Usage

### Interface/Solute/Ion/Custom Modules

| File | Checked | Usage Found |
|------|---------|-------------|
| `quickice/structure_generation/ion_inserter.py` | ✓ | NO - Uses private `_build_molecule_index_from_structure()` |
| `quickice/structure_generation/solute_inserter.py` | ✓ | NO - No molecule index building |
| `quickice/structure_generation/custom_molecule_inserter.py` | ✓ | NO - Builds molecule_index inline |
| `quickice/structure_generation/hydrate_generator.py` | ✓ | NO - Uses private `_build_molecule_index()` |
| `interface_tab.py` | N/A | File does not exist |
| `custom_molecule_tab.py` | N/A | File does not exist |

### Export Files

| File | Checked | Usage Found |
|------|---------|-------------|
| `quickice/gui/export.py` | ✓ | NO - Builds molecule_index inline (lines 88-121) |
| `quickice/gui/hydrate_export.py` | ✓ | NO - Uses structure.molecule_index directly |
| `quickice/structure_generation/gromacs_ion_export.py` | ✓ | NO - No molecule index building |

### Mode Files

| File | Checked | Usage Found |
|------|---------|-------------|
| `quickice/structure_generation/modes/pocket.py` | ✓ | NO - Only imports `count_guest_atoms` |
| `quickice/structure_generation/modes/slab.py` | ✓ | NO - Only imports `count_guest_atoms` |
| `quickice/structure_generation/modes/piece.py` | ✓ | NO - Only imports `count_guest_atoms` |

---

## 4. Replacement Functions

### Private Implementations (Still in Use)

| Function | Location | Used By |
|----------|----------|---------|
| `_build_molecule_index()` | `hydrate_generator.py:476` | HydrateStructureGenerator (line 97) |
| `_build_molecule_index_from_structure()` | `ion_inserter.py:60` | IonInserter.replace_water_with_ions() (line 193) |

### Why Private Implementations Kept Separate

From git commit a73afe0 message:
> "Note: Kept _build_molecule_index implementations separate due to different use cases:
> - hydrate_generator uses residue info
> - ion_inserter uses structure metadata"

### Differences in Signatures

**Public function (never used):**
```python
def build_molecule_index(atom_names: list[str], residue_names: list[str] | None = None) -> list
```

**Private hydrate_generator version:**
```python
def _build_molecule_index(self, atom_names: list[str], positions: np.ndarray, 
                          residue_names: list[str] = None, 
                          residue_seq_nums: list[int] = None) -> list[MoleculeIndex]
```
- Takes additional `positions` and `residue_seq_nums` parameters
- Uses residue sequence numbers for THF molecule grouping

**Private ion_inserter version:**
```python
def _build_molecule_index_from_structure(self, structure) -> list[MoleculeIndex]
```
- Takes a structure object with metadata attributes
- Uses `ice_atom_count`, `water_atom_count`, `guest_atom_count` directly
- Different approach entirely

---

## 5. Git History Analysis

**Function added in:** Commit `a73afe0` (Sat May 2 17:44:55 2026)

**Commit message:**
```
feat(007): consolidate duplicate count_guest_atoms functions

- Create quickice/utils/molecule_utils.py with consolidated utility functions
- Consolidate 4 duplicate _count_guest_atoms implementations into count_guest_atoms
- Update pocket.py, slab.py, piece.py, gromacs_writer.py to use consolidated function
- Add build_molecule_index utility for future consolidation  <-- NEVER WIRED UP
- Note: Kept _build_molecule_index implementations separate due to different use cases
```

**Git search for imports:**
```bash
git log --all --oneline -S "from quickice.utils.molecule_utils import build_molecule_index"
# Result: EMPTY - never imported anywhere
```

---

## 6. Why It Was Never Used

The function was created during a consolidation effort (plan 007) as a "utility for future consolidation." However:

1. **Different use cases emerged** - The private implementations evolved to handle specific scenarios:
   - Hydrate structures need residue sequence numbers for THF grouping
   - Ion insertion needs to build from structure metadata, not raw atom lists

2. **Never wired up** - The function exists but no code path calls it

3. **Signatures diverged** - The public function signature is simpler than what the private methods need

---

## 7. Similar Function Names (Not Related)

| Function | Location | Purpose |
|----------|----------|---------|
| `_build_vtk_molecule_from_molecule_index()` | `hydrate_renderer.py:319` | Builds VTK molecule for rendering - completely different purpose |

---

## 8. Final Verdict

### **REMOVE** ✓

**Certainty: ABSOLUTE**

The function is confirmed dead code with no possibility of hidden usage:

1. ✅ No imports anywhere in the codebase
2. ✅ No direct calls found via grep
3. ✅ All potential caller files checked individually
4. ✅ Git history confirms it was "for future consolidation" but never connected
5. ✅ Private implementations with different signatures exist and are actively used
6. ✅ Export files build molecule_index inline, not using this function

**Recommendation:** Remove `build_molecule_index()` from `quickice/utils/molecule_utils.py` (lines 111-180).

**Safe to remove:** YES - The only other function in the file (`count_guest_atoms`) is actively imported and used.

---

## 9. Cleanup Action

After removal, `quickice/utils/molecule_utils.py` will contain only:
- `count_guest_atoms()` function (lines 17-108)
- Module docstring (lines 1-14)

Total reduction: **70 lines**

---

*Verification complete: 2026-05-16*
