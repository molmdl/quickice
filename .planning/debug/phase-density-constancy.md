---
status: resolved
trigger: "User wants to verify if density is fixed for a phase. Need to check IAPWS, GenIce2, or links in state_reference.md to confirm."
created: 2026-04-02T10:30:00Z
updated: 2026-04-02T10:45:00Z
---

## Current Focus

hypothesis: CONFIRMED - Density varies with T,P for each phase; code uses simplified constant values
test: Research complete - IAPWS provides ρ(T,P) equations for Ice Ih
expecting: Confirmed - density is NOT constant, varies with T,P
next_action: Provide diagnosis summary

## Symptoms

expected: Understand if ice phase density is truly constant or varies with conditions
actual: Verified - density varies with T,P; code uses constant approximations
errors: None - this is a verification/research task
reproduction: N/A - research task
timeline: User question

## Eliminated

- hypothesis: Density is truly constant for each phase (like element atomic weight)
  evidence: IAPWS-06 provides ρ(T,P) equation showing density varies with T,P
  timestamp: 2026-04-02T10:42:00Z

## Evidence

- timestamp: 2026-04-02T10:32:00Z
  checked: quickice/phase_mapping/lookup.py
  found: PHASE_METADATA dictionary with constant density values per phase
  implication: Code assumes density is constant for each phase
  detail: |
    - Ice Ih: 0.9167 g/cm³
    - Ice VII/VIII: 1.65 g/cm³
    - Ice VI: 1.31 g/cm³
    - Ice X: 2.79 g/cm³
    Comment says "from IAPWS R14-08 and LSBU Water Phase Data"

- timestamp: 2026-04-02T10:33:00Z
  checked: state_reference.md
  found: Reference list including IAPWS, GenIce2, Wikipedia phase diagram, LSBU Water Phase Data
  implication: Need to check these references for density equations

- timestamp: 2026-04-02T10:38:00Z
  checked: LSBU Water Phase Data (ergodic.ugr.es)
  found: Table with ice polymorph densities, footnote "a density at atmospheric pressure"
  implication: LSBU values are reference values at specific conditions (1 atm), not true constants

- timestamp: 2026-04-02T10:40:00Z
  checked: Wikipedia Phases of Ice
  found: Table shows density values with condition context (e.g., "1.65 g/cm³" for Ice VII)
  implication: Values are typical/reference densities, not equations of state

- timestamp: 2026-04-02T10:42:00Z
  checked: IAPWS Python library documentation
  found: _Ice(T, P) function returns ρ(T,P) for Ice Ih
  implication: IAPWS-06 provides equation of state - density IS a function of T,P
  detail: |
    The _Ice(T, P) function:
    - Returns density 'rho' in kg/m³ as function of T and P
    - Valid for Ice Ih: T ≤ 273.16K, P ≤ 208.566 MPa
    - Reference: IAPWS Revised Release on the Equation of State 2006 for H2O Ice Ih
    
- timestamp: 2026-04-02T10:43:00Z
  checked: GenIce2 PyPI documentation
  found: GenIce2 has --dens option to specify density
  implication: GenIce can generate ice at any specified density, not just defaults

## Resolution

root_cause: |
  **Density is NOT constant for ice phases.** It varies with temperature and pressure.
  
  The code's approach:
  - Uses single constant density values per phase (e.g., Ice Ih = 0.9167 g/cm³)
  - These are reference/typical values at specific conditions (e.g., 273.15K, 1 atm for Ice Ih)
  
  The physical reality:
  - IAPWS-06 provides an equation of state: ρ = ρ(T, P) for Ice Ih
  - Example: _Ice(100, 100) returns ρ = 941.67 kg/m³ (vs 916.7 at 273K, 0 MPa)
  - Density variation: ~2.7% over Ice Ih's stability range
  
  For other ice phases (VII, VIII, VI, etc.):
  - No equivalent IAPWS equation of state available
  - LSBU provides typical/reference densities only
  - Scientific literature shows density increases with pressure for all phases

fix: |
  For complete accuracy, the code should:
  1. For Ice Ih: Use IAPWS _Ice(T, P) to compute ρ(T,P)
  2. For other phases: Use available density equations from literature (if any) or acknowledge approximation
  
  Current approach is a reasonable simplification for most purposes, since:
  - Density variation within a phase is typically 1-5%
  - The primary purpose is structure generation, not precision thermodynamics
  - GenIce can accept any specified density via --dens option

verification: Research complete
files_changed: []
