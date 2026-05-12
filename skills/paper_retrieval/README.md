# Paper Retrieval & Metadata Parsing Skill

`PaperRetrievalSkill.run()` in `skill.py` now retrieves recent arXiv papers, normalizes their metadata, filters by `date_range`, and returns:

```json
{
  "papers": [],
  "query_keywords": [],
  "keyword_extraction_source": "openai",
  "resolved_search_query": ""
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

Keyword extraction now works in two stages:

- first, an OpenAI Responses API call extracts 2-6 concise technical keyword phrases from the natural-language query;
- second, those phrases are expanded into broader title/abstract search clauses for arXiv retrieval, with concept groups combined using `OR` to maximize recall before downstream ranking/filtering.

The OpenAI call reuses `web_app/local_settings.json` when available, so a model configured in the local web UI can be shared directly with Skill 1. It otherwise falls back to `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_MODEL`, plus these optional config fields:

- `retrieval.llm_keyword_extraction_enabled`
- `retrieval.llm_model`
- `retrieval.llm_timeout_seconds`
- `retrieval.llm_max_keywords`

If the query already uses arXiv fielded syntax such as `cat:cs.LG AND ti:"graph neural networks"`, the query is passed through unchanged. If no OpenAI-compatible key is available or the OpenAI call fails, the Skill falls back to the original heuristic keyword grouping logic.

Independent demo:

```bash
python skills/paper_retrieval/skill.py --query "graph neural networks" --max_results 10
```
