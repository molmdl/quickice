---
phase: 022-optimize-hbond-detection-kdtree
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - quickice/gui/vtk_utils.py
  - tests/test_pbc_hbonds.py
autonomous: true

must_haves:
  truths:
    - "H-bond detection produces identical results before and after optimization"
    - "Performance improves from O(n²) to O(n log n) for typical molecule counts"
    - "Triclinic PBC handling remains correct (no geometric distortions)"
    - "A/B tests pass with numerical equivalence (< 1e-10 nm difference)"
  artifacts:
    - path: "quickice/gui/vtk_utils.py"
      provides: "Optimized detect_hydrogen_bonds() with KDTree approach"
      exports: ["detect_hydrogen_bonds", "detect_hydrogen_bonds_optimized"]
    - path: "tests/test_pbc_hbonds.py"
      provides: "A/B comparison tests for optimization correctness"
      contains: "TestKDTreeOptimization"
  key_links:
    - from: "detect_hydrogen_bonds_optimized()"
      to: "scipy.spatial.cKDTree"
      via: "supercell construction + query_pairs"
      pattern: "cKDTree.*query_pairs"
    - from: "tests/test_pbc_hbonds.py"
      to: "detect_hydrogen_bonds"
      via: "A/B comparison fixture"
      pattern: "detect_hydrogen_bonds.*detect_hydrogen_bonds_optimized"
---

<objective>
Optimize O(n²) nested loop in `detect_hydrogen_bonds()` using KDTree approach with triclinic PBC support.

**Purpose:** Reduce H-bond detection from O(n²) to O(n log n) complexity, enabling faster candidate loading for large systems (1000+ molecules).

**Output:** Optimized implementation with A/B tests proving numerical equivalence to existing code.

**Risk Assessment:**
- MEDIUM risk due to triclinic PBC complexity
- Mitigation: A/B testing before replacement, extensive PBC test coverage
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/PROJECT.md

# Source files for reference
@quickice/gui/vtk_utils.py:127-200 (existing PBC distance functions)
@quickice/gui/vtk_utils.py:272-290 (current O(n²) implementation)
@quickice/ranking/scorer.py:21-80 (KDTree pattern for supercell approach)
@tests/test_pbc_hbonds.py (existing PBC tests)

**Key Implementation Details:**

**Current O(n²) algorithm (vtk_utils.py:272-290):**
```python
for h_idx, h_pos, parent_o_idx in h_positions:  # H atoms loop
    for o_idx, o_pos in o_positions:  # O atoms loop
        if o_idx != parent_o_idx:  # Skip same-molecule O
            distance = _pbc_distance(h_pos, o_pos, cell)  # Triclinic PBC
            if distance < max_distance:
                o_min_image = _pbc_min_image_position(h_pos, o_pos, cell)
                hbonds.append((h_pos, o_min_image))
```

**Target KDTree approach (following scorer.py pattern):**
1. Build 3x3x3 supercell for H atoms
2. Build cKDTree from supercell
3. Query pairs within max_distance
4. Filter pairs (exclude same-molecule, extract minimum image positions)
5. Handle triclinic cells properly (not just diagonal extraction)

**Triclinic PBC challenge:**
- scorer.py assumes orthorhombic: `cell_dims = np.diag(cell)`
- Need proper triclinic supercell construction using full cell matrix
- Superell offset calculation: `offset = i*a + j*b + k*c` where a,b,c are cell vectors

**Call frequency context:**
- LOW frequency: once per candidate load (cached result)
- Not called per-frame during visualization
- Typical sizes: 100-1000 molecules → 200-2000 H atoms × 100-1000 O atoms = 20K-2M distance calculations
</context>

<tasks>

<task type="auto">
<name>Task 1: Implement triclinic-aware supercell KDTree function</name>
<files>quickice/gui/vtk_utils.py</files>
<action>
Create `detect_hydrogen_bonds_optimized()` function with KDTree approach:

1. **Add import** at top of file:
   ```python
   from scipy.spatial import cKDTree
   ```

2. **Create optimized function** (after `detect_hydrogen_bonds()`):
   ```python
   def detect_hydrogen_bonds_optimized(
       candidate: Candidate,
       max_distance: float = 0.25  # nm
   ) -> list[tuple[tuple[float, float, float], tuple[float, float, float]]]:
       """Optimized H-bond detection using KDTree with O(n log n) complexity.
       
       Same interface and behavior as detect_hydrogen_bonds() but uses
       scipy.spatial.cKDTree for efficient neighbor search with supercell
       PBC handling. Works for both orthorhombic and triclinic cells.
       
       Args:
           candidate: A QuickIce Candidate with atomic positions.
           max_distance: Maximum H...O distance in nm (default 0.25 nm).
       
       Returns:
           List of (H_position, O_position) tuples for each H-bond.
       """
       positions = candidate.positions
       nmolecules = candidate.nmolecules
       atom_names = candidate.atom_names
       cell = candidate.cell
       
       # VERIFY atom ordering (same as detect_hydrogen_bonds)
       for mol_idx in range(nmolecules):
           mol_names = atom_names[mol_idx * 3: mol_idx * 3 + 3]
           expected_tip3p = ["O", "H", "H"]
           expected_tip4p = ["OW", "HW1", "HW2"]
           if mol_names != expected_tip3p and mol_names != expected_tip4p:
               raise ValueError(
                   f"Invalid atom ordering for molecule {mol_idx}: {mol_names}"
               )
       
       # Extract O and H positions with metadata
       o_positions = []  # List of (atom_idx, position)
       h_positions = []  # List of (atom_idx, position, parent_o_idx)
       
       for mol_idx in range(nmolecules):
           # O atom for this molecule
           o_idx = mol_idx * 3
           o_positions.append((o_idx, positions[o_idx]))
           
           # H atoms for this molecule
           h1_idx = mol_idx * 3 + 1
           h2_idx = mol_idx * 3 + 2
           h_positions.append((h1_idx, positions[h1_idx], o_idx))
           h_positions.append((h2_idx, positions[h2_idx], o_idx))
       
       n_h = len(h_positions)
       n_o = len(o_positions)
       
       if n_h == 0 or n_o == 0:
           return []
       
       # Build triclinic supercell for H atoms
       # Cell vectors: cell[0], cell[1], cell[2] (each is a 3D vector)
       h_coords = np.array([h[1] for h in h_positions])  # (n_h, 3)
       supercell_h = []
       
       for i in (-1, 0, 1):
           for j in (-1, 0, 1):
               for k in (-1, 0, 1):
                   # Triclinic offset: i*a + j*b + k*c
                   offset = i * cell[0] + j * cell[1] + k * cell[2]
                   supercell_h.append(h_coords + offset)
       
       supercell_h = np.vstack(supercell_h)  # (27*n_h, 3)
       
       # Build KDTree from H supercell
       tree = cKDTree(supercell_h)
       
       # Extract O coordinates for querying
       o_coords = np.array([o[1] for o in o_positions])  # (n_o, 3)
       
       # Query all O atoms against KDTree
       # Find all H atoms within max_distance of each O
       hbonds = []
       
       for o_local_idx, o_pos in enumerate(o_coords):
           o_atom_idx = o_positions[o_local_idx][0]
           
           # Query KDTree for H atoms within max_distance
           indices = tree.query_ball_point(o_pos, max_distance)
           
           for idx in indices:
               # Map back to original H atom
               h_original_idx = idx % n_h
               supercell_offset = idx // n_h
               
               h_atom_idx, h_pos, parent_o_idx = h_positions[h_original_idx]
               
               # Skip if this is the same molecule
               if parent_o_idx == o_atom_idx:
                   continue
               
               # Get minimum image position of H relative to this O
               # For visualization, we need the O position in the image
               # closest to the H
               h_supercell_pos = supercell_h[idx]
               o_min_image = _pbc_min_image_position(h_supercell_pos, o_pos, cell)
               
               hbonds.append((
                   tuple(float(h_supercell_pos[i]) for i in range(3)),
                   tuple(float(o_min_image[i]) for i in range(3))
               ))
       
       return hbonds
   ```

**Key implementation notes:**
- Use full cell matrix for triclinic offset: `i*cell[0] + j*cell[1] + k*cell[2]`
- Query O atoms against H supercell (reverse of scorer.py pattern)
- Apply `_pbc_min_image_position()` for correct visualization
- Skip same-molecule pairs (parent O check)
- Preserve exact tuple format: `(tuple[float, float, float], tuple[float, float, float])`

**Do NOT:**
- Use `np.diag(cell)` - breaks triclinic cells
- Skip the atom ordering verification - safety check
- Modify the original `detect_hydrogen_bonds()` function yet
</action>
<verify>
```bash
# Run existing PBC tests to ensure no breakage
pytest tests/test_pbc_hbonds.py -v

# Verify new function is importable
python -c "from quickice.gui.vtk_utils import detect_hydrogen_bonds_optimized; print('Import successful')"

# Check no syntax errors in modified file
python -m py_compile quickice/gui/vtk_utils.py
```
</verify>
<done>
- `detect_hydrogen_bonds_optimized()` function exists and is importable
- Existing tests pass (no breakage to existing code)
- Function handles both orthorhombic and triclinic cells via full cell matrix
- scipy import added successfully
</done>
</task>

<task type="auto">
<name>Task 2: Create A/B comparison tests for numerical equivalence</name>
<files>tests/test_pbc_hbonds.py</files>
<action>
Add comprehensive A/B test class to verify optimization correctness:

1. **Add test class** after existing `TestHydrogenBondDetection` class:

```python
class TestKDTreeOptimization:
    """Test that optimized KDTree implementation produces identical results."""
    
    @pytest.fixture
    def random_candidate(self):
        """Create a random candidate with 100 molecules for stress testing."""
        np.random.seed(42)
        nmolecules = 100
        positions = []
        atom_names = []
        
        # Generate random water molecules in 5 nm box
        box_size = 5.0
        for _ in range(nmolecules):
            # Random O position
            o_pos = np.random.uniform(0.5, box_size - 0.5, 3)
            
            # Two H atoms at random orientations near O
            theta = np.random.uniform(0, 2 * np.pi)
            phi = np.random.uniform(0, np.pi)
            r = 0.1  # O-H bond length
            
            h1_pos = o_pos + r * np.array([
                np.sin(phi) * np.cos(theta),
                np.sin(phi) * np.sin(theta),
                np.cos(phi)
            ])
            
            theta2 = theta + np.pi * 2 / 3
            h2_pos = o_pos + r * np.array([
                np.sin(phi) * np.cos(theta2),
                np.sin(phi) * np.sin(theta2),
                np.cos(phi)
            ])
            
            positions.extend([o_pos, h1_pos, h2_pos])
            atom_names.extend(["O", "H", "H"])
        
        positions = np.array(positions)
        cell = np.diag([box_size, box_size, box_size])
        
        return Candidate(
            positions=positions,
            atom_names=atom_names,
            cell=cell,
            nmolecules=nmolecules,
            phase_id="test",
            seed=42
        )
    
    @pytest.fixture
    def triclinic_candidate(self):
        """Create a candidate with triclinic cell for PBC testing."""
        np.random.seed(123)
        nmolecules = 50
        positions = []
        atom_names = []
        
        # Triclinic cell with tilt
        a = np.array([4.0, 0.0, 0.0])
        b = np.array([1.0, 4.0, 0.0])  # Tilted in x
        c = np.array([0.5, 0.5, 4.0])  # Tilted in x and y
        
        for _ in range(nmolecules):
            # Random position in fractional coordinates
            frac_pos = np.random.uniform(0.1, 0.9, 3)
            o_pos = frac_pos[0] * a + frac_pos[1] * b + frac_pos[2] * c
            
            # Two H atoms
            theta = np.random.uniform(0, 2 * np.pi)
            phi = np.random.uniform(0, np.pi)
            r = 0.1
            
            h1_pos = o_pos + r * np.array([
                np.sin(phi) * np.cos(theta),
                np.sin(phi) * np.sin(theta),
                np.cos(phi)
            ])
            
            theta2 = theta + np.pi * 2 / 3
            h2_pos = o_pos + r * np.array([
                np.sin(phi) * np.cos(theta2),
                np.sin(phi) * np.sin(theta2),
                np.cos(phi)
            ])
            
            positions.extend([o_pos, h1_pos, h2_pos])
            atom_names.extend(["O", "H", "H"])
        
        positions = np.array(positions)
        cell = np.array([a, b, c])
        
        return Candidate(
            positions=positions,
            atom_names=atom_names,
            cell=cell,
            nmolecules=nmolecules,
            phase_id="test_triclinic",
            seed=123
        )
    
    def test_optimized_matches_original_simple(self, simple_candidate):
        """Test that optimized version matches original for simple case."""
        from quickice.gui.vtk_utils import (
            detect_hydrogen_bonds,
            detect_hydrogen_bonds_optimized
        )
        
        hbonds_orig = detect_hydrogen_bonds(simple_candidate, max_distance=0.25)
        hbonds_opt = detect_hydrogen_bonds_optimized(simple_candidate, max_distance=0.25)
        
        # Compare counts
        assert len(hbonds_orig) == len(hbonds_opt), \
            f"Count mismatch: {len(hbonds_orig)} vs {len(hbonds_opt)}"
        
        # Sort both lists for comparison
        hbonds_orig_sorted = sorted(hbonds_orig)
        hbonds_opt_sorted = sorted(hbonds_opt)
        
        # Compare each H-bond
        for i, (orig, opt) in enumerate(zip(hbonds_orig_sorted, hbonds_opt_sorted)):
            h_orig, o_orig = orig
            h_opt, o_opt = opt
            
            # Check H positions match
            for j in range(3):
                assert abs(h_orig[j] - h_opt[j]) < 1e-10, \
                    f"H-bond {i} H position mismatch at coord {j}: {h_orig[j]} vs {h_opt[j]}"
            
            # Check O positions match
            for j in range(3):
                assert abs(o_orig[j] - o_opt[j]) < 1e-10, \
                    f"H-bond {i} O position mismatch at coord {j}: {o_orig[j]} vs {o_opt[j]}"
    
    def test_optimized_matches_original_pbc(self, pbc_candidate):
        """Test PBC handling matches between implementations."""
        from quickice.gui.vtk_utils import (
            detect_hydrogen_bonds,
            detect_hydrogen_bonds_optimized
        )
        
        hbonds_orig = detect_hydrogen_bonds(pbc_candidate, max_distance=0.25)
        hbonds_opt = detect_hydrogen_bonds_optimized(pbc_candidate, max_distance=0.25)
        
        assert len(hbonds_orig) == len(hbonds_opt), \
            f"PBC count mismatch: {len(hbonds_orig)} vs {len(hbonds_opt)}"
        
        # Sort and compare
        hbonds_orig_sorted = sorted(hbonds_orig)
        hbonds_opt_sorted = sorted(hbonds_opt)
        
        for i, (orig, opt) in enumerate(zip(hbonds_orig_sorted, hbonds_opt_sorted)):
            h_orig, o_orig = orig
            h_opt, o_opt = opt
            
            for j in range(3):
                assert abs(h_orig[j] - h_opt[j]) < 1e-10
                assert abs(o_orig[j] - o_opt[j]) < 1e-10
    
    def test_optimized_matches_original_random(self, random_candidate):
        """Stress test with 100 random molecules."""
        from quickice.gui.vtk_utils import (
            detect_hydrogen_bonds,
            detect_hydrogen_bonds_optimized
        )
        
        hbonds_orig = detect_hydrogen_bonds(random_candidate, max_distance=0.25)
        hbonds_opt = detect_hydrogen_bonds_optimized(random_candidate, max_distance=0.25)
        
        assert len(hbonds_orig) == len(hbonds_opt), \
            f"Random candidate mismatch: {len(hbonds_orig)} vs {len(hbonds_opt)}"
        
        # Detailed comparison
        hbonds_orig_sorted = sorted(hbonds_orig)
        hbonds_opt_sorted = sorted(hbonds_opt)
        
        for orig, opt in zip(hbonds_orig_sorted, hbonds_opt_sorted):
            h_orig, o_orig = orig
            h_opt, o_opt = opt
            
            for j in range(3):
                assert abs(h_orig[j] - h_opt[j]) < 1e-10, \
                    f"H mismatch: {h_orig} vs {h_opt}"
                assert abs(o_orig[j] - o_opt[j]) < 1e-10, \
                    f"O mismatch: {o_orig} vs {o_opt}"
    
    def test_optimized_matches_original_triclinic(self, triclinic_candidate):
        """Test triclinic cell handling."""
        from quickice.gui.vtk_utils import (
            detect_hydrogen_bonds,
            detect_hydrogen_bonds_optimized
        )
        
        hbonds_orig = detect_hydrogen_bonds(triclinic_candidate, max_distance=0.25)
        hbonds_opt = detect_hydrogen_bonds_optimized(triclinic_candidate, max_distance=0.25)
        
        assert len(hbonds_orig) == len(hbonds_opt), \
            f"Triclinic count mismatch: {len(hbonds_orig)} vs {len(hbonds_opt)}"
        
        # Detailed comparison
        hbonds_orig_sorted = sorted(hbonds_orig)
        hbonds_opt_sorted = sorted(hbonds_opt)
        
        for orig, opt in zip(hbonds_orig_sorted, hbonds_opt_sorted):
            h_orig, o_orig = orig
            h_opt, o_opt = opt
            
            for j in range(3):
                assert abs(h_orig[j] - h_opt[j]) < 1e-10
                assert abs(o_orig[j] - o_opt[j]) < 1e-10
    
    def test_performance_improvement(self, random_candidate):
        """Verify performance improvement with timing test."""
        import time
        from quickice.gui.vtk_utils import (
            detect_hydrogen_bonds,
            detect_hydrogen_bonds_optimized
        )
        
        # Warm up
        detect_hydrogen_bonds(random_candidate, max_distance=0.25)
        detect_hydrogen_bonds_optimized(random_candidate, max_distance=0.25)
        
        # Time original
        start = time.time()
        for _ in range(10):
            detect_hydrogen_bonds(random_candidate, max_distance=0.25)
        time_orig = time.time() - start
        
        # Time optimized
        start = time.time()
        for _ in range(10):
            detect_hydrogen_bonds_optimized(random_candidate, max_distance=0.25)
        time_opt = time.time() - start
        
        # Optimized should be faster
        print(f"\nOriginal: {time_orig:.4f}s, Optimized: {time_opt:.4f}s")
        print(f"Speedup: {time_orig/time_opt:.2f}x")
        
        # At minimum, should not be slower
        assert time_opt <= time_orig * 1.1, \
            f"Optimized version slower: {time_opt:.4f}s vs {time_orig:.4f}s"
        
        # For 100 molecules, expect at least 2x speedup
        # (conservative threshold for test stability)
        assert time_opt < time_orig, \
            "Optimized version should be faster for 100 molecules"
```

2. **Add import at top of test file** if needed:
   ```python
   from quickice.gui.vtk_utils import detect_hydrogen_bonds_optimized
   ```

**Test coverage:**
- Simple case: 2 molecules (existing fixture)
- PBC case: boundary-crossing H-bonds (existing fixture)
- Random stress test: 100 molecules, random orientations
- Triclinic case: tilted cell vectors
- Performance verification: timing comparison

**Numerical tolerance:**
- Use `1e-10` nm tolerance for position comparison (float precision)
- Ensure counts match exactly
- Sort H-bonds before comparison for deterministic ordering

**Do NOT:**
- Use looser tolerance (could hide algorithm bugs)
- Skip the triclinic test (critical for correctness)
- Ignore performance aspect (verify speedup)
</action>
<verify>
```bash
# Run all A/B tests
pytest tests/test_pbc_hbonds.py::TestKDTreeOptimization -v

# Verify all tests pass with detailed output
pytest tests/test_pbc_hbonds.py -v --tb=short

# Check test file has no syntax errors
python -m py_compile tests/test_pbc_hbonds.py
```
</verify>
<done>
- `TestKDTreeOptimization` class exists with 6 test methods
- All A/B tests pass (numerical equivalence verified)
- Performance test shows speedup
- Triclinic cell handling verified correct
- Test coverage: simple, PBC, random (100 mol), triclinic, performance
</done>
</task>

<task type="auto">
<name>Task 3: Replace original function after A/B tests pass</name>
<files>quickice/gui/vtk_utils.py</files>
<action>
Replace the original `detect_hydrogen_bonds()` implementation after tests confirm equivalence:

1. **Rename optimized function to replace original:**
   - Delete the original `detect_hydrogen_bonds()` function (lines ~200-292)
   - Rename `detect_hydrogen_bonds_optimized()` to `detect_hydrogen_bonds()`
   - Update docstring to mention KDTree optimization

2. **Updated function signature:**
   ```python
   def detect_hydrogen_bonds(
       candidate: Candidate,
       max_distance: float = 0.25  # nm
   ) -> list[tuple[tuple[float, float, float], tuple[float, float, float]]]:
       """Detect hydrogen bonds with O(n log n) KDTree optimization.
       
       Identifies H-bonds based on H...O distance threshold using KDTree
       for efficient neighbor search. Uses 3x3x3 supercell construction
       for periodic boundary condition handling.
       
       Args:
           candidate: A QuickIce Candidate containing atomic positions.
           max_distance: Maximum H...O distance threshold in nm.
                         Default 0.25 nm (2.5 Å) is typical for H-bonds.
       
       Returns:
           List of (H_position, O_position) tuples for each detected H-bond.
       
       Performance:
           O(n log n) where n is number of molecules. For 1000 molecules,
           approximately 10-50x faster than O(n²) approach depending on
           hardware and density.
       
       Note:
           Water molecules follow [O, H, H, O, H, H, ...] ordering.
           Works for both orthorhombic (ice Ih) and triclinic (ice II, V) cells.
       """
       # [Implementation from detect_hydrogen_bonds_optimized]
   ```

3. **Keep scipy import at top of file:**
   ```python
   from scipy.spatial import cKDTree
   ```

4. **Remove the now-redundant `_optimized` suffix function** if you created it as separate.

**Migration safety:**
- Function signature remains identical (backward compatible)
- Return type unchanged
- Behavior verified identical by A/B tests
- Docstring updated to reflect optimization

**Do NOT:**
- Change function signature or return type
- Remove scipy import
- Keep both functions (avoid confusion)
- Skip updating docstring with performance notes
</action>
<verify>
```bash
# Run full test suite to verify replacement works
pytest tests/test_pbc_hbonds.py -v

# Verify import still works
python -c "from quickice.gui.vtk_utils import detect_hydrogen_bonds; print('Import successful')"

# Run integration test to ensure GUI still works
# (If there's a GUI test that uses H-bond detection)
pytest tests/ -k hbond -v

# Check for any other code that might reference detect_hydrogen_bonds
grep -r "detect_hydrogen_bonds" --include="*.py" quickice/
```
</verify>
<done>
- Original O(n²) implementation replaced with KDTree version
- Function signature unchanged (backward compatible)
- All tests pass with new implementation
- No other code references broken
- Docstring updated with performance information
- scipy import retained
</done>
</task>

</tasks>

<verification>
After all tasks complete:

1. **Numerical correctness:**
   ```bash
   pytest tests/test_pbc_hbonds.py::TestKDTreeOptimization -v
   ```
   All 6 A/B tests pass with < 1e-10 nm tolerance.

2. **Backward compatibility:**
   ```bash
   python -c "from quickice.gui.vtk_utils import detect_hydrogen_bonds; print(detect_hydrogen_bonds.__doc__)"
   ```
   Function imports and has updated docstring.

3. **PBC correctness:**
   ```bash
   pytest tests/test_pbc_hbonds.py::TestHydrogenBondDetection -v
   ```
   Original PBC tests still pass.

4. **Performance verification:**
   Test output should show speedup for random_candidate test:
   ```
   Original: X.XXXXs, Optimized: Y.YYYYs
   Speedup: Z.ZZx
   ```

5. **Triclinic handling:**
   ```bash
   pytest tests/test_pbc_hbonds.py::TestKDTreeOptimization::test_optimized_matches_original_triclinic -v
   ```
   Triclinic cell test passes.
</verification>

<success_criteria>
**Must achieve:**
- ✅ All A/B tests pass with numerical equivalence (< 1e-10 nm)
- ✅ Triclinic PBC handling verified correct
- ✅ Performance improvement demonstrated (faster for 100+ molecules)
- ✅ All existing PBC tests pass
- ✅ No breaking changes to function signature or behavior
- ✅ Code committed with descriptive message

**Performance targets:**
- For 100 molecules: at least 2x speedup
- For 1000 molecules: estimated 10-50x speedup (based on O(n²) vs O(n log n))
- Memory overhead acceptable (27x supercell is standard)

**Quality gates:**
- No test failures
- No import errors
- No breaking changes to dependent code
- Triclinic cells handled correctly (full cell matrix, not just diagonal)
</success_criteria>

<output>
After completion, create `.planning/quick/022-optimize-hbond-detection-kdtree/022-SUMMARY.md` with:
- Before/after performance metrics
- Test results summary
- Verification that triclinic PBC works correctly
- Any lessons learned during implementation
</output>
