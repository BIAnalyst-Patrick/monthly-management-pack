"""``python -m pack.report`` — the command the README documents.

The work lives next to this file: ``cli`` handles arguments and the scratch
output root, ``key`` builds the answer key, ``render`` writes the markdown and
``tables`` writes the CSVs. This module stays as a thin entry point so the
documented command keeps working.
"""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
