---
name: paper-relevance-ranking
description: "Rank retrieved arXiv papers by query relevance with a local TF-IDF baseline and produce Top-K papers with evidence-based ranking reasons."
author: "050817"
version: "1.0.0"
tags:
  - arxiv
  - ranking
  - tfidf
  - research
---

# Paper Relevance Ranking

Use this skill after arXiv metadata has been retrieved and normalized. It selects the most relevant papers for a user query while preserving all source metadata for report generation.

## What It Does

This skill reads papers from Skill 1, builds a ranking document from each paper's `title + abstract`, computes a lightweight TF-IDF representation in pure Python, scores query-paper similarity with cosine similarity, optionally filters by arXiv categories, and returns the best `top_k` papers.

It does not require model access or network access.

## Inputs

- `query`: The user's research topic.
- `papers`: Normalized papers from `data/raw/arxiv_papers.json` or an equivalent in-memory object.
- `top_k`: Number of papers to keep for the briefing.
- `method`: Ranking method. Use `tfidf` unless another method is implemented.
- `allowed_categories`: Optional list of arXiv categories to keep.

## Outputs

Return and save:

- `ranked_papers`: All eligible papers sorted by descending relevance score.
- `top_k_papers`: The first `top_k` ranked papers.

Each ranked paper should preserve all original metadata and append:

- `relevance_score`
- `rank`
- `ranking_reason`

By default, save the output to `data/processed/ranked_papers.json`.

## Configuration

Read project defaults from `config.yaml`:

- `paths.ranked_papers`
- `defaults.top_k`
- `defaults.ranking_method`

## Run

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

## Quality Rules

- Rank only papers supplied by the retrieval step.
- Do not fabricate relevance evidence. Ranking reasons must refer to title, abstract, category, or query-term overlap.
- Preserve paper metadata exactly so later report generation can cite the source record.
- If no papers are available, return an empty ranking with a clear status instead of inventing candidates.
