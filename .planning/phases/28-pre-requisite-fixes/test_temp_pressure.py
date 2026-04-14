#!/usr/bin/env python
from quickice.structure_generation.generator import IceStructureGenerator

# Test without T/P (legacy caller)
phase_info = {
    'phase_id': 'ice_ih',
    'phase_name': 'Ice Ih',
    'density': 0.9167
}
gen = IceStructureGenerator(phase_info, 100)
print('Without T/P:')
print(f'  self.temperature: {gen.temperature}')
print(f'  self.pressure: {gen.pressure}')

# Test with T/P
phase_info_tp = {
    'phase_id': 'ice_ih',
    'phase_name': 'Ice Ih',
    'density': 0.9167,
    'temperature': 273.15,
    'pressure': 0.1
}
gen2 = IceStructureGenerator(phase_info_tp, 100)
print('With T/P:')
print(f'  self.temperature: {gen2.temperature}')
print(f'  self.pressure: {gen2.pressure}')

# Verify metadata has T/P
candidates = gen2.generate_all(1, base_seed=42)
print('\nCandidate metadata:', candidates[0].metadata)
print('  temperature in metadata:', 'temperature' in candidates[0].metadata)
print('  pressure in metadata:', 'pressure' in candidates[0].metadata)

# Test random state restoration on success
import numpy as np
np.random.seed(12345)
state_before = np.random.get_state()[1][:5]  # first 5 elements
candidates = gen2.generate_all(1, base_seed=42)
state_after = np.random.get_state()[1][:5]
print('\nRandom state restoration (success):')
print('  State before:', state_before)
print('  State after:', state_after)
print('  State restored:', list(state_before) == list(state_after))