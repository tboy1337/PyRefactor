"""PyInstaller entry point for the PyRefactor standalone executable."""

import sys

from pyrefactor.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
