# Domain Pitfalls: Complex Hydrate Generation

**Domain:** Clathrate hydrate molecular dynamics simulation + GROMACS structure preparation
**Researched:** 2026-06-12
**Confidence:** HIGH (based on source code analysis, GenIce2 API inspection, and domain expertise)

## Critical Pitfalls

### Pitfall 1: GPL-3.0 License Contamination Risk (atomsk)

**What goes wrong:** A developer on the QuickIce team adds atomsk as a dependency (import or link), contaminating the MIT-licensed codebase with GPL-3.0 obligations. Even distributing atomsk binaries alongside QuickIce in a PyInstaller bundle could create legal ambiguity.

**Why it happens:** atomsk is a well-known crystallography tool with 16,500+ downloads and 430+ citations. Developers may assume "popular = safe to use" without checking the license. The GPL-3.0 constraint is not immediately obvious from atomsk's documentation.

**Consequences:** QuickIce would need to either:
- Release the entire combined work under GPL-3.0 (losing MIT compatibility)
- Remove atomsk dependency and rewrite affected code
- Face legal risk if distributed without compliance

**Prevention:**
- atomsk is **already rejected** in Wave 1 (STACK.md). GenIce2 + pymatgen cover all useful atomsk capabilities.
- Add a `CONTRIBUTING.md` note: "Do not add GPL-licensed dependencies. Check license compatibility before adding any new dependency."
- Use `pip-licenses` or `license-check` in CI to flag GPL packages.

**Detection:** 
- New Python dependency with GPL license
- `import atomsk` anywhere in codebase
- atomsk binary bundled in distribution

---

### Pitfall 2: Ice Rules Violation in Non-Standard Frameworks

**What goes wrong:** When building custom hydrate structures (e.g., via pymatgen or manual coordinate manipulation), the hydrogen atoms in the water framework do not satisfy Bernal-Fowler ice rules (each water molecule donates exactly 2 H-bonds and accepts exactly 2 H-bonds). This produces physically unrealistic structures that will collapse or rearrange during MD equilibration.

**Why it happens:** GenIce2's core algorithm enforces ice rules automatically. But if someone bypasses GenIce2 (Option C: pymatgen builder), they must implement ice rules manually — which is extremely difficult. Even genice2-cif (Option B) relies on the CIF file having a correct O-network topology; if the CIF file is corrupted or has missing oxygen positions, GenIce2 may produce incorrect ice rules.

**Consequences:**
- MD simulation starts with unrealistic H-bond network → immediate energy spike
- Extended equilibration needed (or simulation may crash)
- Published results with wrong ice rules are unreproducible
- Structure may have net polarization (dipole moment ≠ 0), causing artifacts in Ewald summation

**Prevention:**
- **Always use GenIce2 for any structure containing a water O-network.** GenIce2's `generate_ice()` method enforces ice rules via the genice-core algorithm (Node-Rule Compliant graph construction).
- If using genice2-cif, validate the CIF file first (check that all O positions form a valid tetrahedral network).
- Never manually place hydrogen atoms; always let GenIce2's Stage34E algorithm determine H orientations.
- For non-ice frameworks (e.g., semiclathrates where TBA+ replaces water), use GenIce2's `--depol=optimal` instead of `strict` because ions prevent strict depolarization.

**Detection:**
- Ice rules check: count H-donors and H-acceptors per molecule. If any O has ≠ 2 donors + 2 acceptors, rules are violated.
- Net polarization: compute total dipole moment of the unit cell. Should be near zero for bulk ice.
- GenIce2 logs warning if it fails to find a valid directed graph: `"Failed to generate a directed graph."`

---

### Pitfall 3: Cage Occupancy for Unknown Cage Types

**What goes wrong:** When importing a CIF file via genice2-cif (Option B), the resulting structure may have cage types that don't match GenIce2's standard cage naming (5¹² = type 12, 5¹²6² = type 14, 5¹²6⁴ = type 16). The `-g` and `-G` guest flags reference cage types by number, so incorrect cage numbers lead to guests being placed in wrong positions or not at all.

**Why it happens:** GenIce2's cage numbering follows the Jeffrey convention (12 = 5¹², 14 = 5¹²6², 16 = 5¹²6⁴). But genice2-cif generates cage numbers dynamically based on the cage faces found in the structure. For non-standard or hypothetical cage types (e.g., 4¹5⁶6³ in sH, or exotic cages in zeolite-derived structures), the cage numbers may not match the user's expectations.

**Consequences:**
- Guests placed in wrong cages (e.g., large THF in small 5¹² cages)
- No guests placed at all (cage numbers don't match `-g` specs)
- Structure exported with empty cages → MD simulation shows spontaneous cage decomposition

**Prevention:**
- Always run `--assess_cages` first to discover cage types and their numbers before specifying guests.
- In the GUI, show the assessed cage information (cage type, number of faces, cage ID) before asking the user to assign guests.
- For known structures (sI, sII, sH), hardcode the cage mapping in HYDRATE_LATTICES.
- For CIF imports, add a "Cage Assessment" step in the UI that shows cage info before guest assignment.

**Detection:**
- GenIce2 output with zero guest molecules when occupancy > 0
- Guest count doesn't match expected count per unit cell
- Cage assessment log shows unexpected cage numbers

---

### Pitfall 4: PBC Handling for Non-Orthogonal Hydrate Cells

**What goes wrong:** Filled ice C0 (P3₂ space group) and other trigonal/hexagonal phases have non-orthogonal unit cells (e.g., γ = 120°). QuickIce's current PBC wrapping code in `hydrate_generator.py._wrap_positions_to_cell()` handles both orthorhombic and triclinic cells, but VTK rendering and GRO file export may not correctly handle non-orthogonal cell vectors.

**Why it happens:** The GRO file format supports triclinic boxes via 9 values on the last line: `v1(x) v2(y) v3(z) v1(y) v1(z) v2(x) v2(z) v3(x) v3(y)`. However, many GROMACS analysis tools and visualization programs assume orthorhombic boxes. VTK's `SetLattice()` expects a 3×3 matrix, which QuickIce already handles correctly (via transpose in `_set_molecule_lattice`).

**Consequences:**
- Molecules split across periodic boundaries appear broken in VTK viewer
- GRO export with wrong box vectors → GROMACS simulation with wrong cell dimensions
- Density calculations incorrect for non-orthogonal cells

**Prevention:**
- The `_wrap_positions_to_cell()` method already handles triclinic cells via fractional coordinates. Verify it works for the new lattice types (c0te has γ = 120°).
- The VTK lattice setting already transposes the cell matrix. Verify for non-orthogonal cells.
- Test GRO export with a triclinic cell and re-import with `gmx editconf` to verify box dimensions.
- The `_parse_box_line()` method already handles 9-value triclinic box lines. Verify round-trip consistency.

**Detection:**
- VTK viewer shows "broken" molecules (atoms separated by cell length)
- GROMACS energy minimization crashes due to incorrect box dimensions
- `gmx check` reports box inconsistencies

---

### Pitfall 5: Water Model Compatibility for Complex Hydrates

**What goes wrong:** Different hydrate types require different water models for stable MD simulation:
- Standard clathrates (sI, sII, sH) → TIP4P-ICE is standard
- Filled ice C0/C1/C2 at high pressure → TIP4P/2005 may be better (better high-P behavior)
- Semiclathrates with ions → TIP4P-ICE may not correctly model ion-water interactions

If the wrong water model is selected, the MD simulation may show:
- Unphysical hydrate decomposition (cage collapse)
- Wrong lattice parameters after equilibration
- Incorrect guest diffusion coefficients

**Why it happens:** QuickIce currently hardcodes TIP4P-ICE in `hydrate_generator.py`:
```python
water = safe_import('molecule', 'tip4p').Molecule()
```
This means ALL hydrate structures use TIP4P-ICE, regardless of whether it's appropriate.

**Consequences:**
- Filled ice structures generated with TIP4P-ICE may not be stable at the high pressures where they naturally exist
- Semiclathrate structures may have incorrect ion-water interaction energies
- Published simulation results may use a water model inappropriate for the conditions

**Prevention:**
- Add a water model selector to HydrateConfig (TIP4P-ICE, TIP4P/2005, TIP3P, TPC/E, SPC/E, TIP5P)
- Expose GenIce2's water model options (`--water tip4p`, `--water tip3p`, etc.)
- Add recommended water model per lattice type in HYDRATE_LATTICES:
  ```python
  "c0te": {"recommended_water_model": "tip4p2005", ...}
  ```
- In the UI, show a recommendation but allow override
- Bundle ITP files for each water model

**Detection:**
- MD simulation shows rapid hydrate decomposition in first 100 ps
- Lattice parameters drift significantly from experimental values during NPT equilibration
- Energy conservation is poor (wrong LJ parameters for water model)

---

## Moderate Pitfalls

### Pitfall 6: GROMACS Force Field Parameters for Exotic Guest Molecules

**What goes wrong:** Adding new guest molecules (CO2, H2, ethane) requires GROMACS force field parameters (.itp files). If the parameters are wrong or use an incompatible force field (e.g., OPLS-AA guest with TIP4P-ICE water), the MD simulation produces incorrect guest-water interaction energies.

**Why it happens:** Different force fields parameterize Lennard-Jones parameters differently. GAFF/GAFF2 parameters are commonly used for organic guests, but combining rules (Lorentz-Berthelot) with TIP4P-ICE may not give correct cross-interactions. CO2 and H2 have been parameterized in multiple force fields with different approaches.

**Consequences:**
- Incorrect guest binding energy → wrong cage occupancy thermodynamics
- Guest molecules escape from cages during MD (if LJ parameters too weak)
- Guest molecules get trapped in wrong positions (if LJ parameters too strong)

**Prevention:**
- Use established GROMACS parameterizations for common guests:
  - CH4: GAFF2 with TIP4P-ICE cross-parameters (already in QuickIce's `ch4_hydrate.itp`)
  - CO2: Use Zhang-Sprik CO2 model (specifically parameterized for clathrate hydrates)
  - H2: Use Vehkamäki H2 model or GAFF2 with modified charges
  - Ethane: Use OPLS-AA ethane with TIP4P-ICE cross-parameters
- Validate parameters by checking cage binding energy against literature values
- Document the force field source in the .itp file header comments

**Detection:**
- Guest molecules spontaneously leave cages during NPT MD
- Hydration free energy differs significantly from literature values
- LJ energy terms are anomalously high/low compared to reference simulations

---

### Pitfall 7: Density Matching Between Hydrate and Liquid Phases

**What goes wrong:** When creating a hydrate-water interface (via the Interface Construction tab), the hydrate crystal density must match the liquid water density at the simulation temperature. If densities are mismatched, the interface develops artificial stress during NPT equilibration.

**Why it happens:** Hydrate densities vary significantly by type:
- sI CH4 hydrate: ~0.91 g/cm³
- sII THF hydrate: ~0.80 g/cm³  
- Filled ice C0: ~1.17 g/cm³
- Filled ice C1: ~1.25 g/cm³

TIP4P-ICE liquid water at 260K has density ~0.99 g/cm³. Filled ice phases (C0, C1, C2) have much higher densities than liquid water, creating a significant density mismatch at the interface.

**Consequences:**
- Interface develops artificial void or compression during NPT equilibration
- Simulation may crash due to large forces at the interface
- Unphysical melting/freezing behavior at the interface

**Prevention:**
- Calculate expected densities for each hydrate type using `HYDRATE_LATTICES.unit_cell_molecules` and cell dimensions
- For high-density filled ices, warn the user that hydrate-liquid interfaces may not be physically meaningful (these phases exist at high pressure where liquid water doesn't coexist)
- Add a density check in InterfaceBuilder before generation:
  ```python
  if abs(hydrate_density - water_density) > 0.1:
      warn("Large density mismatch between hydrate and liquid")
  ```
- For filled ice phases, suggest using NVT (constant volume) instead of NPT for interface simulations

**Detection:**
- Interface shows visible density discontinuity in VTK viewer
- NPT equilibration causes large box deformation
- Energy spikes at the interface region

---

### Pitfall 8: Crystallographic Data Quality (CIF File Accuracy)

**What goes wrong:** CIF files imported via genice2-cif may have incorrect or incomplete data:
- Missing hydrogen positions (CIF often contains only heavy atom positions)
- Wrong space group symmetry operations
- Incorrect lattice parameters (experimental vs. relaxed DFT values)
- Occupancy disorders not properly specified

**Why it happens:** CIF files from literature are curated to varying standards. COD (Crystallography Open Database) has variable quality. ICSD has high quality but is commercial. CIF files from supplementary materials may have typos or formatting issues.

**Consequences:**
- GenIce2-cif fails to parse the CIF → `ImportError` or `ValueError`
- Incorrect water network → ice rules violation (Pitfall 2)
- Wrong cell dimensions → incorrect density → MD simulation artifacts

**Prevention:**
- Validate CIF files before import using pymatgen:
  ```python
  from pymatgen.core import Structure
  try:
      structure = Structure.from_file("hydrate.cif")
      # Check: structure has O atoms, valid cell, reasonable density
  except Exception as e:
      raise CIFValidationError(f"Invalid CIF file: {e}")
  ```
- Use spglib to verify/refine the space group:
  ```python
  import spglib
  dataset = spglib.get_symmetry_dataset((lattice, positions, numbers))
  if dataset['number'] != expected_spacegroup:
      warn("Space group mismatch")
  ```
- Add a CIF validation step in the GUI (pre-import check)

**Detection:**
- GenIce2 throws `ImportError` when loading CIF
- Number of water molecules in output doesn't match expected count
- Structure density differs significantly from literature value

---

### Pitfall 9: GenIce2 Version Compatibility (Plugin API Stability)

**What goes wrong:** GenIce2's plugin API (Lattice class interface, safe_import behavior, guest flag syntax) may change between versions. QuickIce's code is tightly coupled to GenIce2's internal API via:
- `safe_import('lattice', name).Lattice()`
- `parse_guest(guests, guest_spec)`
- `GenIce(lattice, reshape=supercell_matrix)`
- `ice.generate_ice(formatter, water, guests, depol='strict')`

**Why it happens:** GenIce2 is under active development (current version 2.2.13.1). The plugin system is documented but the internal API is not guaranteed stable. genice2-cif (version 2.2.1) is a separate package with its own versioning.

**Consequences:**
- QuickIce breaks after `pip install --upgrade genice2`
- New GenIce2 version changes Lattice class interface → all custom lattice modules need updating
- `safe_import` behavior changes → lattice discovery fails silently

**Prevention:**
- Pin GenIce2 version in pyproject.toml: `genice2>=2.2.13,<2.3`
- Write integration tests that verify GenIce2 can load all required lattice types
- Add version check at startup:
  ```python
  import genice2
  if genice2.__version__ < "2.2.13":
      warn("GenIce2 version may be incompatible")
  ```
- Monitor GenIce2 changelog: https://github.com/genice-dev/GenIce2/releases

**Detection:**
- `ImportError` or `AttributeError` when loading lattice modules
- GenIce2 generation produces different output than expected
- Test suite failures after dependency updates

---

### Pitfall 10: Python 3.14 Compatibility for New Dependencies

**What goes wrong:** Adding pymatgen (>=2026.5), packmol (>=21.2), or genice2-cif (>=2.2.1) introduces dependencies that may not support Python 3.14 (which will be released in October 2026). NumPy 2.x and SciPy 1.14+ already support 3.14, but some compiled extensions may lag.

**Why it happens:** The Python 3.14 release schedule introduces a free-threading mode (no-GIL) and changes to the C API. Packages with Cython or C extensions need explicit 3.14 support. GenIce2's genice-core package has C extensions that may need updating.

**Consequences:**
- QuickIce cannot be installed on Python 3.14
- Import errors for compiled extensions
- CI pipeline fails on 3.14 test matrix

**Prevention:**
- Pin Python version to 3.11-3.13 in pyproject.toml for now
- Test each new dependency on the target Python version before adding
- Add Python version check:
  ```python
  import sys
  if sys.version_info >= (3, 14):
      warn("Python 3.14+ compatibility not yet verified")
  ```
- Monitor release notes for pymatgen, genice2, and spglib for 3.14 support announcements

**Detection:**
- `pip install` fails with compilation errors on 3.14
- `ImportError` for compiled C extensions
- CI test failures on 3.14 matrix

---

## Minor Pitfalls

### Pitfall 11: Mixed Cage Occupancy GUI Complexity

**What goes wrong:** The mixed cage occupancy UI (two guests per cage type, e.g., CH4 60% + CO2 40% in large cages) adds significant UI complexity. The user must specify:
- Which cage type gets which guest(s)
- Occupancy fraction for each guest
- Per-cage overrides (optional, advanced mode)

**Why it happens:** The current HydratePanel has only one guest dropdown and two occupancy sliders (small/large). Mixed occupancy requires a fundamentally different UI: either a table widget (cage type → guest 1 % + guest 2 %) or multiple dropdowns per cage type.

**Consequences:**
- UI becomes confusing for users who just want "CH4 sI hydrate"
- Validation logic becomes complex (total occupancy per cage must sum to ≤ 100%)
- GenIce2 flag syntax becomes complex: `-g 12=co2*0.6+me*0.4 -g 14=co2`

**Prevention:**
- Keep the simple UI (one guest, one occupancy per cage type) as the default
- Add mixed occupancy as an "Advanced" toggle that reveals additional controls
- Use a two-column table: Guest 1 (%) | Guest 2 (%) per cage type
- Validate that occupancies sum to ≤ 100% per cage type

**Detection:**
- User confusion about how to specify mixed guests
- Occupancy sums > 100% causing GenIce2 to error

---

### Pitfall 12: genice2-cif Plugin Availability and Installation

**What goes wrong:** The `genice2-cif` package is NOT currently installed in the QuickIce environment (confirmed: `pip list | grep genice2-cif` returns nothing). If QuickIce tries to use `safe_import('lattice', 'cif[...]')` without genice2-cif installed, it will fail with an `ImportError`.

**Why it happens:** genice2-cif is a separate package from genice2 and must be explicitly installed. It's not a dependency of genice2 itself. Users may not realize they need it.

**Consequences:**
- CIF import feature appears in UI but fails on use
- Confusing error message: "Failed to import required module" without specifying that genice2-cif is missing

**Prevention:**
- Add `genice2-cif>=2.2.1` as an optional dependency in pyproject.toml: `pip install quickice[cif]`
- Check for genice2-cif availability at startup and disable CIF import UI if not installed
- Provide a clear error message: "Install genice2-cif for CIF import: pip install genice2-cif"
- Add a pre-flight check when user clicks "Import CIF":
  ```python
  try:
      from genice2.lattices import cif  # Check if cif plugin is available
  except ImportError:
      QMessageBox.warning("CIF import requires genice2-cif. Install with: pip install genice2-cif")
  ```

**Detection:**
- `ImportError` when `safe_import('lattice', 'cif[...]')` is called
- genice2-cif missing from `pip list`

---

### Pitfall 13: Multiple ITP File Handling for Complex Hydrate Guests

**What goes wrong:** Complex hydrate structures may have multiple guest molecule types, each requiring its own .itp file. For example, a binary CH4+CO2 sI hydrate needs:
- `tip4p-ice.itp` (water)
- `ch4_hydrate.itp` (methane)
- `co2_hydrate.itp` (carbon dioxide)

The current `HydrateGROMACSExporter` assumes a single guest type. With mixed occupancy, it must handle multiple guest .itp files.

**Why it happens:** The export code iterates over `molecule_index` and writes a single guest .itp entry. With two guest types, the `.top` file needs two `#include` statements and two `[ moleculetype ]` sections.

**Consequences:**
- Export fails with "No .itp file found for guest type" when guest is not in the ITP lookup
- `.top` file has missing `#include` for second guest type
- GROMACS `gmx grompp` fails with topology errors

**Prevention:**
- Refactor `HydrateGROMACSExporter` to iterate over unique guest types in `molecule_index`
- Build `itp_files` dict from ALL unique guest mol_types, not just `config.guest_type`
- Add ITP files for all new guest types to `data/` directory
- Add integration test: export binary CH4+CO2 hydrate → verify `.top` has both `#include` lines

**Detection:**
- `gmx grompp` reports "Invalid .top file" or "Unknown moleculetype"
- Missing `.itp` file for one of the guest types

---

## Risk Matrix

| Pitfall | Likelihood | Impact | Risk Level | Mitigation Priority |
|---------|-----------|--------|------------|---------------------|
| P1: GPL contamination (atomsk) | LOW (already rejected) | CRITICAL | LOW | Document in CONTRIBUTING.md |
| P2: Ice rules violation | MEDIUM (if pymatgen path chosen) | HIGH | MEDIUM | Always use GenIce2 for O-networks |
| P3: Unknown cage occupancy | MEDIUM (CIF import) | MEDIUM | MEDIUM | Add cage assessment step |
| P4: Non-orthogonal PBC | MEDIUM (filled ices) | MEDIUM | MEDIUM | Test c0te with existing PBC code |
| P5: Water model compatibility | HIGH (current: TIP4P-ICE only) | MEDIUM | HIGH | Add water model selector |
| P6: FF parameters for exotic guests | HIGH (new guests need .itp) | MEDIUM | HIGH | Bundle validated .itp files |
| P7: Density mismatch at interface | MEDIUM (filled ice + liquid) | LOW | LOW | Add density warning |
| P8: CIF quality | HIGH (CIF import feature) | MEDIUM | HIGH | Add CIF validation layer |
| P9: GenIce2 version compatibility | MEDIUM (dependency updates) | MEDIUM | MEDIUM | Pin GenIce2 version |
| P10: Python 3.14 compatibility | LOW (not yet released) | LOW | LOW | Pin Python to 3.11-3.13 |
| P11: Mixed occupancy GUI | HIGH (primary feature) | LOW | MEDIUM | Simple default + advanced toggle |
| P12: genice2-cif not installed | HIGH (not in environment) | LOW | MEDIUM | Add optional dependency + pre-check |
| P13: Multiple ITP files | HIGH (binary clathrates) | LOW | MEDIUM | Refactor export for multi-guest |

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Filled ice generation (c0te, c1te, c2te) | P4: Non-orthogonal PBC (γ=120°) | Test triclinic cell handling with c0te; verify VTK rendering and GRO export |
| CO2 guest molecule | P6: FF parameters | Create `co2_hydrate.itp` with Zhang-Sprik or GAFF2 parameters; validate against literature |
| Mixed cage occupancy (CH4+CO2) | P11: Mixed occupancy GUI + P13: Multiple ITP files | Design table-based UI; refactor export for multi-guest .itp |
| CIF import | P8: CIF quality + P3: Unknown cage occupancy + P12: genice2-cif not installed | Add CIF validation with pymatgen; add cage assessment step; add genice2-cif optional dep |
| Water model selector | P5: Water model compatibility | Add recommended model per lattice type; bundle ITP files for each model |
| Semiclathrate TBAB | P2: Ice rules (ions break strict depolarization) + P6: FF parameters for TBA/Br | Use `--depol=optimal`; create TBA/Br .itp files with validated parameters |
| Packmol integration | P3: Cage center extraction accuracy | Use GenIce2's `--assess_cages` output for cage centers; validate placement visually |

## Sources

| Source | URL | Confidence |
|--------|-----|------------|
| QuickIce hydrate_generator.py (local) | `quickice/structure_generation/hydrate_generator.py` | HIGH |
| QuickIce types.py HYDRATE_LATTICES, GUEST_MOLECULES (local) | `quickice/structure_generation/types.py` | HIGH |
| QuickIce hydrate_panel.py (local) | `quickice/gui/hydrate_panel.py` | HIGH |
| QuickIce hydrate_export.py (local) | `quickice/gui/hydrate_export.py` | HIGH |
| QuickIce main_window.py cross-tab flow (local) | `quickice/gui/main_window.py` | HIGH |
| GenIce2 CS1/c0te lattice source (inspected) | `genice2.lattices.CS1`, `genice2.lattices.c0te` | HIGH |
| GenIce2 GenIce.__init__ API (inspected) | `genice2.genice.GenIce` | HIGH |
| GenIce2 generate_ice() method (inspected) | `genice2.genice.GenIce.generate_ice` | HIGH |
| genice2-cif NOT installed (verified) | `pip list | grep genice2-cif` → empty | HIGH |
| Stack research (Wave 1) | `.planning/research/future-ml/complex-hydrate-atomsk/STACK.md` | HIGH |
| Features research (Wave 1) | `.planning/research/future-ml/complex-hydrate-atomsk/FEATURES.md` | HIGH |
| GROMACS manual: triclinic boxes | https://manual.gromacs.org/current/reference-manual/topologies/topological-constraints.html | MEDIUM |
| TIP4P-ICE water model paper | Abascal et al., J. Chem. Phys. 122, 234511 (2005) | MEDIUM |
