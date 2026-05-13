---
name: arxiv-paper-retrieval
description: "Retrieve arXiv paper metadata. Use when the user says 'search arXiv', 'retrieve papers', 'collect paper metadata', or needs Skill 1 of the daily arXiv workflow."
author: "050817"
version: "1.0.0"
tags:
  - arxiv
  - research
  - retrieval
  - metadata
metadata:
  openclaw:
    requires:
      env:
        - OPENAI_API_KEY
        - OPENAI_BASE_URL
        - OPENAI_MODEL
      bins:
        - python3
    primaryEnv: OPENAI_API_KEY
---

# arXiv Paper Retrieval

You are helping the user retrieve candidate arXiv papers for a daily research briefing, literature scan, or downstream ranking workflow.

## When to trigger

Activate when the user says "search arXiv", "retrieve papers", "collect paper metadata", "run Skill 1", "find recent papers", or asks for arXiv papers for a research topic.

## Workflow

### Step 1: Gather input

Ask for or infer:

- `query`: Natural-language research topic or an arXiv fielded query.
- `date_range`: One of `today`, `yesterday`, `last 7 days`, `last 2 weeks`, `all`, or a single ISO date such as `2026-05-01`.
- `max_results`: Maximum number of candidate papers to request.

If the query already uses arXiv field syntax such as `cat:cs.LG AND ti:"graph neural networks"`, pass it through unchanged.

### Step 2: Execute

Run the retrieval script:

```bash
python skills/paper_retrieval/skill.py --query "graph neural networks" --date_range "last 7 days" --max_results 10
```

For broad terms that arXiv may not match well, prefer a fielded query:

```bash
python skills/paper_retrieval/skill.py --query "all:harness" --date_range all --max_results 10
```

The skill builds an arXiv-compatible search query, retrieves paper metadata, filters papers by date, and saves normalized results to `data/raw/arxiv_papers.json` by default.

When `retrieval.llm_keyword_extraction_enabled` is true and an OpenAI-compatible API is configured, use the model to extract concise technical keyword phrases before querying arXiv. If model access is unavailable or fails, fall back to local heuristic keyword grouping.

### Step 3: Present results

Report:

- Number of papers retrieved after date filtering.
- Final arXiv query in `resolved_search_query`.
- Keyword phrases in `query_keywords`.
- Output path, usually `data/raw/arxiv_papers.json`.
- Any `retrieval_error` if arXiv retrieval failed.

## Outputs

Return and save a JSON object containing:

- `papers`: List of normalized paper records.
- `query_keywords`: Keyword phrases used for retrieval.
- `keyword_extraction_source`: `openai`, `heuristic`, or `direct_query`.
- `resolved_search_query`: Final arXiv query string.
- `retrieval_error`: Present only when retrieval fails and empty results are allowed.

Each paper record should include:

- `title`
- `authors`
- `abstract`
- `published_date`
- `arxiv_id`
- `url`
- `pdf_url` when available
- `categories`

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

## Error handling

- If `query` is missing, ask the user to provide a research topic or arXiv fielded query.
- If arXiv times out or rate limits the request, retry according to `config.yaml`; if `retrieval.allow_empty_on_error` is true, return an empty paper list with `retrieval_error`.
- If the LLM keyword extraction API call fails, continue with local heuristic keyword grouping.
- If no papers are found, report an empty retrieval result without inventing metadata.

## Quality rules

- Do not invent metadata. Use only fields returned by arXiv.
- Preserve titles, abstracts, authors, dates, URLs, and categories for later skills.
- Report retrieval failures clearly instead of silently pretending papers were found.
- Keep arXiv requests conservative: use configured retries, backoff, and timeouts.
