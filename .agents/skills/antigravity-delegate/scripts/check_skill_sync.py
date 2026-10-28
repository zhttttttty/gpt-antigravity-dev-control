"""Compare this canonical skill package with another installed copy."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


IGNORED_PARTS = {"__pycache__", ".pytest_cache"}


def manifest(root: Path) -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    for path in root.rglob("*"):
        if not path.is_file() or any(part in IGNORED_PARTS for part in path.parts) or path.suffix.lower() == ".pyc":
            continue
        relative = path.relative_to(root).as_posix()
        raw = path.read_bytes()
        try:
            normalized = raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
        except UnicodeDecodeError:
            normalized = raw
        result[relative] = normalized
    return result


def compare(canonical: Path, other: Path) -> dict[str, object]:
    left = manifest(canonical)
    right = manifest(other)
    missing = sorted(left.keys() - right.keys())
    extra = sorted(right.keys() - left.keys())
    changed = sorted(path for path in left.keys() & right.keys() if left[path] != right[path])
    return {
        "canonical": str(canonical.resolve()),
        "other": str(other.resolve()),
        "in_sync": not (missing or extra or changed),
        "missing": missing,
        "extra": extra,
        "changed": changed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--other", type=Path, required=True)
    args = parser.parse_args()
    if not args.canonical.is_dir() or not args.other.is_dir():
        parser.error("canonical and other must both be skill directories")
    result = compare(args.canonical, args.other)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["in_sync"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
