# Pocus - PHP Package Installer and Runner

Pocus is a Python tool that simplifies PHP package management and execution. It automatically detects and installs the required PHP version based on composer.json requirements, downloads PHP packages, and provides an easy way to run bin scripts and PHP files.

## Features

- **Automatic PHP Version Management**: Detects required PHP version from composer.json and installs it
- **Package Installation**: Installs PHP packages using Composer
- **Bin Script Execution**: Runs bin scripts from installed packages
- **GitHub Repository Support**: Downloads and installs packages directly from GitHub URLs
- **PHP File Execution**: Runs PHP files using the installed PHP version
- **Cross-Platform**: Works on macOS, Linux, and Windows
- **Multiple Architecture Support**: Supports x86_64, arm64, and more

## Installation

```bash
# Clone the repository
git clone https://github.com/pronskiy/pocus.git
cd pocus

# Install as a Python package (optional)
pip install -e .
```

## Usage

### Basic Usage

```bash
# Install a package and its dependencies
python -m pocus phpstan/phpstan

# Run a bin script from an installed package
python -m pocus phpstan/phpstan phpstan analyse path/to/code

# Run a PHP file using the installed PHP version
python -m pocus phpstan/phpstan script.php arg1 arg2
```

### Installing from GitHub

```bash
# Install a package directly from GitHub
python -m pocus https://github.com/phpstan/phpstan
```

### Version Constraints

Pocus supports various version constraints in composer.json:

```json
{
    "require": {
        "php": "^7.4|^8.0"  // Will use PHP 8.0
    }
}
```

## How It Works

1. Pocus reads the PHP version requirement from composer.json
2. It normalizes the PHP version to match available versions
3. It downloads the appropriate PHP binary if it doesn't already exist
4. It stores the PHP binary in ~/.pocus/{version}/
5. It installs the requested package using Composer
6. It executes bin scripts or PHP files as requested

## Directory Structure

```
~/.pocus/
  ├── downloads/       # Temporary storage for downloaded archives
  └── {version}/       # Extracted PHP binaries for each version
      └── php          # PHP binary executable
```

## Requirements

- Python 3.6+
- Internet connection for downloading PHP binaries and packages

## Contributing

Contributions are welcome! Feel free to submit issues or pull requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

