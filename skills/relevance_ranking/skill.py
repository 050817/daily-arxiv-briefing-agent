from __future__ import annotations

import argparse
import math
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent.io_utils import load_json, save_json
from agent.schema import SkillNotImplementedError
from skills.common import add_common_output_arg, not_implemented_result, print_skill_result


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*")
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}


class RelevanceRankingSkill:
    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.paths = self.config.get("paths", {})

    def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        query = str(input_data.get("query", "")).strip()
        if not query:
            raise ValueError("RelevanceRankingSkill requires a non-empty query.")

        papers = list(input_data.get("papers", []))
        top_k = max(0, int(input_data.get("top_k", 5)))
        method = str(input_data.get("method", "tfidf")).strip().lower()
        allowed_categories = input_data.get("allowed_categories")

        filtered_papers = self.apply_category_filter(papers, allowed_categories)
        if method == "tfidf":
            ranked_papers = self.rank_with_tfidf(query, filtered_papers)
        elif method == "sbert":
            ranked_papers = self.rank_with_sbert(query, filtered_papers)
        else:
            raise ValueError(f"Unsupported ranking method: {method!r}. Expected 'tfidf' or 'sbert'.")

        top_k_papers = self.select_top_k(ranked_papers, top_k)
        result = {
            "ranked_papers": ranked_papers,
            "top_k_papers": top_k_papers,
        }
        self.save_results(result, input_data.get("output_path"))
        return result

    def build_document_text(self, paper: dict[str, Any], mode: str = "title_abstract") -> str:
        title = str(paper.get("title", "")).strip()
        abstract = str(paper.get("abstract", "")).strip()
        categories = " ".join(str(category) for category in paper.get("categories", []) if category)

        if mode == "title":
            parts = [title]
        elif mode == "abstract":
            parts = [abstract]
        elif mode == "title_abstract":
            parts = [title, abstract]
        elif mode == "title_abstract_categories":
            parts = [title, abstract, categories]
        else:
            raise ValueError(
                "Unsupported document mode. Expected 'title', 'abstract', "
                "'title_abstract', or 'title_abstract_categories'."
            )
        return " ".join(part for part in parts if part)

    def rank_with_tfidf(self, query: str, papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not papers:
            return []

        documents = [self.build_document_text(paper) for paper in papers]
        document_tokens = [self._tokenize(document) for document in documents]
        query_tokens = self._tokenize(query)

        if not query_tokens:
            return self._attach_ranking_metadata(query, papers, [0.0] * len(papers))

        idf = self._compute_idf(document_tokens + [query_tokens])
        query_vector = self._tfidf_vector(query_tokens, idf)
        scores = [
            self._cosine_similarity(query_vector, self._tfidf_vector(tokens, idf))
            for tokens in document_tokens
        ]
        return self._attach_ranking_metadata(query, papers, scores)

    def rank_with_sbert(self, query: str, papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
        # Keep the public method available while the lightweight project avoids
        # the heavy sentence-transformers dependency.
        return self.rank_with_tfidf(query, papers)

    def apply_category_filter(
        self, papers: list[dict[str, Any]], allowed_categories: list[str] | str | None
    ) -> list[dict[str, Any]]:
        if not allowed_categories:
            return list(papers)

        if isinstance(allowed_categories, str):
            allowed_categories = [allowed_categories]

        allowed = {str(category).strip() for category in allowed_categories if str(category).strip()}
        if not allowed:
            return list(papers)

        filtered = []
        for paper in papers:
            categories = {str(category).strip() for category in paper.get("categories", [])}
            if categories & allowed:
                filtered.append(paper)
        return filtered

    def select_top_k(self, ranked_papers: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
        if top_k <= 0:
            return []
        return ranked_papers[:top_k]

    def save_results(self, result: dict[str, Any], output_path: str | None = None) -> None:
        save_json(result, output_path or self.paths.get("ranked_papers", "data/processed/ranked_papers.json"))

    def _tokenize(self, text: str) -> list[str]:
        return [
            token.lower()
            for token in TOKEN_PATTERN.findall(text)
            if token.lower() not in STOPWORDS
        ]

    def _compute_idf(self, documents: list[list[str]]) -> dict[str, float]:
        document_count = len(documents)
        document_frequency: Counter[str] = Counter()
        for tokens in documents:
            document_frequency.update(set(tokens))
        return {
            token: math.log((document_count + 1) / (frequency + 1)) + 1
            for token, frequency in document_frequency.items()
        }

    def _tfidf_vector(self, tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
        if not tokens:
            return {}

        counts = Counter(tokens)
        total = sum(counts.values())
        return {
            token: (count / total) * idf.get(token, 1.0)
            for token, count in counts.items()
        }

    def _cosine_similarity(self, left: dict[str, float], right: dict[str, float]) -> float:
        if not left or not right:
            return 0.0

        shared_tokens = set(left) & set(right)
        numerator = sum(left[token] * right[token] for token in shared_tokens)
        left_norm = math.sqrt(sum(value * value for value in left.values()))
        right_norm = math.sqrt(sum(value * value for value in right.values()))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return numerator / (left_norm * right_norm)

    def _attach_ranking_metadata(
        self,
        query: str,
        papers: list[dict[str, Any]],
        scores: list[float],
    ) -> list[dict[str, Any]]:
        indexed_papers = list(enumerate(zip(papers, scores)))
        indexed_papers.sort(key=lambda item: (-item[1][1], item[0]))

        ranked_papers: list[dict[str, Any]] = []
        for rank, (_, (paper, score)) in enumerate(indexed_papers, start=1):
            ranked_paper = dict(paper)
            ranked_paper["relevance_score"] = round(float(score), 4)
            ranked_paper["rank"] = rank
            ranked_paper["ranking_reason"] = self._build_ranking_reason(query, paper, float(score))
            ranked_papers.append(ranked_paper)
        return ranked_papers

    def _build_ranking_reason(self, query: str, paper: dict[str, Any], score: float) -> str:
        query_terms = set(self._tokenize(query))
        title_terms = set(self._tokenize(str(paper.get("title", ""))))
        abstract_terms = set(self._tokenize(str(paper.get("abstract", ""))))

        title_matches = sorted(query_terms & title_terms)
        abstract_matches = sorted((query_terms & abstract_terms) - set(title_matches))
        matches = title_matches + abstract_matches

        if matches:
            shown = ", ".join(matches[:5])
            location = "title" if title_matches else "abstract"
            return f"Matches query terms in the {location}: {shown}."
        if score > 0:
            return "Shares related TF-IDF vocabulary with the query."
        return "No direct query-term overlap; ranked after more relevant papers."


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Relevance Ranking Skill independently.")
    parser.add_argument("--input", required=True, help="Path to Skill 1 raw paper JSON.")
    parser.add_argument("--query", type=str, required=True)
    parser.add_argument("--method", type=str, default="tfidf")
    parser.add_argument("--top_k", type=int, default=5)
    parser.add_argument(
        "--allowed-categories",
        nargs="*",
        default=None,
        help="Optional arXiv category filter, e.g. cs.SI cs.LG.",
    )
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
                "allowed_categories": args.allowed_categories,
            }
        )
    except SkillNotImplementedError as exc:
        result = not_implemented_result("relevance_ranking", exc)
    print_skill_result(result, args.output_json)


if __name__ == "__main__":
    main()
