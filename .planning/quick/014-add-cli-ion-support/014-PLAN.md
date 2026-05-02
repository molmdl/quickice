---
phase: 014-add-cli-ion-support
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - quickice/main.py
autonomous: true

must_haves:
  truths:
    - "CLI accepts --insert-ions flag for ion insertion"
    - "CLI accepts --ion-concentration (mol/L)"
    - "CLI accepts --cation and --anion types"
    - "Ion insertion works from command line"
    - "Ions appear in output files"
  artifacts:
    - path: "quickice/main.py"
      provides: "CLI with ion insertion support"
      contains: "--insert-ions"
      contains: "--ion-concentration"
  key_links:
    - from: "quickice/main.py"
      to: "quickice/structure_generation/ion_inserter.py"
      via: "IonInserter class"
      pattern: "from quickice.structure_generation.ion_inserter"
---

<objective>
Add CLI support for ion insertion into liquid phase.

Purpose: Enable command-line access to v4.0 ion insertion features
Output: CLI accepts ion arguments and inserts ions into structures
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/codebase/ARCHITECTURE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add ion insertion arguments to CLI</name>
  <files>quickice/main.py</files>
  <action>
    Extend `quickice/main.py` CLI with ion insertion support:

    1. **Add ion insertion argument group**:
       ```python
       ion_group = parser.add_argument_group('ion insertion')
       ion_group.add_argument('--insert-ions', action='store_true',
                              help='Insert ions into liquid phase')
       ion_group.add_argument('--ion-concentration', type=float, default=0.15,
                              help='Ion concentration in mol/L (default: 0.15)')
       ion_group.add_argument('--cation', type=str, default='NA',
                              help='Cation type (default: NA)')
       ion_group.add_argument('--anion', type=str, default='CL',
                              help='Anion type (default: CL)')
       ```

    2. **Wire ion insertion logic**:
       - Import IonInserter
       - When --insert-ions flag is set:
         ```python
         inserter = IonInserter(concentration=args.ion_concentration,
                                cation=args.cation,
                                anion=args.anion)
         structure = inserter.insert_ions(structure)
         ```
       - Calculate ion count from concentration and box volume
       - Apply after structure generation (ice, hydrate, or interface)

    3. **Integrate with existing modes**:
       - Can combine with --ice, --hydrate, or --interface
       - Insert ions into liquid phase of generated structure

    4. **Test CLI**:
       ```bash
       python -m quickice --ice Ih --insert-ions --ion-concentration 0.2 -o ice_with_ions.gro
       ```

    Reference: quickice/structure_generation/ion_inserter.py
    Reference: quickice/gui/workers/ion_worker.py (for usage pattern)
  </action>
  <verify>
    - CLI accepts --insert-ions, --ion-concentration, --cation, --anion
    - Ions inserted successfully
    - Ion count matches concentration calculation
    - Output file contains ions (check .gro file for NA/CL residues)
  </verify>
  <done>CLI supports ion insertion with concentration and ion type selection</done>
</task>

</tasks>

<verification>
- [ ] --insert-ions argument added
- [ ] --ion-concentration argument added
- [ ] --cation argument added
- [ ] --anion argument added
- [ ] IonInserter integrated
- [ ] Test: python -m quickice --ice Ih --insert-ions --ion-concentration 0.2
- [ ] Output file contains ion residues (NA, CL)
</verification>

<success_criteria>
CLI accepts ion insertion arguments and successfully inserts ions into structures from command line.
</success_criteria>

<output>
After completion, create `.planning/quick/014-add-cli-ion-support/014-SUMMARY.md`
</output>
