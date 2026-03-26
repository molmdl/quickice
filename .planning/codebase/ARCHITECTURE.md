# Architecture

**Analysis Date:** 2026-03-26

## Pattern Overview

**Overall:** Plugin-based modular architecture with staged processing pipeline

**Key Characteristics:**
- Highly modular plugin system for lattices, formats, molecules, and groups
- Seven-stage processing pipeline for ice generation
- Separation of core algorithm (genice-core) from user-facing code
- Hook-based extensibility allowing plugins to intercept any stage

## Layers

**Core Layer:**
- Purpose: Core ice graph algorithm and hydrogen bond network manipulation
- Location: External package `genice-core`
- Contains: Graph algorithms for ice rule satisfaction and depolarization
- Depends on: networkx, numpy
- Used by: `genice2/genice.py`

**Engine Layer:**
- Purpose: Coordinate GenIce workflow and manage state
- Location: `genice2/genice.py`
- Contains: GenIce class, stage orchestration, cell replication, graph operations
- Depends on: genice-core, networkx, numpy, pairlist
- Used by: CLI, plugins

**Plugin Layer:**
- Purpose: Provide extensible functionality for lattices, formats, molecules
- Location: `genice2/lattices/`, `genice2/formats/`, `genice2/molecules/`, `genice2/groups/`
- Contains: Plugin implementations as Python modules
- Depends on: Engine layer base classes
- Used by: CLI, API users

**CLI Layer:**
- Purpose: Command-line interface and argument parsing
- Location: `genice2/cli/genice.py`, `genice2/cli/analice.py`
- Contains: Argument parsers, main entry points
- Depends on: Engine layer, Plugin layer
- Used by: End users via command line

## Data Flow

**Ice Generation Pipeline (7 Stages):**

1. **Stage 1 - Cell Replication:**
   - Input: Lattice plugin (waters, cell, bondlen)
   - Process: Replicate unit cell to desired size
   - Output: `reppositions`, `repcell`, `repcagepos`

2. **Stage 2 - Graph Construction:**
   - Input: `pairs1`, `waters1`, `fixed1`
   - Process: Build hydrogen bond network graph, apply fixed edges
   - Output: `graph` (networkx Graph), `fixedEdges` (networkx DiGraph)

3. **Stage 3 - Ice Rule Application:**
   - Input: `graph`, `fixedEdges`
   - Process: Apply ice rules (2-in 2-out) via cycle tiling algorithm
   - Output: `digraph` (directed ice graph)
   - Note: Uses genice-core `ice_graph()` function

4. **Stage 4 - Depolarization:**
   - Input: `digraph`
   - Process: Minimize total dipole moment
   - Output: Depolarized `digraph`
   - Note: Integrated with Stage 3 in `Stage34E()`

5. **Stage 5 - Molecular Orientation:**
   - Input: `reppositions`, `digraph`
   - Process: Calculate rotation matrices for water molecules
   - Output: `rotmatrices` (3x3 matrices per molecule)

6. **Stage 6 - Water Atom Placement:**
   - Input: `reppositions`, `rotmatrices`, water model plugin
   - Process: Place atomic coordinates for water molecules
   - Output: `universe` (list of molecule containers)

7. **Stage 7 - Guest Placement:**
   - Input: `universe`, `cagepos`, guest molecule plugins
   - Process: Place guest molecules in cages
   - Output: Complete `universe` with all atoms

**State Management:**
- GenIce class maintains state through `self` attributes
- Each stage adds/transforms attributes
- Formatter plugins read final state via hooks

## Key Abstractions

**Lattice Plugin:**
- Purpose: Define crystal structure of ice polymorph
- Examples: `genice2/lattices/1h.py`, `genice2/lattices/CS1.py`
- Pattern: Subclass of `genice2.lattices.Lattice`
- Required attributes: `waters`, `cell`, `coord`
- Optional attributes: `density`, `bondlen`, `pairs`, `fixed`, `cagepos`, `cagetype`

```python
# Example lattice plugin structure
class Lattice(genice2.lattices.Lattice):
    def __init__(self):
        self.density = 0.92
        self.bondlen = 3
        self.cell = cellvectors(a=..., b=..., c=...)
        self.waters = "..."  # positions as string
        self.coord = "absolute"  # or "relative"
        self.cagepos, self.cagetype = parse_cages("...")
```

**Format Plugin:**
- Purpose: Output ice structure in specific file format
- Examples: `genice2/formats/gromacs.py`, `genice2/formats/xyz.py`
- Pattern: Subclass of `genice2.formats.Format` with hooks
- Key method: `hooks()` returns dict of stage -> hook function

```python
# Example format plugin structure
class Format(genice2.formats.Format):
    def hooks(self):
        return {7: self.Hook7}  # Called after Stage 7
    
    def Hook7(self, ice):
        # Access ice.universe, ice.repcell, etc.
        self.output = "..."  # Build output string
```

**Molecule Plugin:**
- Purpose: Define molecular geometry for water models or guests
- Examples: `genice2/molecules/tip3p.py`, `genice2/molecules/ch4.py`
- Pattern: Subclass of `genice2.molecules.Molecule`
- Key method: `get()` returns (name, labels, sites)

```python
# Example molecule plugin structure
class Molecule(genice2.molecules.Molecule):
    def __init__(self):
        self.sites_ = np.array([[0, 0, oz], [0, ohy, ohz], ...])
        self.labels_ = ["O", "H", "H"]
        self.name_ = "SOL"
    
    def get(self):
        return self.name_, self.labels_, self.sites_
```

**Cell:**
- Purpose: Represent simulation cell with periodic boundary conditions
- Location: `genice2/cell.py`
- Key methods: `abs2rel()`, `rel2abs()`, `volume()`, `scale()`
- Handles: Coordinate transformations, cell shape manipulation

## Entry Points

**CLI Entry Point (genice2):**
- Location: `genice2/cli/genice.py:main()`
- Triggers: Command line execution via `genice2` command
- Responsibilities: Parse arguments, load plugins, execute pipeline

**CLI Entry Point (analice2):**
- Location: `genice2/cli/analice.py:main()`
- Triggers: Command line execution via `analice2` command
- Responsibilities: Analyze existing ice structures

**API Entry Point:**
- Location: `genice2/genice.py:GenIce.__init__()` + `generate_ice()`
- Triggers: Python API usage
- Responsibilities: Programmatic ice generation

**Plugin Discovery:**
- Location: `genice2/plugin.py:safe_import()`
- Triggers: Plugin loading
- Responsibilities: Find and load plugins from system, extra, or local paths

## Error Handling

**Strategy:** Exceptions with informative messages

**Patterns:**
- Assert statements for internal consistency checks
- Logger warnings for recoverable issues (e.g., >99999 atoms in GRO format)
- Graceful degradation (e.g., missing rotmatrices in analice)

## Cross-Cutting Concerns

**Logging:** Python logging module with `getLogger()`, INFO/DEBUG levels
**Validation:** Plugin name sanitization via `audit_name()` regex
**Performance:** `@timeit` and `@banner` decorators for profiling
**Periodic Boundaries:** Handled in `cell.py` with `rel_wrap()` function

---

*Architecture analysis: 2026-03-26*
