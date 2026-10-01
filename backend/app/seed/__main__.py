"""``python -m app.seed [--reset]`` entry point."""

from __future__ import annotations

import sys

from app.seed.run_seed import main

if __name__ == "__main__":
    main(reset="--reset" in sys.argv[1:])
