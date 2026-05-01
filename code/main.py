"""Entry-point for the support triage CLI."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure code/ directory is on sys.path regardless of CWD
_CODE_DIR = Path(__file__).parent.resolve()
if str(_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(_CODE_DIR))

# Load .env if present (never overwrites real env vars)
try:
    from dotenv import load_dotenv
    load_dotenv(_CODE_DIR.parent / ".env", override=False)
    load_dotenv(_CODE_DIR / ".env", override=False)
except ImportError:
    pass

from cli.app import app

if __name__ == "__main__":
    app()
