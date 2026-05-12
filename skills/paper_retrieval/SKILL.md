---
name: arxiv-paper-retrieval
description: "Retrieve arXiv papers for a research briefing by turning a topic into an arXiv API query, applying date filters, and saving structured metadata."
author: "050817"
version: "1.0.0"
tags:
  - arxiv
  - research
  - retrieval
  - metadata
---

# arXiv Paper Retrieval

Use this skill when a workflow needs to collect candidate arXiv papers for a research briefing, literature scan, or paper recommendation task.

## What It Does

This skill accepts a user query, optional date range, and result limit. It builds an arXiv-compatible search query, retrieves paper metadata from arXiv, filters papers by publication date, and writes normalized results for downstream skills.

If the query already uses arXiv field syntax such as `cat:cs.LG AND ti:"graph neural networks"`, pass it through unchanged. Otherwise, extract concise technical keyword phrases first. When an OpenAI-compatible API is configured and `retrieval.llm_keyword_extraction_enabled` is true, use the model for keyword extraction. If model access is unavailable or fails, fall back to local heuristic keyword grouping.

## Inputs

- `query`: Natural-language research topic or an arXiv fielded query.
- `date_range`: One of `today`, `yesterday`, `last 7 days`, `last 2 weeks`, `all`, or a single ISO date such as `2026-05-01`.
- `max_results`: Maximum number of candidate papers to request.

## Outputs

Return and save a JSON object containing:

- `papers`: List of normalized paper records.
- `query_keywords`: Keyword phrases used for retrieval.
- `keyword_extraction_source`: `openai`, `heuristic`, or `fielded_query`.
- `resolved_search_query`: Final arXiv query string.
- `retrieval_error`: Present only when retrieval fails and empty results are allowed.

Each paper record should include:

- `title`
- `authors`
- `abstract`
- `published_date`
- `arxiv_id`
- `url`
- `pdf_url`
- `categories`

By default, save the output to `data/raw/arxiv_papers.json`.

## Configuration

Read project defaults from `config.yaml`:

- `paths.raw_papers`
- `defaults.date_range`
- `defaults.max_results`
- `retrieval.request_timeout_seconds`
- `retrieval.max_retries`
- `retrieval.retry_backoff_seconds`
- `retrieval.allow_empty_on_error`
- `retrieval.llm_keyword_extraction_enabled`
- `retrieval.llm_model`
- `retrieval.llm_timeout_seconds`
- `retrieval.llm_max_keywords`

OpenAI-compatible settings may come from `web_app/local_settings.json` or environment variables such as `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `OPENAI_MODEL`.

## Run

```bash
python skills/paper_retrieval/skill.py --query "graph neural networks" --date_range "last 7 days" --max_results 10
```

For broad terms that arXiv may not match well, prefer a fielded query:

```bash
python skills/paper_retrieval/skill.py --query "all:harness" --date_range all --max_results 10
```

## Quality Rules

- Do not invent metadata. Use only fields returned by arXiv.
- Preserve titles, abstracts, authors, dates, URLs, and categories for later skills.
- Report retrieval failures clearly instead of silently pretending papers were found.
- Keep arXiv requests conservative: use configured retries, backoff, and timeouts.
