from __future__ import annotations

import argparse
import math
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent.io_utils import load_config, load_json, save_json
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
GENERIC_CONTEXT_TERMS = {
    "analysis",
    "approach",
    "approaches",
    "engineering",
    "method",
    "methods",
    "model",
    "models",
    "research",
    "study",
    "studies",
    "system",
    "systems",
}
HARNESS_ENGINEERING_CONTEXT_TERMS = {
    "agent",
    "agentic",
    "agents",
    "architecture",
    "architectural",
    "coordination",
    "runtime",
    "runtimes",
    "tool",
    "toolkit",
    "tools",
    "workflow",
    "workflows",
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
        filtered_papers = self.apply_core_query_filter(query, filtered_papers)
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
        scores = [
            score + self._topic_alignment_bonus(query, paper)
            for score, paper in zip(scores, papers)
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

    def apply_core_query_filter(self, query: str, papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
        query_tokens = self._topic_tokens(query)
        if len(query_tokens) < 2:
            return list(papers)
        if not (set(query_tokens) & GENERIC_CONTEXT_TERMS):
            return list(papers)

        strict_terms = set(query_tokens)
        strict_matches = self._papers_matching_terms(papers, strict_terms)
        if strict_matches:
            return strict_matches

        core_terms = {token for token in query_tokens if token not in GENERIC_CONTEXT_TERMS}
        if not core_terms:
            return list(papers)

        matched = self._papers_matching_terms(papers, core_terms)
        return matched or list(papers)

    def _papers_matching_terms(self, papers: list[dict[str, Any]], terms: set[str]) -> list[dict[str, Any]]:
        matched = []
        for paper in papers:
            paper_terms = set(self._topic_tokens(self.build_document_text(paper, "title_abstract_categories")))
            if terms <= paper_terms:
                matched.append(paper)
        return matched

    def select_top_k(self, ranked_papers: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
        if top_k <= 0:
            return []
        return ranked_papers[:top_k]

    def save_results(self, result: dict[str, Any], output_path: str | None = None) -> None:
        save_json(result, output_path or self.paths.get("ranked_papers", "data/processed/ranked_papers.json"))

    def _tokenize(self, text: str) -> list[str]:
        return self._topic_tokens(text)

    def _topic_tokens(self, text: str) -> list[str]:
        normalized_text = text.replace("-", " ").replace("_", " ")
        tokens = []
        for token in TOKEN_PATTERN.findall(normalized_text):
            lowered = token.lower()
            if lowered in STOPWORDS:
                continue
            tokens.append(self._normalize_topic_token(lowered))
        return tokens

    def _normalize_topic_token(self, token: str) -> str:
        if token in {"engineer", "engineered", "engineering"}:
            return "engineering"
        if token in {"harness", "harnessed", "harnesses"}:
            return "harness"
        return token

    def _topic_alignment_bonus(self, query: str, paper: dict[str, Any]) -> float:
        query_tokens = self._topic_tokens(query)
        if len(query_tokens) < 2 or not (set(query_tokens) & GENERIC_CONTEXT_TERMS):
            return 0.0

        query_terms = set(query_tokens)
        title_tokens = self._topic_tokens(str(paper.get("title", "")))
        abstract_tokens = self._topic_tokens(str(paper.get("abstract", "")))
        document_terms = set(title_tokens + abstract_tokens)
        if not query_terms <= document_terms:
            return 0.0

        bonus = 0.04
        if self._contains_phrase(title_tokens, query_tokens):
            bonus += 0.20
        elif self._contains_phrase(abstract_tokens, query_tokens):
            bonus += 0.14
        elif self._terms_are_near(title_tokens + abstract_tokens, query_terms, window=8):
            bonus += 0.03
        if query_terms == {"harness", "engineering"}:
            context_hits = set(title_tokens + abstract_tokens) & HARNESS_ENGINEERING_CONTEXT_TERMS
            bonus += min(0.06, 0.015 * len(context_hits))
        return bonus

    def _contains_phrase(self, tokens: list[str], phrase: list[str]) -> bool:
        if not tokens or not phrase or len(phrase) > len(tokens):
            return False
        phrase_length = len(phrase)
        return any(tokens[index : index + phrase_length] == phrase for index in range(len(tokens) - phrase_length + 1))

    def _terms_are_near(self, tokens: list[str], terms: set[str], window: int) -> bool:
        positions = [index for index, token in enumerate(tokens) if token in terms]
        for start in positions:
            seen = {token for token in tokens[start : start + window] if token in terms}
            if terms <= seen:
                return True
        return False

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
    skill = RelevanceRankingSkill(load_config())
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
