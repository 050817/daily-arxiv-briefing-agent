from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from agent.io_utils import load_json
from agent.schema import SkillNotImplementedError


def add_common_output_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output-json", type=str, default=None)


def load_skill_input(input_path: str | None, defaults: dict[str, Any]) -> dict[str, Any]:
    if not input_path:
        return defaults
    loaded = load_json(input_path)
    return {**defaults, **loaded}


def print_skill_result(result: dict[str, Any], output_json: str | None = None) -> None:
    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text)
    if output_json:
        path = Path(output_json)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def not_implemented_result(skill_name: str, exc: SkillNotImplementedError) -> dict[str, Any]:
    return {
        "status": "not_implemented",
        "skill": skill_name,
        "message": str(exc),
    }
