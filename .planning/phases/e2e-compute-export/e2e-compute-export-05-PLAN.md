---
phase: e2e-compute-export
plan: 05
type: execute
wave: 3
depends_on: ["e2e-compute-export-01", "e2e-compute-export-04"]
files_modified:
  - tests/test_e2e_chain_export_2.py
  - tests/test_e2e_cross_chain_invariants.py
autonomous: true

must_haves:
  truths:
    - "F5 chain (Interface→Ion) export produces .gro with SOL→NA→CL (minimal chain)"
    - "F6 chain (Interface→Solute→Ion) export produces .gro with SOL→CH4_L→NA→CL"
    - "F7 chain (Interface→Solute(THF)→Ion) export produces .gro with SOL→THF_L→NA→CL"
    - "Deeper chains have more ITP files than shallower chains"
    - "Base atom count (ice+water) is preserved across all chain depths"
  artifacts:
    - path: "tests/test_e2e_chain_export_2.py"
      provides: "Simple chain export bridge tests F5-F7"
      contains: "class TestChainF5"
    - path: "tests/test_e2e_cross_chain_invariants.py"
      provides: "Cross-chain invariant tests (ITP cumulative counts, atom conservation)"
      contains: "class TestCrossChainInvariants"
  key_links:
    - from: "tests/test_e2e_chain_export_2.py"
      to: "quickice/output/gromacs_writer.py"
      via: "direct calls to write_ion_gro_file / write_ion_top_file"
      pattern: "write_ion_(gro|top)_file"
    - from: "tests/test_e2e_cross_chain_invariants.py"
      to: "tests/test_e2e_chain_export_1.py"
      via: "comparison of F5-F7 ITP counts against F1-F4 reference"
      pattern: "ITP"
---

<objective>
Create simple chain export tests (F5-F7) and cross-chain invariant validation tests that verify cumulative ITP counts and atom conservation across chain depths.

Purpose: Cover the remaining 3 chain scenarios (F5: minimal, F6: solute CH4, F7: solute THF) and add cross-chain invariant checks that catch data loss across pipeline steps by comparing chain depth vs ITP count vs molecule type count.

Output: tests/test_e2e_chain_export_2.py (3 classes, ~9 methods) + tests/test_e2e_cross_chain_invariants.py (1 class, ~4 methods)
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/e2e-compute-export/e2e-compute-export-RESEARCH.md
@tests/e2e_export_helpers.py
@tests/conftest.py
@quickice/output/gromacs_writer.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create simple chain export tests F5-F7</name>
  <files>tests/test_e2e_chain_export_2.py</files>
  <action>
Create tests/test_e2e_chain_export_2.py with 3 test classes.

**F5: Interface→Ion** (class `TestChainF5`)
- Uses `interface_slab` fixture from conftest.py
- Build chain: `ion = _insert_ions(interface_slab, concentration=0.15)` (direct, no intermediate steps)
- Generate ion.itp: `write_ion_itp(tmp_path / "ion.itp", ion.na_count, ion.cl_count)`
- Export: `write_ion_gro_file(ion, gro_path)`, `write_ion_top_file(ion, top_path)`
- Validates ALL 7 checks:
  1. GRO residue names: SOL→NA→CL (minimal — only 3 molecule types)
  2. GRO atom count: header matches actual lines
  3. TOP [molecules]: SOL, NA, CL
  4. TOP #include: ["tip4p-ice.itp", "ion.itp"] (minimal — only 2 ITPs)
  5. ITP files: tip4p-ice.itp and ion.itp exist with [ moleculetype ]
  6. No guests, no custom, no solutes: all zero
  7. Atom conservation: molecule_index sum == positions.shape[0]

**F6: Interface→Solute→Ion** (class `TestChainF6`)
- Uses `interface_slab` fixture
- Build chain: `solute = _insert_solutes(interface_slab, 'CH4', 0.3)` → `ion = _insert_ions_from_solute(solute, 0.15)`
- Register: `registry.register_liquid_solute("CH4")` before insert_solutes
- Generate ion.itp, export, validate ALL 7 checks:
  1. GRO: SOL→CH4_L→NA→CL (4 molecule types, no custom)
  2. TOP [molecules]: SOL, CH4_L, NA, CL
  3. TOP #include: ["tip4p-ice.itp", "ch4_liquid.itp", "ion.itp"] (3 ITPs)
  4. No custom molecules: `ion.custom_molecule_count == 0`
  5. Solute preserved: `ion.solute_type == "CH4"`, `ion.solute_n_molecules > 0`

**F7: Interface→Solute(THF)→Ion** (class `TestChainF7`)
- Uses `interface_slab` fixture
- Build chain: `solute = _insert_solutes(interface_slab, 'THF', 0.15)` → `ion = _insert_ions_from_solute(solute, 0.15)`
- Register: `registry.register_liquid_solute("THF")` before insert_solutes
- Generate ion.itp, export, validate ALL 7 checks:
  1. GRO: SOL→THF_L→NA→CL (THF = 5 chars, fits GRO limit)
  2. TOP [molecules]: SOL, THF_L, NA, CL
  3. TOP #include: ["tip4p-ice.itp", "thf_liquid.itp", "ion.itp"] (3 ITPs)
  4. Solute preserved: `ion.solute_type == "THF"`, `ion.solute_n_molecules > 0`
  5. THF atom count: each THF_L has 13 atoms (not 5 like CH4)

**CRITICAL:** F6 and F7 use `_insert_ions_from_solute()` with BUG I5 workaround. F5 uses `_insert_ions()` directly (no workaround needed).

**IMPORTANT:** THF solute (THF_L) has 13 atoms per molecule. CH4 solute (CH4_L) has 5 atoms per molecule. This affects atom count expectations in the GRO file.
  </action>
  <verify>cd /share/home/nglokwan/quickice && python -m pytest tests/test_e2e_chain_export_2.py -v --timeout=180 -x</verify>
  <done>F5-F7 chain export tests pass with all 7 validation checks per chain</done>
</task>

<task type="auto">
  <name>Task 2: Create cross-chain invariant tests</name>
  <files>tests/test_e2e_cross_chain_invariants.py</files>
  <action>
Create tests/test_e2e_cross_chain_invariants.py with 1 test class that validates structural invariants ACROSS chains.

**class `TestCrossChainInvariants`** — these tests compare properties across chains to catch data loss:

1. `test_itp_count_increases_with_chain_depth` — Build chains F5, F6, F1 and export. Count #include ITP files in each .top:
   - F5 (Interface→Ion): 2 ITPs (tip4p-ice.itp + ion.itp)
   - F6 (Interface→Solute→Ion): 3 ITPs (tip4p-ice.itp + ch4_liquid.itp + ion.itp)
   - F1 (Interface→Custom→Solute→Ion): 4 ITPs (tip4p-ice.itp + etoh.itp + ch4_liquid.itp + ion.itp)
   Assert: `len(f5_includes) < len(f6_includes) < len(f1_includes)`

2. `test_base_atom_count_preserved_across_chains` — Build F5 and F1 from SAME interface_slab fixture. Compare SOL molecule count in [molecules] section. The SOL count should be identical because neither chain adds or removes water molecules. Assert: `f5_molecules["SOL"] == f1_molecules["SOL"]`

3. `test_molecule_type_count_increases_with_chain_depth` — Count number of distinct molecule types in [molecules] section:
   - F5: 3 types (SOL, NA, CL)
   - F6: 4 types (SOL, CH4_L, NA, CL)
   - F1: 5 types (SOL, ETOH, CH4_L, NA, CL)
   Assert: `len(f5_molecules) < len(f6_molecules) < len(f1_molecules)`

4. `test_hydrate_chain_adds_guest_itp` — Build F5 (no hydrate) and F3 (hydrate→solute→ion). Compare #include lists. F3 should include "ch4_hydrate.itp" which F5 does NOT have. Assert: `"ch4_hydrate.itp" in f3_includes` and `"ch4_hydrate.itp" not in f5_includes`

**Implementation notes:**
- Build all chains inline using helpers from e2e_export_helpers.py
- Use `interface_slab` fixture for F5, F6, F1 comparisons (same fixture = same base structure)
- F3 uses inline hydrate candidate generation: `_hydrate_sI_ch4_candidate()` + `_make_slab_interface()`
- Register registry for each chain appropriately (register_liquid_solute for CH4/THF, register_hydrate_guest for F3)
- Generate ion.itp for each chain's final structure
- Compare ITP counts from parse_top_includes(), molecule counts from parse_top_molecules()
  </action>
  <verify>cd /share/home/nglokwan/quickice && python -m pytest tests/test_e2e_cross_chain_invariants.py -v --timeout=180 -x</verify>
  <done>Cross-chain invariant tests pass: ITP count increases with depth, base atoms preserved, molecule type count increases, hydrate chains add guest ITP</done>
</task>

</tasks>

<verification>
1. pytest tests/test_e2e_chain_export_2.py passes (3 classes, ~9 methods)
2. pytest tests/test_e2e_cross_chain_invariants.py passes (1 class, ~4 methods)
3. F5: minimal chain with 3 molecule types and 2 ITPs
4. F6: CH4 solute chain with 4 types and 3 ITPs
5. F7: THF solute chain with 4 types and 3 ITPs
6. Cross-chain: ITP count monotonically increases with depth
7. Cross-chain: SOL count constant across chains from same interface
8. Cross-chain: molecule type count increases with depth
</verification>

<success_criteria>
- tests/test_e2e_chain_export_2.py exists with 3 test classes, all pass
- tests/test_e2e_cross_chain_invariants.py exists with 1 test class, all pass
- F5-F7 chain exports validated with real GenIce2 data
- Cross-chain invariants catch data loss across pipeline depths
- ITP cumulative count validated: F5(2) < F6(3) < F1(4) < F4(5)
- THF_L 13-atom molecule count validated in F7
</success_criteria>

<output>
After completion, create `.planning/phases/e2e-compute-export/e2e-compute-export-05-SUMMARY.md`
</output>
