"""Small local executor boundary; no provider SDK required."""
from pathlib import Path
from typing import Protocol


class Executor(Protocol):
    def probe(self, logs: Path) -> dict: ...
    def launch(self, worktree: Path, context: Path, receipt: Path, logs: Path) -> dict: ...
