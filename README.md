# Daily arXiv Research Briefing Agent

This repository contains the workflow architecture for a three-skill AI Agent that generates daily arXiv research briefings for social network analysis, graph learning, and related topics.

Skill 1 (paper retrieval) is implemented and can already fetch recent arXiv metadata. Skills 2 and 3 are still scaffolds, so the workflow can be exercised end-to-end up to the first unimplemented downstream stage.

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
    └── test_agent.py
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

At the moment, the workflow skeleton only requires `pyyaml`. Future Skill implementations may add packages such as `arxiv`, `scikit-learn`, `sentence-transformers`, `networkx`, and `matplotlib`.

## Run the Workflow

Run the full Agent:

```bash
python main.py \
  --query "graph neural networks for misinformation detection in social networks" \
  --date_range "last 7 days" \
  --max_results 50 \
  --top_k 5
```

Because Skills 2 and 3 are still empty, the command will stop cleanly at the first unimplemented downstream Skill and return a structured JSON message with status `partial`.

## Stage-by-Stage Experiments

The workflow supports partial execution. This is useful when later Skills are still missing.

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

Use `--strict` if you want the program to raise an error instead of returning a clean `partial` result when a Skill is not implemented.

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

Skills 2 and 3 currently return `status: not_implemented`. Skill 1 now produces real paper metadata output from arXiv.

## Expected Data Contracts

Skill 1 should output:

```json
{
  "papers": []
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
  "figures": []
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

## Run Tests

Run the integration contract tests:

```bash
python -m unittest tests.test_agent
```

The tests verify that:

- missing Skills stop the workflow cleanly;
- earlier stages can be tested even when later Skills are missing;
- the full pipeline contract works after all Skills are filled.

## Development Notes

When implementing a Skill, keep its public `run(input_data: dict) -> dict` interface compatible with the expected data contract. The Agent orchestrator depends on these keys:

- Skill 1: `papers`
- Skill 2: `ranked_papers`, `top_k_papers`
- Skill 3: `report_markdown`, `summaries`, `graph_analysis`, `figures`

After implementing one Skill, run both its independent CLI command and the matching staged workflow command to confirm it integrates correctly.
