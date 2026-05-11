from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml


if getattr(sys, "frozen", False):
    PROJECT_ROOT = Path(sys.executable).resolve().parent
else:
    PROJECT_ROOT = Path(__file__).resolve().parents[1]


def resolve_path(path: str | Path) -> Path:
    path = Path(path)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def ensure_parent(path: str | Path) -> Path:
    resolved = resolve_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def ensure_dir(path: str | Path) -> Path:
    resolved = resolve_path(path)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def load_json(path: str | Path) -> dict[str, Any]:
    resolved = resolve_path(path)
    with resolved.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: dict[str, Any], path: str | Path) -> Path:
    resolved = ensure_parent(path)
    with resolved.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return resolved


def load_config(path: str | Path = "config.yaml") -> dict[str, Any]:
    resolved = resolve_path(path)
    if not resolved.exists():
        return {}
    with resolved.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
