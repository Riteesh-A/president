#!/usr/bin/env python3

import subprocess
import sys
import os

def run_test_suite(test_file):
    """Run a test suite and return the results"""
    print(f"\n{'='*60}")
    print(f"Running {test_file}...")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run([sys.executable, test_file], 
                              capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("✅ Test suite completed successfully")
            return True, result.stdout
        else:
            print("❌ Test suite failed")
            return False, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        print("⏰ Test suite timed out")
        return False, "Test suite timed out after 5 minutes"
    except Exception as e:
        print(f"💥 Error running test suite: {e}")
        return False, str(e)

def main():
    """Run all test suites and provide summary"""
    print("🎮 President Card Game - Complete Test Suite")
    print("=" * 60)
    
    test_files = ['tests.py', 'tests_ui.py']
    results = []
    
    for test_file in test_files:
        if os.path.exists(test_file):
            success, output = run_test_suite(test_file)
            results.append((test_file, success, output))
        else:
            print(f"❌ Test file {test_file} not found")
            results.append((test_file, False, "File not found"))
    
    # Print summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")
    
    all_passed = True
    for test_file, success, output in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_file}: {status}")
        if not success:
            all_passed = False
    
    print(f"\n{'='*60}")
    if all_passed:
        print("🎉 ALL TEST SUITES PASSED!")
        print("✅ Core game logic tests: PASSED")
        print("✅ UI simulation tests: PASSED")
        print("✅ Game is ready for deployment!")
    else:
        print("⚠️  SOME TEST SUITES FAILED")
        print("Please check the output above for details")
    
    print(f"{'='*60}")
    
    # Return appropriate exit code
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main()) 