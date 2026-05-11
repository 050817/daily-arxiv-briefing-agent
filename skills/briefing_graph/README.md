# Briefing Generation & Research Graph Analysis Skill

`BriefingGraphSkill` turns ranked Top-K papers into readable Markdown and PDF research briefings plus a lightweight keyword co-occurrence graph.

The implementation is intentionally local and dependency-light:

- summaries are generated only from title and abstract evidence;
- unsupported fields are reported as `Not mentioned in abstract`;
- keywords are extracted with a controlled vocabulary plus readable phrase scoring;
- graph analysis is computed with built-in Python data structures;
- visualizations are saved as SVG files, so no `networkx` or `matplotlib` dependency is required.
- PDF reports are generated with `reportlab` and follow a fixed 10-section briefing structure.

The Skill returns:

```json
{
  "report_markdown": "outputs/reports/daily_briefing.md",
  "report_pdf": "outputs/reports/daily_briefing.pdf",
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
  --output outputs/reports/daily_briefing.md \
  --output-pdf outputs/reports/daily_briefing.pdf
```

Expected generated files:

```text
outputs/reports/daily_briefing.md
outputs/reports/daily_briefing.pdf
outputs/figures/keyword_graph.svg
outputs/figures/top_keywords.svg
```
