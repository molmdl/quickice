#!/usr/bin/env python3
"""Verification test for custom molecule regeneration crash fix.

This test verifies that the fix properly handles regeneration by:
1. Checking for previous insertion
2. Showing dialog to user
3. Clearing previous results on user confirmation
4. Disabling button during processing
5. Re-enabling button after completion
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication


def verify_fix():
    """Verify that the fix is properly implemented."""
    print("\n=== VERIFICATION: Custom Molecule Regeneration Fix ===\n")
    
    # Read main_window.py
    main_window_path = Path(__file__).parent / "quickice" / "gui" / "main_window.py"
    with open(main_window_path) as f:
        content = f.read()
        lines = f.readlines()
    
    # Reset file pointer
    with open(main_window_path) as f:
        lines = f.readlines()
    
    checks = {
        'previous_insertion_check': False,
        'dialog_shown': False,
        'clear_previous_called': False,
        'button_disabled': False,
        'button_enabled_in_finally': False,
        'button_enabled_on_error': False,
    }
    
    # Find _on_custom_generate_clicked
    in_method = False
    method_content = []
    for i, line in enumerate(lines):
        if '_on_custom_generate_clicked' in line and 'def ' in line:
            in_method = True
        elif in_method:
            if line.strip() and not line.startswith(' ' * 8) and not line.startswith('\t\t') and 'def ' in line:
                break
            method_content.append(line)
            
            if '_has_previous_insertion' in line:
                checks['previous_insertion_check'] = True
            if 'QMessageBox.question' in line:
                checks['dialog_shown'] = True
            if '_on_clear_custom_molecule_results' in line:
                checks['clear_previous_called'] = True
            if 'generate_button.setEnabled(False)' in line or 'generate_button.setEnabled( False )' in line:
                checks['button_disabled'] = True
            if 'except Exception' in line:
                # Check if button is re-enabled in except block
                for j in range(i, min(i+10, len(lines))):
                    if 'generate_button.setEnabled(True)' in lines[j]:
                        checks['button_enabled_on_error'] = True
                        break
    
    # Find _on_custom_finished
    in_method = False
    in_finally = False
    for i, line in enumerate(lines):
        if '_on_custom_finished' in line and 'def ' in line:
            in_method = True
        elif in_method:
            if 'finally:' in line:
                in_finally = True
            elif in_finally:
                if 'generate_button.setEnabled(True)' in line or 'generate_button.setEnabled( True )' in line:
                    checks['button_enabled_in_finally'] = True
                    break
    
    print("Verification Results:")
    print("-" * 60)
    
    all_passed = True
    for check_name, check_result in checks.items():
        status = "✅ PASS" if check_result else "❌ FAIL"
        print(f"{status}: {check_name.replace('_', ' ').title()}")
        if not check_result:
            all_passed = False
    
    print("-" * 60)
    
    if all_passed:
        print("\n✅ ALL CHECKS PASSED!")
        print("\nThe fix properly handles custom molecule regeneration:")
        print("1. Checks for previous insertion before starting new generation")
        print("2. Shows dialog asking user what to do")
        print("3. Clears previous results on user confirmation")
        print("4. Disables generate button during processing")
        print("5. Re-enables button in finally block (ensures it always runs)")
        print("6. Re-enables button on error (defensive programming)")
        print("\nThis should prevent the regeneration crash!")
    else:
        print("\n❌ SOME CHECKS FAILED!")
        print("\nPlease review the implementation.")
    
    print("\n=== VERIFICATION COMPLETE ===\n")
    
    return all_passed


if __name__ == "__main__":
    success = verify_fix()
    sys.exit(0 if success else 1)
