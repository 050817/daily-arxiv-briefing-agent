from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent.io_utils import load_json
from skills.relevance_ranking.skill import RelevanceRankingSkill


SAMPLE_PAPERS = [
    {
        "title": "Graph Neural Networks for Social Misinformation Detection",
        "authors": ["A. Researcher"],
        "abstract": "We study graph neural networks for misinformation detection in social networks.",
        "published_date": "2026-05-01",
        "arxiv_id": "2605.00001",
        "url": "https://arxiv.org/abs/2605.00001",
        "categories": ["cs.SI", "cs.LG"],
    },
    {
        "title": "A Survey of Image Segmentation Models",
        "authors": ["B. Scientist"],
        "abstract": "This paper reviews convolutional and transformer models for image segmentation.",
        "published_date": "2026-05-02",
        "arxiv_id": "2605.00002",
        "url": "https://arxiv.org/abs/2605.00002",
        "categories": ["cs.CV"],
    },
    {
        "title": "Community Detection in Dynamic Social Networks",
        "authors": ["C. Analyst"],
        "abstract": "We detect evolving communities and social network structures over time.",
        "published_date": "2026-05-03",
        "arxiv_id": "2605.00003",
        "url": "https://arxiv.org/abs/2605.00003",
        "categories": ["cs.SI"],
    },
]


class RelevanceRankingSkillTest(unittest.TestCase):
    def test_run_ranks_papers_and_preserves_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "ranked_papers.json"
            skill = RelevanceRankingSkill({"paths": {"ranked_papers": str(output_path)}})

            result = skill.run(
                {
                    "query": "graph neural networks misinformation detection",
                    "papers": SAMPLE_PAPERS,
                    "top_k": 2,
                    "method": "tfidf",
                }
            )

            self.assertEqual(len(result["ranked_papers"]), 3)
            self.assertEqual(len(result["top_k_papers"]), 2)
            self.assertEqual(
                result["ranked_papers"][0]["title"],
                "Graph Neural Networks for Social Misinformation Detection",
            )
            self.assertEqual(result["ranked_papers"][0]["authors"], ["A. Researcher"])
            self.assertEqual(result["ranked_papers"][0]["url"], "https://arxiv.org/abs/2605.00001")
            self.assertEqual(result["ranked_papers"][0]["rank"], 1)
            self.assertGreater(result["ranked_papers"][0]["relevance_score"], 0)
            self.assertIn("ranking_reason", result["ranked_papers"][0])
            self.assertTrue(output_path.exists())
            self.assertEqual(load_json(output_path), result)

    def test_apply_category_filter_uses_category_intersection(self):
        skill = RelevanceRankingSkill()

        filtered = skill.apply_category_filter(SAMPLE_PAPERS, ["cs.SI", "stat.ML"])

        self.assertEqual([paper["arxiv_id"] for paper in filtered], ["2605.00001", "2605.00003"])

    def test_apply_category_filter_accepts_single_category_string(self):
        skill = RelevanceRankingSkill()

        filtered = skill.apply_category_filter(SAMPLE_PAPERS, "cs.CV")

        self.assertEqual([paper["arxiv_id"] for paper in filtered], ["2605.00002"])

    def test_select_top_k_handles_zero(self):
        skill = RelevanceRankingSkill()
        ranked = skill.rank_with_tfidf("social networks", SAMPLE_PAPERS)

        self.assertEqual(skill.select_top_k(ranked, 0), [])

    def test_build_document_text_supports_modes(self):
        skill = RelevanceRankingSkill()
        paper = SAMPLE_PAPERS[0]

        self.assertEqual(
            skill.build_document_text(paper, "title"),
            "Graph Neural Networks for Social Misinformation Detection",
        )
        self.assertIn("cs.SI", skill.build_document_text(paper, "title_abstract_categories"))


if __name__ == "__main__":
    unittest.main()
