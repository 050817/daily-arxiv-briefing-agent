---
name: arxiv-briefing-graph
description: "Generate arXiv Markdown/PDF briefings, keyword graphs, archives, and file Q&A. Use when the user says 'generate report', 'make PDF', 'draw keyword graph', 'chat with archive', or needs Skill 3 of the daily arXiv workflow."
author: "050817"
version: "1.0.0"
tags:
  - arxiv
  - briefing
  - pdf
  - visualization
  - archive
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

# arXiv Briefing and Graph Report

You are helping the user turn ranked arXiv papers into a readable daily research briefing with Markdown, PDF, keyword graphs, archives, and grounded archive Q&A.

## When to trigger

Activate when the user says "generate report", "make PDF", "draw keyword graph", "create research briefing", "run Skill 3", "archive this result", "chat with archive", or asks for a daily arXiv briefing from ranked papers.

## Workflow

### Step 1: Gather input

Ask for or infer:

For report generation:

- `query`: User research topic.
- `input`: Path to Skill 2 output, usually `data/processed/ranked_papers.json`.
- `top_k`: Number of ranked papers to include.
- `output`: Markdown report path.
- `output_pdf`: PDF report path.
- `figures_dir`: Figure output directory.
- `archive_dir`: Archive output directory when archiving is requested.

For Q&A over an existing archive, do not rerun the full workflow. Ask for or infer:

- `archive_path`: Path to an existing archive folder, usually under `archives/<query-and-time>/`.
- `message`: User question about the archived report, papers, figures, or metadata.

The archive folder should contain any available files from `metadata.json`, `report.md`, `ranked_papers.json`, `raw_papers.json`, and `chat.json`.

### Step 2: Execute

Run the briefing script:

```bash
python skills/briefing_graph/skill.py \
  --input data/processed/ranked_papers.json \
  --query "graph neural networks" \
  --top_k 5 \
  --output outputs/reports/daily_briefing.md \
  --output-pdf outputs/reports/daily_briefing.pdf
```

Using the repository sample:

```bash
python skills/briefing_graph/skill.py \
  --input examples/sample_ranked_papers.json \
  --query "graph neural networks" \
  --output outputs/reports/daily_briefing.md \
  --output-pdf outputs/reports/daily_briefing.pdf
```

The skill reads ranked papers, creates evidence-grounded paper cards, computes keyword and topic relationships, writes a Markdown report, renders a PDF report, saves SVG figures, and supports archive Q&A over generated files.

When `briefing.ai_summary_enabled` is true and an OpenAI-compatible API is configured, use the model to summarize papers, generate report-level trend interpretation, recommended reading order, limitations, and answer archive questions. If model access is unavailable or fails, use local title/abstract heuristics, local report rules, and local archive search.

For Q&A over an existing archive, call `chat_with_archive(archive_path, message)` or the equivalent web/API entry point. This path only reads the selected archive and appends the conversation to `chat.json`; it does not rerun Skill 1 retrieval, Skill 2 ranking, or Skill 3 report generation.

### Step 3: Present results

Report:

- Markdown report path.
- PDF report path.
- Generated figure paths.
- Archive path when archiving is enabled.
- Whether report-level insights came from the LLM or local rules.
- Any retrieval warning or empty-result status.

## Outputs

Return and save:

- `report_markdown`: Markdown briefing path.
- `report_pdf`: PDF briefing path.
- `summaries`: Evidence-grounded summaries and paper cards.
- `graph_analysis`: Keyword/topic graph data.
- `figures`: Generated SVG figure paths.
- `report_insights`: Trend interpretation, recommended reading order, limitations, and evidence source.
- `archive_id`: Archive folder identifier when archiving is enabled.

Expected files:

```text
outputs/reports/daily_briefing.md
outputs/reports/daily_briefing.pdf
outputs/figures/keyword_graph.svg
outputs/figures/top_keywords.svg
archives/<query-and-time>/
```

## Report structure

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

Inputs for archive Q&A:

- `archive_path`: Path to an existing archive folder.
- `message`: User question about the archived result.

The skill reads `metadata.json`, `report.md`, `ranked_papers.json`, and `raw_papers.json` from the selected archive when those files are present. The answer and user question are saved back to `chat.json`.

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

## Error handling

- If the ranked paper input JSON path is missing, ask the user to run Skill 2 first or provide a valid ranked paper file.
- If there are no papers, generate a clear empty-result report instead of hallucinating content.
- If PDF generation fails because `reportlab` is missing, ask the user to install dependencies with `python -m pip install -r requirements.txt`.
- If LLM summarization or report-level insight generation fails, fall back to local rules and continue generating the report.
- If archive Q&A has no supporting evidence, say the archive does not contain enough evidence.

## Quality rules

- Summaries must use only paper titles, abstracts, and metadata.
- Unsupported details must be written as `Not mentioned in abstract`.
- Do not claim novelty, results, datasets, or methods unless the abstract or metadata supports them.
- LLM-generated trend interpretation, reading order, and limitations must use only selected paper evidence, ranking reasons, and keyword graph data.
- PDF, Markdown, figures, and archive metadata should remain consistent with one another.
