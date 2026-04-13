# Documentation Context Dump - Ice II Interface Block

## Summary

Ice II (rhombohedral, space group R-3) is now **permanently blocked** for all interface modes with a clear error message. This is a fundamental crystallographic constraint - Ice II cannot have an orthogonal supercell.

## Technical Details

### Why Ice II Doesn't Work

- **Ice II lattice vectors**: `a=[1.556,0,0]`, `b=[-0.610,1.431,0]`, `c=[-0.610,-0.924,1.093]`
- Both `b[0]` and `c[0]` are negative, creating a **parallelogram** XY projection
- When tiling a parallelogram into an orthogonal box, **triangular gaps are geometrically unavoidable**
- Exhaustive search found zero orthogonal triples for any integer combination

### Why Ice V Works

- Ice V has `b[0]=0`, only `c[0]` is negative
- XY projection is **rectangular**, so it tiles cleanly into orthogonal boxes

### Supported Triclinic Phases

| Phase | Temperature | Pressure | Status |
|-------|-------------|----------|--------|
| Ice V | 253K | 500 MPa | ✅ Works correctly |
| Ice VI | 180K | 1000 MPa | ✅ Works correctly |
| Ice II | 238K | 300 MPa | ❌ Blocked - crystallographic constraint |

## Error Message

When users try Ice II interfaces, they see:

```
InterfaceGenerationError: [slab/piece/pocket] Ice II (rhombohedral, space group R-3) is not supported for interface generation.

Ice II has a rhombohedral crystal structure that cannot be transformed to an orthogonal supercell (this is a fundamental crystallographic constraint). When forced into an orthogonal simulation box, Ice II develops triangular gaps at the corners, leaving significant empty regions.

Supported triclinic phases:
  • Ice V: Works correctly (rectangular XY projection)
  • Ice VI: Works correctly

For Ice II interfaces, consider using a different phase or contact support for future triclinic box output.
```

## Files Modified

| File | Change |
|------|--------|
| `quickice/structure_generation/interface_builder.py` | Added Ice II validation (lines 119-132) |
| `tests/test_triclinic_interface.py` | Tests now expect Ice II rejection |
| `tests/test_integration_v35.py` | Tests now use Ice V for triclinic testing |

## Documentation Tasks Needed

1. **README.md**: Update supported phases section to note Ice II limitation
2. **Docs**: Add crystallographic constraints explanation for triclinic phases
3. **In-app help**: Show warning when user selects T=238K, P=300MPa (Ice II region)
4. **Info panel**: Display phase support status (Ice II: "Not supported for interfaces")

## Commit

- **Hash**: `afb0394`
- **Message**: fix: block Ice II interface generation with clear error message