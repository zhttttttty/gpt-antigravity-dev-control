#!/usr/bin/env python3
"""Location-independent forwarding only; repository owns implementation."""
import argparse
from pathlib import Path
import subprocess
import sys

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("--repo", type=Path, default=Path.cwd())
args, rest = parser.parse_known_args()
repo = args.repo.resolve()
entry = repo / ".ai/scripts/delegate.py"
if not entry.is_file():
    parser.error("--repo must contain .ai/scripts/delegate.py")
raise SystemExit(subprocess.call([sys.executable, str(entry), "--repo", str(repo), *rest], cwd=repo))
