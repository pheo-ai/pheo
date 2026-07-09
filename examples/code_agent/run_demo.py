#!/usr/bin/env python3
"""Thin repo wrapper for the packaged code-agent demo."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pheo.examples.code_agent.run_demo import main


if __name__ == "__main__":
    raise SystemExit(main())
