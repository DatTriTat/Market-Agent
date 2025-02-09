from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def read_text(path: str) -> str:
    p = Path(path)
    if p.exists():
        return p.read_text(encoding="utf-8")
    return ""


def normalize_text(s: str) -> str:
    return " ".join((s or "").strip().split())
