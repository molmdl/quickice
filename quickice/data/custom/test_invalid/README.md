# Test Invalid Molecule Files

Intentionally **invalid or problematic** molecule files for testing error/warning handling.
Do NOT use these as examples of correct input files.

For valid examples, see parent directory: `quickice/data/custom/etoh.gro` and `etoh.itp`.

## Files

| File | Issue | Purpose |
|------|-------|---------|
| `etoh_mismatch.gro` | Header says 9 atoms, body has only 6 | Test atom count mismatch error |
| `not_a_gro.txt` | Plain text, not GRO format | Test invalid file type error |
| `etoh_no_atomtypes.itp` | Missing `[ atomtypes ]` section | Test missing atomtypes warning |
| `na_single.gro` | Single Na+ ion (charge +0.85) | Test non-neutral charge warning |
| `na_single.itp` | Paired ITP for na_single.gro | Paired with na_single.gro |
