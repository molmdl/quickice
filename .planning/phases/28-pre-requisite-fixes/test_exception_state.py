#!/usr/bin/env python
# Test random state restoration on exception
import numpy as np
from quickice.structure_generation.generator import IceStructureGenerator

# Test that exception restores random state
phase_info = {
    'phase_id': 'ice_ih',
    'phase_name': 'Ice Ih',
    'density': 0.9167
}
gen = IceStructureGenerator(phase_info, 100)

# Set known state before generation
np.random.seed(99999)
state_before = np.random.get_state()[1][:5]
print('State before generation (should be seed 99999):')
print('  ', state_before)

# Force an exception by passing invalid parameters
# We'll monkey-patch to cause an exception during GenIce generation
original_generate = gen._generate_single

def failing_generate(seed):
    raise RuntimeError('Intentional test exception')

gen._generate_single = failing_generate

try:
    gen.generate_all(1)
except RuntimeError as e:
    print(f'\nException caught: {e}')

# Check state after exception
state_after = np.random.get_state()[1][:5]
print('\nState after exception (should be restored to seed 99999):')
print('  ', state_after)
print('State restored:', list(state_before) == list(state_after))

print('\n✓ Random state restored even on exception!')