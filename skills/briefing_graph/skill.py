from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent.io_utils import load_json
from agent.schema import SkillNotImplementedError
from skills.common import add_common_output_arg, not_implemented_result, print_skill_result


class BriefingGraphSkill:
    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.paths = self.config.get("paths", {})

    def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        raise SkillNotImplementedError(
            "BriefingGraphSkill.run() is empty. Implement summaries, keyword graph, figures, and report generation here."
        )

    def generate_structured_summary(self, paper: dict[str, Any]) -> dict[str, Any]:
        raise SkillNotImplementedError("BriefingGraphSkill.generate_structured_summary() is empty.")

    def extract_keywords(self, papers: list[dict[str, Any]]) -> dict[str, list[str]]:
        raise SkillNotImplementedError("BriefingGraphSkill.extract_keywords() is empty.")

    def build_keyword_graph(self, paper_keywords: dict[str, list[str]]) -> Any:
        raise SkillNotImplementedError("BriefingGraphSkill.build_keyword_graph() is empty.")

    def analyze_graph(self, graph: Any) -> dict[str, Any]:
        raise SkillNotImplementedError("BriefingGraphSkill.analyze_graph() is empty.")

    def visualize_graph(self, graph: Any, output_path: str) -> None:
        raise SkillNotImplementedError("BriefingGraphSkill.visualize_graph() is empty.")

    def generate_markdown_report(
        self,
        query: str,
        papers: list[dict[str, Any]],
        summaries: list[dict[str, Any]],
        graph_analysis: dict[str, Any],
    ) -> str:
        raise SkillNotImplementedError("BriefingGraphSkill.generate_markdown_report() is empty.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Briefing Graph Skill independently.")
    parser.add_argument("--input", required=True, help="Path to Skill 2 ranked paper JSON.")
    parser.add_argument("--query", type=str, default="")
    parser.add_argument("--top_k", type=int, default=5)
    parser.add_argument("--output", type=str, default="outputs/reports/daily_briefing.md")
    add_common_output_arg(parser)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = load_json(args.input)
    top_k_papers = payload.get("top_k_papers") or payload.get("ranked_papers", [])[: args.top_k]
    skill = BriefingGraphSkill()
    try:
        result = skill.run(
            {
                "query": args.query or payload.get("query", ""),
                "top_k_papers": top_k_papers,
                "output": args.output,
            }
        )
    except SkillNotImplementedError as exc:
        result = not_implemented_result("briefing_graph", exc)
    print_skill_result(result, args.output_json)


if __name__ == "__main__":
    main()
