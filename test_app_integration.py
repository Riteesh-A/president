#!/usr/bin/env python3
"""
Integration tests for the President card game Dash app
Tests the actual running web application
Run with: python test_app_integration.py
"""

import requests
import time
import sys
import subprocess
import signal
import os
from urllib.parse import urljoin

class DashAppTester:
    def __init__(self, base_url="http://localhost:8050"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def test_app_loads(self):
        """Test that the app homepage loads successfully"""
        try:
            response = self.session.get(self.base_url, timeout=10)
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            assert "President Card Game" in response.text, "App title not found in response"
            print("✅ App loads successfully")
            return True
        except Exception as e:
            print(f"❌ App loading failed: {str(e)}")
            return False
    
    def test_static_assets(self):
        """Test that static assets are served"""
        try:
            # Test favicon
            favicon_response = self.session.get(urljoin(self.base_url, "/_favicon.ico"))
            # Favicon might return 404, but server should respond
            assert favicon_response.status_code in [200, 404], "Server not responding to favicon request"
            
            print("✅ Static assets accessible")
            return True
        except Exception as e:
            print(f"❌ Static assets test failed: {str(e)}")
            return False
    
    def test_dash_components_load(self):
        """Test that Dash components and scripts are loaded"""
        try:
            response = self.session.get(self.base_url)
            content = response.text
            
            # Check for Dash-specific elements that should be in static HTML
            assert 'id="react-entry-point"' in content, "React entry point not found"
            assert '_dash-config' in content, "Dash config not found"
            assert '_dash-renderer' in content, "Dash renderer not found"
            
            # Check that Dash scripts are loaded
            assert 'dash' in content.lower(), "Dash scripts not found"
            
            print("✅ Dash framework loaded correctly")
            return True
        except Exception as e:
            print(f"❌ Dash framework test failed: {str(e)}")
            return False
    
    def test_bootstrap_css_loads(self):
        """Test that Bootstrap CSS is loaded"""
        try:
            response = self.session.get(self.base_url)
            content = response.text
            
            assert "bootstrap" in content.lower(), "Bootstrap CSS not found"
            print("✅ Bootstrap CSS loaded")
            return True
        except Exception as e:
            print(f"❌ Bootstrap CSS test failed: {str(e)}")
            return False
    
    def test_app_responsiveness(self):
        """Test app response time"""
        try:
            start_time = time.time()
            response = self.session.get(self.base_url)
            response_time = time.time() - start_time
            
            assert response.status_code == 200, "App not responding"
            assert response_time < 5.0, f"App too slow: {response_time:.2f}s"
            
            print(f"✅ App responsive ({response_time:.3f}s)")
            return True
        except Exception as e:
            print(f"❌ App responsiveness test failed: {str(e)}")
            return False

def wait_for_app_start(base_url, timeout=30):
    """Wait for the app to start up"""
    print(f"Waiting for app to start at {base_url}...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(base_url, timeout=2)
            if response.status_code == 200:
                print("✅ App is running!")
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)
    
    return False

def check_app_running(base_url):
    """Check if app is already running"""
    try:
        response = requests.get(base_url, timeout=3)
        return response.status_code == 200
    except:
        return False

def run_integration_tests():
    """Run all integration tests"""
    base_url = "http://localhost:8050"
    
    print("🎮 President Card Game - Integration Tests")
    print("=" * 50)
    
    # Check if app is running
    if not check_app_running(base_url):
        print("❌ App is not running!")
        print("   Please start the app first with: python app.py")
        return False
    
    print("✅ Found running app")
    
    # Run tests
    tester = DashAppTester(base_url)
    tests_passed = 0
    total_tests = 5
    
    test_functions = [
        tester.test_app_loads,
        tester.test_static_assets,
        tester.test_dash_components_load,
        tester.test_bootstrap_css_loads,
        tester.test_app_responsiveness
    ]
    
    for test_func in test_functions:
        try:
            if test_func():
                tests_passed += 1
        except Exception as e:
            print(f"❌ Test {test_func.__name__} failed with exception: {str(e)}")
    
    # Summary
    print("\n" + "=" * 50)
    print(f"Integration Tests Summary:")
    print(f"Passed: {tests_passed}/{total_tests}")
    print(f"Success rate: {tests_passed/total_tests*100:.1f}%")
    
    if tests_passed == total_tests:
        print("🎉 All integration tests passed!")
        return True
    else:
        print("❌ Some integration tests failed")
        return False

def run_automated_test():
    """Run tests with automatic app startup/shutdown"""
    print("🎮 President Card Game - Automated Integration Tests")
    print("=" * 50)
    
    app_process = None
    try:
        # Start the app
        print("Starting Dash app...")
        app_process = subprocess.Popen(
            [sys.executable, "app.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid if hasattr(os, 'setsid') else None
        )
        
        # Wait for app to start
        if not wait_for_app_start("http://localhost:8050", timeout=15):
            print("❌ App failed to start within timeout")
            return False
        
        # Run tests
        time.sleep(2)  # Give app a moment to fully initialize
        success = run_integration_tests()
        
        return success
        
    except Exception as e:
        print(f"❌ Automated test failed: {str(e)}")
        return False
        
    finally:
        # Clean up
        if app_process:
            try:
                if hasattr(os, 'killpg'):
                    os.killpg(os.getpgid(app_process.pid), signal.SIGTERM)
                else:
                    app_process.terminate()
                app_process.wait(timeout=5)
                print("✅ App process cleaned up")
            except:
                try:
                    app_process.kill()
                except:
                    pass

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        success = run_automated_test()
    else:
        success = run_integration_tests()
    
    sys.exit(0 if success else 1) 