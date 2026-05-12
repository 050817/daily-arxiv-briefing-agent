from __future__ import annotations

import argparse
import html
import itertools
import json
import math
import re
import shutil
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent.io_utils import ensure_dir, ensure_parent, load_json, save_json
from agent.openai_compat import load_openai_compatible_settings, resolve_openai_compatible_config
from agent.schema import SkillNotImplementedError
from skills.common import add_common_output_arg, not_implemented_result, print_skill_result


TOKEN_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9-]*")
SENTENCE_PATTERN = re.compile(r"(?<=[.!?])\s+")
STOPWORDS = {
    "a",
    "about",
    "across",
    "after",
    "all",
    "also",
    "an",
    "and",
    "are",
    "as",
    "at",
    "based",
    "be",
    "been",
    "between",
    "both",
    "by",
    "can",
    "for",
    "from",
    "has",
    "have",
    "in",
    "into",
    "is",
    "it",
    "its",
    "may",
    "more",
    "of",
    "on",
    "or",
    "our",
    "paper",
    "papers",
    "propose",
    "proposes",
    "show",
    "shows",
    "study",
    "studies",
    "that",
    "the",
    "their",
    "this",
    "through",
    "to",
    "using",
    "via",
    "we",
    "with",
}

CONTROLLED_PHRASES = [
    "graph neural networks",
    "social networks",
    "misinformation detection",
    "community detection",
    "link prediction",
    "influence maximization",
    "recommendation systems",
    "graph learning",
    "network analysis",
    "dynamic networks",
    "node classification",
    "knowledge graphs",
    "graph mining",
    "temporal networks",
    "heterogeneous networks",
    "social recommendation",
    "centrality",
]

METHOD_TERMS = {
    "architecture",
    "framework",
    "graph neural networks",
    "gnn",
    "transformer",
    "tf-idf",
    "embedding",
    "toolkit",
    "community detection",
    "link prediction",
    "classification",
    "clustering",
    "centrality",
    "pagerank",
    "label propagation",
    "network analysis",
}

EVIDENCE_TERMS = {
    "accuracy",
    "case studies",
    "experiment",
    "experiments",
    "evaluate",
    "evaluates",
    "evaluation",
    "dataset",
    "datasets",
    "report",
    "reports",
    "results",
    "sample",
    "case study",
    "simulation",
}

LIMITATION_TERMS = {
    "limitation",
    "limitations",
    "future work",
    "however",
    "although",
    "limited",
    "challenges",
}


class BriefingGraphSkill:
    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.paths = self.config.get("paths", {})
        self.briefing_config = self.config.get("briefing", {})

    def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        query = str(input_data.get("query", "")).strip()
        papers = list(input_data.get("top_k_papers", []))
        output_path = input_data.get("output") or input_data.get("output_path") or self.paths.get(
            "report", "outputs/reports/daily_briefing.md"
        )
        output_pdf_path = (
            input_data.get("output_pdf")
            or input_data.get("output_pdf_path")
            or self.paths.get("report_pdf", "outputs/reports/daily_briefing.pdf")
        )
        figures_dir = input_data.get("figures_dir") or self.paths.get("figures_dir", "outputs/figures")
        retrieval_error = str(input_data.get("retrieval_error") or "").strip()
        retrieved_paper_count = input_data.get("retrieved_paper_count")

        summaries = [self.generate_structured_summary(paper, query) for paper in papers]
        paper_keywords = self.extract_keywords(papers)
        self._add_query_focus_keywords(paper_keywords, papers, query)
        graph = self.build_keyword_graph(paper_keywords)
        graph["query"] = query
        graph_analysis = self.analyze_graph(graph)

        figures = self._write_visualizations(graph, graph_analysis, figures_dir) if papers else []
        report_path = self.generate_markdown_report(
            query,
            papers,
            summaries,
            graph_analysis,
            figures,
            output_path,
            retrieval_error=retrieval_error,
            retrieved_paper_count=retrieved_paper_count,
        )
        pdf_path = self.generate_pdf_report(
            query,
            papers,
            summaries,
            graph_analysis,
            figures,
            output_pdf_path,
            retrieval_error=retrieval_error,
            retrieved_paper_count=retrieved_paper_count,
        )

        return {
            "report_markdown": report_path,
            "report_pdf": pdf_path,
            "summaries": summaries,
            "graph_analysis": graph_analysis,
            "figures": figures,
            "retrieval_error": retrieval_error,
        }

    def generate_structured_summary(self, paper: dict[str, Any], query: str = "") -> dict[str, Any]:
        if self._ai_summary_enabled():
            try:
                return self._generate_ai_structured_summary(paper, query)
            except Exception:
                pass
        return self._generate_rule_structured_summary(paper, query)

    def _generate_rule_structured_summary(self, paper: dict[str, Any], query: str = "") -> dict[str, Any]:
        title = self._clean_text(str(paper.get("title", "")))
        abstract = self._clean_text(str(paper.get("abstract", "")))
        sentences = self._split_sentences(abstract)

        return {
            "title": title or "Untitled paper",
            "one_sentence_summary": self._build_one_sentence_summary(title, abstract),
            "topic_relevance": self._build_topic_relevance(query, sentences, str(paper.get("ranking_reason", ""))),
            "problem": self._find_best_problem_sentence(sentences)
            or self._infer_problem_from_title(title),
            "method": self._find_best_sentence(sentences, METHOD_TERMS) or "Not mentioned in abstract",
            "contribution": self._find_best_contribution_sentence(sentences) or "Not mentioned in abstract",
            "experiment_or_evidence": self._find_best_sentence(sentences, EVIDENCE_TERMS)
            or "Not mentioned in abstract",
            "limitation": self._find_best_limitation_sentence(sentences) or "Not mentioned in abstract",
            "evidence_source": "title and abstract only",
        }

    def chat_with_archive(self, archive_path: str | Path, message: str) -> dict[str, Any]:
        archive = Path(archive_path)
        if not archive.exists() or not archive.is_dir():
            raise FileNotFoundError("archive not found")
        clean_message = str(message or "").strip()
        if not clean_message:
            raise ValueError("message is required")

        context = self.load_archive_context(archive)
        answer = self.answer_archive_question(clean_message, context)
        chat_path = archive / "chat.json"
        chat = load_json(chat_path) if chat_path.exists() else {"messages": []}
        chat["messages"].extend(
            [
                {"role": "user", "content": clean_message},
                {"role": "assistant", "content": answer},
            ]
        )
        save_json(chat, chat_path)
        return {"answer": answer, "messages": chat["messages"]}

    def load_archive_context(self, archive_path: str | Path) -> str:
        archive = Path(archive_path)
        chunks = []
        for name in ["metadata.json", "report.md", "ranked_papers.json", "raw_papers.json"]:
            path = archive / name
            if path.exists():
                text = path.read_text(encoding="utf-8", errors="replace")
                chunks.append(f"[{name}]\n{text[:12000]}")
        return "\n\n".join(chunks)

    def answer_archive_question(self, message: str, context: str) -> str:
        if self._openai_api_key():
            try:
                return self._call_openai_chat(
                    [
                        {
                            "role": "system",
                            "content": (
                                "You answer questions about an archived arXiv briefing. "
                                "Use only the provided report/archive context. If the answer is not in the files, say so."
                            ),
                        },
                        {"role": "user", "content": f"Archive context:\n{context[:30000]}\n\nQuestion: {message}"},
                    ],
                    timeout_seconds=float(self.briefing_config.get("chat_timeout_seconds", 60)),
                )
            except Exception as exc:
                return (
                    "模型接口调用失败，下面给出基于归档文件的本地回答。\n\n"
                    f"接口错误: {exc}\n\n{self._fallback_archive_answer(message, context)}"
                )
        return self._fallback_archive_answer(message, context)

    def _generate_ai_structured_summary(self, paper: dict[str, Any], query: str = "") -> dict[str, Any]:
        title = self._clean_text(str(paper.get("title", ""))) or "Untitled paper"
        abstract = self._clean_text(str(paper.get("abstract", "")))
        if not abstract:
            raise RuntimeError("AI summary requires an abstract.")

        prompt = (
            "Create an evidence-grounded structured summary for one arXiv paper. "
            "Use only the title, abstract, ranking reason, and query below. "
            "Do not infer methods, experiments, limitations, or claims that are not stated. "
            "If a field is not supported by the abstract, write exactly 'Not mentioned in abstract'. "
            "Return JSON only with these string keys: title, one_sentence_summary, topic_relevance, "
            "problem, method, contribution, experiment_or_evidence, limitation, evidence_source.\n\n"
            f"Query: {query or 'Not provided'}\n"
            f"Title: {title}\n"
            f"Ranking reason: {paper.get('ranking_reason', '')}\n"
            f"Abstract: {abstract[:6000]}"
        )
        content = self._call_openai_chat(
            [
                {
                    "role": "system",
                    "content": (
                        "You are a careful research briefing assistant. "
                        "You must return valid JSON and stay grounded in the provided abstract."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            timeout_seconds=float(self.briefing_config.get("ai_summary_timeout_seconds", 60)),
        )
        payload = self._parse_json_object(content)
        summary = self._normalize_ai_summary(payload, title)
        summary["evidence_source"] = "AI summary grounded in title and abstract only"
        return summary

    def _call_openai_chat(self, messages: list[dict[str, str]], *, timeout_seconds: float = 60) -> str:
        config = self._openai_config()
        api_key = config.get("api_key", "")
        if not api_key:
            raise RuntimeError("No OpenAI-compatible API key is configured.")
        base_url = config["api_url"].rstrip("/")
        request_body = {
            "model": config["model"],
            "messages": messages,
        }
        request = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=json.dumps(request_body).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read(500).decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
        data = json.loads(body)
        return str(data["choices"][0]["message"]["content"])

    def _parse_json_object(self, content: str) -> dict[str, Any]:
        text = content.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```$", "", text)
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if not match:
                raise
            payload = json.loads(match.group(0))
        if not isinstance(payload, dict):
            raise ValueError("AI summary response must be a JSON object.")
        return payload

    def _normalize_ai_summary(self, payload: dict[str, Any], fallback_title: str) -> dict[str, str]:
        keys = [
            "title",
            "one_sentence_summary",
            "topic_relevance",
            "problem",
            "method",
            "contribution",
            "experiment_or_evidence",
            "limitation",
            "evidence_source",
        ]
        summary = {key: self._clean_text(str(payload.get(key, ""))) for key in keys}
        summary["title"] = summary["title"] or fallback_title or "Untitled paper"
        for key in keys:
            if key == "title":
                continue
            if not summary[key]:
                summary[key] = "Not mentioned in abstract"
        return summary

    def _fallback_archive_answer(self, message: str, context: str) -> str:
        terms = [term.lower() for term in message.split() if len(term) > 2]
        lines = [line.strip() for line in context.splitlines() if line.strip()]
        matches = [
            line for line in lines if any(term in line.lower() for term in terms)
        ][:8]
        if not matches:
            matches = lines[:8]
        evidence = "\n".join(f"- {line[:420]}" for line in matches)
        return (
            "当前使用本地归档文件检索式回答。\n\n"
            f"相关文件片段:\n{evidence}\n\n"
            "如果需要真正的模型对话，请在网页的模型 API 设置中保存可用的 API URL、Model 和 API Key。"
        )

    def _ai_summary_enabled(self) -> bool:
        return bool(self.briefing_config.get("ai_summary_enabled", False)) and bool(self._openai_api_key())

    def _openai_api_key(self) -> str:
        return self._openai_config().get("api_key", "")

    def _openai_config(self) -> dict[str, str]:
        settings = load_openai_compatible_settings()
        return resolve_openai_compatible_config(
            configured_base_url=str(settings.get("api_url", "")).strip(),
            configured_model=str(settings.get("model", "")).strip(),
            configured_api_key=str(settings.get("api_key", "")).strip(),
            default_model=str(self.briefing_config.get("llm_model", "gpt-5.4")),
        )

    def extract_keywords(self, papers: list[dict[str, Any]]) -> dict[str, list[str]]:
        document_frequencies = self._document_frequencies(papers)
        paper_keywords: dict[str, list[str]] = {}

        for index, paper in enumerate(papers, start=1):
            paper_id = self._paper_id(paper, index)
            text = self._paper_text(paper)
            phrase_counts = Counter(self._extract_candidate_phrases(text))
            scored: list[tuple[str, float]] = []

            for phrase, count in phrase_counts.items():
                if len(phrase) < 3:
                    continue
                df = document_frequencies.get(phrase, 1)
                idf = math.log((len(papers) + 1) / (df + 1)) + 1
                controlled_bonus = 1.5 if phrase in CONTROLLED_PHRASES else 1.0
                length_bonus = 1.0 + min(len(phrase.split()) - 1, 2) * 0.2
                scored.append((phrase, count * idf * controlled_bonus * length_bonus))

            scored.sort(key=lambda item: (-item[1], item[0]))
            paper_keywords[paper_id] = self._select_readable_keywords(scored, limit=8)

        return paper_keywords

    def build_keyword_graph(self, paper_keywords: dict[str, list[str]]) -> dict[str, Any]:
        nodes: Counter[str] = Counter()
        edges: Counter[tuple[str, str]] = Counter()

        for keywords in paper_keywords.values():
            unique_keywords = sorted(dict.fromkeys(keywords))
            nodes.update(unique_keywords)
            for left, right in itertools.combinations(unique_keywords, 2):
                edges[(left, right)] += 1

        return {
            "nodes": dict(nodes),
            "edges": {f"{left}|||{right}": weight for (left, right), weight in edges.items()},
            "paper_keywords": paper_keywords,
        }

    def analyze_graph(self, graph: dict[str, Any]) -> dict[str, Any]:
        nodes = graph.get("nodes", {})
        edge_items = self._edge_items(graph)
        node_names = sorted(nodes)
        adjacency: dict[str, dict[str, int]] = {node: {} for node in node_names}
        for left, right, weight in edge_items:
            adjacency[left][right] = adjacency[left].get(right, 0) + weight
            adjacency[right][left] = adjacency[right].get(left, 0) + weight

        num_nodes = len(node_names)
        num_edges = len(edge_items)
        possible_edges = num_nodes * (num_nodes - 1) / 2
        density = round(num_edges / possible_edges, 4) if possible_edges else 0.0
        weighted_degree = {
            node: sum(adjacency[node].values())
            for node in node_names
        }
        average_degree = round(sum(len(neighbors) for neighbors in adjacency.values()) / num_nodes, 4) if num_nodes else 0.0
        query_focus = self._query_focus_terms(str(graph.get("query", "")))
        central_keywords = [
            {
                "keyword": node,
                "paper_count": int(nodes[node]),
                "weighted_degree": weighted_degree[node],
                "degree": len(adjacency[node]),
            }
            for node in sorted(
                node_names,
                key=lambda item: (
                    -self._query_focus_score(item, query_focus),
                    -weighted_degree[item],
                    -nodes[item],
                    item,
                ),
            )[:10]
        ]

        communities = self._connected_components(adjacency)
        return {
            "num_nodes": num_nodes,
            "num_edges": num_edges,
            "density": density,
            "average_degree": average_degree,
            "central_keywords": central_keywords,
            "communities": communities,
            "paper_keywords": graph.get("paper_keywords", {}),
        }

    def visualize_graph(self, graph: Any, output_path: str) -> None:
        graph_dict = graph if isinstance(graph, dict) else {"nodes": {}, "edges": {}}
        analysis = self.analyze_graph(graph_dict)
        self._write_keyword_graph_svg(graph_dict, analysis, output_path)

    def archive_outputs(
        self,
        query: str,
        artifacts: dict[str, Any],
        *,
        archive_dir: str | None = None,
        messages: list[dict[str, str]] | None = None,
        metadata_extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        root = ensure_dir(archive_dir or self.paths.get("archive_dir", "archives"))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_id = f"{self._slugify(query or 'untitled')}_{timestamp}"
        destination = root / archive_id
        destination.mkdir(parents=True, exist_ok=True)

        copied: dict[str, str] = {}
        for key, value in artifacts.items():
            if not value:
                continue
            source = Path(str(value))
            if not source.is_absolute():
                source = Path.cwd() / source
            if not source.exists() or source.is_dir():
                continue
            target_name = self._archive_filename(key, source)
            target = destination / target_name
            shutil.copy2(source, target)
            copied[key] = target.name

        chat_messages = messages or []
        (destination / "chat.json").write_text(
            json.dumps({"messages": chat_messages}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        metadata = {
            "id": archive_id,
            "query": query,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "files": copied,
        }
        if metadata_extra:
            metadata.update(metadata_extra)
        (destination / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return {"id": archive_id, "path": str(destination), "files": copied, "metadata": metadata}

    def generate_markdown_report(
        self,
        query: str,
        papers: list[dict[str, Any]],
        summaries: list[dict[str, Any]],
        graph_analysis: dict[str, Any],
        figures: list[str] | None = None,
        output_path: str | None = None,
        retrieval_error: str = "",
        retrieved_paper_count: int | None = None,
    ) -> str:
        output_path = output_path or self.paths.get("report", "outputs/reports/daily_briefing.md")
        resolved = ensure_parent(output_path)
        report = self._build_report_markdown(
            query,
            papers,
            summaries,
            graph_analysis,
            figures or [],
            retrieval_error=retrieval_error,
            retrieved_paper_count=retrieved_paper_count,
        )
        resolved.write_text(report, encoding="utf-8")
        return str(resolved)

    def generate_pdf_report(
        self,
        query: str,
        papers: list[dict[str, Any]],
        summaries: list[dict[str, Any]],
        graph_analysis: dict[str, Any],
        figures: list[str] | None = None,
        output_path: str | None = None,
        retrieval_error: str = "",
        retrieved_paper_count: int | None = None,
    ) -> str:
        output_path = output_path or self.paths.get("report_pdf", "outputs/reports/daily_briefing.pdf")
        resolved = ensure_parent(output_path)
        sections = self._build_pdf_sections(
            query,
            papers,
            summaries,
            graph_analysis,
            figures or [],
            retrieval_error=retrieval_error,
            retrieved_paper_count=retrieved_paper_count,
        )
        self._write_pdf_report(query, sections, str(resolved))
        return str(resolved)

    def _build_pdf_sections(
        self,
        query: str,
        papers: list[dict[str, Any]],
        summaries: list[dict[str, Any]],
        graph_analysis: dict[str, Any],
        figures: list[str],
        retrieval_error: str = "",
        retrieved_paper_count: int | None = None,
    ) -> list[dict[str, Any]]:
        central_keywords = graph_analysis.get("central_keywords", [])
        communities = graph_analysis.get("communities", [])
        relevance_warning = self._build_relevance_warning(query, papers)
        top_keywords = ", ".join(item["keyword"] for item in central_keywords[:5]) or "Not available"
        search_status = "Completed"
        if retrieval_error:
            search_status = f"Retrieval failed: {self._format_retrieval_error(retrieval_error)}"
        elif retrieved_paper_count == 0 and not papers:
            search_status = "Completed, but no papers were available for briefing"

        return [
            {
                "title": "1. Executive Summary",
                "body": [
                    self._executive_summary_text(query, papers, central_keywords, relevance_warning),
                    'Evidence policy: summaries use only paper titles and abstracts; unsupported fields say "Not mentioned in abstract".',
                ],
            },
            {
                "title": "2. Search Overview",
                "body": [
                    f"Query: {query or 'Not provided'}",
                    f"Retrieved papers supplied to briefing: {retrieved_paper_count if retrieved_paper_count is not None else len(papers)}",
                    f"Papers included in report: {len(papers)}",
                    f"Search status: {search_status}",
                ],
            },
            {
                "title": "3. Top Papers to Read",
                "table": {
                    "headers": ["Rank", "Title", "Score", "Categories"],
                    "rows": [
                        [
                            str(paper.get("rank", index)),
                            str(paper.get("title", "Untitled paper")),
                            str(paper.get("relevance_score", "")),
                            ", ".join(str(category) for category in paper.get("categories", [])) or "Not provided",
                        ]
                        for index, paper in enumerate(papers, start=1)
                    ],
                },
                "empty": "No papers were available for ranking.",
            },
            {
                "title": "4. Paper Cards",
                "cards": [
                    {
                        "heading": f"{index}. {summary['title']}",
                        "items": [
                            ("Topic relevance", summary["topic_relevance"]),
                            ("Problem", summary["problem"]),
                            ("Method", summary["method"]),
                            ("Contribution", summary["contribution"]),
                            ("Evidence", summary["experiment_or_evidence"]),
                            ("Limitation", summary["limitation"]),
                        ],
                    }
                    for index, summary in enumerate(summaries, start=1)
                ],
                "empty": "No paper cards were generated.",
            },
            {
                "title": "5. Research Trend Map",
                "body": [
                    (
                        "The most connected extracted topics are "
                        f"{top_keywords}. This describes recurring vocabulary in the selected abstracts, "
                        "not the broader arXiv corpus."
                    )
                    if papers
                    else "Trend analysis was not run because no papers were available."
                ],
            },
            {
                "title": "6. Keyword / Topic Network",
                "body": [
                    f"Nodes: {graph_analysis.get('num_nodes', 0)}",
                    f"Edges: {graph_analysis.get('num_edges', 0)}",
                    f"Density: {graph_analysis.get('density', 0.0)}",
                    f"Average degree: {graph_analysis.get('average_degree', 0.0)}",
                    "Central keywords: " + top_keywords,
                    "Figure files: " + (", ".join(self._display_path(figure) for figure in figures) if figures else "None"),
                    self._format_community_summary(communities),
                ],
            },
            {
                "title": "7. Novelty & Relevance Analysis",
                "body": self._novelty_relevance_points(query, papers, summaries, relevance_warning),
            },
            {
                "title": "8. Suggested Reading Order",
                "body": [
                    f"{index}. {paper.get('title', 'Untitled paper')} - {paper.get('ranking_reason', 'Ranked by relevance score.')}"
                    for index, paper in enumerate(papers, start=1)
                ]
                or ["No reading order is available."],
            },
            {
                "title": "9. Possible Research Ideas",
                "body": self._research_idea_points(query, central_keywords, summaries),
            },
            {
                "title": "10. Limitations of This Search",
                "body": self._search_limitations(retrieval_error, papers, relevance_warning),
            },
        ]

    def _write_pdf_report(self, query: str, sections: list[dict[str, Any]], output_path: str) -> None:
        try:
            from reportlab.lib import colors
            from reportlab.lib.enums import TA_CENTER
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.lib.units import inch
            from reportlab.platypus import (
                KeepTogether,
                PageBreak,
                Paragraph,
                SimpleDocTemplate,
                Spacer,
                Table,
                TableStyle,
            )
        except ImportError as exc:
            raise RuntimeError(
                "PDF generation requires reportlab. Install dependencies with: "
                "python -m pip install -r requirements.txt"
            ) from exc

        styles = getSampleStyleSheet()
        styles.add(
            ParagraphStyle(
                name="ReportTitle",
                parent=styles["Title"],
                alignment=TA_CENTER,
                fontName="Helvetica-Bold",
                fontSize=20,
                leading=24,
                spaceAfter=12,
            )
        )
        styles.add(
            ParagraphStyle(
                name="SectionTitle",
                parent=styles["Heading2"],
                fontName="Helvetica-Bold",
                fontSize=13,
                leading=16,
                textColor=colors.HexColor("#0f172a"),
                spaceBefore=10,
                spaceAfter=8,
            )
        )
        styles.add(
            ParagraphStyle(
                name="SmallBody",
                parent=styles["BodyText"],
                fontName="Helvetica",
                fontSize=8.7,
                leading=11.2,
                spaceAfter=5,
            )
        )
        styles.add(
            ParagraphStyle(
                name="CardHeading",
                parent=styles["Heading3"],
                fontName="Helvetica-Bold",
                fontSize=10,
                leading=12,
                spaceBefore=6,
                spaceAfter=4,
            )
        )

        story: list[Any] = []
        story.append(Paragraph("Daily arXiv Research Briefing", styles["ReportTitle"]))
        story.append(Paragraph(f"Query: {self._pdf_escape(query or 'Not provided')}", styles["BodyText"]))
        story.append(Paragraph(f"Date: {datetime.now().strftime('%Y-%m-%d')}", styles["BodyText"]))
        story.append(Spacer(1, 0.14 * inch))

        for section in sections:
            story.append(Paragraph(self._pdf_escape(section["title"]), styles["SectionTitle"]))
            if section.get("body"):
                for item in section["body"]:
                    story.append(Paragraph(self._pdf_escape(str(item)), styles["SmallBody"]))
            if section.get("table"):
                rows = section["table"]["rows"]
                if rows:
                    headers = section["table"]["headers"]
                    table_data = [
                        [Paragraph(self._pdf_escape(str(cell)), styles["SmallBody"]) for cell in headers]
                    ]
                    for row in rows:
                        table_data.append(
                            [Paragraph(self._pdf_escape(str(cell)), styles["SmallBody"]) for cell in row]
                        )
                    table = Table(table_data, colWidths=[0.45 * inch, 3.45 * inch, 0.75 * inch, 1.25 * inch])
                    table.setStyle(
                        TableStyle(
                            [
                                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
                                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                                ("TOPPADDING", (0, 0), (-1, -1), 4),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                            ]
                        )
                    )
                    story.append(table)
                    story.append(Spacer(1, 0.08 * inch))
                else:
                    story.append(Paragraph(self._pdf_escape(section.get("empty", "No data available.")), styles["SmallBody"]))
            if section.get("cards"):
                for card in section["cards"]:
                    card_story = [Paragraph(self._pdf_escape(card["heading"]), styles["CardHeading"])]
                    for label, value in card["items"]:
                        card_story.append(
                            Paragraph(
                                f"<b>{self._pdf_escape(label)}:</b> {self._pdf_escape(str(value))}",
                                styles["SmallBody"],
                            )
                        )
                    story.append(KeepTogether(card_story))
                    story.append(Spacer(1, 0.05 * inch))
            elif "cards" in section:
                story.append(Paragraph(self._pdf_escape(section.get("empty", "No cards available.")), styles["SmallBody"]))
            if section["title"].startswith("4. "):
                story.append(PageBreak())
            else:
                story.append(Spacer(1, 0.07 * inch))

        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=0.62 * inch,
            leftMargin=0.62 * inch,
            topMargin=0.62 * inch,
            bottomMargin=0.58 * inch,
            title="Daily arXiv Research Briefing",
            author="Daily arXiv Briefing Agent",
        )
        doc.build(story, onFirstPage=self._pdf_page_footer, onLaterPages=self._pdf_page_footer)

    def _pdf_page_footer(self, canvas: Any, doc: Any) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColorRGB(0.35, 0.4, 0.48)
        canvas.drawString(doc.leftMargin, 0.35 * 72, "Daily arXiv Research Briefing")
        canvas.drawRightString(8.5 * 72 - doc.rightMargin, 0.35 * 72, f"Page {doc.page}")
        canvas.restoreState()

    def _pdf_escape(self, value: str) -> str:
        return html.escape(self._clean_text(value), quote=False)

    def _executive_summary_text(
        self,
        query: str,
        papers: list[dict[str, Any]],
        central_keywords: list[dict[str, Any]],
        relevance_warning: str,
    ) -> str:
        if not papers:
            return f"No papers were available for query: {query or 'Not provided'}."
        top_title = papers[0].get("title", "the top-ranked paper")
        keywords = ", ".join(item["keyword"] for item in central_keywords[:3]) or "no stable keywords"
        warning = f" Relevance caution: {relevance_warning}" if relevance_warning else ""
        return (
            f"This briefing reviews {len(papers)} arXiv papers retrieved for '{query}'. "
            f"The top-ranked paper is '{top_title}'. The selected abstracts most often connect around: {keywords}."
            f"{warning}"
        )

    def _format_community_summary(self, communities: list[dict[str, Any]]) -> str:
        if not communities:
            return "Keyword communities: none detected"
        parts = []
        for community in communities[:3]:
            keywords = ", ".join(community.get("keywords", [])[:8])
            parts.append(f"Community {community.get('id')}: {keywords}")
        return "Keyword communities: " + "; ".join(parts)

    def _novelty_relevance_points(
        self,
        query: str,
        papers: list[dict[str, Any]],
        summaries: list[dict[str, Any]],
        relevance_warning: str,
    ) -> list[str]:
        if not papers:
            return ["No novelty or relevance analysis is available because no papers were selected."]
        points = []
        if relevance_warning:
            points.append(relevance_warning)
        else:
            points.append(f"All selected papers were ranked against the query '{query}' using title and abstract text.")
        for summary in summaries[:3]:
            points.append(f"{summary['title']}: {summary['topic_relevance']}")
        return points

    def _research_idea_points(
        self,
        query: str,
        central_keywords: list[dict[str, Any]],
        summaries: list[dict[str, Any]],
    ) -> list[str]:
        if not summaries:
            return ["No research ideas were generated because no papers were selected."]
        keywords = [item["keyword"] for item in central_keywords[:4]]
        keyword_text = ", ".join(keywords) if keywords else query or "the search topic"
        return [
            f"Compare how different papers operationalize {query or 'the query'} across datasets, models, or evaluation settings.",
            f"Use the recurring topic cluster ({keyword_text}) as a starting point for a focused literature review.",
            "Design a follow-up search that adds a domain qualifier to reduce broad keyword matches.",
        ]

    def _search_limitations(
        self,
        retrieval_error: str,
        papers: list[dict[str, Any]],
        relevance_warning: str,
    ) -> list[str]:
        if retrieval_error and not papers:
            return [
                f"Primary limitation: {self._format_retrieval_error(retrieval_error)}",
                "No substantive research conclusions should be drawn from an empty retrieval result.",
                "Retry later or run the briefing from cached paper JSON.",
            ]
        limitations = [
            "The report only uses titles, abstracts, metadata, and ranking fields.",
            "It does not read full PDFs, citations, appendices, code repositories, or external web pages.",
            "Keyword communities are based on co-occurrence in the selected Top-K papers and are descriptive rather than causal.",
        ]
        if relevance_warning:
            limitations.append(relevance_warning)
        return limitations

    def _build_report_markdown(
        self,
        query: str,
        papers: list[dict[str, Any]],
        summaries: list[dict[str, Any]],
        graph_analysis: dict[str, Any],
        figures: list[str],
        retrieval_error: str = "",
        retrieved_paper_count: int | None = None,
    ) -> str:
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        central_keywords = graph_analysis.get("central_keywords", [])
        communities = graph_analysis.get("communities", [])

        lines = [
            "# Daily arXiv Research Briefing",
            "",
            f"- Query: {query or 'Not provided'}",
            f"- Generated at: {generated_at}",
            f"- Papers included: {len(papers)}",
            "- Evidence policy: summaries use only paper titles and abstracts; unsupported fields say \"Not mentioned in abstract\".",
            "",
        ]

        if retrieval_error:
            lines.extend(
                [
                    "## Retrieval Status",
                    "",
                    f"Data retrieval failed before analysis: {self._format_retrieval_error(retrieval_error)}",
                    "",
                    "This report contains no paper evidence from arXiv for this run. Do not interpret the empty result as evidence that no research exists on the topic.",
                    "",
                    "Recommended next action: retry later, lower request frequency, or run Skill 2/3 from cached paper JSON.",
                    "",
                ]
            )
        elif retrieved_paper_count == 0 and not papers:
            lines.extend(
                [
                    "## Retrieval Status",
                    "",
                    "No papers were available for briefing. This may mean the query returned no results, date filtering removed all results, or retrieval input was empty.",
                    "",
                ]
            )

        relevance_warning = self._build_relevance_warning(query, papers)
        if relevance_warning:
            lines.extend(["## Relevance Caution", "", relevance_warning, ""])

        lines.extend(["## Top Papers", ""])

        if papers:
            lines.extend(
                [
                    "| Rank | Title | Score | Categories | Link |",
                    "|---:|---|---:|---|---|",
                ]
            )
            for index, paper in enumerate(papers, start=1):
                rank = paper.get("rank", index)
                title = self._escape_markdown(str(paper.get("title", "Untitled paper")))
                score = paper.get("relevance_score", "")
                categories = ", ".join(str(category) for category in paper.get("categories", [])) or "Not provided"
                url = str(paper.get("url", "")).strip()
                link = f"[arXiv]({url})" if url else "Not provided"
                lines.append(f"| {rank} | {title} | {score} | {categories} | {link} |")
        else:
            lines.append("No papers were provided to the briefing Skill.")

        lines.extend(["", "## Structured Summaries", ""])
        if not summaries:
            lines.extend(["No summaries were generated because no papers were available.", ""])
        for index, summary in enumerate(summaries, start=1):
            lines.extend(
                [
                    f"### {index}. {self._escape_markdown(summary['title'])}",
                    "",
                    f"- One-sentence summary: {summary['one_sentence_summary']}",
                    f"- Topic relevance: {summary['topic_relevance']}",
                    f"- Problem: {summary['problem']}",
                    f"- Method: {summary['method']}",
                    f"- Contribution: {summary['contribution']}",
                    f"- Experiment or evidence: {summary['experiment_or_evidence']}",
                    f"- Limitation: {summary['limitation']}",
                    "",
                ]
            )

        lines.extend(["## Keyword Network Analysis", ""])
        if not papers:
            lines.extend(["Analysis not run because no papers were retrieved or supplied.", ""])
        else:
            lines.extend(
                [
                    f"- Nodes: {graph_analysis.get('num_nodes', 0)}",
                    f"- Edges: {graph_analysis.get('num_edges', 0)}",
                    f"- Density: {graph_analysis.get('density', 0.0)}",
                    f"- Average degree: {graph_analysis.get('average_degree', 0.0)}",
                    "",
                ]
            )

        lines.extend(["### Central Keywords", ""])
        if not papers:
            lines.append("No central keywords were extracted because no papers were available.")
        elif central_keywords:
            lines.extend(["| Keyword | Paper Count | Weighted Degree |", "|---|---:|---:|"])
            for item in central_keywords[:10]:
                lines.append(
                    f"| {self._escape_markdown(item['keyword'])} | {item['paper_count']} | {item['weighted_degree']} |"
                )
        else:
            lines.append("No central keywords were extracted.")

        lines.extend(["", "### Keyword Communities", ""])
        if not papers:
            lines.append("No keyword communities were detected because no papers were available.")
        elif communities:
            for community in communities:
                keywords = ", ".join(community["keywords"])
                lines.append(f"- Community {community['id']} ({community['size']} keywords): {keywords}")
        else:
            lines.append("No keyword communities were detected.")

        lines.extend(["", "## Trend Interpretation", ""])
        relevance_warning = self._build_relevance_warning(query, papers)
        if not papers:
            lines.append("Trend interpretation not run because there is no paper evidence for this run.")
        elif relevance_warning:
            lines.append(
                "Keyword analysis is available, but the selected papers are only weakly cohesive for the query. "
                "Treat the graph as a description of retrieved abstracts, not as a focused map of the full query topic."
            )
        elif central_keywords:
            top_terms = ", ".join(item["keyword"] for item in central_keywords[:5])
            lines.append(
                "The most connected extracted topics are "
                f"{top_terms}. This indicates recurring vocabulary in the selected abstracts, "
                "not a claim about the broader arXiv corpus."
            )
        else:
            lines.append("Not enough keyword evidence was available to infer topic patterns.")

        lines.extend(["", "## Recommended Reading Order", ""])
        if papers:
            for index, paper in enumerate(papers, start=1):
                reason = paper.get("ranking_reason", "Ranked by the previous relevance Skill.")
                lines.append(f"{index}. {paper.get('title', 'Untitled paper')} - {reason}")
        else:
            lines.append("No reading order is available.")

        lines.extend(["", "## Figures", ""])
        if figures:
            for figure in figures:
                lines.append(f"- {self._display_path(figure)}")
        else:
            lines.append("No figures were generated because no paper keyword graph was available.")

        lines.extend(["", "## Limitations", ""])
        if retrieval_error and not papers:
            lines.extend(
                [
                    "- Primary limitation for this run: no source papers were available because upstream arXiv retrieval failed.",
                    "- No ranking, summarization, keyword graph analysis, trend interpretation, or figures should be treated as substantive research output for this run.",
                    "- Retry later or provide cached paper JSON to run downstream Skills without calling arXiv again.",
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    "- This report only uses title, abstract, metadata, and ranking fields supplied to Skill 3.",
                    "- It does not read full PDFs, citations, experiments, or external web pages.",
                    "- Keyword communities are based on co-occurrence in the selected Top-K papers, so they are descriptive rather than causal.",
                    "",
                ]
            )
        return "\n".join(lines)

    def _write_visualizations(
        self,
        graph: dict[str, Any],
        graph_analysis: dict[str, Any],
        figures_dir: str,
    ) -> list[str]:
        resolved_dir = ensure_dir(figures_dir)
        graph_path = resolved_dir / "keyword_graph.svg"
        bar_path = resolved_dir / "top_keywords.svg"
        self._write_keyword_graph_svg(graph, graph_analysis, str(graph_path))
        self._write_top_keywords_svg(graph_analysis.get("central_keywords", []), str(bar_path))
        return [str(graph_path), str(bar_path)]

    def _write_keyword_graph_svg(self, graph: dict[str, Any], analysis: dict[str, Any], output_path: str) -> None:
        resolved = ensure_parent(output_path)
        keywords = [item["keyword"] for item in analysis.get("central_keywords", [])[:12]]
        width, height = 900, 620
        cx, cy, radius = width / 2, height / 2 + 20, 220
        positions: dict[str, tuple[float, float]] = {}
        for index, keyword in enumerate(keywords):
            angle = (2 * math.pi * index / max(len(keywords), 1)) - math.pi / 2
            positions[keyword] = (cx + radius * math.cos(angle), cy + radius * math.sin(angle))

        edge_lines = []
        for left, right, weight in self._edge_items(graph):
            if left not in positions or right not in positions:
                continue
            x1, y1 = positions[left]
            x2, y2 = positions[right]
            stroke_width = min(6, 1 + weight)
            edge_lines.append(
                f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                f'stroke="#9aa7b3" stroke-width="{stroke_width}" opacity="0.55" />'
            )

        node_lines = []
        for keyword in keywords:
            x, y = positions[keyword]
            label = html.escape(keyword)
            node_lines.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="34" fill="#2563eb" opacity="0.92" />')
            node_lines.append(
                f'<text x="{x:.1f}" y="{y + 52:.1f}" text-anchor="middle" '
                'font-family="Arial, sans-serif" font-size="13" fill="#172033">'
                f"{label}</text>"
            )

        if not keywords:
            node_lines.append(
                '<text x="450" y="320" text-anchor="middle" font-family="Arial, sans-serif" '
                'font-size="18" fill="#475569">No keywords available</text>'
            )

        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="#f8fafc"/>
  <text x="36" y="46" font-family="Arial, sans-serif" font-size="24" font-weight="700" fill="#0f172a">Keyword Co-occurrence Network</text>
  <text x="36" y="76" font-family="Arial, sans-serif" font-size="14" fill="#475569">Top connected keywords from selected papers; thicker lines mean repeated co-occurrence.</text>
  {''.join(edge_lines)}
  {''.join(node_lines)}
</svg>
"""
        resolved.write_text(svg, encoding="utf-8")

    def _write_top_keywords_svg(self, central_keywords: list[dict[str, Any]], output_path: str) -> None:
        resolved = ensure_parent(output_path)
        items = central_keywords[:10]
        width = 900
        row_height = 42
        height = 130 + max(len(items), 1) * row_height
        max_value = max((item["weighted_degree"] for item in items), default=1)
        rows = []
        for index, item in enumerate(items):
            y = 96 + index * row_height
            bar_width = 560 * (item["weighted_degree"] / max_value) if max_value else 0
            label = html.escape(item["keyword"])
            rows.append(
                f'<text x="36" y="{y + 20}" font-family="Arial, sans-serif" font-size="14" fill="#172033">{label}</text>'
                f'<rect x="280" y="{y}" width="{bar_width:.1f}" height="24" rx="4" fill="#0f766e"/>'
                f'<text x="{292 + bar_width:.1f}" y="{y + 18}" font-family="Arial, sans-serif" font-size="13" fill="#172033">{item["weighted_degree"]}</text>'
            )
        if not rows:
            rows.append(
                '<text x="36" y="120" font-family="Arial, sans-serif" font-size="16" fill="#475569">No keywords available</text>'
            )

        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="#f8fafc"/>
  <text x="36" y="46" font-family="Arial, sans-serif" font-size="24" font-weight="700" fill="#0f172a">Top Central Keywords</text>
  <text x="36" y="74" font-family="Arial, sans-serif" font-size="14" fill="#475569">Weighted degree in the selected-paper keyword graph.</text>
  {''.join(rows)}
</svg>
"""
        resolved.write_text(svg, encoding="utf-8")

    def _document_frequencies(self, papers: list[dict[str, Any]]) -> Counter[str]:
        frequencies: Counter[str] = Counter()
        for paper in papers:
            frequencies.update(set(self._extract_candidate_phrases(self._paper_text(paper))))
        return frequencies

    def _extract_candidate_phrases(self, text: str) -> list[str]:
        lowered = text.lower()
        phrases: list[str] = []
        for phrase in CONTROLLED_PHRASES:
            if phrase in lowered:
                phrases.append(phrase)

        tokens = self._tokens_from_text(lowered)
        phrases.extend(tokens)
        for sentence in self._split_sentences(lowered):
            sentence_tokens = self._tokens_from_text(sentence)
            ngram_size = 2
            for index in range(0, max(len(sentence_tokens) - ngram_size + 1, 0)):
                ngram = sentence_tokens[index : index + ngram_size]
                if any(token in STOPWORDS for token in ngram) or len(set(ngram)) < len(ngram):
                    continue
                phrases.append(" ".join(ngram))
        return phrases

    def _tokens_from_text(self, text: str) -> list[str]:
        normalized_text = text.replace("-", " ").replace("_", " ")
        tokens = []
        for token in TOKEN_PATTERN.findall(normalized_text):
            lowered = token.lower()
            if lowered in STOPWORDS or len(lowered) <= 2:
                continue
            tokens.append(self._normalize_topic_token(lowered))
        return tokens

    def _normalize_topic_token(self, token: str) -> str:
        if token in {"engineer", "engineered", "engineering", "engineers"}:
            return "engineering"
        if token in {"harness", "harnessed", "harnesses"}:
            return "harness"
        return token

    def _build_topic_relevance(self, query: str, sentences: list[str], ranking_reason: str) -> str:
        query_terms = set(self._tokens_from_text(query))
        if not query_terms:
            return ranking_reason or "No query was provided."

        for sentence in sentences:
            if self._is_metadata_sentence(sentence):
                continue
            sentence_terms = set(self._tokens_from_text(sentence))
            if query_terms <= sentence_terms:
                return sentence

        matched_reason = ranking_reason.strip()
        if matched_reason:
            return matched_reason
        return "The title or abstract does not contain all main query terms."

    def _select_readable_keywords(self, scored: list[tuple[str, float]], limit: int) -> list[str]:
        selected: list[str] = []
        controlled = [(phrase, score) for phrase, score in scored if phrase in CONTROLLED_PHRASES]
        other = [(phrase, score) for phrase, score in scored if phrase not in CONTROLLED_PHRASES]
        for phrase, _ in controlled + other:
            if self._is_redundant_keyword(phrase, selected):
                continue
            selected.append(phrase)
            if len(selected) >= limit:
                break
        return selected

    def _is_redundant_keyword(self, phrase: str, selected: list[str]) -> bool:
        phrase_terms = set(phrase.split())
        for existing in selected:
            existing_terms = set(existing.split())
            if phrase == existing:
                return True
            if phrase in existing and len(phrase.split()) < len(existing.split()):
                return True
            if phrase not in CONTROLLED_PHRASES and existing in CONTROLLED_PHRASES and phrase_terms & existing_terms:
                return True
            if len(phrase_terms) == 1 and phrase_terms <= existing_terms:
                return True
            overlap = len(phrase_terms & existing_terms)
            if overlap >= 2:
                return True
        return False

    def _paper_text(self, paper: dict[str, Any]) -> str:
        return self._clean_text(f"{paper.get('title', '')}. {paper.get('abstract', '')}")

    def _build_one_sentence_summary(self, title: str, abstract: str) -> str:
        first_sentence = self._split_sentences(abstract)[0] if self._split_sentences(abstract) else ""
        if first_sentence:
            return first_sentence
        if title:
            return f"The title indicates a paper about {title}."
        return "Not mentioned in abstract"

    def _safe_claim_from_title(self, title: str) -> str:
        if not title:
            return "Not mentioned in abstract"
        return f"The title indicates the topic: {title}."

    def _infer_problem_from_title(self, title: str) -> str:
        if not title:
            return "Not mentioned in abstract"
        match = re.search(r"\bfor\s+(.+)$", title, flags=re.IGNORECASE)
        if match:
            return f"The title frames the target problem as {match.group(1).strip()}."
        return self._safe_claim_from_title(title)

    def _find_best_sentence(self, sentences: list[str], cues: set[str] | list[str]) -> str:
        cue_list = [cue.lower() for cue in cues]
        for sentence in sentences:
            if self._is_metadata_sentence(sentence):
                continue
            lowered = sentence.lower()
            if any(cue in lowered for cue in cue_list):
                return sentence
        return ""

    def _find_best_problem_sentence(self, sentences: list[str]) -> str:
        cues = [
            "difficult",
            "costs",
            "barrier",
            "barriers",
            "bottleneck",
            "challenge",
            "problem",
            "gap",
            "requires",
            "limited",
            "degrade",
            "poor fit",
            "because",
        ]
        return self._find_best_sentence(sentences, cues)

    def _find_best_limitation_sentence(self, sentences: list[str]) -> str:
        cues = ["limitation", "limitations", "future work", "however", "although", "limited by", "challenge"]
        for sentence in sentences:
            if self._is_metadata_sentence(sentence):
                continue
            lowered = sentence.lower()
            if "not only" in lowered:
                continue
            if any(cue in lowered for cue in cues):
                return sentence
        return ""

    def _find_best_contribution_sentence(self, sentences: list[str]) -> str:
        strong_cues = ["contribution", "introduce", "present", "propose", "release", "toolkit", "provides", "framework"]
        weak_cues = ["approach", "model"]
        return self._find_best_sentence(sentences, strong_cues) or self._find_best_sentence(sentences, weak_cues)

    def _is_metadata_sentence(self, sentence: str) -> bool:
        lowered = sentence.lower()
        return "http://" in lowered or "https://" in lowered or "available at" in lowered

    def _split_sentences(self, text: str) -> list[str]:
        cleaned = self._clean_text(text)
        if not cleaned:
            return []
        return [sentence.strip() for sentence in SENTENCE_PATTERN.split(cleaned) if sentence.strip()]

    def _clean_text(self, value: str) -> str:
        return " ".join(value.split())

    def _connected_components(self, adjacency: dict[str, dict[str, int]]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        components: list[list[str]] = []
        for node in sorted(adjacency):
            if node in seen:
                continue
            stack = [node]
            component: list[str] = []
            seen.add(node)
            while stack:
                current = stack.pop()
                component.append(current)
                for neighbor in adjacency[current]:
                    if neighbor not in seen:
                        seen.add(neighbor)
                        stack.append(neighbor)
            components.append(sorted(component))

        components.sort(key=lambda item: (-len(item), item[0] if item else ""))
        return [
            {"id": index, "size": len(component), "keywords": component[:12]}
            for index, component in enumerate(components, start=1)
        ]

    def _edge_items(self, graph: dict[str, Any]) -> list[tuple[str, str, int]]:
        edges = []
        for key, weight in graph.get("edges", {}).items():
            left, right = key.split("|||", maxsplit=1)
            edges.append((left, right, int(weight)))
        return edges

    def _paper_id(self, paper: dict[str, Any], fallback_index: int) -> str:
        return str(paper.get("arxiv_id") or paper.get("title") or f"paper_{fallback_index}")

    def _add_query_focus_keywords(
        self,
        paper_keywords: dict[str, list[str]],
        papers: list[dict[str, Any]],
        query: str,
    ) -> None:
        query_terms = self._tokens_from_text(query)
        if not query_terms:
            return
        query_phrase = " ".join(query_terms)
        for index, paper in enumerate(papers, start=1):
            paper_id = self._paper_id(paper, index)
            paper_terms = set(self._tokens_from_text(self._paper_text(paper)))
            additions = [term for term in query_terms if term in paper_terms]
            if len(additions) == len(query_terms) and len(query_terms) > 1:
                additions.insert(0, query_phrase)
            current = paper_keywords.setdefault(paper_id, [])
            for keyword in reversed(additions):
                if keyword not in current:
                    current.insert(0, keyword)
            paper_keywords[paper_id] = current[:10]

    def _escape_markdown(self, value: str) -> str:
        return value.replace("|", "\\|")

    def _display_path(self, value: str) -> str:
        path = Path(value)
        try:
            return str(path.resolve().relative_to(Path.cwd().resolve())).replace("\\", "/")
        except ValueError:
            return str(path)

    def _slugify(self, value: str) -> str:
        tokens = re.findall(r"[A-Za-z0-9]+", value.lower())
        slug = "-".join(tokens[:8])
        return slug or "untitled"

    def _archive_filename(self, key: str, source: Path) -> str:
        names = {
            "report_markdown": "report.md",
            "report_pdf": "report.pdf",
            "keyword_graph": "keyword_graph.svg",
            "top_keywords": "top_keywords.svg",
            "raw_papers": "raw_papers.json",
            "ranked_papers": "ranked_papers.json",
        }
        return names.get(key, source.name)

    def _format_retrieval_error(self, error: str) -> str:
        if "HTTP Error 429" in error:
            attempts_match = re.search(r"after\s+(\d+)\s+attempt", error)
            attempts = attempts_match.group(1) if attempts_match else "multiple"
            return f"arXiv returned HTTP 429 (rate limited) after {attempts} attempts."
        return f"`{error}`"

    def _build_relevance_warning(self, query: str, papers: list[dict[str, Any]]) -> str:
        if not query or not papers:
            return ""
        query_terms = self._query_terms(query)
        if not query_terms or len(self._tokens_from_text(query)) < 2:
            return ""

        full_match_count = 0
        weak_examples: list[str] = []
        for paper in papers:
            text_terms = set(self._tokens_from_text(self._paper_text(paper)))
            matched = query_terms & text_terms
            if matched == query_terms:
                full_match_count += 1
            elif len(weak_examples) < 3:
                title = paper.get("title", "Untitled paper")
                weak_examples.append(f"{title} matches only: {', '.join(sorted(matched)) or 'none'}")

        if full_match_count / len(papers) >= 0.75:
            return ""
        examples = "; ".join(weak_examples)
        return (
            f"Only {full_match_count} of {len(papers)} selected papers contain all main query terms "
            f"({', '.join(sorted(query_terms))}). The remaining papers may be broader keyword matches rather than tightly focused matches for this query."
            + (f" Examples: {examples}." if examples else "")
        )

    def _query_terms(self, query: str) -> set[str]:
        return {
            token
            for token in self._tokens_from_text(query)
            if token not in {"engineering", "research", "study"}
        } or set(self._tokens_from_text(query))

    def _query_focus_terms(self, query: str) -> set[str]:
        terms = self._tokens_from_text(query)
        focus = set(terms)
        if len(terms) > 1:
            focus.add(" ".join(terms))
        return focus

    def _query_focus_score(self, keyword: str, query_focus: set[str]) -> int:
        if keyword in query_focus:
            return 2 if " " in keyword else 1
        return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Briefing Graph Skill independently.")
    parser.add_argument("--input", required=True, help="Path to Skill 2 ranked paper JSON.")
    parser.add_argument("--query", type=str, default="")
    parser.add_argument("--top_k", type=int, default=5)
    parser.add_argument("--output", type=str, default="outputs/reports/daily_briefing.md")
    parser.add_argument("--output-pdf", type=str, default="outputs/reports/daily_briefing.pdf")
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
                "output_pdf": args.output_pdf,
            }
        )
    except SkillNotImplementedError as exc:
        result = not_implemented_result("briefing_graph", exc)
    print_skill_result(result, args.output_json)


if __name__ == "__main__":
    main()
