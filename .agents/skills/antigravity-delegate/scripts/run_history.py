"""Inspect daily run records without launching, cleaning or accepting work."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess


RUN_ID = re.compile(r"\d{8}T\d{6}Z-[0-9a-f]{8}\Z")


def history(root: Path, ident: str | None = None, limit: int = 20) -> dict:
    if limit < 1 or limit > 1000:
        raise ValueError("--limit must be between 1 and 1000")
    if ident is not None and ident != "latest" and not RUN_ID.fullmatch(ident):
        raise ValueError("Expected a run ID or latest")
    common = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
                            cwd=root, check=True, capture_output=True, text=True,
                            encoding="utf-8", timeout=15).stdout.strip()
    directory = Path(common).resolve() / "agy-runs"
    if directory.is_symlink():
        raise ValueError("Run history directory must not be a link")
    records = sorted((p for p in directory.glob("*/result.json") if RUN_ID.fullmatch(p.parent.name)),
                     key=lambda p: (p.stat().st_mtime_ns, p.parent.name), reverse=True)
    if ident:
        records = records[:1] if ident == "latest" else [directory / ident / "result.json"]
        if not records or not records[0].is_file():
            raise ValueError("No daily run found; preview or execute with run first")
    summaries, errors = [], []
    for path in records[:limit]:
        try:
            if (path.resolve() != directory / path.parent.name / "result.json"
                    or path.stat().st_size > 8_000_000):
                raise ValueError("Linked or oversized run record")
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or data.get("run_id") != path.parent.name:
                raise ValueError("Run record identity mismatch")
            if ident:
                return data
            summaries.append({key: data.get(key) for key in (
                "run_id", "status", "checks_status", "worktree", "result_file", "elapsed_seconds", "next_step")})
        except (ValueError, OSError) as exc:
            if ident:
                raise ValueError(f"Cannot read run {path.parent.name}: {exc}") from exc
            errors.append({"run_id": path.parent.name, "error": str(exc)})
    return {"runs": summaries, "total": len(records), "errors": errors,
            "next_step": "Use runs RUN-ID for the complete record; review its diff, new files and check logs"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id", nargs="?")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    print(json.dumps(history(Path.cwd(), args.run_id, args.limit), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
