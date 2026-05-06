from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent.io_utils import save_json
from agent.schema import SkillNotImplementedError
from skills.common import add_common_output_arg, not_implemented_result, print_skill_result


class PaperRetrievalSkill:
    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.paths = self.config.get("paths", {})

    def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        raise SkillNotImplementedError(
            "PaperRetrievalSkill.run() is empty. Implement arXiv search and metadata parsing here."
        )

    def search_arxiv(self, query: str, max_results: int) -> list[Any]:
        raise SkillNotImplementedError("PaperRetrievalSkill.search_arxiv() is empty.")

    def filter_by_date(self, papers: list[dict[str, Any]], date_range: str) -> list[dict[str, Any]]:
        raise SkillNotImplementedError("PaperRetrievalSkill.filter_by_date() is empty.")

    def parse_metadata(self, raw_paper: Any) -> dict[str, Any]:
        raise SkillNotImplementedError("PaperRetrievalSkill.parse_metadata() is empty.")

    def save_results(self, papers: list[dict[str, Any]], output_path: str | None = None) -> None:
        save_json({"papers": papers}, output_path or self.paths.get("raw_papers", "data/raw/arxiv_papers.json"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Paper Retrieval Skill independently.")
    parser.add_argument("--query", type=str, required=True)
    parser.add_argument("--date_range", type=str, default="last 7 days")
    parser.add_argument("--max_results", type=int, default=50)
    add_common_output_arg(parser)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    skill = PaperRetrievalSkill()
    try:
        result = skill.run(
            {
                "query": args.query,
                "date_range": args.date_range,
                "max_results": args.max_results,
            }
        )
    except SkillNotImplementedError as exc:
        result = not_implemented_result("paper_retrieval", exc)
    print_skill_result(result, args.output_json)


if __name__ == "__main__":
    main()
