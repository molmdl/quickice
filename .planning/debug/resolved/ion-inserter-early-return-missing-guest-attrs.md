---
status: resolved
trigger: "ion-inserter-early-return-missing-guest-attrs: The first early-return path in IonInserter.replace_water_with_ions() is missing guest_nmolecules and guest_atom_count"
created: 2026-06-19T00:00:00Z
updated: 2026-06-19T00:01:00Z
---

## Current Focus

hypothesis: CONFIRMED — Path 1 missing guest attrs
test: Added guest_nmolecules and guest_atom_count to Path 1 IonStructure constructor
expecting: Guest data now propagates correctly on all three paths
next_action: Archive session

## Symptoms

expected: All three early-return paths in replace_water_with_ions() should propagate guest_nmolecules and guest_atom_count to IonStructure
actual: The first early-return path (~line 235, "no water molecules found in structure") constructs IonStructure WITHOUT guest_nmolecules or guest_atom_count — they default to 0, losing guest data
errors: If the inserter hits this path, exported .gro and .top files will have no guest molecules even though the input structure had them
reproduction: Pass a structure to IonInserter.replace_water_with_ions() that has guest molecules but no water molecules
started: The other two early-return paths were fixed in commit 13d0302 but guest attrs for path 1 were missed

## Eliminated

## Evidence

- timestamp: 2026-06-19T00:00:00Z
  checked: ion_inserter.py lines 235-256 (Path 1 IonStructure constructor)
  found: Path 1 IonStructure constructor is missing guest_nmolecules and guest_atom_count kwargs
  implication: Guest data will be lost when Path 1 is hit, defaults to 0

- timestamp: 2026-06-19T00:00:00Z
  checked: ion_inserter.py lines 277-300 (Path 2 IonStructure constructor)
  found: Path 2 has guest_nmolecules=getattr(structure, 'guest_nmolecules', 0) and guest_atom_count=getattr(structure, 'guest_atom_count', 0)
  implication: Confirms Path 2 was correctly fixed

- timestamp: 2026-06-19T00:00:00Z
  checked: ion_inserter.py lines 329-352 (Path 3 IonStructure constructor)
  found: Path 3 has guest_nmolecules and guest_atom_count
  implication: Confirms Path 3 was correctly fixed

- timestamp: 2026-06-19T00:00:30Z
  checked: types.py IonStructure dataclass defaults
  found: guest_nmolecules: int = 0 and guest_atom_count: int = 0 are defaults
  implication: Omitting these kwargs causes silent data loss (defaults to 0)

- timestamp: 2026-06-19T00:00:45Z
  checked: Applied fix + ran all ion-related tests (26 tests)
  found: All 26 tests pass including 6 new regression tests
  implication: Fix is verified with no regressions

## Resolution

root_cause: Path 1 (no water found, line 235-256) IonStructure constructor was missing guest_nmolecules and guest_atom_count kwargs — they were omitted when commit 13d0302 added them to Paths 2 and 3 only
fix: Added guest_nmolecules=getattr(structure, 'guest_nmolecules', 0) and guest_atom_count=getattr(structure, 'guest_atom_count', 0) to the IonStructure constructor in Path 1, matching the pattern used in Paths 2 and 3
verification: 26 ion-related tests pass (14 e2e + 3 scancode + 1 hydrate + 2 solute + 6 new Path 1 regression tests). New tests specifically verify guest attr propagation through Path 1 early return.
files_changed:
  - quickice/structure_generation/ion_inserter.py: Added guest_nmolecules and guest_atom_count to Path 1 IonStructure constructor
  - tests/test_ion_path1_guest_attrs.py: New regression test file with 6 tests
