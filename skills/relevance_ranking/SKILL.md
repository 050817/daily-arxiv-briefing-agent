---
name: paper-relevance-ranking
description: "Rank retrieved arXiv papers by relevance. Use when the user says 'rank papers', 'filter papers', 'select top-k papers', or needs Skill 2 of the daily arXiv workflow."
author: "050817"
version: "1.0.0"
tags:
  - arxiv
  - ranking
  - tfidf
  - research
metadata:
  openclaw:
    requires:
      env: []
      bins:
        - python3
    primaryEnv: ""
---

# Paper Relevance Ranking

You are helping the user rank retrieved arXiv papers by relevance to a research query while preserving source metadata for report generation.

## When to trigger

Activate when the user says "rank papers", "filter papers", "select top-k papers", "run Skill 2", "choose the most relevant papers", or asks to prepare retrieved papers for a briefing.

## Workflow

### Step 1: Gather input

Ask for or infer:

- `query`: The user's research topic.
- `input`: Path to Skill 1 output, usually `data/raw/arxiv_papers.json`.
- `top_k`: Number of papers to keep for the briefing.
- `method`: Ranking method. Use `tfidf` unless another method is implemented.
- `allowed_categories`: Optional arXiv category filter.

### Step 2: Execute

Run the ranking script:

```bash
python skills/relevance_ranking/skill.py \
  --input data/raw/arxiv_papers.json \
  --query "graph neural networks" \
  --method tfidf \
  --top_k 5
```

With category filtering:

```bash
python skills/relevance_ranking/skill.py \
  --input data/raw/arxiv_papers.json \
  --query "graph neural networks" \
  --allowed-categories cs.SI cs.LG stat.ML \
  --top_k 5
```

The skill reads normalized papers, builds a ranking document from each paper's `title + abstract`, computes a lightweight TF-IDF representation in pure Python, scores query-paper similarity with cosine similarity, optionally filters by arXiv categories, and saves ranked results to `data/processed/ranked_papers.json` by default.

This skill does not require model access or network access.

### Step 3: Present results

Report:

- Number of input papers.
- Number of ranked papers.
- Number of Top-K papers selected.
- Top paper titles and scores.
- Output path, usually `data/processed/ranked_papers.json`.

## Outputs

Return and save:

- `ranked_papers`: All eligible papers sorted by descending relevance score.
- `top_k_papers`: The first `top_k` ranked papers.

Each ranked paper should preserve all original metadata and append:

- `relevance_score`
- `rank`
- `ranking_reason`

## Configuration

Read project defaults from `config.yaml`:

- `paths.ranked_papers`
- `defaults.top_k`
- `defaults.ranking_method`

## Error handling

- If `query` is missing, ask the user to provide a research topic.
- If the input JSON path is missing, ask the user to run Skill 1 first or provide a valid paper JSON file.
- If no papers are available, return an empty ranking with a clear status instead of inventing candidates.
- If category filtering removes all papers, report that the filter was too restrictive.

## Quality rules

- Rank only papers supplied by the retrieval step.
- Do not fabricate relevance evidence. Ranking reasons must refer to title, abstract, category, or query-term overlap.
- Preserve paper metadata exactly so later report generation can cite the source record.
- Keep the ranking deterministic and explainable.
