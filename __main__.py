"""
Pocus - PHP Package Installer and Bin Script Runner

This module allows the package to be executed directly with:
python -m pocus

It provides the same functionality as running main.py directly.
"""

from pocus.main import main

if __name__ == "__main__":
    main()
