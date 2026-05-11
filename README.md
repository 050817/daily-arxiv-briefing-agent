# Daily arXiv Research Briefing Agent

This repository contains a three-skill AI Agent that generates daily arXiv research briefings for social network analysis, graph learning, and related topics.

All three Skills are implemented:

- Skill 1 retrieves recent arXiv metadata.
- Skill 2 ranks papers with a lightweight TF-IDF baseline.
- Skill 3 generates a Markdown briefing plus SVG keyword-graph visualizations.

## Repository Structure

```text
.
├── main.py
├── config.yaml
├── requirements.txt
├── agent/
│   ├── orchestrator.py
│   ├── schema.py
│   └── io_utils.py
├── skills/
│   ├── paper_retrieval/
│   │   ├── skill.py
│   │   └── README.md
│   ├── relevance_ranking/
│   │   ├── skill.py
│   │   └── README.md
│   └── briefing_graph/
│       ├── skill.py
│       └── README.md
├── examples/
│   ├── sample_raw_papers.json
│   └── sample_ranked_papers.json
├── data/
│   ├── raw/
│   └── processed/
├── outputs/
│   ├── reports/
│   └── figures/
└── tests/
    ├── test_agent.py
    ├── test_briefing_graph.py
    ├── test_paper_retrieval.py
    └── test_relevance_ranking.py
```

## Environment Setup

Create and activate a Python environment:

```bash
conda create -n arxiv-agent python=3.10 -y
conda activate arxiv-agent
```

Install dependencies:

```bash
pip install -r requirements.txt
```

The implemented workflow uses `pyyaml` for configuration, `reportlab` for PDF generation, and `pypdf`/`pdfplumber` for PDF checks and inspection. Retrieval uses arXiv HTTP endpoints through the Python standard library, Skill 2 uses a pure-Python TF-IDF baseline, and Skill 3 writes SVG figures directly, so no `networkx` or `matplotlib` dependency is required for the current implementation.

## Run the Workflow

Run the full Agent:

```bash
python main.py \
  --query "graph neural networks for misinformation detection in social networks" \
  --date_range "last 7 days" \
  --max_results 50 \
  --top_k 5
```

This command runs retrieval, ranking, and briefing end-to-end, then writes raw paper JSON, ranked paper JSON, Markdown and PDF reports, and keyword figures to the configured output paths.

## Run the HTTP Web App

Start the local web interface:

```bash
python web_app/server.py
```

Open:

```text
http://127.0.0.1:8765
```

The web page lets you:

- enter a query and run the full retrieval/ranking/briefing workflow;
- choose an arbitrary recent-day window, or search all dates;
- preview and download the generated PDF report;
- preview and download keyword/topic SVG figures;
- chat about the archived report files;
- browse archives by topic plus query date range. Archive folders are saved as `keyword + timestamp` under `archives/`, and each `metadata.json` stores the query start/end dates.

For model-backed chat, set an OpenAI-compatible API configuration before starting the server:

```bash
set OPENAI_API_KEY=your_key
set OPENAI_BASE_URL=https://api.openai.com/v1
set OPENAI_MODEL=gpt-4.1-mini
python web_app/server.py
```

The web page also saves these values to `web_app/local_settings.json`. Skill 1 reuses that same local file for LLM keyword extraction, so you do not need to enter the API URL, model, and key twice.

If no API key is configured, the chat panel still works in local file-search mode.

### Double-click Launcher

On Windows, you can double-click:

```text
dist/DailyArxivWeb.exe
```

The executable starts the local HTTP server and opens the browser automatically. Keep the terminal window open while using the page; closing it stops the local web app.

To rebuild the executable after code changes:

```bash
python -m PyInstaller --noconfirm --onefile --name DailyArxivWeb --paths . --collect-all reportlab --hidden-import agent.io_utils --hidden-import agent.orchestrator --hidden-import agent.schema --hidden-import skills.common --hidden-import skills.paper_retrieval.skill --hidden-import skills.relevance_ranking.skill --hidden-import skills.briefing_graph.skill --add-data "web_app/static;web_app/static" web_app/server.py
```

The web UI can store API URL, model, and API key from the browser. These values are saved only on this machine in:

```text
web_app/local_settings.json
```

That file is ignored by Git.

## Stage-by-Stage Experiments

The workflow supports partial execution. This is useful for isolated debugging, demos, and Skill-by-Skill experiments.

Run only Skill 1:

```bash
python main.py \
  --query "graph neural networks" \
  --stop-after retrieval
```

Run Skill 2 using existing raw paper data:

```bash
python main.py \
  --query "graph neural networks" \
  --start-at ranking \
  --stop-after ranking \
  --input examples/sample_raw_papers.json
```

Run Skill 3 using existing ranked paper data:

```bash
python main.py \
  --query "graph neural networks" \
  --start-at briefing \
  --stop-after briefing \
  --input examples/sample_ranked_papers.json
```

Use `--strict` during development if you want the program to raise an error instead of returning a clean `partial` result when a Skill raises `SkillNotImplementedError`.

## Run Each Skill Independently

Skill 1:

```bash
python skills/paper_retrieval/skill.py \
  --query "graph neural networks misinformation detection" \
  --max_results 50
```

Skill 2:

```bash
python skills/relevance_ranking/skill.py \
  --input examples/sample_raw_papers.json \
  --query "graph neural networks for misinformation detection" \
  --method tfidf \
  --top_k 5
```

Skill 3:

```bash
python skills/briefing_graph/skill.py \
  --input examples/sample_ranked_papers.json \
  --query "graph neural networks for misinformation detection" \
  --top_k 5 \
  --output outputs/reports/daily_briefing.md
```

Skill 2 produces ranked paper metadata and Top-K filtered papers. Skill 3 produces the final Markdown briefing, keyword analysis, and SVG visualizations.

## Expected Data Contracts

Skill 1 should output:

```json
{
  "papers": [],
  "query_keywords": [],
  "keyword_extraction_source": "openai",
  "resolved_search_query": ""
}
```

Skill 2 should output:

```json
{
  "ranked_papers": [],
  "top_k_papers": []
}
```

Skill 3 should output:

```json
{
  "report_markdown": "outputs/reports/daily_briefing.md",
  "summaries": [],
  "graph_analysis": {},
  "figures": [],
  "retrieval_error": ""
}
```

Recommended output paths are configured in `config.yaml`:

```text
data/raw/arxiv_papers.json
data/processed/ranked_papers.json
outputs/reports/daily_briefing.md
outputs/figures/
```

Skill 1 request reliability can also be tuned in `config.yaml` through:

- `retrieval.request_timeout_seconds`
- `retrieval.max_retries`
- `retrieval.retry_backoff_seconds`

Skill 1 now attempts OpenAI-based keyword extraction before building the final arXiv query. It first checks `web_app/local_settings.json` if you have already saved model settings in the local web app, then falls back to environment variables, and finally to the project defaults in `config.yaml`. The behavior is controlled through:

- `retrieval.llm_keyword_extraction_enabled`
- `retrieval.llm_model`
- `retrieval.llm_timeout_seconds`
- `retrieval.llm_max_keywords`

If no OpenAI-compatible API key is available or the LLM call fails, Skill 1 falls back to the original heuristic query expansion logic.

## Run Tests

Run the full automated test suite:

```bash
python -m unittest discover -s tests
```

Run a specific test module:

```bash
python -m unittest tests.test_relevance_ranking
```

The tests verify that:

- retrieval, ranking, and briefing all satisfy their current data contracts;
- stage-by-stage execution works from intermediate JSON files;
- missing or intentionally stubbed Skills still stop the workflow cleanly when needed.

## Development Notes

When implementing a Skill, keep its public `run(input_data: dict) -> dict` interface compatible with the expected data contract. The Agent orchestrator depends on these keys:

- Skill 1: `papers`
- Skill 2: `ranked_papers`, `top_k_papers`
- Skill 3: `report_markdown`, `summaries`, `graph_analysis`, `figures`

After implementing one Skill, run both its independent CLI command and the matching staged workflow command to confirm it integrates correctly.
