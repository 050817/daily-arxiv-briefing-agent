# Briefing Generation & Research Graph Analysis Skill

Fill `BriefingGraphSkill.run()` in `skill.py` to return:

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
