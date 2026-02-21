#!/usr/bin/env python
"""
Script to run all tests and generate a comprehensive HTML and text report.
Run this script from the project root:
python shs_system/tests/run_tests.py
"""
import os
import sys
import subprocess
import argparse
import datetime
import webbrowser
from pathlib import Path


def create_report_directory():
    """Create a directory for storing test reports if it doesn't exist."""
    report_dir = Path("test_reports")
    report_dir.mkdir(exist_ok=True)
    return report_dir


def run_tests(args):
    """Run the Django tests with the specified options."""
    cmd = [sys.executable, "manage.py", "test", "shs_system"]

    if args.verbosity:
        cmd.extend(["-v", str(args.verbosity)])

    if args.failfast:
        cmd.append("--failfast")

    if args.keepdb:
        cmd.append("--keepdb")

    if args.specific:
        cmd.append(args.specific)

    print("\n" + "=" * 80)
    print("Running tests...")
    print("=" * 80 + "\n")

    # Run tests and capture output
    process = subprocess.run(cmd, capture_output=True, text=True)
    return process


def run_coverage(args, report_dir):
    """Run tests with coverage and generate reports."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # Base command for coverage
    cmd = ["coverage", "run", "--source=shs_system", "manage.py", "test", "shs_system"]

    if args.specific:
        cmd.append(args.specific)

    if args.verbosity:
        cmd.extend(["-v", str(args.verbosity)])

    if args.failfast:
        cmd.append("--failfast")

    if args.keepdb:
        cmd.append("--keepdb")

    print("\n" + "=" * 80)
    print("Running tests with coverage...")
    print("=" * 80 + "\n")

    # Run tests with coverage
    process = subprocess.run(cmd, capture_output=True, text=True)

    # Generate coverage reports
    print("\n" + "=" * 80)
    print("Generating coverage reports...")
    print("=" * 80 + "\n")

    text_report_path = report_dir / f"coverage_report_{timestamp}.txt"
    html_report_dir = report_dir / f"coverage_html_{timestamp}"

    # Generate text report
    subprocess.run(
        ["coverage", "report"],
        stdout=open(text_report_path, "w"),
        stderr=subprocess.STDOUT,
    )

    # Generate HTML report
    subprocess.run(["coverage", "html", "-d", str(html_report_dir)])

    return {
        "process": process,
        "text_report_path": text_report_path,
        "html_report_dir": html_report_dir,
    }


def generate_html_report(test_output, coverage_info, report_dir):
    """Generate a combined HTML report with test results and coverage information."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = report_dir / f"test_report_{timestamp}.html"

    # Read coverage report content
    coverage_text = "Coverage report not available"
    if (
        coverage_info
        and coverage_info.get("text_report_path")
        and coverage_info["text_report_path"].exists()
    ):
        with open(coverage_info["text_report_path"], "r") as f:
            coverage_text = f.read()

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>School App Test Report - {timestamp}</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; max-width: 1200px; margin: 0 auto; }}
            h1, h2, h3 {{ color: #333; }}
            .header {{ background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
            .section {{ margin-bottom: 30px; }}
            .summary {{ display: flex; justify-content: space-between; flex-wrap: wrap; }}
            .summary-box {{ background-color: #f8f9fa; padding: 15px; margin: 10px; border-radius: 5px; flex: 1; min-width: 250px; }}
            .success {{ background-color: #d4edda; }}
            .failure {{ background-color: #f8d7da; }}
            pre {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto; white-space: pre-wrap; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #f2f2f2; }}
            tr:hover {{ background-color: #f5f5f5; }}
            .footer {{ margin-top: 50px; padding-top: 20px; border-top: 1px solid #eee; font-size: 0.9em; color: #666; }}
            .coverage-link {{ margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>School App Test Report</h1>
            <p>Generated on {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        </div>

        <div class="section">
            <h2>Test Summary</h2>
            <div class="summary">
                <div class="summary-box {'success' if 'FAILED=' not in test_output.stdout else 'failure'}">
                    <h3>Status</h3>
                    <p>{'PASSED' if 'FAILED=' not in test_output.stdout else 'FAILED'}</p>
                </div>
                <div class="summary-box">
                    <h3>Coverage</h3>
                    <p>See detailed coverage report below</p>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Test Output</h2>
            <pre>{test_output.stdout}</pre>
            {f'<pre style="color: red;">{test_output.stderr}</pre>' if test_output.stderr else ''}
        </div>

        <div class="section">
            <h2>Coverage Report</h2>
            <pre>{coverage_text}</pre>
            
            {f'<p class="coverage-link">View detailed HTML coverage report: <a href="{coverage_info["html_report_dir"] / "index.html"}" target="_blank">Open Coverage Report</a></p>' if coverage_info and coverage_info.get("html_report_dir") else ''}
        </div>

        <div class="footer">
            <p>School App Testing Framework</p>
        </div>
    </body>
    </html>
    """

    with open(report_path, "w") as f:
        f.write(html_content)

    return report_path


def main():
    """Main function to parse arguments and run tests."""
    parser = argparse.ArgumentParser(description="Run tests for the School App system")
    parser.add_argument(
        "-v",
        "--verbosity",
        type=int,
        choices=[0, 1, 2, 3],
        default=2,
        help="Verbosity level for test output",
    )
    parser.add_argument(
        "-f", "--failfast", action="store_true", help="Stop on first test failure"
    )
    parser.add_argument(
        "-k",
        "--keepdb",
        action="store_true",
        help="Keep the test database between test runs",
    )
    parser.add_argument(
        "-c",
        "--coverage",
        action="store_true",
        help="Run tests with coverage measurement",
    )
    parser.add_argument(
        "-s",
        "--specific",
        type=str,
        help="Run specific test module, class or method (e.g. 'test_models.UserModelTest')",
    )
    parser.add_argument(
        "-o",
        "--open-report",
        action="store_true",
        help="Open HTML report in browser after tests",
    )

    args = parser.parse_args()

    # Create report directory
    report_dir = create_report_directory()

    coverage_info = None
    if args.coverage:
        coverage_info = run_coverage(args, report_dir)
        test_output = coverage_info["process"]
    else:
        test_output = run_tests(args)

    # Generate HTML report
    report_path = generate_html_report(test_output, coverage_info, report_dir)

    print("\n" + "=" * 80)
    print(f"Report generated: {report_path}")

    if coverage_info and coverage_info.get("html_report_dir"):
        print(
            f"Coverage HTML report: {coverage_info['html_report_dir'] / 'index.html'}"
        )

    print("=" * 80 + "\n")

    # Open report in browser if requested
    if args.open_report:
        webbrowser.open(f"file://{report_path.absolute()}")

        if coverage_info and coverage_info.get("html_report_dir"):
            webbrowser.open(
                f"file://{(coverage_info['html_report_dir'] / 'index.html').absolute()}"
            )

    # Return error code if tests failed
    if "FAILED=" in test_output.stdout or test_output.returncode != 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
