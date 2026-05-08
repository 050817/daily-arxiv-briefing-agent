from __future__ import annotations

from typing import Any

from agent.io_utils import load_config, load_json
from agent.schema import STAGES, SkillNotImplementedError, WorkflowResult, validate_stage
from skills.briefing_graph.skill import BriefingGraphSkill
from skills.paper_retrieval.skill import PaperRetrievalSkill
from skills.relevance_ranking.skill import RelevanceRankingSkill


class DailyArxivBriefingAgent:
    """Coordinates the three Skill pipeline with stage-level experiment support."""

    def __init__(self, config_path: str = "config.yaml"):
        self.config = load_config(config_path)
        self.paths = self.config.get("paths", {})
        self.retrieval_skill = PaperRetrievalSkill(self.config)
        self.ranking_skill = RelevanceRankingSkill(self.config)
        self.briefing_skill = BriefingGraphSkill(self.config)

    def run(
        self,
        user_input: dict[str, Any],
        *,
        start_at: str = "retrieval",
        stop_after: str = "briefing",
        input_path: str | None = None,
        allow_missing: bool = True,
    ) -> dict[str, Any]:
        validate_stage(start_at, name="start_at")
        validate_stage(stop_after, name="stop_after")

        start_index = STAGES.index(start_at)
        stop_index = STAGES.index(stop_after)
        if start_index > stop_index:
            raise ValueError("start_at must not come after stop_after.")

        outputs: dict[str, Any] = {}
        completed: list[str] = []
        output_paths: dict[str, str] = {}

        if input_path:
            loaded = load_json(input_path)
            self._seed_outputs(start_at, outputs, loaded)

        for stage in STAGES[start_index : stop_index + 1]:
            try:
                if stage == "retrieval":
                    outputs["retrieval"] = self.retrieval_skill.run(user_input)
                    output_paths["raw_papers"] = self.paths.get("raw_papers", "data/raw/arxiv_papers.json")
                elif stage == "ranking":
                    papers = self._get_papers(outputs)
                    outputs["ranking"] = self.ranking_skill.run(
                        {
                            "query": user_input["query"],
                            "papers": papers,
                            "top_k": user_input.get("top_k", 5),
                            "method": user_input.get("method", "tfidf"),
                            "allowed_categories": user_input.get("allowed_categories"),
                        }
                    )
                    output_paths["ranked_papers"] = self.paths.get(
                        "ranked_papers", "data/processed/ranked_papers.json"
                    )
                elif stage == "briefing":
                    top_k_papers = self._get_top_k_papers(outputs)
                    retrieval_output = outputs.get("retrieval", {})
                    outputs["briefing"] = self.briefing_skill.run(
                        {
                            "query": user_input["query"],
                            "top_k_papers": top_k_papers,
                            "retrieval_error": retrieval_output.get("retrieval_error"),
                            "retrieved_paper_count": len(retrieval_output.get("papers", [])),
                        }
                    )
                    output_paths["report"] = self.paths.get("report", "outputs/reports/daily_briefing.md")

                completed.append(stage)
            except SkillNotImplementedError as exc:
                if not allow_missing:
                    raise
                result = WorkflowResult(
                    status="partial",
                    completed_stages=completed,
                    outputs=outputs,
                    output_paths=output_paths,
                    message=(
                        f"Stopped at {stage}: {exc} Implement this Skill or run with "
                        f"--stop-after {completed[-1] if completed else stage} for earlier-stage experiments."
                    ),
                )
                return result.to_dict()

        return WorkflowResult(
            status="success",
            completed_stages=completed,
            outputs=outputs,
            output_paths=output_paths,
            message="Workflow completed.",
        ).to_dict()

    def _seed_outputs(self, start_at: str, outputs: dict[str, Any], loaded: dict[str, Any]) -> None:
        if start_at == "ranking":
            outputs["retrieval"] = loaded if "papers" in loaded else {"papers": loaded.get("papers", [])}
        elif start_at == "briefing":
            outputs["ranking"] = loaded

    def _get_papers(self, outputs: dict[str, Any]) -> list[dict[str, Any]]:
        retrieval = outputs.get("retrieval", {})
        return retrieval.get("papers", [])

    def _get_top_k_papers(self, outputs: dict[str, Any]) -> list[dict[str, Any]]:
        ranking = outputs.get("ranking", {})
        return ranking.get("top_k_papers") or ranking.get("ranked_papers", [])
