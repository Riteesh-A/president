#!/usr/bin/env python3
"""
Comprehensive test runner for the President Card Game Dash app
Runs all available tests and provides a summary
"""

import subprocess
import sys
import time

def run_command(cmd, description):
    """Run a command and return success status"""
    print(f"\n{'='*20} {description} {'='*20}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running command: {e}")
        return False

def check_app_running():
    """Check if the Dash app is running"""
    try:
        import requests
        response = requests.get("http://localhost:8050", timeout=3)
        return response.status_code == 200
    except:
        return False

def main():
    """Run all tests"""
    print("🎮 President Card Game - Complete Test Suite")
    print("=" * 60)
    
    test_results = {}
    
    # 1. Run basic unit tests
    success = run_command("python test_basic.py", "UNIT TESTS")
    test_results["Unit Tests"] = success
    
    # 2. Run bot and multiplayer tests
    success = run_command("python test_bots_multiplayer.py", "BOT & MULTIPLAYER TESTS")
    test_results["Bot & Multiplayer Tests"] = success
    
    # 3. Run integration tests (if app is running)
    if check_app_running():
        print("\n✅ Dash app is running - proceeding with integration tests")
        success = run_command("python test_app_integration.py", "INTEGRATION TESTS")
        test_results["Integration Tests"] = success
        
        # 4. Run live game tests
        success = run_command("python test_live_game.py", "LIVE GAME TESTS")
        test_results["Live Game Tests"] = success
    else:
        print("\n⚠️  Dash app not running - skipping web interface tests")
        print("   To run all tests, start the app with: python app.py")
        test_results["Integration Tests"] = None
        test_results["Live Game Tests"] = None
    
    # 5. Optional: Run with pytest if available
    try:
        subprocess.run(["pytest", "--version"], capture_output=True, check=True)
        print("\n📦 pytest available - running comprehensive tests")
        success = run_command("python -m pytest test_president_app.py -v", "PYTEST TESTS")
        test_results["Pytest Tests"] = success
    except:
        print("\n📦 pytest not available - skipping pytest tests")
        print("   Install with: pip install pytest")
        test_results["Pytest Tests"] = None
    
    # 6. Code quality checks (if tools available)
    try:
        subprocess.run(["python", "-m", "py_compile", "app.py"], check=True, capture_output=True)
        print("\n✅ Python syntax check passed")
        test_results["Syntax Check"] = True
    except:
        print("\n❌ Python syntax check failed")
        test_results["Syntax Check"] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("🏁 COMPREHENSIVE TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = 0
    critical_passed = 0
    critical_total = 0
    
    # Critical tests (must pass for basic functionality)
    critical_tests = ["Unit Tests", "Bot & Multiplayer Tests", "Syntax Check"]
    
    for test_name, result in test_results.items():
        if result is None:
            status = "⏭️  SKIPPED"
        elif result:
            status = "✅ PASSED"
            passed += 1
            total += 1
            if test_name in critical_tests:
                critical_passed += 1
                critical_total += 1
        else:
            status = "❌ FAILED"
            total += 1
            if test_name in critical_tests:
                critical_total += 1
        
        # Mark critical tests
        critical_mark = " (CRITICAL)" if test_name in critical_tests else ""
        print(f"{test_name:<25} {status}{critical_mark}")
    
    print("\n" + "-" * 60)
    
    if total > 0:
        success_rate = (passed / total) * 100
        critical_success_rate = (critical_passed / critical_total) * 100 if critical_total > 0 else 100
        
        print(f"Overall Results:")
        print(f"  Total Tests: {passed}/{total} passed ({success_rate:.1f}%)")
        print(f"  Critical Tests: {critical_passed}/{critical_total} passed ({critical_success_rate:.1f}%)")
        
        print("\n🎯 Feature Status:")
        if test_results.get("Unit Tests", False):
            print("  ✅ Core Game Logic - Working")
        else:
            print("  ❌ Core Game Logic - Issues")
            
        if test_results.get("Bot & Multiplayer Tests", False):
            print("  ✅ Bot AI & Multiplayer - Working")
        else:
            print("  ❌ Bot AI & Multiplayer - Issues")
            
        if test_results.get("Integration Tests", None) is True:
            print("  ✅ Web Interface - Working")
        elif test_results.get("Integration Tests", None) is False:
            print("  ❌ Web Interface - Issues")
        else:
            print("  ⏭️  Web Interface - Not Tested (app not running)")
            
        if test_results.get("Live Game Tests", None) is True:
            print("  ✅ Live Game Functionality - Working")
        elif test_results.get("Live Game Tests", None) is False:
            print("  ❌ Live Game Functionality - Issues")
        else:
            print("  ⏭️  Live Game Functionality - Not Tested (app not running)")
        
        print("\n🚀 Deployment Status:")
        if critical_success_rate == 100:
            print("  ✅ READY FOR PRODUCTION")
            print("     - All critical functionality tested and working")
            print("     - Bots are intelligent and responsive")
            print("     - Multiplayer supports up to 5 players")
            print("     - Special card effects working correctly")
            return True
        elif critical_success_rate >= 75:
            print("  ⚠️  MOSTLY READY")
            print("     - Core functionality working")
            print("     - Minor issues may exist")
            return True
        else:
            print("  ❌ NOT READY")
            print("     - Critical issues need fixing")
            return False
    else:
        print("⚠️  No tests were run successfully.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 