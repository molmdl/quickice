"""Quick test of guest molecule handling in ion insertion."""
import numpy as np
from quickice.structure_generation.types import InterfaceStructure
from quickice.structure_generation.ion_inserter import IonInserter

# Create test interface structure: 10 ice + 1 guest + 5 water = 16 molecules, 40+5+20 = 65 atoms
# But let's keep it simple: ice 10*4=40 atoms, guest 5 atoms, water 5*4=20 atoms = 65 atoms
positions = np.random.rand(65, 3)

# Atom names: 40 ice atoms + 5 guest atoms + 20 water atoms (just HW to keep under 65)
atom_names = (['OW']*40 + ['C']*5 + ['HW1']*20)[:65]

iface = InterfaceStructure(
    positions=positions,
    atom_names=atom_names,
    cell=np.eye(3) * 5,
    ice_atom_count=40,
    water_atom_count=20,
    ice_nmolecules=10,
    water_nmolecules=5,
    mode='pocket',
    guest_atom_count=5,
    guest_nmolecules=1,
    report='test'
)

# Build molecule index
inserter = IonInserter()
mol_index = inserter._build_molecule_index_from_structure(iface)

print('Molecule index built:')
for m in mol_index:
    print(f'  {m.mol_type}: start_idx={m.start_idx}, count={m.count}')

# Check for guest entries
guests = [m for m in mol_index if m.mol_type == 'guest']
print(f'\nGuest entries found: {len(guests)}')
if guests:
    print('SUCCESS: Guests included in molecule_index')
else:
    print('FAILURE: No guest entries')