# Paper Retrieval & Metadata Parsing Skill

Fill `PaperRetrievalSkill.run()` in `skill.py` to return:

```json
{
  "papers": []
}
```

The full workflow expects this Skill to save results to `data/raw/arxiv_papers.json`.

Independent demo:

```bash
python skills/paper_retrieval/skill.py --query "graph neural networks" --max_results 10
```
