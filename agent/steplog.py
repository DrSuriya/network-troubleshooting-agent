"""Append-only step log: one JSON line per agent step."""

import json
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_LOG_PATH = Path(__file__).parent / "logs" / "steps.jsonl"


def log_step(tool, inputs, output, reason, path=DEFAULT_LOG_PATH):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "time": datetime.now(timezone.utc).isoformat(),
        "tool": tool,
        "inputs": inputs,
        "output": output,
        "reason": reason,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
