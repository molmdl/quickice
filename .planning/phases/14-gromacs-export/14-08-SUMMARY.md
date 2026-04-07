---
phase: 14-gromacs-export
plan: 08
completed: 2026-04-07
status: complete
gap_closure: true
---

# 14-08: Update Documentation and GUI Labels

**Objective:** Update documentation and GUI labels for GROMACS export clarity

## Completed Tasks

| Task | Commit | Files Modified |
|------|--------|----------------|
| Add GROMACS export section to README | `7b10914` | README.md |
| Update CLI reference documentation | `5d51163` | docs/cli-reference.md |
| Update GUI guide documentation | `9586fa5` | docs/gui-guide.md |
| Update molecule count label for clarity | `f15f813` | quickice/gui/view.py |

## Additional Fixes During Execution

| Commit | Description |
|--------|-------------|
| `165b7f2` | Manual fix: documentions and topologies - credit topology source, fix output filename units, use Amber defaults |
| `2301646` | Improve CLI GROMACS export behavior |
| `dedee46` | Add TIP4P-ICE credit and clarify GROMACS export |
| `3360d08` | Handle TIP4P atom names in validator |
| `ddb96db` | Handle TIP4P oxygen atom name (OW) in scorer |
| `235f835` | Optimize GROMACS export - single top/itp for all candidates |
| `d3b6ca3` | Update GROMACS export docs - single top/itp for all candidates |
| `cd4da78` | Add CLI GROMACS export sample |
| `41c8788` | Update CLI STDOUT example with the -g flag |
| `ec06bf2` | Fix GUI GROMACS export filename with dots |
| `4a8942a` | Handle TIP4P water in 3D viewer and add missing CLI docs |
| `684c594` | Correct supported ice phases (8, not 12) |

## Deliverables

### Documentation Updates

**README.md:**
- Added comprehensive GROMACS Export section
- Included TIP4P-ICE reference citation (DOI: 10.1063/1.1931662)
- CLI and GUI usage examples
- Water model description

**docs/cli-reference.md:**
- Added `--gromacs` and `--candidate` flags
- Documented GROMACS export workflow
- Explained molecule count distinction (minimum vs actual)

**docs/gui-guide.md:**
- GROMACS export instructions (Ctrl+G shortcut)
- Water model (TIP4P-ICE) documentation
- Exported file descriptions (.gro, .top, .itp)
- Molecule count explanation

### GUI Updates

**quickice/gui/view.py:**
- Changed label from "Number of molecules:" to "Minimum number of molecules:"
- Updated placeholder text to indicate actual count may be higher
- Enhanced help tooltip to explain minimum vs actual distinction

## Must-Haves Verification

| Truth | Status |
|-------|--------|
| User can find GROMACS export documentation in README and docs | ✓ Verified |
| TIP4P-ICE reference citation is available | ✓ DOI included |
| GUI label clarifies minimum vs actual molecule count | ✓ Label updated |

## Issues Resolved

1. **Documentation gaps:** Added complete GROMACS export documentation across README, CLI reference, and GUI guide
2. **TIP4P-ICE citation:** Added proper academic citation with DOI
3. **GUI clarity:** Updated label to clarify minimum molecule count vs actual count due to crystal symmetry

## Testing Notes

- Human checkpoint verified all documentation and GUI changes
- All changes committed with atomic commits
- Working tree clean at completion

---

*Plan completed: 2026-04-07*
