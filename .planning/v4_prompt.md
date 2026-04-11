# v3.5 - 4 features
1. Enhancement of current features
   a. triclinic to othogonal transformation to let the interface generator support all the ice phases supported by genice2
   b. support interface generation in cli
   c. water density based on temperature and pressure
   d. ice Ih use accurate IAPWS density 
2. tab 3/4: insert molecules to interface system:
   a. salt: 
      - number of NaCl from conc
      - replace water not ice
   b. custom
      - to liquid phase:
         - random and custom mode (user specified COM xyz and custom rotation)
         - user provide topology and coordinate
      - to ice: this may override or done without tab 1 generation
         - mol supported by genice2
         - single or multiple
         - give me the list of molecules so I can provide topology
         - important: correct unit cell for methane hydrate. this could be different from tab1 generation
         - optional: include use specified molecules
   c. 3d viewer
      - display style of ice, water, inserted small mol, inserted large mol, inserted ions
