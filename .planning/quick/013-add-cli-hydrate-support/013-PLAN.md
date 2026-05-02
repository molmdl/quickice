---
phase: 013-add-cli-hydrate-support
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - quickice/main.py
autonomous: true

must_haves:
  truths:
    - "CLI accepts --hydrate flag for hydrate generation"
    - "CLI accepts --lattice-type (sI, sII, sH)"
    - "CLI accepts --guest (CH4, THF)"
    - "Hydrate generation works from command line"
    - "Output files generated correctly"
  artifacts:
    - path: "quickice/main.py"
      provides: "CLI with hydrate support"
      contains: "--hydrate"
      contains: "--lattice-type"
      contains: "--guest"
  key_links:
    - from: "quickice/main.py"
      to: "quickice/structure_generation/hydrate_generator.py"
      via: "HydrateGenerator class"
      pattern: "from quickice.structure_generation.hydrate_generator"
---

<objective>
Add CLI support for hydrate structure generation.

Purpose: Enable command-line access to v4.0 hydrate features
Output: CLI accepts hydrate arguments and generates structures
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
  <name>Task 1: Add hydrate arguments to CLI</name>
  <files>quickice/main.py</files>
  <action>
    Extend `quickice/main.py` CLI with hydrate generation support:

    1. **Add hydrate argument group**:
       ```python
       hydrate_group = parser.add_argument_group('hydrate generation')
       hydrate_group.add_argument('--hydrate', action='store_true',
                                   help='Generate hydrate structure')
       hydrate_group.add_argument('--lattice-type', type=str, default='sI',
                                   choices=['sI', 'sII', 'sH'],
                                   help='Hydrate lattice type (default: sI)')
       hydrate_group.add_argument('--guest', type=str, default='CH4',
                                   choices=['CH4', 'THF'],
                                   help='Guest molecule type (default: CH4)')
       ```

    2. **Wire hydrate generation logic**:
       - Import HydrateGenerator and HydrateConfig
       - When --hydrate flag is set:
         ```python
         config = HydrateConfig(lattice_type=args.lattice_type, guest=args.guest)
         generator = HydrateGenerator(config)
         structure = generator.generate()
         ```
       - Integrate with existing export logic (GRO, PDB output)

    3. **Handle mutual exclusivity**:
       - Hydrate mode should work with existing ice generation
       - If both --ice and --hydrate specified, clarify behavior or error

    4. **Test CLI**:
       ```bash
       python -m quickice --hydrate --lattice-type sI --guest CH4 -o hydrate.gro
       ```

    Reference: quickice/structure_generation/hydrate_generator.py
    Reference: quickice/gui/workers/hydrate_worker.py (for usage pattern)
  </action>
  <verify>
    - CLI accepts --hydrate, --lattice-type, --guest
    - Hydrate structure generated successfully
    - Output file created
    - Help text displays new arguments
  </verify>
  <done>CLI supports hydrate generation with lattice type and guest selection</done>
</task>

</tasks>

<verification>
- [ ] --hydrate argument added
- [ ] --lattice-type argument added (sI, sII, sH)
- [ ] --guest argument added (CH4, THF)
- [ ] HydrateGenerator integrated
- [ ] Test: python -m quickice --hydrate --lattice-type sII --guest THF
- [ ] Output file generated
</verification>

<success_criteria>
CLI accepts hydrate arguments and successfully generates hydrate structures from command line.
</success_criteria>

<output>
After completion, create `.planning/quick/013-add-cli-hydrate-support/013-SUMMARY.md`
</output>
