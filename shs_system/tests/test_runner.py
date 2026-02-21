"""
Test runner script for the SHS System.
This script runs all tests and generates a detailed report.
To run: python manage.py test shs_system
"""

import os
import sys
import time
import unittest
from django.test.runner import DiscoverRunner
from django.conf import settings
from django.utils.termcolors import colorize


class DetailedTestRunner(DiscoverRunner):
    """
    Custom test runner that provides more detailed output and statistics.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.test_results = {
            "success": 0,
            "failure": 0,
            "error": 0,
            "skipped": 0,
            "total": 0,
        }
        self.failed_tests = []
        self.start_time = time.time()

    def run_suite(self, suite):
        """Run the test suite with custom result handling."""
        result = unittest.TextTestRunner(
            verbosity=self.verbosity,
            failfast=self.failfast,
        ).run(suite)

        self.test_results["success"] = (
            result.testsRun
            - len(result.failures)
            - len(result.errors)
            - len(result.skipped)
        )
        self.test_results["failure"] = len(result.failures)
        self.test_results["error"] = len(result.errors)
        self.test_results["skipped"] = len(result.skipped)
        self.test_results["total"] = result.testsRun

        # Store failed tests information
        for failure in result.failures:
            self.failed_tests.append({"test": str(failure[0]), "message": failure[1]})

        for error in result.errors:
            self.failed_tests.append({"test": str(error[0]), "message": error[1]})

        return result

    def suite_result(self, suite, result, **kwargs):
        """Display a summary of test results."""
        duration = time.time() - self.start_time

        print("\n" + "=" * 80)
        print(colorize("TEST RESULTS SUMMARY", fg="white", opts=("bold",)))
        print("=" * 80)

        # Print statistics
        print(colorize(f"Total tests: {self.test_results['total']}", fg="white"))
        print(colorize(f"Passed: {self.test_results['success']}", fg="green"))
        print(colorize(f"Failed: {self.test_results['failure']}", fg="red"))
        print(colorize(f"Errors: {self.test_results['error']}", fg="red"))
        print(colorize(f"Skipped: {self.test_results['skipped']}", fg="yellow"))
        print(colorize(f"Time taken: {duration:.2f} seconds", fg="white"))

        # Print failed tests details
        if self.failed_tests:
            print("\n" + "=" * 80)
            print(colorize("FAILED TESTS DETAILS", fg="red", opts=("bold",)))
            print("=" * 80)

            for i, test in enumerate(self.failed_tests):
                print(f"{i+1}. {colorize(test['test'], fg='red')}")
                # Print only the first few lines of the error message to avoid flooding the console
                error_lines = test["message"].strip().split("\n")[:10]
                for line in error_lines:
                    print(f"   {line}")
                if len(error_lines) > 10:
                    print("   ...")
                print()

        return super().suite_result(suite, result, **kwargs)


def get_test_runner_with_tags(*tags):
    """
    Returns a test runner class that only runs tests with the specified tags.
    """

    class TaggedTestRunner(DetailedTestRunner):
        def build_suite(self, *args, **kwargs):
            kwargs["tags"] = tags
            return super().build_suite(*args, **kwargs)

    return TaggedTestRunner
