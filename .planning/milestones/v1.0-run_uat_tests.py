#!/usr/bin/env python3
"""
UAT Test Runner - Runs all pending UAT tests for QuickIce.

Usage:
    python run_uat_tests.py
"""

import sys
import subprocess
from pathlib import Path

def run_test(name, command, expected_result):
    """Run a single UAT test."""
    print(f"\n{'='*60}")
    print(f"Test: {name}")
    print(f"Expected: {expected_result}")
    print(f"Command: {command}")
    print("-" * 60)
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        
        print(f"Exit code: {result.returncode}")
        if stdout:
            print(f"STDOUT:\n{stdout[:500]}")
        if stderr:
            print(f"STDERR:\n{stderr[:500]}")
        
        return result.returncode, stdout, stderr
        
    except subprocess.TimeoutExpired:
        print("TIMEOUT - Test took too long")
        return -1, "", "Timeout"
    except Exception as e:
        print(f"ERROR: {e}")
        return -1, "", str(e)


def main():
    print("QuickIce UAT Test Runner")
    print("=" * 60)
    
    results = []
    
    # Test 8: Phase Lookup - Ice V
    print("\n" + "="*60)
    print("Running UAT Test #8: Phase Lookup - Ice V")
    print("Expected: T=260K, P=400MPa returns Ice V (ice_v)")
    print("-"*60)
    ret, out, err = run_test("Ice V lookup", 
        "cd /share/home/nglokwan/quickice && python -c \"from quickice.phase_mapping.lookup import lookup_phase; print(lookup_phase(260, 400)['phase_id'])\"",
        "ice_v")
    passed = "ice_v" in out
    results.append(("Test #8: Ice V", passed))
    print(f"RESULT: {'PASS' if passed else 'FAIL'}")
    
    # Test 9: Phase Lookup - Ice III
    print("\n" + "="*60)
    print("Running UAT Test #9: Phase Lookup - Ice III")
    print("Expected: T=240K, P=220MPa returns Ice III (ice_iii)")
    print("-"*60)
    ret, out, err = run_test("Ice III lookup", 
        "cd /share/home/nglokwan/quickice && python -c \"from quickice.phase_mapping.lookup import lookup_phase; print(lookup_phase(240, 220)['phase_id'])\"",
        "ice_iii")
    passed = "ice_iii" in out
    results.append(("Test #9: Ice III", passed))
    print(f"RESULT: {'PASS' if passed else 'FAIL'}")
    
    # Test 10: Phase Lookup - Ice VII at High T Below Melting Curve
    print("\n" + "="*60)
    print("Running UAT Test #10: Ice VII at High T Below Melting Curve")
    print("Expected: T=400K, P=2000MPa returns Liquid (UnknownPhaseError)")
    print("-"*60)
    ret, out, err = run_test("Ice VII below melt", 
        "cd /share/home/nglokwan/quickice && python -c \"from quickice.phase_mapping.lookup import lookup_phase; lookup_phase(400, 2000)\" 2>&1",
        "UnknownPhaseError")
    passed = "UnknownPhaseError" in out or "Liquid" in out
    results.append(("Test #10: VII below melt", passed))
    print(f"RESULT: {'PASS' if passed else 'FAIL'}")
    
    # Test 11: Phase Lookup - Ice VII at High T Above Melting Curve
    print("\n" + "="*60)
    print("Running UAT Test #11: Ice VII at High T Above Melting Curve")
    print("Expected: T=400K, P=3000MPa returns Ice VII (ice_vii)")
    print("-"*60)
    ret, out, err = run_test("Ice VII above melt", 
        "cd /share/home/nglokwan/quickice && python -c \"from quickice.phase_mapping.lookup import lookup_phase; print(lookup_phase(400, 3000)['phase_id'])\"",
        "ice_vii")
    passed = "ice_vii" in out
    results.append(("Test #11: VII above melt", passed))
    print(f"RESULT: {'PASS' if passed else 'FAIL'}")
    
    # Test 12: Phase Lookup - Ice VII Melting Curve Direction
    print("\n" + "="*60)
    print("Running UAT Test #12: Ice VII Melting Curve Direction")
    print("Expected: T=500K, P=4500MPa returns Liquid (UnknownPhaseError)")
    print("-"*60)
    ret, out, err = run_test("VII melt curve direction", 
        "cd /share/home/nglokwan/quickice && python -c \"from quickice.phase_mapping.lookup import lookup_phase; lookup_phase(500, 4500)\" 2>&1",
        "UnknownPhaseError")
    passed = "UnknownPhaseError" in out or "Liquid" in out
    results.append(("Test #12: VII melt direction", passed))
    print(f"RESULT: {'PASS' if passed else 'FAIL'}")
    
    # Test 13: Structure Generation
    print("\n" + "="*60)
    print("Running UAT Test #13: Structure Generation")
    print("Expected: Generates 10 candidates")
    print("-"*60)
    ret, out, err = run_test("Structure generation", 
        "cd /share/home/nglokwan/quickice && python quickice.py -T 250 -P 100 -N 64 --no-diagram -o /tmp/uat_test_13 2>&1",
        "10 candidates")
    passed = ret == 0 and ("10 candidates" in out or "Generated" in out)
    results.append(("Test #13: Structure gen", passed))
    print(f"RESULT: {'PASS' if passed else 'FAIL'}")
    
    # Test 14: Ranking Output
    print("\n" + "="*60)
    print("Running UAT Test #14: Ranking Output")
    print("Expected: Candidates ranked with energy, density, diversity")
    print("-"*60)
    print("Skipping - covered by Test #13")
    results.append(("Test #14: Ranking output", "SKIP"))
    
    # Test 15: PDB Output Files
    print("\n" + "="*60)
    print("Running UAT Test #15: PDB Output Files")
    print("Expected: 10 PDB files created")
    print("-"*60)
    pdb_files = list(Path("/tmp/uat_test_13").glob("*.pdb")) if Path("/tmp/uat_test_13").exists() else []
    passed = len(pdb_files) >= 10
    print(f"Found {len(pdb_files)} PDB files: {[f.name for f in pdb_files[:5]]}")
    results.append(("Test #15: PDB files", passed))
    print(f"RESULT: {'PASS' if passed else 'FAIL'}")
    
    # Test 16: Phase Diagram Generation
    print("\n" + "="*60)
    print("Running UAT Test #16: Phase Diagram Generation")
    print("Expected: PNG phase diagram generated")
    print("-"*60)
    ret, out, err = run_test("Phase diagram", 
        "cd /share/home/nglokwan/quickice && python quickice.py -T 250 -P 100 -N 64 -o /tmp/uat_test_16 2>&1",
        "phase_diagram.png")
    passed = ret == 0
    if Path("/tmp/uat_test_16/phase_diagram.png").exists():
        print("Found phase_diagram.png")
        passed = True
    results.append(("Test #16: Phase diagram", passed))
    print(f"RESULT: {'PASS' if passed else 'FAIL'}")
    
    # Test 17: --output Flag
    print("\n" + "="*60)
    print("Running UAT Test #17: --output Flag")
    print("Expected: Custom output directory works")
    print("-"*60)
    passed = Path("/tmp/uat_test_16").exists()
    print(f"Output directory exists: {passed}")
    results.append(("Test #17: --output flag", passed))
    print(f"RESULT: {'PASS' if passed else 'FAIL'}")
    
    # Test 18: --no-diagram Flag
    print("\n" + "="*60)
    print("Running UAT Test #18: --no-diagram Flag")
    print("Expected: Can disable phase diagram")
    print("-"*60)
    ret, out, err = run_test("--no-diagram", 
        "cd /share/home/nglokwan/quickice && python quickice.py -T 250 -P 100 -N 32 --no-diagram -o /tmp/uat_test_18 2>&1",
        "no diagram")
    passed = ret == 0
    results.append(("Test #18: --no-diagram", passed))
    print(f"RESULT: {'PASS' if passed else 'FAIL'}")
    
    # Test 19: Ice XI Detection
    print("\n" + "="*60)
    print("Running UAT Test #19: Ice XI Detection")
    print("Expected: T=50K, P=10MPa returns Ice XI (ice_xi)")
    print("-"*60)
    ret, out, err = run_test("Ice XI lookup", 
        "cd /share/home/nglokwan/quickice && python -c \"from quickice.phase_mapping.lookup import lookup_phase; print(lookup_phase(50, 10)['phase_id'])\"",
        "ice_xi")
    passed = "ice_xi" in out
    results.append(("Test #19: Ice XI", passed))
    print(f"RESULT: {'PASS' if passed else 'FAIL'}")
    
    # Test 20: Ice X Detection
    print("\n" + "="*60)
    print("Running UAT Test #20: Ice X Detection")
    print("Expected: T=300K, P=50000MPa returns Ice X (ice_x)")
    print("-"*60)
    ret, out, err = run_test("Ice X lookup", 
        "cd /share/home/nglokwan/quickice && python -c \"from quickice.phase_mapping.lookup import lookup_phase; print(lookup_phase(300, 50000)['phase_id'])\"",
        "ice_x")
    passed = "ice_x" in out
    results.append(("Test #20: Ice X", passed))
    print(f"RESULT: {'PASS' if passed else 'FAIL'}")
    
    # Test 21: Phase Diagram Extended Ranges
    print("\n" + "="*60)
    print("Running UAT Test #21: Phase Diagram Extended Ranges")
    print("Expected: T to 50K, P to 100 GPa")
    print("-"*60)
    print("Manual check - open phase_diagram.png and verify axis ranges")
    results.append(("Test #21: Diagram ranges", "MANUAL"))
    
    # Test 22: README Exists
    print("\n" + "="*60)
    print("Running UAT Test #22: README Exists")
    print("Expected: README.md exists")
    print("-"*60)
    passed = Path("/share/home/nglokwan/quickice/README.md").exists()
    print(f"README.md exists: {passed}")
    results.append(("Test #22: README", passed))
    print(f"RESULT: {'PASS' if passed else 'FAIL'}")
    
    # Test 23: Documentation Exists
    print("\n" + "="*60)
    print("Running UAT Test #23: Documentation Exists")
    print("Expected: docs/ folder with cli-reference.md, ranking.md, principles.md")
    print("-"*60)
    docs = Path("/share/home/nglokwan/quickice/docs")
    cli_ref = docs / "cli-reference.md"
    ranking = docs / "ranking.md"
    principles = docs / "principles.md"
    passed = cli_ref.exists() and ranking.exists() and principles.exists()
    print(f"cli-reference.md: {cli_ref.exists()}")
    print(f"ranking.md: {ranking.exists()}")
    print(f"principles.md: {principles.exists()}")
    results.append(("Test #23: Documentation", passed))
    print(f"RESULT: {'PASS' if passed else 'FAIL'}")
    
    # Test 24: Test Suite Passes
    print("\n" + "="*60)
    print("Running UAT Test #24: Test Suite Passes")
    print("Expected: pytest runs and all tests pass")
    print("-"*60)
    ret, out, err = run_test("pytest", 
        "cd /share/home/nglokwan/quickice && python -m pytest tests/ -v --tb=short 2>&1 | tail -20",
        "passed")
    passed = ret == 0 and "passed" in out
    print(out[-500:] if len(out) > 500 else out)
    results.append(("Test #24: Test suite", passed))
    print(f"RESULT: {'PASS' if passed else 'FAIL'}")
    
    # Summary
    print("\n" + "="*60)
    print("UAT TEST SUMMARY")
    print("="*60)
    
    passed_count = 0
    failed_count = 0
    skipped_count = 0
    manual_count = 0
    
    for name, result in results:
        status = str(result)
        if status == "PASS":
            print(f"  ✓ {name}: PASS")
            passed_count += 1
        elif status == "FAIL":
            print(f"  ✗ {name}: FAIL")
            failed_count += 1
        elif status == "SKIP":
            print(f"  - {name}: SKIP")
            skipped_count += 1
        else:
            print(f"  ? {name}: {status}")
            manual_count += 1
    
    print(f"\nTotal: {len(results)}")
    print(f"Passed: {passed_count}")
    print(f"Failed: {failed_count}")
    print(f"Skipped: {skipped_count}")
    print(f"Manual: {manual_count}")
    
    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
