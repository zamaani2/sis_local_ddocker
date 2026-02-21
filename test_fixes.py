#!/usr/bin/env python
"""
Quick Test Runner to Verify Authentication Fixes
Runs specific test categories that were affected by auth issues
"""

import os
import sys
import subprocess
from datetime import datetime


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(f" {text}")
    print("=" * 80 + "\n")


def run_test(test_path, description):
    """Run a specific test and return results."""
    print_header(f"Testing: {description}")
    print(f"Test Path: {test_path}\n")

    try:
        result = subprocess.run(
            ["python", "manage.py", "test", test_path, "--verbosity=2"],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("⏱️  TEST TIMEOUT - Test took longer than 5 minutes")
        return False
    except Exception as e:
        print(f"❌ ERROR running test: {e}")
        return False


def main():
    """Run all test categories."""
    print_header("Authentication Fix Verification Tests")
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    test_suite = [
        ("shs_system.tests.test_models.UserModelTest", "User Model Tests"),
        (
            "shs_system.tests.test_security.SQLInjectionProtectionTest",
            "SQL Injection Protection",
        ),
        (
            "shs_system.tests.test_comprehensive_deployment.SecurityConfigurationTest",
            "Security Configuration",
        ),
        (
            "shs_system.tests.test_comprehensive_deployment.AuthenticationSecurityTest",
            "Authentication Security",
        ),
    ]

    results = {}

    for test_path, description in test_suite:
        success = run_test(test_path, description)
        results[description] = success

    # Print summary
    print_header("TEST RESULTS SUMMARY")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for description, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status:12} - {description}")

    print(f"\n{'='*80}")
    print(f"Total: {passed}/{total} test categories passed")
    print(f"Success Rate: {(passed/total*100):.1f}%")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Authentication fixes are working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total-passed} test categories still have issues.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
