# Briefing Generation & Research Graph Analysis Skill

`BriefingGraphSkill` turns ranked Top-K papers into a readable Markdown research briefing and a lightweight keyword co-occurrence graph.

The implementation is intentionally local and dependency-light:

- summaries are generated only from title and abstract evidence;
- unsupported fields are reported as `Not mentioned in abstract`;
- keywords are extracted with a controlled vocabulary plus readable phrase scoring;
- graph analysis is computed with built-in Python data structures;
- visualizations are saved as SVG files, so no `networkx` or `matplotlib` dependency is required.

The Skill returns:

```json
{
  "report_markdown": "outputs/reports/daily_briefing.md",
  "summaries": [],
  "graph_analysis": {},
  "figures": []
}
```

Independent demo using Skill 2 output:

```bash
python skills/briefing_graph/skill.py --input data/processed/ranked_papers.json --top_k 5
```

Demo using the repository sample:

```bash
python skills/briefing_graph/skill.py \
  --input examples/sample_ranked_papers.json \
  --query "graph neural networks" \
  --output outputs/reports/daily_briefing.md
```

Expected generated files:

```text
outputs/reports/daily_briefing.md
outputs/figures/keyword_graph.svg
outputs/figures/top_keywords.svg
```
