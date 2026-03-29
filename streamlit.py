#!/usr/bin/env python3
"""Project launcher for Streamlit.

Usage:
  python streamlit.py
  python streamlit.py --server.port 8550 --server.headless true
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HOME_FILE = ROOT / "Home.py"


def _remove_local_shadowing() -> None:
    # This file is intentionally named streamlit.py; remove local paths so the
    # real installed `streamlit` package is imported instead of this file.
    root_str = str(ROOT)
    sys.path[:] = [p for p in sys.path if p not in ("", root_str)]


def main() -> int:
    if not HOME_FILE.exists():
        print(f"Error: {HOME_FILE} not found.", file=sys.stderr)
        return 1

    _remove_local_shadowing()

    from streamlit.web.cli import main as streamlit_main

    args = ["streamlit", "run", str(HOME_FILE)]

    if not any(arg.startswith("--server.port") for arg in sys.argv[1:]):
        args.extend(["--server.port", "8501"])
    if not any(arg.startswith("--server.headless") for arg in sys.argv[1:]):
        args.extend(["--server.headless", "true"])

    args.extend(sys.argv[1:])
    sys.argv = args
    return int(streamlit_main())


if __name__ == "__main__":
    raise SystemExit(main())
