# Pocus - PHP Version Installer

## Project Description

Pocus is a tool designed to automatically download and install specific PHP versions based on the requirements specified in a composer.json file. It simplifies the process of managing PHP versions for different projects by automatically detecting the required PHP version and downloading the appropriate binary for the user's operating system and architecture.

## Key Features

- Automatically detects required PHP version from composer.json
- Supports various version constraints (^, ~, >=)
- Downloads the appropriate PHP binary for the current operating system and architecture
- Stores downloaded PHP binaries in a user-specific directory (~/.pocus)
- Cross-platform support (macOS, Linux, Windows)
- Multiple architecture support (x86_64, arm64)

## Project Structure

The project consists of the following files:

- **php_installer.py**: The main implementation file containing the PhpInstaller class and main function. This handles reading the composer.json file, determining the required PHP version, and downloading the appropriate PHP binary.

- **main.py**: A template file created by PyCharm, not currently used in the project.

## Usage

To use Pocus, simply run the php_installer.py script from a directory containing a composer.json file:

```bash
python php_installer.py
```

The script will:
1. Read the PHP version requirement from composer.json
2. Normalize the PHP version to match available versions
3. Download the appropriate PHP binary if it doesn't already exist
4. Store the PHP binary in ~/.pocus/{version}/

## Implementation Details

### PhpInstaller Class

The PhpInstaller class provides the following methods:

- **download_php**: Downloads PHP binary based on platform and PHP version requirements
- **compare_versions**: Compares two version strings
- **normalize_php_version**: Finds the best matching PHP version from available versions
- **download**: Downloads a file with SSL verification
- **read_composer_json**: Reads composer.json and extracts PHP version requirement

### Directory Structure

Pocus creates the following directory structure in the user's home directory:

```
~/.pocus/
  ├── downloads/       # Temporary storage for downloaded archives
  └── {version}/       # Extracted PHP binaries for each version
      └── php          # PHP binary executable
```

## Development

To contribute to Pocus, you can:

1. Add support for more PHP versions in the `available_versions` list
2. Improve version constraint parsing
3. Add more features like version switching or environment management
