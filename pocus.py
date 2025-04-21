#!/usr/bin/env python3
"""
Pocus - PHP Package Installer and Bin Script Runner

This script allows you to:
1. Install PHP packages with the correct PHP version
2. Run bin scripts from installed packages
3. Download and install packages directly from GitHub repositories
4. Run PHP files using the installed PHP version

Examples:
    # Install a package from Packagist
    python main.py phpstan/phpstan

    # Install a package and run a bin script
    python main.py phpstan/phpstan phpstan analyse src/

    # Run a bin script from an already installed package
    python main.py phpstan/phpstan phpstan analyse --level=5 src/

    # Install a package from GitHub (downloads the repository archive)
    python main.py https://github.com/phpstan/phpstan phpstan analyse src/

    # Run a PHP file using the installed PHP version
    python main.py phpstan/phpstan script.php arg1 arg2
"""

import os
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

def download_github_repository_archive(github_url, target_dir):
    """
    Download a GitHub repository as an archive and extract it.

    Args:
        github_url (str): The GitHub repository URL
        target_dir (str): The directory to extract the repository to

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        import shutil
        import tempfile
        import zipfile

        # Clear the target directory if it exists and has content
        if os.path.exists(target_dir) and os.listdir(target_dir):
            print(f"Clearing existing directory: {target_dir}")
            for item in os.listdir(target_dir):
                item_path = os.path.join(target_dir, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)

        # Parse the GitHub URL to get the username and repository name
        # Example: https://github.com/username/repo -> username/repo
        parts = github_url.rstrip('/').split('github.com/')
        if len(parts) != 2:
            print(f"Error: Invalid GitHub URL format: {github_url}")
            return False

        repo_path = parts[1]

        # Construct the archive URL (using ZIP format)
        # We'll try 'main' branch first, then 'master' if that fails
        archive_url = f"https://github.com/{repo_path}/archive/refs/heads/main.zip"

        # Create a temporary directory to download the archive
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = os.path.join(temp_dir, "repo.zip")

            # Download the archive
            print(f"Downloading repository archive from {archive_url}...")
            try:
                response = requests.get(archive_url, stream=True)
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    # Try 'master' branch if 'main' branch doesn't exist
                    archive_url = f"https://github.com/{repo_path}/archive/refs/heads/master.zip"
                    print(f"Main branch not found, trying master branch: {archive_url}")
                    response = requests.get(archive_url, stream=True)
                    response.raise_for_status()
                else:
                    raise

            # Save the archive
            with open(archive_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Extract the archive
            print(f"Extracting repository archive to {target_dir}...")
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                # Get the name of the root directory in the archive
                root_dir = zip_ref.namelist()[0].split('/')[0]

                # Extract to the temporary directory first
                zip_ref.extractall(temp_dir)

                # Move the contents to the target directory
                extracted_dir = os.path.join(temp_dir, root_dir)

                # Create the target directory if it doesn't exist
                os.makedirs(target_dir, exist_ok=True)

                # Copy the contents to the target directory
                for item in os.listdir(extracted_dir):
                    s = os.path.join(extracted_dir, item)
                    d = os.path.join(target_dir, item)
                    if os.path.isdir(s):
                        shutil.copytree(s, d, dirs_exist_ok=True)
                    else:
                        shutil.copy2(s, d)

        print(f"Successfully downloaded and extracted repository to {target_dir}")

        # Check if composer.json exists in the extracted repository
        composer_json_path = os.path.join(target_dir, 'composer.json')
        if not os.path.exists(composer_json_path):
            print(f"Error: composer.json not found in the repository")
            return False

        return True
    except Exception as e:
        print(f"Error downloading GitHub repository archive: {e}")
        return False

def download_composer_json_from_github(github_url, target_path):
    """
    Download composer.json from a GitHub repository.

    This function is kept for backward compatibility.
    It's recommended to use download_github_repository_archive instead.

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
        print(f"Running 'php composer.phar install --no-dev ' in {package_dir}...")
        result = subprocess.run(
            [php_binary_path, composer_path, "--no-dev", "install"],
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
    Main function to handle package installation, bin script execution, and PHP file execution.

    This function:
    1. Parses command-line arguments
    2. Installs the specified PHP package if not already installed
       - For GitHub URLs, downloads the repository archive
       - For package names, creates a composer.json with the package requirement
    3. Executes the specified bin script or PHP file with the correct PHP version
       - If the second argument ends with .php, it's treated as a PHP file
       - Otherwise, it's treated as a bin script from the vendor/bin directory

    Example usage:
        # Install a package from Packagist
        python main.py phpstan/phpstan phpstan analyse src/

        # Install a package from GitHub (downloads the repository archive)
        python main.py https://github.com/phpstan/phpstan phpstan analyse src/

        # Run a PHP file using the installed PHP version
        python main.py phpstan/phpstan script.php arg1 arg2
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Install PHP packages using specific PHP versions and run bin scripts or PHP files')
    parser.add_argument('package', help='PHP package name (vendor/package) or GitHub URL (for GitHub URLs, the repository archive will be downloaded)')
    parser.add_argument('bin_script', nargs='?', help='Bin script to execute (e.g., phpstan) or PHP file to run (e.g., script.php)')
    parser.add_argument('script_args', nargs=argparse.REMAINDER, help='Arguments to pass to the bin script or PHP file')
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
        # For GitHub URLs, download the repository archive
        if not download_github_repository_archive(package_input, package_dir):
            print("Failed to download GitHub repository archive")
            return

        # Read PHP version requirement from composer.json in the extracted repository
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

        # Check if package is already installed
        vendor_dir = os.path.join(package_dir, 'vendor')
        if os.path.exists(vendor_dir) and os.path.isdir(vendor_dir):
            print(f"Package appears to be already installed in {package_dir}")
        else:
            # Run composer install
            run_composer_install(package_dir, php_binary_path, composer_path)

        # Execute bin script or PHP file if specified
        if args.bin_script:
            if args.bin_script.endswith('.php'):
                # It's a PHP file
                execute_php_file(package_dir, php_binary_path, args.bin_script, args.script_args)
            else:
                # It's a bin script
                execute_bin_script(package_dir, php_binary_path, args.bin_script, args.script_args)
    except Exception as e:
        print(f"Error: {e}")
        return

def execute_php_file(package_dir, php_binary_path, php_file, script_args):
    """
    Execute a PHP file using the installed PHP version.

    Args:
        package_dir (str): The package directory
        php_binary_path (str): Path to the PHP binary
        php_file (str): Path to the PHP file to execute (relative to the current directory)
        script_args (list): Arguments to pass to the PHP file

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get the absolute path of the PHP file
        php_file_path = os.path.abspath(php_file)

        # Check if the PHP file exists
        if not os.path.exists(php_file_path):
            print(f"Error: PHP file '{php_file}' not found")
            return False

        # Make sure the PHP binary is executable
        os.chmod(php_binary_path, 0o755)

        # Change to the package directory
        os.chdir(package_dir)

        # Prepare the command
        command = [php_binary_path, php_file_path] + script_args

        print(f"Executing: {' '.join(command)}")

        # Execute the PHP file
        process = subprocess.Popen(command)
        process.wait()

        if process.returncode != 0:
            print(f"PHP file execution failed with return code {process.returncode}")
            return False

        return True
    except Exception as e:
        print(f"Error executing PHP file: {e}")
        return False

def execute_bin_script(package_dir, php_binary_path, bin_script, script_args):
    """
    Execute a bin script from the installed package.

    Args:
        package_dir (str): The package directory
        php_binary_path (str): Path to the PHP binary
        bin_script (str): Name of the bin script to execute
        script_args (list): Arguments to pass to the bin script

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Check if the bin script exists in the vendor/bin directory
        bin_dir = os.path.join(package_dir, 'vendor', 'bin')
        bin_script_path = os.path.join(bin_dir, bin_script)

        if not os.path.exists(bin_script_path):
            print(f"Error: Bin script '{bin_script}' not found in {bin_dir}")
            return False

        # Make sure the PHP binary is executable
        os.chmod(php_binary_path, 0o755)

        # Change to the package directory
        os.chdir(package_dir)

        # Prepare the command
        command = [php_binary_path, bin_script_path] + script_args

        print(f"Executing: {' '.join(command)}")

        # Execute the bin script
        process = subprocess.Popen(command)
        process.wait()

        if process.returncode != 0:
            print(f"Bin script execution failed with return code {process.returncode}")
            return False

        return True
    except Exception as e:
        print(f"Error executing bin script: {e}")
        return False

if __name__ == "__main__":
    main()
