# QuickIce Principles

This document explains the philosophy, approach, and design decisions behind QuickIce.

## What QuickIce Does

QuickIce generates ice structure candidates for given thermodynamic conditions (temperature and pressure). Given T and P inputs, it:

1. **Maps conditions to ice phases** - Determines which ice polymorph is stable at the given T, P
2. **Generates candidate structures** - Uses GenIce2 to create plausible atomic configurations
3. **Ranks candidates** - Scores structures based on geometric assumptions
4. **Outputs results** - Saves ranked PDB files and a phase diagram

The goal is to quickly generate starting structures for further analysis, not to perform physics simulations.

---

## Why QuickIce Exists

QuickIce is a **pure "vibe coding" project** - built for exploration and learning, not production science.

The original motivation was simple curiosity:
- What does Ice VII look like at 2 GPa?
- How does Ice XI differ from Ice Ih?
- Can I quickly generate reasonable starting structures for arbitrary conditions?

QuickIce answers these questions without requiring:
- Complex simulation setup
- Deep knowledge of molecular dynamics
- Expensive computational resources

It's a tool for rapid exploration of ice phase space.

---

## How It Works

QuickIce operates in a pipeline of phases:

### Phase 1: Input Validation

CLI arguments are validated for correct types and ranges:
- Temperature: 0-500 K
- Pressure: 0-10000 MPa
- Molecules: 4-100000

Invalid inputs exit immediately with helpful error messages.

### Phase 2: Phase Mapping

Temperature and pressure are mapped to an ice polymorph using:
- IAPWS R14-08 melting curves (high confidence)
- Triple point data from literature
- Linear interpolation for solid-solid boundaries (medium confidence)

The mapping identifies which of 12 ice phases is stable at the input conditions:
- Ice Ih, Ic, II, III, IV, V, VI, VII, VIII, IX, X, XI, XV

### Phase 3: Structure Generation

Candidates are generated using GenIce2, a combinatorial ice structure generator:
- Creates hydrogen-disordered structures consistent with the ice rules
- Uses cell dimensions appropriate for the phase
- Generates multiple candidates with different random seeds

### Phase 4: Ranking

Candidates are scored and ranked using three estimated components:
- **Energy score:** O-O distance deviation from ideal (0.276 nm)
- **Density score:** Deviation from expected phase density
- **Diversity score:** Rewards unique seeds

Lower combined score = better candidate.

### Phase 5: Output

Results are saved to the output directory:
- `candidate_N.pdb` - Ranked structures in PDB format
- `phase_diagram.png` - Water phase diagram with input conditions marked

---

## Key Design Decisions

### No Physics Simulations

QuickIce does NOT perform:
- Molecular dynamics (MD) simulations
- Energy minimization
- Force field calculations
- Quantum chemistry calculations

Structures are generated combinatorially by GenIce2 and scored with geometric estimations. This makes QuickIce fast but approximate.

**Why?** Real MD simulations require:
- Hours to days of computation
- Specialized software (GROMACS, LAMMPS, etc.)
- Force field expertise
- Careful equilibration protocols

QuickIce provides structures in seconds for rapid exploration.

### IAPWS R14-08 for Phase Boundaries

Phase boundaries are based on IAPWS R14-08 (International Association for the Properties of Water and Steam), the internationally validated standard for water/ice thermodynamics.

This ensures high confidence for:
- Ice Ih/Liquid boundary (melting curve)
- Ice III, V, VI, VII boundaries at high pressure

Solid-solid boundaries use linear interpolation between triple points (medium confidence).

### GenIce2 for Structure Generation

GenIce2 is a well-established tool for generating ice structures. It:
- Enforces the ice rules (two donors, two acceptors per oxygen)
- Supports all common ice polymorphs
- Generates hydrogen-disordered (proton-disordered) structures

QuickIce wraps GenIce2 with condition-based selection and ranking.

### Knowledge-based Scoring

The ranking system uses simple geometric estimations:
- O-O distances as an energy proxy
- Density matching for phase consistency
- Seed diversity for structural variety

These are **not physics** - they're practical metrics for distinguishing "good" structures from "obviously wrong" ones.

For accurate energetics, feed QuickIce outputs into proper MD simulations.

---

## What QuickIce Does NOT Do

### No Energy Minimization

Structures come straight from GenIce2 without optimization. They may have:
- Suboptimal hydrogen bond angles
- Local strains
- Non-equilibrium configurations

**Solution:** Run energy minimization with your preferred MD engine if needed.

### No Equilibration

QuickIce generates initial structures, not equilibrated ones. Real ice at given T, P will have:
- Thermal fluctuations
- Proton dynamics
- Density variations

**Solution:** Run MD equilibration after generating structures.

### No Free Energy Calculations

QuickIce cannot determine phase stability. It maps T, P to phases based on literature boundaries, not thermodynamic calculations.

For phase stability analysis, use:
- Free energy perturbation methods
- Thermodynamic integration
- Enhanced sampling techniques

### No Defect Generation

QuickIce generates ideal crystalline structures. Real ice contains:
- Vacancies
- Interstitials
- Grain boundaries
- Dislocations

**Solution:** Introduce defects manually or through simulation.

---

## References

### GenIce2

GenIce2 is used for structure generation:

- Repository: https://github.com/genice-dev/GenIce2
- Paper: "GenIce: Hydrogen-disordered ice structures by combinatorial generation" (J. Comput. Chem. 2017)
- DOI: https://doi.org/10.1002/jcc.25077

### IAPWS R14-08

Phase boundaries are based on the IAPWS Release on the Equation of State for Ice Ih (R14-08):

- Document: https://www.iapws.org/relguide/MeltSub.html
- Provides melting curves and thermodynamic properties for Ice Ih

### spglib

spglib is used for crystal symmetry analysis and validation:

- Repository: https://github.com/atztogo/spglib
- Paper: "Spglib: a software library for crystal symmetry search" (Sci. Technol. Adv. Mater. Meth. 2024)
- DOI: https://doi.org/10.1080/27660400.2024.2384822

### Ice Phase Diagrams

Phase boundary data compiled from multiple sources:
- Wagner et al., "The IAPWS Industrial Formulation 1997 for the Thermodynamic Properties of Water and Steam"
- Londono et al., "Neutron diffraction studies of ices III and IX" (J. Chem. Phys. 1993) — DOI: https://doi.org/10.1063/1.464942
- Lobban et al., "The structure of a new phase of ice" (Nature 1998) — DOI: https://doi.org/10.1038/34622
- Salzmann et al., "Ice XV: A New Thermodynamically Stable Phase of Ice" (Phys. Rev. Lett. 2009) — DOI: https://doi.org/10.1103/physrevlett.103.105701

---

## When to Use QuickIce

### Good Use Cases

- Exploring ice phase space quickly
- Generating starting structures for MD simulations
- Teaching and learning about ice polymorphs
- Rapid prototyping of ice structure workflows

### Not Suitable For

- Accurate thermodynamic properties
- Phase stability predictions
- Production-quality scientific publications (validate with MD)
- Studying defects or dynamics

---

## Contributing

QuickIce is a vibe coding project. Contributions welcome:

- Bug reports and fixes
- Additional ice phases
- Improved estimations
- Documentation improvements

---

## See Also

- [CLI Reference](./cli-reference.md) - Command-line usage
- [Ranking Methodology](./ranking.md) - How candidates are scored

---

*QuickIce: Generate ice structures quickly, for the joy of exploration.*
