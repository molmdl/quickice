# Prompt 6: Code Refactoring

**Workflow:** `/gsd-plan-phase`
**Priority:** LOW

---

## Prompt to Paste

```
Phase: Code Refactoring

Goals:
1. Split gromacs_writer.py (1559 lines) into smaller modules
2. Split main_window.py (1317 lines) into smaller modules
3. Split phase_diagram.py (1132 lines) into smaller modules
4. Remove deprecated atoms_per_molecule heuristic in water_filler.py
5. Add CLI support for hydrate generation (--hydrate, --lattice-type, --guest)
6. Add CLI support for ion insertion (--insert-ions, --ion-concentration)
7. Add progress reporting for long CLI operations

Reference: .planning/codebase/CONCERNS.md
Reference: .planning/codebase/ARCHITECTURE.md
```
