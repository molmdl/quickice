---
status: investigating
trigger: "unit-cell-mismatch"
created: "2026-04-02T00:00:00.000Z"
updated: "2026-04-02T00:00:00.000Z"
---

## Current Focus
hypothesis: Unit cell wireframe box is drawn from origin (0,0,0) assuming orthogonal cell, but actual lattice vectors may be offset or non-orthogonal. This causes misalignment between displayed box and actual molecule positions.
test: 1) Examine cell vectors in generated structure 2) Check if positions start at origin 3) Verify create_unit_cell_actor handles offset cells
expecting: Find that unit cell box originates at (0,0,0) while molecules may be centered elsewhere
next_action: Check actual cell data and positions from generator

## Symptoms
expected: Gridbox unit cell should match init cell, or clarity on which is correct
actual: Two different unit cells displayed - one in gridbox after generation, another after clicking init cell
errors: None reported
reproduction: 1) Generate a structure 2) Observe unit cell in gridbox 3) Click init cell button 4) Observe different unit cell appears
started: Reported on Debian 12 testing of 3D viewer

## Eliminated
<!-- APPEND only - prevents re-investigating -->

## Evidence
<!-- APPEND only - facts discovered -->

## Resolution
root_cause: 
fix: 
verification: 
files_changed: []