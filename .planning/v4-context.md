# v4.0 Molecule Insertion — Future Context

**Status:** Deferred until v3.5 complete
**Defined:** 2026-04-12

---

## Goal

Add molecule insertion capabilities to interface systems via new tabs.

---

## Tab Structure (4 tabs)

| Tab | Name | Purpose |
|-----|------|---------|
| Tab 1 | Ice Generation | (existing) Pure ice generation |
| Tab 2 | Molecules to Ice | GenIce hydrates + custom molecules |
| Tab 3 | Interface Construction | (existing) Ice-water interfaces |
| Tab 4 | Insert to Liquid | Ions + custom molecules to liquid phase |

---

## Tab 2: Molecules to Ice

**Use case:** Generate clathrate hydrates or insert molecules into ice lattice.

### Features

1. **GenIce2 Hydrate Support**
   - List of supported molecules from GenIce2
   - User provides topology (.itp) for selected molecule
   - Single or multiple molecule insertion
   - Correct unit cell for methane hydrate (different from Tab 1)

2. **Custom Molecules to Ice**
   - User-provided .gro + .itp files
   - Placement: replace Tab 1 operation or post-process
   - Optional: user-specified orientation

### Inputs

- Molecule selection (from GenIce2 list or custom)
- Topology file (.itp)
- Coordinates (.gro) — for custom
- Number of molecules

---

## Tab 4: Insert to Liquid

**Use case:** Add ions or solutes to the liquid water phase of an interface.

### Features

1. **Salt (NaCl)**
   - Input: concentration (mol/L or g/kg)
   - Auto-calculate number of Na+ and Cl- ions
   - Replace water molecules, NOT ice molecules
   - Use TIP4P-ICE compatible ion parameters

2. **Custom Molecules**
   - User-provided .gro + .itp files
   - Two placement modes:
     - **Random:** Random positions in liquid phase
     - **Custom:** User-specified center-of-mass (x, y, z) + rotation matrix

### Inputs

- Ion/molecule selection
- Concentration or count
- Placement mode (random/custom)
- Custom COM coordinates (if custom mode)
- Topology file (.itp)
- Coordinates (.gro)

---

## 3D Viewer Enhancements

### Display Styles by Molecule Type

| Type | Default Style | Color |
|------|---------------|-------|
| Ice (water) | Lines | Cyan |
| Liquid (water) | Lines | Cornflower blue |
| Ions (Na+, Cl-) | VDW spheres | Yellow/green |
| Small molecules | Ball-and-stick | Orange |
| Large molecules | Stick | Magenta |

### Controls

- Toggle visibility per molecule type
- Style selection dropdown per type
- Color picker per type

---

## GROMACS Export

- Single .top file with all molecule types
- Include all .itp files (bundled + user-provided)
- Molecule type ordering: SOL, ions, solutes

---

## Dependencies

- No new libraries required
- GenIce2 already supports hydrate generation
- scipy for spatial placement
- VTK already supports multiple actor styles

---

## Technical Notes

1. **Ion insertion:** Must avoid replacing ice molecules (use collision detection to identify liquid vs ice regions)

2. **Hydrate unit cells:** Methane hydrate structure I/II have different unit cells than pure ice Ih — GenIce2 handles this

3. **Topology bundling:** User-provided .itp files should be bundled with export or referenced with absolute paths

4. **Placement validation:** Check for overlaps after insertion, warn if clashes detected

---

## Open Questions (to resolve before v4.0 planning)

1. Should hydrate generation replace Tab 1 or be a separate workflow?
2. Should custom molecule insertion validate against GenIce2?
3. How to handle multiple different custom molecules (multiple .gro/.itp pairs)?
4. Should ion parameters be bundled or user-provided?

---

*Context saved: 2026-04-12*
*Use when starting v4.0 milestone*
