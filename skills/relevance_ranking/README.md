# Relevance Ranking & Filtering Skill

Fill `RelevanceRankingSkill.run()` in `skill.py` to return:

```json
{
  "ranked_papers": [],
  "top_k_papers": []
}
```

Independent demo using Skill 1 output:

```bash
python skills/relevance_ranking/skill.py --input data/raw/arxiv_papers.json --query "graph neural networks" --top_k 5
```
