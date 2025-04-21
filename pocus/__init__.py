"""
Pocus - PHP Package Installer and Bin Script Runner

This package allows you to:
1. Install PHP packages with the correct PHP version
2. Run bin scripts from installed packages
3. Download and install packages directly from GitHub repositories
4. Run PHP files using the installed PHP version
"""

from pocus.php_installer import PhpInstaller
from pocus.pocus import main, execute_bin_script, execute_php_file

__all__ = ['PhpInstaller', 'main', 'execute_bin_script', 'execute_php_file']
