from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from socket import timeout as SocketTimeout
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent.io_utils import save_json
from agent.schema import SkillNotImplementedError
from skills.common import add_common_output_arg, not_implemented_result, print_skill_result

ARXIV_API_URL = "https://export.arxiv.org/api/query"
ATOM_NAMESPACE = {"atom": "http://www.w3.org/2005/Atom"}
ARXIV_FIELD_PREFIXES = ("ti", "au", "abs", "co", "jr", "cat", "rn", "id", "all")
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "by",
    "for",
    "from",
    "in",
    "into",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}


class PaperRetrievalSkill:
    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.paths = self.config.get("paths", {})
        self.retrieval_config = self.config.get("retrieval", {})

    def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        query = str(input_data.get("query", "")).strip()
        if not query:
            raise ValueError("PaperRetrievalSkill requires a non-empty query.")

        max_results = max(1, int(input_data.get("max_results", 50)))
        date_range = str(input_data.get("date_range", "last 7 days")).strip()
        keyword_phrases, keyword_source = self._extract_keyword_phrases(query)
        resolved_search_query = self._build_search_query(query, keyword_phrases=keyword_phrases)

        try:
            raw_papers = self.search_arxiv(query, max_results, keyword_phrases=keyword_phrases)
        except RuntimeError as exc:
            if not self._allow_empty_on_error():
                raise
            result = {
                "papers": [],
                "retrieval_error": str(exc),
                "query": query,
                "date_range": date_range,
                "query_keywords": keyword_phrases,
                "keyword_extraction_source": keyword_source,
                "resolved_search_query": resolved_search_query,
            }
            self.save_results(result)
            return result

        parsed_papers = [self.parse_metadata(raw_paper) for raw_paper in raw_papers]
        filtered_papers = self.filter_by_date(parsed_papers, date_range)
        result = {
            "papers": filtered_papers,
            "query_keywords": keyword_phrases,
            "keyword_extraction_source": keyword_source,
            "resolved_search_query": resolved_search_query,
        }
        self.save_results(result)
        return result

    def search_arxiv(
        self,
        query: str,
        max_results: int,
        *,
        keyword_phrases: list[str] | None = None,
    ) -> list[Any]:
        search_query = self._build_search_query(query, keyword_phrases=keyword_phrases)
        request_url = f"{ARXIV_API_URL}?{urlencode(self._build_request_params(search_query, max_results))}"
        request = Request(
            request_url,
            headers={
                "User-Agent": "daily-arxiv-briefing-agent/1.0 (research briefing workflow)",
            },
        )

        payload = self._fetch_with_retries(request)

        try:
            root = ET.fromstring(payload)
        except ET.ParseError as exc:
            raise RuntimeError(f"Received an invalid XML response from arXiv: {exc}") from exc

        return root.findall("atom:entry", ATOM_NAMESPACE)

    def filter_by_date(self, papers: list[dict[str, Any]], date_range: str) -> list[dict[str, Any]]:
        start_date, end_date = self._resolve_date_range(date_range)
        if start_date is None and end_date is None:
            return papers

        filtered: list[dict[str, Any]] = []
        for paper in papers:
            published_date = self._parse_iso_date(paper.get("published_date", ""))
            if published_date is None:
                continue
            if start_date is not None and published_date < start_date:
                continue
            if end_date is not None and published_date > end_date:
                continue
            filtered.append(paper)
        return filtered

    def parse_metadata(self, raw_paper: Any) -> dict[str, Any]:
        if not isinstance(raw_paper, ET.Element):
            raise TypeError("raw_paper must be an XML element from the arXiv Atom feed.")

        title = self._normalize_whitespace(raw_paper.findtext("atom:title", default="", namespaces=ATOM_NAMESPACE))
        abstract = self._normalize_whitespace(
            raw_paper.findtext("atom:summary", default="", namespaces=ATOM_NAMESPACE)
        )
        authors = [
            self._normalize_whitespace(author.text or "")
            for author in raw_paper.findall("atom:author/atom:name", ATOM_NAMESPACE)
            if self._normalize_whitespace(author.text or "")
        ]

        published_text = raw_paper.findtext("atom:published", default="", namespaces=ATOM_NAMESPACE)
        published_date = ""
        parsed_date = self._parse_iso_datetime(published_text)
        if parsed_date is not None:
            published_date = parsed_date.date().isoformat()

        canonical_url = raw_paper.findtext("atom:id", default="", namespaces=ATOM_NAMESPACE).strip()
        alternate_url = self._extract_alternate_url(raw_paper)
        url = alternate_url or canonical_url

        categories = self._extract_categories(raw_paper)

        return {
            "title": title,
            "authors": authors,
            "abstract": abstract,
            "published_date": published_date,
            "arxiv_id": self._extract_arxiv_id(canonical_url),
            "url": url,
            "categories": categories,
        }

    def save_results(self, result: dict[str, Any], output_path: str | None = None) -> None:
        save_json(result, output_path or self.paths.get("raw_papers", "data/raw/arxiv_papers.json"))

    def _build_request_params(self, search_query: str, max_results: int) -> dict[str, Any]:
        return {
            "search_query": search_query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

    def _fetch_with_retries(self, request: Request) -> bytes:
        timeout_seconds = self._get_timeout_seconds()
        max_retries = self._get_max_retries()
        backoff_seconds = self._get_retry_backoff_seconds()
        total_attempts = max_retries + 1
        last_error: Exception | None = None
        attempts_made = 0

        for attempt_index in range(total_attempts):
            attempts_made += 1
            try:
                with urlopen(request, timeout=timeout_seconds) as response:
                    return response.read()
            except (HTTPError, URLError, TimeoutError, SocketTimeout) as exc:
                last_error = exc
                is_last_attempt = attempt_index == total_attempts - 1
                if is_last_attempt or not self._is_retriable_request_error(exc):
                    break
                delay = backoff_seconds * (2**attempt_index)
                if delay > 0:
                    time.sleep(delay)

        raise RuntimeError(
            f"Failed to retrieve papers from arXiv after {attempts_made} attempt(s): {last_error}"
        ) from last_error

    def _is_retriable_request_error(self, exc: Exception) -> bool:
        if isinstance(exc, HTTPError):
            return exc.code in {408, 429, 500, 502, 503, 504}
        return True

    def _get_timeout_seconds(self) -> float:
        value = self.retrieval_config.get("request_timeout_seconds", 30)
        timeout_seconds = float(value)
        if timeout_seconds <= 0:
            raise ValueError("retrieval.request_timeout_seconds must be positive.")
        return timeout_seconds

    def _get_max_retries(self) -> int:
        value = int(self.retrieval_config.get("max_retries", 2))
        if value < 0:
            raise ValueError("retrieval.max_retries must be non-negative.")
        return value

    def _get_retry_backoff_seconds(self) -> float:
        value = self.retrieval_config.get("retry_backoff_seconds", 1)
        backoff_seconds = float(value)
        if backoff_seconds < 0:
            raise ValueError("retrieval.retry_backoff_seconds must be non-negative.")
        return backoff_seconds

    def _allow_empty_on_error(self) -> bool:
        return bool(self.retrieval_config.get("allow_empty_on_error", False))

    def _build_search_query(self, query: str, keyword_phrases: list[str] | None = None) -> str:
        if self._looks_like_arxiv_query(query):
            return query.strip()

        concept_groups = self._concept_groups_from_phrases(keyword_phrases) if keyword_phrases else self._extract_concept_groups(query)
        if not concept_groups:
            raise ValueError("Query must contain at least one searchable token.")
        return " AND ".join(self._build_group_clause(group) for group in concept_groups)

    def _resolve_date_range(self, date_range: str) -> tuple[date | None, date | None]:
        value = date_range.strip().lower()
        today = datetime.now(timezone.utc).date()

        if not value or value in {"all", "any", "*"}:
            return None, None
        if value == "today":
            return today, today
        if value == "yesterday":
            yesterday = today - timedelta(days=1)
            return yesterday, yesterday

        last_match = re.fullmatch(r"last\s+(\d+)\s+(day|days|week|weeks|month|months)", value)
        if last_match:
            amount = int(last_match.group(1))
            unit = last_match.group(2)
            if amount < 1:
                raise ValueError("date_range must use a positive amount.")

            multiplier = 1
            if unit.startswith("week"):
                multiplier = 7
            elif unit.startswith("month"):
                multiplier = 30

            span_days = amount * multiplier
            start_date = today - timedelta(days=span_days - 1)
            return start_date, today

        exact_date = self._parse_iso_date(value)
        if exact_date is not None:
            return exact_date, exact_date

        raise ValueError(
            "Unsupported date_range. Use 'today', 'yesterday', 'all', "
            "an ISO date like '2026-05-01', or ranges such as 'last 7 days'."
        )

    def _parse_iso_datetime(self, value: str) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    def _parse_iso_date(self, value: str) -> date | None:
        if not value:
            return None
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").date()
        except ValueError:
            return None

    def _normalize_whitespace(self, value: str) -> str:
        return " ".join(value.split())

    def _extract_keyword_phrases(self, query: str) -> tuple[list[str], str]:
        if self._looks_like_arxiv_query(query):
            return [], "direct_query"

        if self._llm_keyword_extraction_enabled():
            try:
                keyword_phrases = self._extract_keyword_phrases_with_llm(query)
                if keyword_phrases:
                    return keyword_phrases, "openai"
            except RuntimeError:
                pass

        return self._extract_keyword_phrases_heuristically(query), "heuristic"

    def _extract_keyword_phrases_heuristically(self, query: str) -> list[str]:
        return [" ".join(group) for group in self._extract_concept_groups(query)]

    def _extract_keyword_phrases_with_llm(self, query: str) -> list[str]:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set for LLM keyword extraction.")

        request = Request(
            f"{self._get_openai_base_url().rstrip('/')}/responses",
            data=json.dumps(
                {
                    "model": self._get_llm_model(),
                    "instructions": (
                        "You extract concise technical search phrases for academic paper retrieval. "
                        "Return only JSON with a top-level 'keywords' array. "
                        "Each item must be a short phrase of 1 to 4 words. "
                        "Prefer technical concepts that should appear in an arXiv title or abstract. "
                        "Return between 2 and 6 phrases when possible."
                    ),
                    "input": (
                        f"Research query: {query}\n"
                        "Return JSON only in this format: "
                        '{"keywords": ["phrase 1", "phrase 2"]}'
                    ),
                }
            ).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "daily-arxiv-briefing-agent/1.0 (llm-keyword-extraction)",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=self._get_llm_timeout_seconds()) as response:
                payload = response.read()
        except (HTTPError, URLError, TimeoutError, SocketTimeout) as exc:
            raise RuntimeError(f"Failed to extract keywords with OpenAI: {exc}") from exc

        try:
            response_data = json.loads(payload.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"OpenAI response was not valid JSON: {exc}") from exc

        output_text = self._extract_output_text_from_openai_response(response_data)
        keyword_phrases = self._parse_llm_keyword_response(output_text)
        if not keyword_phrases:
            raise RuntimeError("OpenAI keyword extraction returned no usable keywords.")
        return keyword_phrases[: self._get_llm_max_keywords()]

    def _extract_output_text_from_openai_response(self, response_data: dict[str, Any]) -> str:
        output_text = str(response_data.get("output_text", "")).strip()
        if output_text:
            return output_text

        fragments: list[str] = []
        for item in response_data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"} and content.get("text"):
                    fragments.append(str(content["text"]))
        return "\n".join(fragment.strip() for fragment in fragments if fragment.strip())

    def _parse_llm_keyword_response(self, output_text: str) -> list[str]:
        text = output_text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"OpenAI keyword extraction did not return valid JSON: {exc}") from exc

        if isinstance(payload, dict):
            values = payload.get("keywords") or payload.get("phrases") or payload.get("concepts") or []
        elif isinstance(payload, list):
            values = payload
        else:
            values = []

        normalized: list[str] = []
        seen: set[str] = set()
        for value in values:
            phrase = " ".join(str(value).split()).strip("\"' ")
            if not phrase:
                continue
            lowered = phrase.lower()
            if lowered in seen:
                continue
            normalized.append(phrase)
            seen.add(lowered)
        return normalized

    def _llm_keyword_extraction_enabled(self) -> bool:
        return bool(self.retrieval_config.get("llm_keyword_extraction_enabled", True))

    def _get_llm_model(self) -> str:
        return str(self.retrieval_config.get("llm_model", "gpt-5.2")).strip() or "gpt-5.2"

    def _get_llm_timeout_seconds(self) -> float:
        value = self.retrieval_config.get("llm_timeout_seconds", 20)
        timeout_seconds = float(value)
        if timeout_seconds <= 0:
            raise ValueError("retrieval.llm_timeout_seconds must be positive.")
        return timeout_seconds

    def _get_llm_max_keywords(self) -> int:
        value = int(self.retrieval_config.get("llm_max_keywords", 6))
        if value < 1:
            raise ValueError("retrieval.llm_max_keywords must be positive.")
        return value

    def _get_openai_base_url(self) -> str:
        return str(
            self.retrieval_config.get("openai_base_url")
            or os.getenv("OPENAI_BASE_URL")
            or "https://api.openai.com/v1"
        ).strip()

    def _extract_alternate_url(self, raw_paper: ET.Element) -> str:
        for link in raw_paper.findall("atom:link", ATOM_NAMESPACE):
            if link.attrib.get("rel") == "alternate" and link.attrib.get("href"):
                return link.attrib["href"].strip()
        return ""

    def _extract_categories(self, raw_paper: ET.Element) -> list[str]:
        categories: list[str] = []
        for category in raw_paper.findall("atom:category", ATOM_NAMESPACE):
            term = category.attrib.get("term", "").strip()
            if term and term not in categories:
                categories.append(term)
        return categories

    def _extract_arxiv_id(self, canonical_url: str) -> str:
        if "/abs/" in canonical_url:
            return canonical_url.rsplit("/abs/", maxsplit=1)[-1]
        return canonical_url.rstrip("/").rsplit("/", maxsplit=1)[-1]

    def _looks_like_arxiv_query(self, query: str) -> bool:
        normalized = query.strip()
        if not normalized:
            return False
        if "%22" in normalized or "%28" in normalized or "%29" in normalized:
            return True
        field_pattern = rf"\b(?:{'|'.join(ARXIV_FIELD_PREFIXES)}):"
        return re.search(field_pattern, normalized, flags=re.IGNORECASE) is not None

    def _extract_concept_groups(self, query: str) -> list[list[str]]:
        groups: list[list[str]] = []
        current_group: list[str] = []

        for raw_part in re.findall(r'"[^"]+"|\S+', query, flags=re.UNICODE):
            if raw_part.startswith('"') and raw_part.endswith('"'):
                if current_group:
                    groups.append(current_group)
                    current_group = []
                phrase_terms = self._normalize_group_terms(raw_part[1:-1].split())
                if phrase_terms:
                    groups.append(phrase_terms)
                continue

            token = self._normalize_token(raw_part)
            if not token:
                continue
            if token.lower() in STOPWORDS:
                if current_group:
                    groups.append(current_group)
                    current_group = []
                continue
            current_group.append(token)

        if current_group:
            groups.append(current_group)

        normalized_groups = []
        for group in groups:
            normalized = self._normalize_group_terms(group)
            if normalized:
                normalized_groups.append(normalized)
        return normalized_groups

    def _concept_groups_from_phrases(self, keyword_phrases: list[str]) -> list[list[str]]:
        groups: list[list[str]] = []
        for phrase in keyword_phrases:
            normalized = self._normalize_group_terms(phrase.split())
            if normalized:
                groups.append(normalized)
        return groups

    def _build_group_clause(self, group: list[str]) -> str:
        if len(group) == 1:
            return self._build_term_clause(group[0])

        if len(group) <= 3:
            alternatives = []
            phrase = self._build_phrase_clause(group)
            if phrase:
                alternatives.append(phrase)
            alternatives.append(self._combine_with_and(self._build_term_clause(term) for term in group))
            return self._combine_with_or(alternatives)

        chunk_clauses = []
        for chunk in self._chunk_terms_for_phrases(group):
            alternatives = []
            phrase = self._build_phrase_clause(chunk)
            if phrase:
                alternatives.append(phrase)
            alternatives.append(self._combine_with_and(self._build_term_clause(term) for term in chunk))
            chunk_clauses.append(self._combine_with_or(alternatives))
        return " AND ".join(chunk_clauses)

    def _chunk_terms_for_phrases(self, terms: list[str]) -> list[list[str]]:
        chunks: list[list[str]] = []
        index = 0
        total = len(terms)
        while index < total:
            remaining = total - index
            if remaining == 4:
                chunk_size = 2
            elif remaining > 4:
                chunk_size = 3
            else:
                chunk_size = remaining
            chunks.append(terms[index : index + chunk_size])
            index += chunk_size
        return chunks

    def _build_phrase_clause(self, terms: list[str]) -> str:
        if len(terms) < 2:
            return ""
        phrase = " ".join(terms)
        return f'(ti:"{phrase}" OR abs:"{phrase}")'

    def _build_term_clause(self, term: str) -> str:
        return f"(ti:{term} OR abs:{term})"

    def _combine_with_or(self, clauses: list[str]) -> str:
        unique_clauses: list[str] = []
        seen: set[str] = set()
        for clause in clauses:
            if clause and clause not in seen:
                unique_clauses.append(clause)
                seen.add(clause)
        return f"({' OR '.join(unique_clauses)})"

    def _combine_with_and(self, clauses: Any) -> str:
        unique_clauses: list[str] = []
        seen: set[str] = set()
        for clause in clauses:
            if clause and clause not in seen:
                unique_clauses.append(clause)
                seen.add(clause)
        return f"({' AND '.join(unique_clauses)})"

    def _normalize_group_terms(self, terms: list[str]) -> list[str]:
        normalized_terms: list[str] = []
        seen: set[str] = set()
        for raw_term in terms:
            token = self._normalize_token(raw_term)
            if not token:
                continue
            lowered = token.lower()
            if lowered in STOPWORDS or lowered in seen:
                continue
            normalized_terms.append(token)
            seen.add(lowered)
        return normalized_terms

    def _normalize_token(self, value: str) -> str:
        return value.strip("\"'.,;:()[]{}")


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
