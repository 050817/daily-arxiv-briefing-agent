from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from skills.briefing_graph.skill import BriefingGraphSkill


SAMPLE_TOP_K_PAPERS = [
    {
        "title": "Graph Neural Networks for Social Misinformation Detection",
        "authors": ["A. Researcher"],
        "abstract": (
            "We study graph neural networks for misinformation detection in social networks. "
            "Experiments on benchmark datasets show improved detection results."
        ),
        "published_date": "2026-05-01",
        "arxiv_id": "2605.00001",
        "url": "https://arxiv.org/abs/2605.00001",
        "categories": ["cs.SI", "cs.LG"],
        "rank": 1,
        "relevance_score": 0.91,
        "ranking_reason": "Matches query terms in the title.",
    },
    {
        "title": "Community Detection in Dynamic Social Networks",
        "authors": ["B. Analyst"],
        "abstract": "This paper presents a framework for community detection in dynamic social networks.",
        "published_date": "2026-05-02",
        "arxiv_id": "2605.00002",
        "url": "https://arxiv.org/abs/2605.00002",
        "categories": ["cs.SI"],
        "rank": 2,
        "relevance_score": 0.72,
        "ranking_reason": "Matches social network vocabulary.",
    },
]


class BriefingGraphSkillTest(unittest.TestCase):
    def test_generate_structured_summary_is_abstract_grounded(self):
        skill = BriefingGraphSkill()

        summary = skill.generate_structured_summary(SAMPLE_TOP_K_PAPERS[1])

        self.assertEqual(summary["title"], "Community Detection in Dynamic Social Networks")
        self.assertIn("framework for community detection", summary["method"])
        self.assertEqual(summary["experiment_or_evidence"], "Not mentioned in abstract")
        self.assertEqual(summary["limitation"], "Not mentioned in abstract")
        self.assertEqual(summary["evidence_source"], "title and abstract only")

    def test_keyword_graph_analysis_finds_central_keywords(self):
        skill = BriefingGraphSkill()

        paper_keywords = skill.extract_keywords(SAMPLE_TOP_K_PAPERS)
        graph = skill.build_keyword_graph(paper_keywords)
        analysis = skill.analyze_graph(graph)

        self.assertGreater(analysis["num_nodes"], 0)
        self.assertGreater(analysis["num_edges"], 0)
        central = [item["keyword"] for item in analysis["central_keywords"]]
        self.assertIn("social networks", central)
        self.assertNotIn("detection graph neural", central)
        self.assertTrue(analysis["communities"])

    def test_run_writes_report_and_figures(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "daily_briefing.md"
            figures_dir = Path(tmpdir) / "figures"
            skill = BriefingGraphSkill({"paths": {"report": str(report_path), "figures_dir": str(figures_dir)}})

            result = skill.run(
                {
                    "query": "graph neural networks for misinformation detection",
                    "top_k_papers": SAMPLE_TOP_K_PAPERS,
                }
            )

            self.assertEqual(result["report_markdown"], str(report_path))
            self.assertTrue(report_path.exists())
            report = report_path.read_text(encoding="utf-8")
            self.assertIn("Evidence policy", report)
            self.assertIn("Not mentioned in abstract", report)
            self.assertIn("## Keyword Network Analysis", report)
            self.assertEqual(len(result["figures"]), 2)
            for figure in result["figures"]:
                self.assertTrue(Path(figure).exists())
                self.assertIn("<svg", Path(figure).read_text(encoding="utf-8"))

    def test_empty_run_with_retrieval_error_is_explicit_and_does_not_generate_figures(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "daily_briefing.md"
            skill = BriefingGraphSkill({"paths": {"report": str(report_path), "figures_dir": str(Path(tmpdir) / "figures")}})

            result = skill.run(
                {
                    "query": "harness engineering",
                    "top_k_papers": [],
                    "retrieval_error": "Failed to retrieve papers from arXiv: HTTP Error 429",
                    "retrieved_paper_count": 0,
                }
            )

            self.assertEqual(result["figures"], [])
            report = report_path.read_text(encoding="utf-8")
            self.assertIn("Data retrieval failed before analysis", report)
            self.assertIn("arXiv returned HTTP 429 (rate limited)", report)
            self.assertIn("Do not interpret the empty result as evidence", report)
            self.assertIn("Analysis not run because no papers were retrieved or supplied.", report)
            self.assertIn("Primary limitation for this run", report)

    def test_summary_does_not_use_metadata_url_as_problem_or_not_only_as_limitation(self):
        skill = BriefingGraphSkill()
        paper = {
            "title": "BioMedArena: An Open-source Toolkit for Building and Evaluating Biomedical Deep Research Agents",
            "abstract": (
                "Building a deep research agent today is an exercise in glue code because harness and tool registry all differ. "
                "We call this the per-paper engineering tax and release BioMedArena, an open-source toolkit that not only alleviates it but also provides an arena for fair comparison. "
                "The toolkit is available at https://github.com/AI-in-Health/BioMedArena."
            ),
        }

        summary = skill.generate_structured_summary(paper)

        self.assertIn("glue code", summary["problem"])
        self.assertNotIn("https://", summary["problem"])
        self.assertIn("release BioMedArena", summary["contribution"])
        self.assertEqual(summary["experiment_or_evidence"], "Not mentioned in abstract")
        self.assertEqual(summary["limitation"], "Not mentioned in abstract")

    def test_report_warns_when_query_terms_are_weakly_covered(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "briefing.md"
            skill = BriefingGraphSkill({"paths": {"report": str(report_path), "figures_dir": str(Path(tmpdir) / "figures")}})
            papers = [
                {
                    "title": "Harness Evaluation Toolkit",
                    "abstract": "The harness reduces model evaluation engineering effort.",
                    "rank": 1,
                    "relevance_score": 0.1,
                },
                {
                    "title": "Quantum Engineering Study",
                    "abstract": "This paper studies engineering for quantum systems.",
                    "rank": 2,
                    "relevance_score": 0.01,
                },
            ]

            skill.run({"query": "harness engineering", "top_k_papers": papers})

            report = report_path.read_text(encoding="utf-8")
            self.assertIn("## Relevance Caution", report)
            self.assertIn("broader keyword matches", report)

    def test_graph_query_report_does_not_include_unrelated_hard_coded_topic_text(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "briefing.md"
            skill = BriefingGraphSkill({"paths": {"report": str(report_path), "figures_dir": str(Path(tmpdir) / "figures")}})

            skill.run(
                {
                    "query": "graph neural networks",
                    "top_k_papers": SAMPLE_TOP_K_PAPERS,
                }
            )

            report = report_path.read_text(encoding="utf-8")
            self.assertNotIn("harness engineering", report)
            self.assertNotIn("harness-engineering", report)

    def test_query_focus_keywords_are_added_when_supported_by_paper_text(self):
        skill = BriefingGraphSkill()
        papers = [
            {
                "title": "Harness Evaluation Toolkit",
                "abstract": "The harness reduces evaluation engineering effort.",
            }
        ]
        paper_keywords = {"Harness Evaluation Toolkit": ["toolkit"]}

        skill._add_query_focus_keywords(paper_keywords, papers, "harness engineering")

        self.assertEqual(
            paper_keywords["Harness Evaluation Toolkit"][:3],
            ["harness engineering", "harness", "engineering"],
        )


if __name__ == "__main__":
    unittest.main()
