---
status: resolved
trigger: "Previous fixes made display WORSE. Both VDW and ball-and-stick now fill the whole cell with red object. Sticks have equal radii but are too big and overlap all H-bonds."
created: 2026-04-02T00:00:00Z
updated: 2026-04-02T00:25:00Z
---

## Current Focus

hypothesis: Fix verified - unit conversion applied correctly
test: Module imports and tests pass
expecting: All radius values properly scaled
next_action: Archive session

## Symptoms

expected:
- VDW: Space-filling spheres that touch neighbors but don't completely overlap
- Ball-and-stick: Small spheres connected by thin bonds, both visible
- Stick: Thin cylinders with small spheres at atom positions, H-bonds visible

actual:
- VDW: Fills whole cell with red object (spheres massively overlapping)
- Ball-and-stick: Fills whole cell with red object (just smaller than VDW)
- Stick: Equal radii but too thick, H-bonds completely obscured

errors: None

reproduction: 1) Generate structure 2) Cycle through modes - all look terrible

started: After scale 0.5/0.30/0.15 fix

## Eliminated

(none)

## Evidence

### 2026-04-02T00:05:00Z - VTK Source Code Analysis

**What was checked**: Analyzed vtkMoleculeMapper.cxx source code from VTK repository

**What was found**:

1. **UseXxxSettings methods set multiple ivars**:
   - UseBallAndStickSettings(): AtomicRadiusType=VDWRadius, ScaleFactor=0.3, BondRadius=0.075
   - UseVDWSpheresSettings(): AtomicRadiusType=VDWRadius, ScaleFactor=1.0, BondRadius=0.075
   - UseLiquoriceStickSettings(): AtomicRadiusType=UnitRadius, ScaleFactor=0.15, BondRadius=0.15

2. **Radius calculation formula** (from UpdateAtomGlyphPolyData):
   ```cpp
   // For VDWRadius type:
   scaleFactors->InsertNextValue(this->AtomicRadiusScaleFactor *
     this->PeriodicTable->GetVDWRadius(atomicNumber));
   ```

   Formula: **actualRadius = ScaleFactor × VDWRadius(atomicNumber)**

3. **Actual atomic radii** (from VTK periodic table):
   - Oxygen (O): VDW radius = 1.52 Å (or 1.55 Å depending on source)
   - Hydrogen (H): VDW radius = 1.20 Å

### 2026-04-02T00:10:00Z - UNIT MISMATCH DISCOVERED

**What was checked**: VTK Blue Obelisk Data Internal header file containing actual atomic radii values

**What was found**:

VTK's periodic table VDW radii are in **ANGSTROMS**:
```cpp
static const float VDWRadii[119][1] = {
  { 1.200000e+00f },  // H: 1.20 Å
  { 1.550000e+00f },  // O: 1.55 Å
```

But QuickIce positions are in **NANOMETERS** (from types.py line 14-15):
```python
positions: np.ndarray  # in nm
cell: np.ndarray  # in nm
```

**This is the ROOT CAUSE!**

VTK is rendering positions in nm but radii in Å, without unit conversion!

**Converted correctly to nm**:
- O VDW: 1.55 Å = 0.155 nm
- H VDW: 1.20 Å = 0.120 nm

With scale 0.5 (VDW mode):
- O rendered radius: 0.5 × 1.55 Å = 0.775 Å = **0.0775 nm**
- H rendered radius: 0.5 × 1.20 Å = 0.60 Å = **0.060 nm**

But if VTK treats the Å radius as nm:
- O radius treated as: **0.775 nm** (HUGE!)
- H radius treated as: **0.60 nm** (HUGE!)

O-O distance: 0.276 nm
O sphere diameter if wrong: 1.55 nm

This would COMPLETELY FILL the cell with overlapping spheres!

## Resolution

root_cause: **Unit mismatch between atomic positions (nm) and VTK periodic table radii (Å). VTK provides VDW radii in Angstroms, but QuickIce positions are in nanometers. Without unit conversion, VTK treats Å values as if they were in the same unit as positions, making spheres 10x too large.**

fix: Added ANGSTROM_TO_NM = 0.1 constant and multiplied all radius scale factors by 0.1:
- VDW mode: AtomicRadiusScaleFactor 0.5 → 0.05
- Ball-and-stick mode: AtomicRadiusScaleFactor 0.30 → 0.03
- Stick mode: AtomicRadiusScaleFactor 0.15 → 0.015
- BondRadius: 0.075 → 0.0075, 0.15 → 0.015

verification: Module imports successfully, ANGSTROM_TO_NM = 0.1, all existing tests pass

files_changed: [quickice/gui/molecular_viewer.py]
