#!/usr/bin/env python
"""
Script to update Django settings to use the custom test runner.
Run this script from the project root:
python shs_system/tests/update_settings.py
"""
import os
import re
import sys


def update_settings_file(settings_path):
    """
    Updates the Django settings file to use the custom test runner.
    """
    # Read the current settings file
    with open(settings_path, "r") as f:
        settings_content = f.read()

    # Check if the TEST_RUNNER setting already exists
    test_runner_pattern = re.compile(r"^TEST_RUNNER\s*=.*$", re.MULTILINE)

    if test_runner_pattern.search(settings_content):
        # Update existing TEST_RUNNER setting
        modified_content = test_runner_pattern.sub(
            "TEST_RUNNER = 'shs_system.tests.test_runner.DetailedTestRunner'",
            settings_content,
        )
    else:
        # Add TEST_RUNNER setting at the end of the file
        if settings_content.endswith("\n"):
            modified_content = (
                settings_content
                + "\n# Custom test runner configuration\nTEST_RUNNER = 'shs_system.tests.test_runner.DetailedTestRunner'\n"
            )
        else:
            modified_content = (
                settings_content
                + "\n\n# Custom test runner configuration\nTEST_RUNNER = 'shs_system.tests.test_runner.DetailedTestRunner'\n"
            )

    # Write the modified content back to the settings file
    with open(settings_path, "w") as f:
        f.write(modified_content)

    print(f"Successfully updated {settings_path} to use the custom test runner.")


def ensure_installed_apps(settings_path):
    """
    Ensures that the required apps are in INSTALLED_APPS.
    """
    # Read the current settings file
    with open(settings_path, "r") as f:
        settings_content = f.read()

    # Check if coverage is already in INSTALLED_APPS
    if (
        "'django_nose'," not in settings_content
        and '"django_nose",' not in settings_content
    ):
        # Find the INSTALLED_APPS setting
        installed_apps_pattern = re.compile(
            r"INSTALLED_APPS\s*=\s*\[([^\]]*)\]", re.DOTALL
        )
        match = installed_apps_pattern.search(settings_content)

        if match:
            # Insert django_nose into INSTALLED_APPS
            apps_content = match.group(1)
            if apps_content.strip().endswith(","):
                new_apps_content = apps_content + "\n    'django_nose',\n"
            else:
                new_apps_content = apps_content + ",\n    'django_nose',\n"

            modified_content = settings_content.replace(apps_content, new_apps_content)

            # Write the modified content back to the settings file
            with open(settings_path, "w") as f:
                f.write(modified_content)

            print(f"Added django_nose to INSTALLED_APPS in {settings_path}.")
        else:
            print(
                "Could not find INSTALLED_APPS setting. Please add 'django_nose' manually."
            )
    else:
        print("django_nose is already in INSTALLED_APPS.")


def create_coverage_config():
    """
    Creates a .coveragerc file for configuring coverage.py.
    """
    coveragerc_content = """[run]
source = shs_system
omit =
    */migrations/*
    */tests/*
    */admin.py
    */apps.py
    */urls.py
    */wsgi.py
    */asgi.py
    manage.py

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    def __str__
    raise NotImplementedError
    if settings.DEBUG
    pass
    raise ImportError
    if 0:
    if __name__ == .__main__.:
"""

    with open(".coveragerc", "w") as f:
        f.write(coveragerc_content)

    print("Created .coveragerc configuration file.")


def main():
    """
    Main function to update Django settings and create coverage configuration.
    """
    # Find the Django settings file
    settings_path = None
    project_dirs = os.listdir()

    # First check the predefined path
    if os.path.exists("SchoolApp/settings.py"):
        settings_path = "SchoolApp/settings.py"
    else:
        # Try to find it by looking for settings.py in subdirectories
        for d in project_dirs:
            if os.path.isdir(d) and os.path.exists(os.path.join(d, "settings.py")):
                settings_path = os.path.join(d, "settings.py")
                break

    if not settings_path:
        print("Error: Could not find Django settings.py file.")
        sys.exit(1)

    # Update the settings file
    update_settings_file(settings_path)

    # Create coverage configuration
    create_coverage_config()

    print("\nSetup complete. You can now run tests with the custom runner using:")
    print("python manage.py test shs_system")
    print("\nTo run tests with coverage:")
    print("coverage run --source='shs_system' manage.py test shs_system")
    print("coverage report")
    print("coverage html")


if __name__ == "__main__":
    main()
