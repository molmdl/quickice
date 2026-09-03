"""E2E test package (scaffolded by 48.3-20 for the wave-7 move plans).

Subdirectories group the root ``test_e2e_*.py`` files by concern per the
INFRA §4.3 layout. Contains NO conftest.py by design (INFRA collision rule:
no e2e conftest may shadow test_output/custom_structure names) — fixtures
live in their test modules or in tests/e2e_chain_fixtures.py.
"""
