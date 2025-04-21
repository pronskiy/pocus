#!/usr/bin/env python3

import os
import platform
import tarfile
import json
from pathlib import Path
import requests


class PhpInstaller:
    @staticmethod
    def download_php(php_version, download_path, bin_dir):
        """
        Download PHP binary based on platform and PHP version requirements.

        Args:
            php_version (str): PHP version constraint
            download_path (str): Path to download the PHP binary
            bin_dir (str): Directory to extract the PHP binary

        Returns:
            bool: True if successful
        """
        # Determine OS
        system = platform.system()
        os_map = {
            'Darwin': 'macos',
            'Linux': 'linux',
            'Windows': 'win'
        }
        os_name = os_map.get(system)
        if not os_name:
            raise ValueError(f"Unsupported operating system: {system}")

        # Determine architecture
        machine = platform.machine()
        arch_map = {
            'arm64': 'aarch64',
            'x86_64': 'x86_64',
            'AMD64': 'x86_64'  # Windows reports AMD64 for x86_64
        }
        arch = arch_map.get(machine)
        if not arch:
            raise ValueError(f"Unsupported architecture: {machine}")

        # Normalize PHP version
        php_version = PhpInstaller.normalize_php_version(php_version)

        # Construct filename
        php_file = f"php-{php_version}-cli-{os_name}-{arch}.tar.gz"

        # Base URL
        base_url = "https://dl.static-php.dev/static-php-cli/common/"

        # Download URL
        download_url = base_url + php_file

        # Create directories if they don't exist
        os.makedirs(download_path, exist_ok=True)
        os.makedirs(bin_dir, exist_ok=True)

        # Download file
        file_path = os.path.join(download_path, php_file)
        print(f"Downloading {download_url}...")
        PhpInstaller.download(download_url, file_path)

        # Extract file
        with tarfile.open(file_path) as tar:
            tar.extractall(path=bin_dir)

        return True

    @staticmethod
    def compare_versions(version1, version2):
        """
        Compare two version strings.

        Args:
            version1 (str): First version string
            version2 (str): Second version string

        Returns:
            int: -1 if version1 < version2, 0 if version1 == version2, 1 if version1 > version2
        """
        v1_parts = [int(x) for x in version1.split('.')]
        v2_parts = [int(x) for x in version2.split('.')]

        # Pad with zeros if necessary
        while len(v1_parts) < 3:
            v1_parts.append(0)
        while len(v2_parts) < 3:
            v2_parts.append(0)

        # Compare parts
        for i in range(max(len(v1_parts), len(v2_parts))):
            v1 = v1_parts[i] if i < len(v1_parts) else 0
            v2 = v2_parts[i] if i < len(v2_parts) else 0

            if v1 < v2:
                return -1
            elif v1 > v2:
                return 1

        return 0

    @staticmethod
    def normalize_php_version(php_version):
        """
        Find the best matching PHP version from available versions.

        Args:
            php_version (str): PHP version constraint

        Returns:
            str: Normalized PHP version
        """
        # Available PHP versions (hardcoded for now, same as in PHP script)
        available_versions = [
            '8.0.30',
            '8.1.23', '8.1.25', '8.1.26', '8.1.27', '8.1.28', '8.1.29', '8.1.30', '8.1.31', '8.1.32',
            '8.2.10', '8.2.12', '8.2.13', '8.2.14', '8.2.15', '8.2.16', '8.2.17', '8.2.18', '8.2.19', '8.2.21', '8.2.22', '8.2.23', '8.2.24', '8.2.25', '8.2.26', '8.2.27', '8.2.28',
            '8.3.0', '8.3.1', '8.3.10', '8.3.11', '8.3.12', '8.3.13', '8.3.14', '8.3.17', '8.3.19', '8.3.2', '8.3.20', '8.3.3', '8.3.4', '8.3.6', '8.3.7', '8.3.9',
            '8.4.1', '8.4.4', '8.4.5',
        ]
        available_versions.reverse()  # Reverse to get latest versions first

        # Handle double version constraints like "^7.4|^8.0"
        if '|' in php_version:
            # Split by | and use the upper version (last one)
            constraints = php_version.split('|')
            # Use the last constraint (upper version)
            return PhpInstaller.normalize_php_version(constraints[-1].strip())

        # Simple version matching for now
        # This is a simplified version of Composer's version parser
        # For more complex constraints, we would need a more sophisticated parser
        if php_version.startswith('^'):
            # ^8.1 means >=8.1.0 <9.0.0
            major_minor = php_version[1:].split('.')
            if len(major_minor) >= 2:
                major, minor = major_minor[0], major_minor[1]
                for version in available_versions:
                    v_parts = version.split('.')
                    if v_parts[0] == major and int(v_parts[1]) >= int(minor):
                        return version
            else:
                major = major_minor[0]
                for version in available_versions:
                    if version.startswith(f"{major}."):
                        return version
        elif php_version.startswith('~'):
            # ~8.1 means >=8.1.0 <8.2.0
            major_minor = php_version[1:].split('.')
            if len(major_minor) >= 2:
                major, minor = major_minor[0], major_minor[1]
                for version in available_versions:
                    v_parts = version.split('.')
                    if v_parts[0] == major and v_parts[1] == minor:
                        return version
        elif php_version.startswith('>='):
            # >=8.1 means version 8.1 or higher
            constraint_version = php_version[2:]
            for version in available_versions:
                if PhpInstaller.compare_versions(version, constraint_version) >= 0:
                    return version
        else:
            # Exact version or fallback
            for version in available_versions:
                if version.startswith(php_version):
                    return version

        # If no match found, return as is (might be an exact version)
        return php_version

    @staticmethod
    def download(file_source, file_target):
        """
        Download a file with SSL verification.

        Args:
            file_source (str): URL to download from
            file_target (str): Path to save the file to
        """
        # Get the directory of the current script
        script_dir = os.path.dirname(os.path.abspath(__file__))

        r = requests.get(file_source, allow_redirects=True)
        with open(file_target, 'wb') as f:
            f.write(r.content)

    @staticmethod
    def download_composer(pocus_dir):
        """
        Download the latest stable version of Composer if it doesn't already exist.

        Args:
            pocus_dir (str): Path to the .pocus directory

        Returns:
            bool: True if successful or already exists
        """
        composer_url = "https://getcomposer.org/download/latest-stable/composer.phar"
        composer_path = os.path.join(pocus_dir, "composer.phar")

        # Check if Composer already exists
        if os.path.exists(composer_path):
            print(f"Composer is already downloaded at {composer_path}")
            return True

        # Create directory if it doesn't exist
        os.makedirs(pocus_dir, exist_ok=True)

        # Download Composer
        print(f"Downloading Composer from {composer_url}...")
        try:
            PhpInstaller.download(composer_url, composer_path)
            print(f"Successfully downloaded Composer to {composer_path}")
            return True
        except Exception as e:
            print(f"Error downloading Composer: {e}")
            return False

    @staticmethod
    def read_composer_json(composer_json_path):
        """
        Read composer.json and extract PHP version requirement.

        Args:
            composer_json_path (str): Path to composer.json

        Returns:
            str: PHP version constraint
        """
        with open(composer_json_path, 'r') as f:
            composer_data = json.load(f)

        # Extract PHP version requirement
        if 'require' in composer_data and 'php' in composer_data['require']:
            return composer_data['require']['php']
        else:
            raise ValueError("No PHP version requirement found in composer.json")

def main():
    """
    Main function to download PHP binary based on composer.json.
    """
    # Get the current directory
    current_dir = os.getcwd()

    # Path to composer.json
    composer_json_path = os.path.join(current_dir, 'composer.json')

    # Check if composer.json exists
    if not os.path.exists(composer_json_path):
        print("Error: composer.json not found in the current directory")
        print("Please make sure you're running this script from a directory containing a composer.json file.")
        return

    # Read PHP version requirement from composer.json
    try:
        php_version = PhpInstaller.read_composer_json(composer_json_path)
        print(f"Found PHP version requirement: {php_version}")
    except Exception as e:
        print(f"Error reading composer.json: {e}")
        print("Please make sure your composer.json file has a valid 'require' section with a 'php' entry.")
        return

    # Normalize PHP version
    normalized_version = PhpInstaller.normalize_php_version(php_version)
    if normalized_version != php_version:
        print(f"Normalized PHP version: {normalized_version}")

    # Get system information
    system = platform.system()
    machine = platform.machine()
    print(f"Detected system: {system} ({machine})")

    # Set up paths in ~/.pocus directory
    home_dir = str(Path.home())
    pocus_dir = os.path.join(home_dir, '.pocus')
    version_dir = os.path.join(pocus_dir, normalized_version)
    download_path = os.path.join(pocus_dir, 'downloads')
    bin_dir = version_dir

    # Download PHP binary
    try:
        # Check if PHP binary already exists
        php_binary_path = os.path.join(bin_dir, 'php')
        if os.path.exists(php_binary_path):
            print(f"PHP {normalized_version} is already downloaded at {bin_dir}")
            print(f"PHP binary path: {php_binary_path}")
        else:
            print(f"Downloading PHP {normalized_version}...")
            PhpInstaller.download_php(php_version, download_path, bin_dir)
            print(f"Successfully downloaded PHP {normalized_version} to {bin_dir}")
            print(f"PHP binary path: {os.path.join(bin_dir, 'php')}")

        # Download Composer
        PhpInstaller.download_composer(pocus_dir)
    except Exception as e:
        print(f"Error downloading PHP: {e}")
        print("\nTroubleshooting suggestions:")
        print("1. Check your internet connection")
        print("2. Verify that the PHP version specified in composer.json is available")
        print("3. Try running the script with administrator/root privileges")
        print("4. Check if your system's architecture and OS are supported")

if __name__ == "__main__":
    main()
