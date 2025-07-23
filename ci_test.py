#!/usr/bin/env python3

"""
Continuous Integration Test Script for President Card Game
This script runs all test suites and provides clear output for CI/CD pipelines.
Run this script on every code change to ensure all functionality works correctly.
"""

import subprocess
import sys
import os
import time

def run_test_with_timeout(test_file, timeout=300):
    """Run a test file with timeout and return results"""
    print(f"🧪 Running {test_file}...")
    start_time = time.time()
    
    try:
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        duration = time.time() - start_time
        
        if result.returncode == 0:
            print(f"✅ {test_file} PASSED ({duration:.2f}s)")
            return True, result.stdout, duration
        else:
            print(f"❌ {test_file} FAILED ({duration:.2f}s)")
            return False, result.stdout + result.stderr, duration
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {test_file} TIMEOUT after {timeout}s")
        return False, f"Test timed out after {timeout} seconds", timeout
    except Exception as e:
        print(f"💥 {test_file} ERROR: {e}")
        return False, str(e), 0

def main():
    """Main CI test function"""
    print("🎮 President Card Game - CI Test Suite")
    print("=" * 60)
    print(f"Python version: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    print("=" * 60)
    
    # Test files to run
    test_files = [
        'tests.py',      # Core game logic tests
        'tests_ui.py'    # UI simulation tests
    ]
    
    # Results tracking
    results = []
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    total_duration = 0
    
    # Run each test file
    for test_file in test_files:
        if not os.path.exists(test_file):
            print(f"❌ Test file {test_file} not found!")
            results.append((test_file, False, f"File {test_file} not found", 0))
            failed_tests += 1
            continue
            
        success, output, duration = run_test_with_timeout(test_file)
        results.append((test_file, success, output, duration))
        total_duration += duration
        
        if success:
            passed_tests += 1
        else:
            failed_tests += 1
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 CI TEST SUMMARY")
    print("=" * 60)
    
    for test_file, success, output, duration in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_file:<15} {status} ({duration:.2f}s)")
    
    print(f"\nTotal Duration: {total_duration:.2f}s")
    print(f"Tests Passed: {passed_tests}")
    print(f"Tests Failed: {failed_tests}")
    
    # Final result
    print("\n" + "=" * 60)
    if failed_tests == 0:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Core game logic: PASSED")
        print("✅ UI simulation: PASSED")
        print("✅ Game is ready for deployment!")
        print("=" * 60)
        return 0
    else:
        print("❌ SOME TESTS FAILED!")
        print("Please check the output above for details.")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 