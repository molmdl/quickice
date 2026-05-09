#!/usr/bin/env python3
"""Simple debug script to verify missing regeneration check.

This script confirms that _on_custom_generate_clicked lacks:
1. Check for previous insertion
2. Dialog asking what to do
3. Cleanup of previous results
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication


def analyze_code():
    """Analyze the code to find missing checks."""
    print("\n=== ANALYZING CODE FOR REGENERATION CRASH ===\n")
    
    # Read main_window.py
    main_window_path = Path(__file__).parent / "quickice" / "gui" / "main_window.py"
    with open(main_window_path) as f:
        lines = f.readlines()
    
    # Find _on_custom_generate_clicked method
    print("1. Analyzing _on_custom_generate_clicked method...")
    in_method = False
    method_lines = []
    for i, line in enumerate(lines, 1):
        if '_on_custom_generate_clicked' in line and 'def ' in line:
            in_method = True
            start_line = i
        elif in_method:
            if line.strip() and not line.startswith(' ' * 8) and not line.startswith('\t\t'):
                # End of method
                break
            method_lines.append((i, line))
    
    # Check for key patterns
    print(f"   Found method starting at line {start_line}")
    
    checks = {
        'previous_insertion': False,
        'clear_previous': False,
        'button_disabled': False,
        'button_enabled': False,
        'dialog': False,
    }
    
    for line_num, line in method_lines:
        if '_has_previous_insertion' in line:
            checks['previous_insertion'] = True
        if 'clear_previous' in line.lower():
            checks['clear_previous'] = True
        if 'generate_button.setEnabled(False)' in line or 'generate_button.setEnabled( False )' in line:
            checks['button_disabled'] = True
        if 'generate_button.setEnabled(True)' in line or 'generate_button.setEnabled( True )' in line:
            checks['button_enabled'] = True
        if 'QMessageBox' in line:
            checks['dialog'] = True
    
    print("\n2. Checking for critical safety mechanisms:")
    print(f"   - Check for previous insertion: {checks['previous_insertion']}")
    print(f"   - Clear previous results: {checks['clear_previous']}")
    print(f"   - Disable generate button: {checks['button_disabled']}")
    print(f"   - Re-enable generate button: {checks['button_enabled']}")
    print(f"   - Show dialog to user: {checks['dialog']}")
    
    # Find _on_custom_finished method
    print("\n3. Analyzing _on_custom_finished method...")
    in_method = False
    finish_lines = []
    for i, line in enumerate(lines, 1):
        if '_on_custom_finished' in line and 'def ' in line:
            in_method = True
            start_line = i
        elif in_method:
            if line.strip() and not line.startswith(' ' * 8) and not line.startswith('\t\t'):
                break
            finish_lines.append((i, line))
    
    finish_checks = {
        'button_enabled': False,
        'cleanup': False,
    }
    
    for line_num, line in finish_lines:
        if 'generate_button.setEnabled(True)' in line or 'generate_button.setEnabled( True )' in line:
            finish_checks['button_enabled'] = True
        if 'del self._custom_worker' in line or 'del self._custom_worker_thread' in line:
            finish_checks['cleanup'] = True
    
    print(f"   Found method starting at line {start_line}")
    print(f"   - Re-enable generate button: {finish_checks['button_enabled']}")
    print(f"   - Cleanup worker/thread: {finish_checks['cleanup']}")
    
    # Compare with hydrate panel
    print("\n4. Comparing with hydrate panel (_on_hydrate_generate_clicked)...")
    in_method = False
    hydrate_lines = []
    for i, line in enumerate(lines, 1):
        if '_on_hydrate_generate_clicked' in line and 'def ' in line:
            in_method = True
            start_line = i
        elif in_method:
            if line.strip() and not line.startswith(' ' * 8) and not line.startswith('\t\t'):
                break
            hydrate_lines.append((i, line))
    
    hydrate_checks = {
        'button_disabled': False,
        'button_enabled_in_complete': False,
    }
    
    for line_num, line in hydrate_lines:
        if 'generate_button.setEnabled(False)' in line or 'generate_button.setEnabled( False )' in line:
            hydrate_checks['button_disabled'] = True
    
    # Also check the completion handler
    for i, line in enumerate(lines, 1):
        if '_on_hydrate_generation_complete' in line and 'def ' in line:
            in_complete = True
            for j in range(i, min(i+50, len(lines))):
                if 'generate_button.setEnabled(True)' in lines[j]:
                    hydrate_checks['button_enabled_in_complete'] = True
                    break
            break
    
    print(f"   - Disable generate button: {hydrate_checks['button_disabled']}")
    print(f"   - Re-enable in complete handler: {hydrate_checks['button_enabled_in_complete']}")
    
    # Summary
    print("\n=== CRITICAL FINDINGS ===\n")
    
    issues = []
    if not checks['previous_insertion']:
        issues.append("❌ NO check for _has_previous_insertion before starting new generation")
    if not checks['clear_previous']:
        issues.append("❌ NO cleanup of previous custom molecule results")
    if not checks['dialog']:
        issues.append("❌ NO dialog asking user what to do (unlike mode switching)")
    if not checks['button_disabled']:
        issues.append("❌ NO disabling of generate button during processing (unlike hydrate panel)")
    if not finish_checks['button_enabled']:
        issues.append("❌ NO re-enabling of generate button after completion")
    
    if issues:
        print("ISSUES FOUND:\n")
        for issue in issues:
            print(f"  {issue}")
        
        print("\n\nROOT CAUSE:")
        print("  When user clicks Generate a second time (regeneration in same mode):")
        print("  1. No check prevents creating new worker while previous state exists")
        print("  2. No cleanup of previous results/viewer state")
        print("  3. Button remains clickable during processing")
        print("  4. No user confirmation dialog")
        print("  5. This can lead to:")
        print("     - Thread collision if clicked rapidly")
        print("     - VTK viewer state corruption")
        print("     - Silent crash (segfault)")
        
        print("\n\nFIX REQUIRED:")
        print("  Add the same safety mechanisms as mode switching:")
        print("  1. Check _has_previous_insertion at start of _on_custom_generate_clicked")
        print("  2. If True, show dialog asking to clear or add to existing")
        print("  3. If user chooses to clear, call _on_clear_custom_molecule_results")
        print("  4. Disable generate button when worker starts")
        print("  5. Re-enable generate button in _on_custom_finished")
    else:
        print("✅ All safety mechanisms present - no issues found")
    
    print("\n=== ANALYSIS COMPLETE ===\n")


if __name__ == "__main__":
    analyze_code()
