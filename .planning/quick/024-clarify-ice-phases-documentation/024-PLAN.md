---
phase: quick-024
plan: 01
type: execute
wave: 1
depends_on: []
files_modified: [README.md]
autonomous: true

must_haves:
  truths:
    - "Users understand which phases can be generated vs only detected"
    - "Documentation accurately reflects GenIce2 capabilities"
    - "No confusion when Ice IX/XI/XV/X selected in phase diagram"
  artifacts:
    - path: "README.md"
      provides: "Updated ice phase documentation"
      contains: "Phase Detection"
  key_links:
    - from: "README.md line 226"
      to: "mapper.py PHASE_TO_GENICE"
      via: "documentation accuracy"
---

<objective>
Clarify ice phase documentation to distinguish between phases that can be detected (12) and phases that can be generated (8).

Purpose: Prevent user confusion when selecting Ice IX/XI/XV/X in the phase diagram and expecting structure generation.
Output: Updated README.md with two clear tables and explanatory note.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md

## Current Issue

**README.md line 228** states: "QuickIce supports 12 ice polymorphs with GenIce2 lattice implementations"

This is misleading because:
- 12 phases CAN be detected in the phase diagram (lookup.py)
- Only 8 phases CAN be generated via GenIce2 (mapper.py)
- Ice IX, XI, XV, X are detectable but NOT generatable

**Impact:** Users selecting Ice IX/XI/XV/X in the phase diagram see phase info but get no candidates generated, leading to confusion.

## Verified Capabilities

**Detection (12 phases):**
- Source: `quickice/phase_mapping/lookup.py`
- Detects based on T/P conditions: Ice Ih, Ic, II, III, IV, V, VI, VII, VIII, IX, XI, XV, X

**Generation (8 phases):**
- Source: `quickice/structure_generation/mapper.py` (PHASE_TO_GENICE)
- ice_ih → ice1h
- ice_ic → ice1c
- ice_ii → ice2
- ice_iii → ice3
- ice_v → ice5
- ice_vi → ice6
- ice_vii → ice7
- ice_viii → ice8

**Missing from generation:**
- Ice IX (ordered Ice III)
- Ice XI (ordered Ice Ih)
- Ice XV (ordered Ice VI)
- Ice X (symmetric high-pressure phase)
</context>

<tasks>

<task type="auto">
  <name>Update README.md Supported Ice Phases section</name>
  <files>README.md</files>
  <action>
Replace lines 226-247 in README.md with two distinct tables:

**Replace this section:**
```markdown
## Supported Ice Phases

QuickIce supports 12 ice polymorphs with GenIce2 lattice implementations:

| Phase | Crystal System | Pressure Range | Temperature Range |
|-------|----------------|----------------|-------------------|
| Ice Ih | Hexagonal | 0-200 MPa | 0-273K |
...
```

**With:**
```markdown
## Ice Phase Support

QuickIce distinguishes between phase detection and structure generation capabilities:

### Phase Detection (12 phases)

The interactive phase diagram can identify 12 ice polymorphs based on temperature and pressure conditions:

| Phase | Crystal System | Pressure Range | Temperature Range |
|-------|----------------|----------------|-------------------|
| Ice Ih | Hexagonal | 0-200 MPa | 0-273K |
| Ice Ic | Cubic | Low pressure | < 150K |
| Ice II | Rhombohedral | 200-600 MPa | < 250K |
| Ice III | Tetragonal | 200-400 MPa | 250-260K |
| Ice IV | Rhombohedral | 400-600 MPa | 250-270K |
| Ice V | Monoclinic | 400-600 MPa | 250-270K |
| Ice VI | Tetragonal | 600-2000 MPa | 250-350K |
| Ice VII | Cubic | > 2000 MPa | 273-355K |
| Ice VIII | Ordered VII | > 2000 MPa | < 273K |
| Ice IX | Ordered III | 200-400 MPa | < 175K |
| Ice XI | Ordered Ih | Low pressure | < 72K |
| Ice X | Symmetric | > 40 GPa | > 273K |

**Note:** Phase boundaries depend on both T and P simultaneously. Ranges above are approximate.

### Structure Generation (8 phases)

GenIce2 lattice implementations are available for 8 ice polymorphs:

| Phase | GenIce Lattice | Notes |
|-------|----------------|-------|
| Ice Ih | ice1h | Most common form |
| Ice Ic | ice1c | Cubic ice |
| Ice II | ice2 | Rhombohedral (no interface support) |
| Ice III | ice3 | Tetragonal |
| Ice V | ice5 | Monoclinic |
| Ice VI | ice6 | Double network |
| Ice VII | ice7 | Double network |
| Ice VIII | ice8 | Ordered Ice VII |

**Detection-only phases:** Ice IX, XI, XV, and X appear in the phase diagram for informational purposes but cannot generate molecular structures. This is a GenIce2 library limitation.

**Interface construction:** All generatable phases except Ice II work with Tab 2 interface generation. Ice II (rhombohedral) cannot form orthogonal supercells.
```

**Why this approach:**
- Two distinct tables make the capability difference crystal clear
- Users immediately see which phases are generatable
- Explicit note about GenIce2 limitation manages expectations
- Preserves all existing T/P range information
- Adds useful GenIce lattice name mapping for technical users
</action>
  <verify>
Check that:
1. README.md contains "### Phase Detection (12 phases)" heading
2. README.md contains "### Structure Generation (8 phases)" heading
3. README.md contains "Detection-only phases: Ice IX, XI, XV, and X" text
4. README.md no longer claims "12 ice polymorphs with GenIce2 lattice implementations"
</verify>
  <done>
README.md accurately documents the distinction between 12 detectable phases and 8 generatable phases. Users selecting Ice IX/XI/XV/X will understand why no candidates are generated.
</done>
</task>

</tasks>

<verification>
- README.md section restructured with two tables
- Clear distinction between detection (12) and generation (8) capabilities
- Explicit note about GenIce2 limitations
- All existing phase information preserved
</verification>

<success_criteria>
- Users understand which phases can generate structures
- Documentation does not mislead about GenIce2 capabilities
- No ambiguity about Ice IX/XI/XV/X support status
</success_criteria>

<output>
After completion, create `.planning/quick/024-clarify-ice-phases-documentation/024-SUMMARY.md`
</output>
