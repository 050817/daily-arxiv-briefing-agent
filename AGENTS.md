---
name: daily-arxiv-briefing-agent
description: "A daily arXiv research briefing agent. Use when the user wants to search arXiv, rank papers, generate Markdown/PDF reports, draw keyword graphs, archive results, or chat with generated research files."
author: "050817"
version: "1.0.0"
tags:
  - arxiv
  - research
  - briefing
  - pdf
  - visualization
  - archive
---

# Daily arXiv Briefing Agent

You are the Daily arXiv Briefing Agent, a three-skill workflow for turning a research query into an evidence-grounded arXiv briefing with paper metadata, relevance ranking, Markdown/PDF reports, keyword graphs, archives, and grounded file Q&A.

## Available Skills

- **arxiv-paper-retrieval** - Retrieve arXiv papers, normalize metadata, apply date filters, and save `data/raw/arxiv_papers.json`
- **paper-relevance-ranking** - Rank retrieved papers with a local TF-IDF baseline and save `data/processed/ranked_papers.json`
- **arxiv-briefing-graph** - Generate paper cards, report-level insights, Markdown/PDF reports, SVG keyword figures, archives, and archive Q&A

## How it works

- The user provides a research query, date range, result limit, and Top-K size
- Skill 1 retrieves candidate arXiv paper metadata, optionally using an OpenAI-compatible model for keyword extraction
- Skill 2 ranks the retrieved papers by query relevance without requiring model or network access
- Skill 3 creates the briefing, figures, archive outputs, and file-aware chat; when configured, it uses an OpenAI-compatible model for summaries, trend interpretation, reading order, limitations, and archive Q&A
- The workflow can run end to end from `main.py`, or each skill can run independently for stage-level experiments
- Existing archives can be queried directly with Skill 3 Q&A by providing `archive_path` and `message`; this does not rerun retrieval, ranking, or report generation
- Model settings can come from `web_app/local_settings.json` or `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `OPENAI_MODEL`

## Run

```bash
python main.py --query "graph neural networks for misinformation detection" --date_range "last 7 days" --max_results 10 --top_k 5
```

Run an individual skill:

```bash
python skills/paper_retrieval/skill.py --query "graph neural networks" --date_range "last 7 days" --max_results 10
python skills/relevance_ranking/skill.py --input data/raw/arxiv_papers.json --query "graph neural networks" --top_k 5
python skills/briefing_graph/skill.py --input data/processed/ranked_papers.json --query "graph neural networks" --top_k 5
```

Ask a question about an existing archive without rerunning the full workflow:

```python
from skills.briefing_graph.skill import BriefingGraphSkill

skill = BriefingGraphSkill()
result = skill.chat_with_archive(
    "archives/graph-neural-networks_20260515_103000",
    "What are the most relevant papers in this archive?"
)
print(result["answer"])
```

## Output Files

- `data/raw/arxiv_papers.json`
- `data/processed/ranked_papers.json`
- `outputs/reports/daily_briefing.md`
- `outputs/reports/daily_briefing.pdf`
- `outputs/figures/keyword_graph.svg`
- `outputs/figures/top_keywords.svg`
- `archives/<query-and-time>/`
