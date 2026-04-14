# Force Field Notes - Phase 30

**Created:** 2026-04-15

## TRAPPE-AA Compatibility Issue

**Problem:** CO2 and H2 from Phase 29 require TRAPPE-AA force field, which may not be compatible with other force fields (TIP4P-ICE for water, OPLS-AA for ions, etc.)

**Current state:**
- Phase 29 GUI lists CO2, H2 as guest molecule options
- TRAPPE-AA is specialized for CO2/H2 but not compatible with TIP4P-family water

**Options:**
1. **Remove** CO2 and H2 from guest options (keep only CH4, THF)
2. **Use separate FF** - accept TRAPPE-AA for guests, not compatible with water/ions
3. **Find compatible** - research if any parameter set works across all

**Recommendation:** Option 1 - Remove CO2 and H2, keep CH4/THF only for now. This is simpler and avoids FF mixing issues.

---

## Ion Force Field - Phase 30

| Option | Status | Notes |
|--------|--------|-------|
| GROMACS built-in (amberGS.ff NA/CL) | Ready to use | Default, no extra files needed |
| Madrid-2019 | Available from user | Better for concentrated solutions |
| User-provided custom | Support via #include | Phase 32 path |

**For planning:** Use GROMACS built-in NA/CL as default.

---

## Guest Molecule FF - Phase 29 (affected)

| Molecule | FF Needed | Provided? |
|----------|------------|-----------|
| CH4 | OPLS-AA or GAFF | No |
| THF | OPLS-AA | No |
| CO2 | TRAPPE-AA | REMOVE (compatibility) |
| H2 | TRAPPE-AA | REMOVE (compatibility) |

**Action needed:** Before testing GROMACS export with guests, user must provide CH4.itp and THF.itp files.

---

*This file tracks FF-related decisions for Phase 30 and affects Phase 29 export functionality.*