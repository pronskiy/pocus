#!/usr/bin/env python3

import os
import sys
import hashlib
import argparse
import requests
import json
import subprocess
from pathlib import Path
from php_installer import PhpInstaller

def generate_hash(input_string):
    """
    Generate a hash from the input string.

    Args:
        input_string (str): The input string to hash

    Returns:
        str: The generated hash
    """
    return hashlib.md5(input_string.encode()).hexdigest()

def is_github_url(input_string):
    """
    Check if the input string is a GitHub URL.

    Args:
        input_string (str): The input string to check

    Returns:
        bool: True if the input is a GitHub URL, False otherwise
    """
    return input_string.startswith("https://github.com/") or input_string.startswith("http://github.com/")

def download_composer_json_from_github(github_url, target_path):
    """
    Download composer.json from a GitHub repository.

    Args:
        github_url (str): The GitHub repository URL
        target_path (str): The path to save composer.json to

    Returns:
        bool: True if successful, False otherwise
    """
    # Convert GitHub URL to raw content URL for composer.json
    # Example: https://github.com/user/repo -> https://raw.githubusercontent.com/user/repo/master/composer.json
    parts = github_url.rstrip('/').split('github.com/')
    if len(parts) != 2:
        print(f"Error: Invalid GitHub URL format: {github_url}")
        return False

    repo_path = parts[1]
    raw_url = f"https://raw.githubusercontent.com/{repo_path}/master/composer.json"

    try:
        print(f"Downloading composer.json from {raw_url}...")
        response = requests.get(raw_url)
        response.raise_for_status()  # Raise an exception for 4XX/5XX responses

        # Save the composer.json file
        with open(target_path, 'wb') as f:
            f.write(response.content)

        print(f"Successfully downloaded composer.json to {target_path}")
        return True
    except Exception as e:
        print(f"Error downloading composer.json from GitHub: {e}")
        return False

def create_composer_json_for_package(package_name, target_path):
    """
    Create a composer.json file for a package with the latest non-dev version and PHP requirement.

    Args:
        package_name (str): The package name (vendor/package)
        target_path (str): The path to save composer.json to

    Returns:
        tuple: (bool, str) - Success status and PHP version requirement
    """
    try:
        # Query Packagist API for package information
        packagist_url = f"https://packagist.org/packages/{package_name}.json"
        print(f"Querying Packagist for package: {package_name}...")
        response = requests.get(packagist_url)
        response.raise_for_status()

        package_data = response.json()

        # Check if package data exists
        if 'package' not in package_data or 'versions' not in package_data['package']:
            print(f"Error: Could not find version information for package: {package_name}")
            return False, None

        # Get all versions
        versions = package_data['package']['versions']

        # Filter out dev versions and find the latest stable version
        latest_version = None
        latest_version_name = None

        for version_name, version_data in versions.items():
            # Skip dev versions
            if 'dev' in version_name or 'alpha' in version_name or 'beta' in version_name or 'RC' in version_name:
                continue

            # Skip aliases
            if version_data.get('version_normalized', '').endswith('.9999999-dev'):
                continue

            if latest_version is None or version_data.get('version_normalized', '0.0.0') > latest_version.get('version_normalized', '0.0.0'):
                latest_version = version_data
                latest_version_name = version_name

        if latest_version is None:
            print(f"Error: Could not find a stable version for package: {package_name}")
            return False, None

        print(f"Found latest stable version: {latest_version_name}")

        # Get PHP version requirement
        php_version = None
        if 'require' in latest_version and 'php' in latest_version['require']:
            php_version = latest_version['require']['php']
            print(f"PHP version requirement: {php_version}")
        else:
            print(f"Warning: No PHP version requirement found for {package_name}. Using default.")
            php_version = ">=7.0"

        # Create composer.json content
        composer_json = {
            "name": "pocus/temp-project",
            "description": "Temporary project created by Pocus",
            "type": "project",
            "require": {
                "php": php_version,
                package_name: latest_version_name
            }
        }

        # Write composer.json file
        with open(target_path, 'w') as f:
            json.dump(composer_json, f, indent=4)

        print(f"Created composer.json at {target_path} with {package_name}:{latest_version_name} and PHP:{php_version}")
        return True, php_version
    except Exception as e:
        print(f"Error creating composer.json for package: {e}")
        return False, None

def run_composer_install(package_dir, php_binary_path, composer_path):
    """
    Run 'php composer.phar install' in the package directory.

    Args:
        package_dir (str): The package directory
        php_binary_path (str): Path to the PHP binary
        composer_path (str): Path to the Composer PHAR file

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Make sure the PHP binary is executable
        os.chmod(php_binary_path, 0o755)

        # Change to the package directory
        os.chdir(package_dir)

        # Run the composer install command
        print(f"Running 'php composer.phar install' in {package_dir}...")
        result = subprocess.run(
            [php_binary_path, composer_path, "install"],
            capture_output=True,
            text=True
        )

        # Print the output
        print(result.stdout)

        if result.returncode != 0:
            print(f"Error running composer install: {result.stderr}")
            return False

        print("Composer install completed successfully")
        return True
    except Exception as e:
        print(f"Error running composer install: {e}")
        return False

def main():
    """
    Main function to handle package installation.
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Install PHP packages using specific PHP versions')
    parser.add_argument('package', help='PHP package name (vendor/package) or GitHub URL')
    args = parser.parse_args()

    # Get the package name or GitHub URL
    package_input = args.package

    # Generate a hash of the input
    input_hash = generate_hash(package_input)

    # Set up paths
    home_dir = str(Path.home())
    pocus_dir = os.path.join(home_dir, '.pocus')
    package_dir = os.path.join(pocus_dir, input_hash)
    composer_json_path = os.path.join(package_dir, 'composer.json')

    # Create the package directory if it doesn't exist
    os.makedirs(package_dir, exist_ok=True)

    # Handle composer.json based on input type
    php_version = None

    if is_github_url(package_input):
        # For GitHub URLs, download composer.json as before
        if not download_composer_json_from_github(package_input, composer_json_path):
            print("Failed to download composer.json from GitHub")
            return

        # Read PHP version requirement from downloaded composer.json
        try:
            php_version = PhpInstaller.read_composer_json(composer_json_path)
            print(f"Found PHP version requirement: {php_version}")
        except Exception as e:
            print(f"Error reading composer.json: {e}")
            return
    else:
        # For package names, create a custom composer.json with the latest version
        success, php_version = create_composer_json_for_package(package_input, composer_json_path)
        if not success:
            print("Failed to create composer.json for package")
            return

        # PHP version is already obtained from create_composer_json_for_package

    # Normalize PHP version
    normalized_version = PhpInstaller.normalize_php_version(php_version)
    if normalized_version != php_version:
        print(f"Normalized PHP version: {normalized_version}")

    # Set up paths for PHP and Composer
    version_dir = os.path.join(pocus_dir, normalized_version)
    download_path = os.path.join(pocus_dir, 'downloads')
    php_binary_path = os.path.join(version_dir, 'php')
    composer_path = os.path.join(pocus_dir, 'composer.phar')

    # Ensure PHP is downloaded
    try:
        # Check if PHP binary already exists
        if os.path.exists(php_binary_path):
            print(f"PHP {normalized_version} is already downloaded at {version_dir}")
        else:
            print(f"Downloading PHP {normalized_version}...")
            PhpInstaller.download_php(php_version, download_path, version_dir)
            print(f"Successfully downloaded PHP {normalized_version} to {version_dir}")

        # Ensure Composer is downloaded
        PhpInstaller.download_composer(pocus_dir)

        # Run composer install
        run_composer_install(package_dir, php_binary_path, composer_path)
    except Exception as e:
        print(f"Error: {e}")
        return

if __name__ == "__main__":
    main()
