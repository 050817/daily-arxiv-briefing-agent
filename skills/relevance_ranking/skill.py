from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent.io_utils import load_json, save_json
from agent.schema import SkillNotImplementedError
from skills.common import add_common_output_arg, not_implemented_result, print_skill_result


class RelevanceRankingSkill:
    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.paths = self.config.get("paths", {})

    def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        raise SkillNotImplementedError(
            "RelevanceRankingSkill.run() is empty. Implement ranking and Top-K filtering here."
        )

    def build_document_text(self, paper: dict[str, Any], mode: str = "title_abstract") -> str:
        raise SkillNotImplementedError("RelevanceRankingSkill.build_document_text() is empty.")

    def rank_with_tfidf(self, query: str, papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
        raise SkillNotImplementedError("RelevanceRankingSkill.rank_with_tfidf() is empty.")

    def rank_with_sbert(self, query: str, papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
        raise SkillNotImplementedError("RelevanceRankingSkill.rank_with_sbert() is empty.")

    def apply_category_filter(
        self, papers: list[dict[str, Any]], allowed_categories: list[str] | None
    ) -> list[dict[str, Any]]:
        raise SkillNotImplementedError("RelevanceRankingSkill.apply_category_filter() is empty.")

    def select_top_k(self, ranked_papers: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
        raise SkillNotImplementedError("RelevanceRankingSkill.select_top_k() is empty.")

    def save_results(self, result: dict[str, Any], output_path: str | None = None) -> None:
        save_json(result, output_path or self.paths.get("ranked_papers", "data/processed/ranked_papers.json"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Relevance Ranking Skill independently.")
    parser.add_argument("--input", required=True, help="Path to Skill 1 raw paper JSON.")
    parser.add_argument("--query", type=str, required=True)
    parser.add_argument("--method", type=str, default="tfidf")
    parser.add_argument("--top_k", type=int, default=5)
    add_common_output_arg(parser)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = load_json(args.input)
    skill = RelevanceRankingSkill()
    try:
        result = skill.run(
            {
                "query": args.query,
                "papers": payload.get("papers", []),
                "method": args.method,
                "top_k": args.top_k,
            }
        )
    except SkillNotImplementedError as exc:
        result = not_implemented_result("relevance_ranking", exc)
    print_skill_result(result, args.output_json)


if __name__ == "__main__":
    main()
