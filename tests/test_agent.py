from __future__ import annotations

import unittest

from agent.orchestrator import DailyArxivBriefingAgent
from agent.schema import SkillNotImplementedError


class MissingRetrievalSkill:
    def run(self, input_data):
        raise SkillNotImplementedError("PaperRetrievalSkill.run() is intentionally unavailable for this test.")


class FakeRetrievalSkill:
    def run(self, input_data):
        return {
            "papers": [
                {
                    "title": "Graph Neural Networks for Social Misinformation",
                    "authors": ["A. Researcher"],
                    "abstract": "We study graph neural networks for misinformation detection.",
                    "published_date": "2026-05-01",
                    "arxiv_id": "2605.00001",
                    "url": "https://arxiv.org/abs/2605.00001",
                    "categories": ["cs.SI", "cs.LG"],
                }
            ]
        }


class FakeRankingSkill:
    def run(self, input_data):
        paper = dict(input_data["papers"][0])
        paper.update({"rank": 1, "relevance_score": 0.95, "ranking_reason": "Matches query keywords."})
        return {"ranked_papers": [paper], "top_k_papers": [paper]}


class FakeBriefingSkill:
    def run(self, input_data):
        return {
            "report_markdown": "outputs/reports/daily_briefing.md",
            "summaries": [{"title": input_data["top_k_papers"][0]["title"]}],
            "graph_analysis": {"num_nodes": 0, "num_edges": 0},
            "figures": [],
        }


class DailyArxivBriefingAgentTest(unittest.TestCase):
    def test_missing_first_skill_stops_cleanly(self):
        agent = DailyArxivBriefingAgent()
        agent.retrieval_skill = MissingRetrievalSkill()
        result = agent.run({"query": "graph neural networks"}, stop_after="retrieval")

        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["completed_stages"], [])
        self.assertIn("intentionally unavailable", result["message"])

    def test_can_stop_after_retrieval_when_later_skills_are_missing(self):
        agent = DailyArxivBriefingAgent()
        agent.retrieval_skill = FakeRetrievalSkill()

        result = agent.run({"query": "graph neural networks"}, stop_after="retrieval")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["completed_stages"], ["retrieval"])
        self.assertEqual(len(result["outputs"]["retrieval"]["papers"]), 1)

    def test_full_pipeline_contract_with_filled_skills(self):
        agent = DailyArxivBriefingAgent()
        agent.retrieval_skill = FakeRetrievalSkill()
        agent.ranking_skill = FakeRankingSkill()
        agent.briefing_skill = FakeBriefingSkill()

        result = agent.run({"query": "graph neural networks", "top_k": 1})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["completed_stages"], ["retrieval", "ranking", "briefing"])
        self.assertEqual(result["outputs"]["ranking"]["top_k_papers"][0]["rank"], 1)
        self.assertEqual(result["outputs"]["briefing"]["report_markdown"], "outputs/reports/daily_briefing.md")


if __name__ == "__main__":
    unittest.main()
