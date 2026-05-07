# Relevance Ranking & Filtering Skill

`RelevanceRankingSkill.run()` ranks papers from Skill 1 by relevance to the user query and returns:

```json
{
  "ranked_papers": [
    {
      "title": "Paper title",
      "authors": ["Author A"],
      "abstract": "Paper abstract",
      "published_date": "2026-05-01",
      "arxiv_id": "2605.00001",
      "url": "https://arxiv.org/abs/2605.00001",
      "categories": ["cs.SI", "cs.LG"],
      "relevance_score": 0.87,
      "rank": 1,
      "ranking_reason": "Matches query terms in the title: graph, networks."
    }
  ],
  "top_k_papers": []
}
```

The implementation keeps all original metadata from Skill 1 and appends ranking fields. This allows Skill 3 to generate summaries and graph analysis without losing authors, URLs, dates, or categories.

## Method

- Builds each ranking document from `title + abstract`.
- Computes a lightweight TF-IDF representation in pure Python.
- Scores query-paper similarity with cosine similarity.
- Supports optional arXiv category filtering through `allowed_categories`.
- Selects the first `top_k` papers after sorting by descending relevance score.
- Saves results to `data/processed/ranked_papers.json` by default.

Independent demo using Skill 1 output:

```bash
python skills/relevance_ranking/skill.py \
  --input data/raw/arxiv_papers.json \
  --query "graph neural networks" \
  --method tfidf \
  --top_k 5
```

Optional category filter:

```bash
python skills/relevance_ranking/skill.py \
  --input data/raw/arxiv_papers.json \
  --query "graph neural networks" \
  --allowed-categories cs.SI cs.LG stat.ML \
  --top_k 5
```
