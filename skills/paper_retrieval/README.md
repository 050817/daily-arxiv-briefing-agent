# Paper Retrieval & Metadata Parsing Skill

`PaperRetrievalSkill.run()` in `skill.py` now retrieves recent arXiv papers, normalizes their metadata, filters by `date_range`, and returns:

```json
{
  "papers": []
}
```

The full workflow expects this Skill to save results to `data/raw/arxiv_papers.json`.

Supported `date_range` values include:

- `last 7 days`
- `last 2 weeks`
- `today`
- `yesterday`
- `all`
- a single ISO date such as `2026-05-01`

The network request behavior is configurable in `config.yaml`:

- `retrieval.request_timeout_seconds`
- `retrieval.max_retries`
- `retrieval.retry_backoff_seconds`

Plain-language queries are automatically expanded into broader title/abstract search clauses for better recall. If you already provide arXiv fielded syntax such as `cat:cs.LG AND ti:"graph neural networks"`, the query is passed through unchanged.

Independent demo:

```bash
python skills/paper_retrieval/skill.py --query "graph neural networks" --max_results 10
```
