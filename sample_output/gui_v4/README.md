# Contents
This directory has sample gromacs-ready files of 3 systems supported by QuickIce GUI v4: 
1. ice at 273.15K 0.1MPa
2. methane hydrate (sI cage, 100% occupancy of both small and large cages)
3. THF hydrate (sII cage, 0% occupancy of small cages, 100% of large cages)

Each system was exported at the initial generation step, slab interface generation, and after ion insertion.

# Forcefield parameters (see docs for citation)
Ions: Madrid2019
water/ice: TIP4P-ice
CH4 and THF: GAFF2 with RESP2(0.5) partial charge, prepared with Multiwfn and Sobtop.

# Directory structure
```
├── README.md
├── ch4
│   ├── ch4.itp
│   ├── hydrate_sI_ch4_1x1x1.gro
│   ├── hydrate_sI_ch4_1x1x1.top
│   ├── ion
│   │   ├── ch4.itp
│   │   ├── ion.itp
│   │   ├── ions_54na_54cl.gro
│   │   ├── ions_54na_54cl.top
│   │   └── tip4p-ice.itp
│   ├── slab
│   │   ├── ch4.itp
│   │   ├── interface_slab.gro
│   │   ├── interface_slab.top
│   │   └── tip4p-ice.itp
│   └── tip4p-ice.itp
├── ice
│   ├── ice_ih_273K_0.10MPa_c1.gro
│   ├── ice_ih_273K_0.10MPa_c1.itp
│   ├── ice_ih_273K_0.10MPa_c1.top
│   ├── ion
│   │   ├── ion.itp
│   │   ├── ions_56na_56cl.gro
│   │   ├── ions_56na_56cl.top
│   │   └── tip4p-ice.itp
│   └── slab
│       ├── interface_slab.gro
│       ├── interface_slab.top
│       └── tip4p-ice.itp
└── thf
    ├── hydrate_sII_thf_1x1x1.gro
    ├── hydrate_sII_thf_1x1x1.top
    ├── ion
    │   ├── ion.itp
    │   ├── ions_31na_31cl.gro
    │   ├── ions_31na_31cl.top
    │   ├── thf.itp
    │   └── tip4p-ice.itp
    ├── slab
    │   ├── interface_slab.gro
    │   ├── interface_slab.top
    │   ├── thf.itp
    │   └── tip4p-ice.itp
    ├── thf.itp
    └── tip4p-ice.itp

9 directories, 37 files
```
