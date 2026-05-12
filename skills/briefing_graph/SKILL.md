---
name: arxiv-briefing-graph
description: "Generate grounded arXiv research briefings with Markdown/PDF reports, keyword co-occurrence graphs, SVG figures, archiving, and archive Q&A."
author: "050817"
version: "1.0.0"
tags:
  - arxiv
  - briefing
  - pdf
  - visualization
  - archive
---

# arXiv Briefing and Graph Report

Use this skill after papers have been retrieved and ranked. It turns Top-K papers into a readable daily arXiv research briefing, visual keyword analysis, archive files, and grounded file-aware chat responses.

## What It Does

This skill reads ranked papers, creates evidence-grounded paper cards, computes keyword and topic relationships, writes a Markdown report, renders a PDF report, saves SVG figures, and supports archive Q&A over generated files.

When `briefing.ai_summary_enabled` is true and an OpenAI-compatible API is configured, the skill uses the model to summarize papers and answer archive questions. Model output must be grounded in the provided title, abstract, metadata, report, PDF text, figure metadata, or archive JSON. If model access is unavailable or fails, use local title/abstract heuristics and local archive search.

## Inputs

- `query`: User research topic.
- `top_k_papers`: Ranked papers from Skill 2.
- `ranked_papers`: Optional full ranked list for context.
- `output`: Markdown report path.
- `output_pdf`: PDF report path.
- `figures_dir`: Figure output directory.
- `archive_dir`: Archive output directory.

## Outputs

Return and save:

- `report_markdown`: Markdown briefing path.
- `report_pdf`: PDF briefing path.
- `summaries`: Evidence-grounded summaries and paper cards.
- `graph_analysis`: Keyword/topic graph data.
- `figures`: Generated SVG figure paths.
- `archive_id`: Archive folder identifier when archiving is enabled.

Expected files:

```text
outputs/reports/daily_briefing.md
outputs/reports/daily_briefing.pdf
outputs/figures/keyword_graph.svg
outputs/figures/top_keywords.svg
archives/<query-and-time>/
```

## Report Structure

The PDF and Markdown report should follow this structure:

1. Executive Summary
2. Search Overview
3. Top Papers to Read
4. Paper Cards
5. Research Trend Map
6. Keyword / Topic Network
7. Novelty & Relevance Analysis
8. Suggested Reading Order
9. Possible Research Ideas
10. Limitations of This Search

## Archive Q&A

The archive chat logic belongs to this skill. Use `chat_with_archive()` or equivalent project entry points to answer questions about a selected archive.

Rules for archive chat:

- Prefer the configured OpenAI-compatible model when available.
- Use only archived report text, metadata JSON, paper abstracts, and figure metadata as evidence.
- If the answer is not supported by archived files, say that the archive does not contain enough evidence.
- If model access fails, fall back to local search over archive files and clearly state that the answer is local-search based.

## Configuration

Read project defaults from `config.yaml`:

- `paths.report`
- `paths.report_pdf`
- `paths.figures_dir`
- `paths.archive_dir`
- `briefing.ai_summary_enabled`
- `briefing.llm_model`
- `briefing.ai_summary_timeout_seconds`
- `briefing.chat_timeout_seconds`

OpenAI-compatible settings may come from `web_app/local_settings.json` or environment variables such as `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `OPENAI_MODEL`.

## Run

```bash
python skills/briefing_graph/skill.py \
  --input data/processed/ranked_papers.json \
  --query "graph neural networks" \
  --top_k 5 \
  --output outputs/reports/daily_briefing.md \
  --output-pdf outputs/reports/daily_briefing.pdf
```

Using the sample file:

```bash
python skills/briefing_graph/skill.py \
  --input examples/sample_ranked_papers.json \
  --query "graph neural networks" \
  --output outputs/reports/daily_briefing.md \
  --output-pdf outputs/reports/daily_briefing.pdf
```

## Quality Rules

- Summaries must use only paper titles, abstracts, and metadata.
- Unsupported details must be written as `Not mentioned in abstract`.
- Do not claim novelty, results, datasets, or methods unless the abstract or metadata supports them.
- If there are no papers, generate a clear empty-result report instead of hallucinating content.
- PDF, Markdown, figures, and archive metadata should remain consistent with one another.
