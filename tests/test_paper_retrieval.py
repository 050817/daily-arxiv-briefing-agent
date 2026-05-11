from __future__ import annotations

import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from agent.io_utils import load_json
from skills.paper_retrieval.skill import ATOM_NAMESPACE, PaperRetrievalSkill


SAMPLE_ENTRY = """
<entry xmlns="http://www.w3.org/2005/Atom">
  <id>https://arxiv.org/abs/2605.00001v1</id>
  <updated>2026-05-02T00:00:00Z</updated>
  <published>2026-05-01T12:34:56Z</published>
  <title>
    Graph Neural Networks for Social Misinformation Detection
  </title>
  <summary>
    This paper studies graph neural networks for misinformation detection in social networks.
  </summary>
  <author><name>A. Researcher</name></author>
  <author><name>B. Scientist</name></author>
  <link href="https://arxiv.org/abs/2605.00001v1" rel="alternate" type="text/html" />
  <category term="cs.SI" scheme="http://arxiv.org/schemas/atom" />
  <category term="cs.LG" scheme="http://arxiv.org/schemas/atom" />
</entry>
""".strip()


class PaperRetrievalSkillTest(unittest.TestCase):
    def test_build_search_query_can_use_llm_keyword_phrases(self):
        skill = PaperRetrievalSkill()

        search_query = skill._build_search_query(
            "graph neural networks for misinformation detection",
            keyword_phrases=["graph neural networks", "misinformation detection"],
        )

        self.assertEqual(
            search_query,
            '((ti:"graph neural networks" OR abs:"graph neural networks") OR ((ti:graph OR abs:graph) AND (ti:neural OR abs:neural) AND (ti:networks OR abs:networks))) AND ((ti:"misinformation detection" OR abs:"misinformation detection") OR ((ti:misinformation OR abs:misinformation) AND (ti:detection OR abs:detection)))',
        )

    def test_build_search_query_broadens_natural_language_query(self):
        skill = PaperRetrievalSkill()

        search_query = skill._build_search_query("graph neural networks for misinformation detection")

        self.assertEqual(
            search_query,
            '((ti:"graph neural networks" OR abs:"graph neural networks") OR ((ti:graph OR abs:graph) AND (ti:neural OR abs:neural) AND (ti:networks OR abs:networks))) AND ((ti:"misinformation detection" OR abs:"misinformation detection") OR ((ti:misinformation OR abs:misinformation) AND (ti:detection OR abs:detection)))',
        )

    def test_build_search_query_requires_all_terms_in_short_phrase(self):
        skill = PaperRetrievalSkill()

        search_query = skill._build_search_query("harness engineering")

        self.assertEqual(
            search_query,
            '((ti:"harness engineering" OR abs:"harness engineering") OR ((ti:harness OR abs:harness) AND (ti:engineering OR abs:engineering)))',
        )

    def test_build_search_query_preserves_non_ascii_tokens(self):
        skill = PaperRetrievalSkill()

        search_query = skill._build_search_query('图神经 networks, misinformation')

        self.assertIn(" AND ", search_query)
        self.assertIn("misinformation", search_query)

    def test_build_search_query_preserves_advanced_arxiv_syntax(self):
        skill = PaperRetrievalSkill()

        search_query = skill._build_search_query('cat:cs.LG AND ti:"graph neural networks"')

        self.assertEqual(search_query, 'cat:cs.LG AND ti:"graph neural networks"')

    def test_parse_metadata_extracts_expected_fields(self):
        skill = PaperRetrievalSkill()
        paper = skill.parse_metadata(ET.fromstring(SAMPLE_ENTRY))

        self.assertEqual(paper["title"], "Graph Neural Networks for Social Misinformation Detection")
        self.assertEqual(paper["authors"], ["A. Researcher", "B. Scientist"])
        self.assertEqual(
            paper["abstract"],
            "This paper studies graph neural networks for misinformation detection in social networks.",
        )
        self.assertEqual(paper["published_date"], "2026-05-01")
        self.assertEqual(paper["arxiv_id"], "2605.00001v1")
        self.assertEqual(paper["url"], "https://arxiv.org/abs/2605.00001v1")
        self.assertEqual(paper["categories"], ["cs.SI", "cs.LG"])

    def test_filter_by_date_keeps_only_recent_papers(self):
        skill = PaperRetrievalSkill()
        today = datetime.now(timezone.utc).date()
        papers = [
            {"title": "today", "published_date": today.isoformat()},
            {"title": "within_range", "published_date": (today - timedelta(days=6)).isoformat()},
            {"title": "out_of_range", "published_date": (today - timedelta(days=7)).isoformat()},
            {"title": "missing_date", "published_date": ""},
        ]

        filtered = skill.filter_by_date(papers, "last 7 days")

        self.assertEqual([paper["title"] for paper in filtered], ["today", "within_range"])

    def test_run_returns_papers_and_saves_results(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "raw" / "arxiv_papers.json"
            skill = PaperRetrievalSkill({"paths": {"raw_papers": str(output_path)}})
            skill.search_arxiv = lambda query, max_results, keyword_phrases=None: [ET.fromstring(SAMPLE_ENTRY)]

            result = skill.run(
                {
                    "query": "graph neural networks misinformation detection",
                    "date_range": "all",
                    "max_results": 5,
                }
            )

            self.assertEqual(len(result["papers"]), 1)
            self.assertEqual(
                result["query_keywords"],
                ["graph neural networks misinformation detection"],
            )
            self.assertEqual(result["keyword_extraction_source"], "heuristic")
            self.assertIn("ti:", result["resolved_search_query"])
            self.assertTrue(output_path.exists())
            saved = load_json(output_path)
            self.assertEqual(saved, result)

    def test_run_can_return_empty_result_on_retrieval_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "raw" / "arxiv_papers.json"
            skill = PaperRetrievalSkill(
                {
                    "paths": {"raw_papers": str(output_path)},
                    "retrieval": {"allow_empty_on_error": True},
                }
            )
            skill.search_arxiv = lambda query, max_results, keyword_phrases=None: (_ for _ in ()).throw(RuntimeError("HTTP Error 429"))

            result = skill.run({"query": "harness engineering", "date_range": "all", "max_results": 5})

            self.assertEqual(result["papers"], [])
            self.assertIn("HTTP Error 429", result["retrieval_error"])
            self.assertEqual(result["query_keywords"], ["harness engineering"])
            self.assertEqual(result["keyword_extraction_source"], "heuristic")
            self.assertTrue(output_path.exists())

    def test_run_uses_llm_keyword_phrases_when_available(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "raw" / "arxiv_papers.json"
            skill = PaperRetrievalSkill({"paths": {"raw_papers": str(output_path)}})
            skill._extract_keyword_phrases_with_llm = lambda query: ["graph neural networks", "misinformation detection"]

            captured = {}

            def fake_search(query, max_results, keyword_phrases=None):
                captured["query"] = query
                captured["keyword_phrases"] = keyword_phrases
                return [ET.fromstring(SAMPLE_ENTRY)]

            skill.search_arxiv = fake_search

            result = skill.run(
                {
                    "query": "graph neural networks for misinformation detection",
                    "date_range": "all",
                    "max_results": 5,
                }
            )

            self.assertEqual(
                captured["keyword_phrases"],
                ["graph neural networks", "misinformation detection"],
            )
            self.assertEqual(
                result["query_keywords"],
                ["graph neural networks", "misinformation detection"],
            )
            self.assertEqual(result["keyword_extraction_source"], "openai")

    def test_parse_llm_keyword_response_accepts_json_object(self):
        skill = PaperRetrievalSkill()

        keywords = skill._parse_llm_keyword_response(
            '{"keywords": ["graph neural networks", "misinformation detection", "graph neural networks"]}'
        )

        self.assertEqual(keywords, ["graph neural networks", "misinformation detection"])

    def test_search_arxiv_retries_after_transient_network_error(self):
        skill = PaperRetrievalSkill(
            {
                "retrieval": {
                    "request_timeout_seconds": 5,
                    "max_retries": 2,
                    "retry_backoff_seconds": 0,
                }
            }
        )
        payload = f'<feed xmlns="{ATOM_NAMESPACE["atom"]}">{SAMPLE_ENTRY}</feed>'.encode("utf-8")
        attempts = []

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return payload

        def fake_urlopen(request, timeout):
            attempts.append(timeout)
            if len(attempts) == 1:
                raise URLError("temporary network failure")
            return FakeResponse()

        with patch("skills.paper_retrieval.skill.urlopen", side_effect=fake_urlopen):
            entries = skill.search_arxiv("graph neural networks", 3)

        self.assertEqual(len(entries), 1)
        self.assertEqual(attempts, [5.0, 5.0])

    def test_search_arxiv_does_not_retry_non_retriable_http_error(self):
        skill = PaperRetrievalSkill({"retrieval": {"max_retries": 3, "retry_backoff_seconds": 0}})
        attempts = []

        def fake_urlopen(request, timeout):
            attempts.append(timeout)
            raise HTTPError(request.full_url, 400, "Bad Request", hdrs=None, fp=None)

        with patch("skills.paper_retrieval.skill.urlopen", side_effect=fake_urlopen):
            with self.assertRaises(RuntimeError) as context:
                skill.search_arxiv("graph neural networks", 3)

        self.assertIn("after 1 attempt(s)", str(context.exception))
        self.assertEqual(len(attempts), 1)

    def test_invalid_retrieval_timeout_config_raises_value_error(self):
        skill = PaperRetrievalSkill({"retrieval": {"request_timeout_seconds": 0}})

        with self.assertRaises(ValueError):
            skill._get_timeout_seconds()


if __name__ == "__main__":
    unittest.main()
