#!/usr/bin/env python
"""
Comprehensive Test Runner for SchoolApp Deployment Readiness
This script runs all tests and generates a detailed deployment readiness report.
"""

import os
import sys
import subprocess
import json
from datetime import datetime
from pathlib import Path


# Color codes for terminal output
class Colors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def print_header(text):
    """Print a formatted header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text:^80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}\n")


def print_section(text):
    """Print a formatted section header."""
    print(f"\n{Colors.OKBLUE}{Colors.BOLD}{'-'*80}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{Colors.BOLD}{'-'*80}{Colors.ENDC}\n")


def print_success(text):
    """Print success message."""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_warning(text):
    """Print warning message."""
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")


def print_error(text):
    """Print error message."""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_info(text):
    """Print info message."""
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")


def run_command(command, description):
    """Run a shell command and return the result."""
    print_info(f"Running: {description}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )
        return result
    except subprocess.TimeoutExpired:
        print_error(f"Command timed out: {command}")
        return None
    except Exception as e:
        print_error(f"Error running command: {str(e)}")
        return None


def check_environment():
    """Check environment configuration."""
    print_section("1. Environment Configuration Check")

    issues = []
    warnings = []

    # Check if .env file exists
    if os.path.exists(".env"):
        print_success(".env file exists")
    else:
        issues.append(".env file not found")
        print_error(".env file not found")

    # Check if requirements.txt exists
    if os.path.exists("requirements.txt"):
        print_success("requirements.txt exists")
    else:
        issues.append("requirements.txt not found")
        print_error("requirements.txt not found")

    # Check if manage.py exists
    if os.path.exists("manage.py"):
        print_success("manage.py exists")
    else:
        issues.append("manage.py not found")
        print_error("manage.py not found")

    # Check Python version
    python_version = sys.version.split()[0]
    print_info(f"Python version: {python_version}")
    if sys.version_info >= (3, 8):
        print_success("Python version is compatible (>= 3.8)")
    else:
        issues.append(f"Python version {python_version} is too old (need >= 3.8)")
        print_error(f"Python version {python_version} is too old (need >= 3.8)")

    return issues, warnings


def run_django_check():
    """Run Django system check."""
    print_section("2. Django System Check")

    result = run_command("python manage.py check", "Django system check")

    if result and result.returncode == 0:
        print_success("Django system check passed")
        return []
    else:
        print_error("Django system check failed")
        if result:
            print(result.stdout)
            print(result.stderr)
        return ["Django system check failed"]


def run_deployment_check():
    """Run Django deployment check."""
    print_section("3. Django Deployment Check")

    result = run_command("python manage.py check --deploy", "Django deployment check")

    issues = []
    warnings = []

    if result:
        output = result.stdout + result.stderr
        if "System check identified no issues" in output:
            print_success("No deployment issues found")
        else:
            print_warning("Deployment check found some issues:")
            print(output)
            if "ERRORS" in output:
                issues.append("Deployment check found errors")
            if "WARNINGS" in output:
                warnings.append("Deployment check found warnings")

    return issues, warnings


def check_database_migrations():
    """Check if all migrations are applied."""
    print_section("4. Database Migrations Check")

    result = run_command(
        "python manage.py showmigrations --plan", "Checking database migrations"
    )

    issues = []

    if result and result.returncode == 0:
        output = result.stdout
        if "[ ]" in output:
            print_warning("Some migrations are not applied")
            issues.append("Unapplied migrations found")
            print(output)
        else:
            print_success("All migrations are applied")
    else:
        print_error("Could not check migrations")
        issues.append("Migration check failed")

    return issues


def run_unit_tests():
    """Run unit tests."""
    print_section("5. Unit Tests")

    result = run_command(
        "python manage.py test shs_system.tests.test_models --verbosity=2",
        "Running model tests",
    )

    if result and result.returncode == 0:
        print_success("Unit tests passed")
        return []
    else:
        print_error("Unit tests failed")
        if result:
            print(result.stdout)
            print(result.stderr)
        return ["Unit tests failed"]


def run_integration_tests():
    """Run integration tests."""
    print_section("6. Integration Tests")

    result = run_command(
        "python manage.py test shs_system.tests.test_integration --verbosity=2",
        "Running integration tests",
    )

    if result and result.returncode == 0:
        print_success("Integration tests passed")
        return []
    else:
        print_error("Integration tests failed")
        if result:
            print(result.stdout)
            print(result.stderr)
        return ["Integration tests failed"]


def run_view_tests():
    """Run view tests."""
    print_section("7. View Tests")

    result = run_command(
        "python manage.py test shs_system.tests.test_views --verbosity=2",
        "Running view tests",
    )

    if result and result.returncode == 0:
        print_success("View tests passed")
        return []
    else:
        print_error("View tests failed")
        if result:
            print(result.stdout)
            print(result.stderr)
        return ["View tests failed"]


def run_deployment_tests():
    """Run deployment readiness tests."""
    print_section("8. Deployment Readiness Tests")

    result = run_command(
        "python manage.py test shs_system.tests.test_comprehensive_deployment --verbosity=2",
        "Running deployment tests",
    )

    if result and result.returncode == 0:
        print_success("Deployment tests passed")
        return []
    else:
        print_error("Deployment tests failed")
        if result:
            print(result.stdout)
            print(result.stderr)
        return ["Deployment tests failed"]


def run_code_coverage():
    """Run tests with coverage."""
    print_section("9. Code Coverage Analysis")

    # Run coverage
    result = run_command(
        "coverage run --source='shs_system' manage.py test shs_system",
        "Running tests with coverage",
    )

    if result and result.returncode == 0:
        # Generate report
        coverage_result = run_command("coverage report", "Generating coverage report")

        if coverage_result:
            print(coverage_result.stdout)

            # Extract coverage percentage
            lines = coverage_result.stdout.split("\n")
            for line in lines:
                if "TOTAL" in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        coverage_pct = parts[-1].replace("%", "")
                        try:
                            coverage_num = float(coverage_pct)
                            if coverage_num >= 80:
                                print_success(
                                    f"Code coverage: {coverage_pct}% (Target: >= 80%)"
                                )
                                return []
                            else:
                                print_warning(
                                    f"Code coverage: {coverage_pct}% (Target: >= 80%)"
                                )
                                return [f"Code coverage below target: {coverage_pct}%"]
                        except ValueError:
                            pass

        print_info("Coverage report generated successfully")
        print_info("Run 'coverage html' to generate HTML report")
        return []
    else:
        print_error("Coverage analysis failed")
        return ["Coverage analysis failed"]


def check_security_settings():
    """Check security settings."""
    print_section("10. Security Settings Check")

    issues = []
    warnings = []

    try:
        # Import Django settings
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SchoolApp.settings")
        import django

        django.setup()
        from django.conf import settings

        # Check DEBUG
        if settings.DEBUG:
            warnings.append("DEBUG is enabled (should be False in production)")
            print_warning("DEBUG is enabled")
        else:
            print_success("DEBUG is disabled")

        # Check SECRET_KEY
        if settings.SECRET_KEY:
            print_success("SECRET_KEY is configured")
        else:
            issues.append("SECRET_KEY is not configured")
            print_error("SECRET_KEY is not configured")

        # Check ALLOWED_HOSTS
        if settings.ALLOWED_HOSTS:
            print_success(f"ALLOWED_HOSTS configured: {settings.ALLOWED_HOSTS}")
            if "*" in settings.ALLOWED_HOSTS and not settings.DEBUG:
                warnings.append("Wildcard in ALLOWED_HOSTS is insecure in production")
                print_warning("Wildcard in ALLOWED_HOSTS")
        else:
            issues.append("ALLOWED_HOSTS is empty")
            print_error("ALLOWED_HOSTS is empty")

        # Check session security
        if settings.SESSION_COOKIE_HTTPONLY:
            print_success("SESSION_COOKIE_HTTPONLY is enabled")
        else:
            warnings.append("SESSION_COOKIE_HTTPONLY should be enabled")
            print_warning("SESSION_COOKIE_HTTPONLY is disabled")

        # Check CSRF cookie security
        if settings.CSRF_COOKIE_HTTPONLY:
            print_success("CSRF_COOKIE_HTTPONLY is enabled")
        else:
            warnings.append("CSRF_COOKIE_HTTPONLY should be enabled")
            print_warning("CSRF_COOKIE_HTTPONLY is disabled")

    except Exception as e:
        issues.append(f"Could not check security settings: {str(e)}")
        print_error(f"Error checking security settings: {str(e)}")

    return issues, warnings


def generate_report(all_issues, all_warnings):
    """Generate final report."""
    print_header("DEPLOYMENT READINESS REPORT")

    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Summary
    total_issues = sum(
        len(issues) if isinstance(issues, list) else 1
        for issues in all_issues
        if issues
    )
    total_warnings = sum(
        len(warnings) if isinstance(warnings, list) else 1
        for warnings in all_warnings
        if warnings
    )

    print_section("Summary")
    print(f"Total Issues: {total_issues}")
    print(f"Total Warnings: {total_warnings}\n")

    # Detailed issues
    if total_issues > 0:
        print_section("Issues Found (Must Fix Before Deployment)")
        for i, issues in enumerate(all_issues, 1):
            if issues:
                if isinstance(issues, list):
                    for issue in issues:
                        print_error(issue)
                else:
                    print_error(issues)
    else:
        print_success("No critical issues found!")

    # Detailed warnings
    if total_warnings > 0:
        print_section("Warnings (Should Review)")
        for i, warnings in enumerate(all_warnings, 1):
            if warnings:
                if isinstance(warnings, list):
                    for warning in warnings:
                        print_warning(warning)
                else:
                    print_warning(warnings)

    # Final verdict
    print_header("FINAL VERDICT")
    if total_issues == 0:
        print_success("✓ System is READY for deployment!")
        if total_warnings > 0:
            print_warning(
                f"Please review {total_warnings} warning(s) before deployment"
            )
        return True
    else:
        print_error(f"✗ System is NOT READY for deployment!")
        print_error(f"Please fix {total_issues} issue(s) before deploying")
        return False


def save_report_to_file(all_issues, all_warnings):
    """Save report to a file."""
    report_file = f"deployment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    with open(report_file, "w") as f:
        f.write("=" * 80 + "\n")
        f.write("DEPLOYMENT READINESS REPORT\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        total_issues = sum(
            len(issues) if isinstance(issues, list) else 1
            for issues in all_issues
            if issues
        )
        total_warnings = sum(
            len(warnings) if isinstance(warnings, list) else 1
            for warnings in all_warnings
            if warnings
        )

        f.write("SUMMARY\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total Issues: {total_issues}\n")
        f.write(f"Total Warnings: {total_warnings}\n\n")

        if total_issues > 0:
            f.write("ISSUES FOUND\n")
            f.write("-" * 80 + "\n")
            for issues in all_issues:
                if issues:
                    if isinstance(issues, list):
                        for issue in issues:
                            f.write(f"✗ {issue}\n")
                    else:
                        f.write(f"✗ {issues}\n")
            f.write("\n")

        if total_warnings > 0:
            f.write("WARNINGS\n")
            f.write("-" * 80 + "\n")
            for warnings in all_warnings:
                if warnings:
                    if isinstance(warnings, list):
                        for warning in warnings:
                            f.write(f"⚠ {warning}\n")
                    else:
                        f.write(f"⚠ {warnings}\n")
            f.write("\n")

        f.write("=" * 80 + "\n")
        if total_issues == 0:
            f.write("VERDICT: System is READY for deployment!\n")
        else:
            f.write("VERDICT: System is NOT READY for deployment!\n")
        f.write("=" * 80 + "\n")

    print_info(f"Report saved to: {report_file}")


def main():
    """Main function to run all checks."""
    print_header("SCHOOLAPP COMPREHENSIVE DEPLOYMENT READINESS TEST")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    all_issues = []
    all_warnings = []

    try:
        # 1. Environment check
        issues, warnings = check_environment()
        all_issues.append(issues)
        all_warnings.append(warnings)

        # 2. Django check
        issues = run_django_check()
        all_issues.append(issues)

        # 3. Deployment check
        issues, warnings = run_deployment_check()
        all_issues.append(issues)
        all_warnings.append(warnings)

        # 4. Migrations check
        issues = check_database_migrations()
        all_issues.append(issues)

        # 5. Unit tests
        issues = run_unit_tests()
        all_issues.append(issues)

        # 6. Integration tests
        issues = run_integration_tests()
        all_issues.append(issues)

        # 7. View tests
        issues = run_view_tests()
        all_issues.append(issues)

        # 8. Deployment tests
        issues = run_deployment_tests()
        all_issues.append(issues)

        # 9. Code coverage
        issues = run_code_coverage()
        all_issues.append(issues)

        # 10. Security settings
        issues, warnings = check_security_settings()
        all_issues.append(issues)
        all_warnings.append(warnings)

    except KeyboardInterrupt:
        print_error("\n\nTest run interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"\n\nUnexpected error: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    # Generate final report
    is_ready = generate_report(all_issues, all_warnings)

    # Save report to file
    save_report_to_file(all_issues, all_warnings)

    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Exit with appropriate code
    sys.exit(0 if is_ready else 1)


if __name__ == "__main__":
    main()
