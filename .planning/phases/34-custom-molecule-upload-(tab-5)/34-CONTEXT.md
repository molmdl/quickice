# Phase 34: Custom Molecule Upload - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Upload custom molecules via .gro/.itp file pairs and insert them into liquid water with validation. Users can choose between random placement (with overlap checking) or precise placement (specifying center-of-mass position and rotation).

This phase does NOT include: solute selection from predefined molecules (Phase 33), ion insertion (separate tab), or 3D preview rotation widgets (future enhancement).

</domain>

<decisions>
## Implementation Decisions

### File Upload Workflow

- **Separate upload buttons** — One button for .gro file, one button for .itp file (not combined dialog)
- **Mismatched residue name handling** — When .gro and .itp have different residue names:
  - Show dialog asking if .itp residue name should override
  - If user accepts: proceed with .itp residue name
  - If user declines: block and require re-selection
- **Button state after selection** — Upload button shows selected filename with clear/replace option nearby
- **Post-validation workflow** — After both files successfully validated:
  - Show molecule info (atom count, residue name)
  - Then allow user to configure placement settings

### Placement Mode Controls

- **Mode selection UI** — Dropdown with dynamic controls (controls appear below based on selection)
- **Liquid region detection prerequisite** — Before showing placement controls, detect liquid region to constrain XYZ position ranges
- **Default mode** — Random placement is the default mode when controls first appear
- **Value persistence** — User-configured values (position, rotation) are preserved when switching between Random and Custom modes
- **Custom mode multi-molecule support** — Custom mode allows placing multiple molecules, each with different positions

### Position & Rotation Input

- **Position input** — Text fields for X, Y, Z coordinates (not spin boxes or sliders)
- **Rotation input** — Numeric inputs for Euler angles (α, β, γ) in degrees
  - Note: 3D preview widget deferred to future enhancement (not needed for symmetrical small molecules)
  - Planner should note this as future improvement
- **Multiple position management** — Sequential add with count:
  - Add positions one at a time
  - "Add Another" button
  - Running count of positions added
- **Default values** — New custom position defaults to:
  - Position: center of detected liquid region
  - Rotation: (0°, 0°, 0°)

### OpenCode's Discretion

- **Error presentation details** — Exact wording of validation error messages, inline vs modal presentation (user did not select this area for discussion)
- **UI layout specifics** — Exact spacing, typography, control arrangement
- **Validation progress feedback** — How to show "validating..." state
- **Molecule info display format** — How atom count, residue name, etc. are presented

</decisions>

<specifics>
## Specific Ideas

- "Detect liquid region to limit XYZ range for placement" — constrains where molecules can be inserted
- Numeric inputs preferred for rotation (simpler than visual widgets for this phase)
- Future consideration: 3D preview would be useful for future tabs with larger/more complex molecules

</specifics>

<deferred>
## Deferred Ideas

- **3D rotation preview widget** — Would be useful for future tabs with larger/asymmetric molecules. Note for planning documentation.
- **Drag-and-drop file upload** — Could be added later as convenience feature

</deferred>

---

*Phase: 34-custom-molecule-upload-(tab-5)*
*Context gathered: 2026-05-05*
