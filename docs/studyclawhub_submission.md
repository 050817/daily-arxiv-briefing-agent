# StudyClawHub Submission Notes

StudyClawHub expects each submitted skill to be a directory that contains a `SKILL.md` file.

## Recommended Submission Set

Submit the project as three standalone skills:

| Field | Skill 1 | Skill 2 | Skill 3 |
| --- | --- | --- | --- |
| Type | skill | skill | skill |
| Name | `arxiv-paper-retrieval` | `paper-relevance-ranking` | `arxiv-briefing-graph` |
| Repo URL | `https://github.com/050817/daily-arxiv-briefing-agent` | `https://github.com/050817/daily-arxiv-briefing-agent` | `https://github.com/050817/daily-arxiv-briefing-agent` |
| GitHub Username | `050817` | `050817` | `050817` |
| Path | `skills/paper_retrieval` | `skills/relevance_ranking` | `skills/briefing_graph` |
| Description | Retrieve arXiv papers and save structured metadata. | Rank retrieved papers by query relevance. | Generate Markdown/PDF briefings, figures, archives, and archive Q&A. |

## What Not To Submit

Do not submit local secrets, generated binaries, or generated experiment outputs as part of a skill entry:

- `web_app/local_settings.json`
- API keys or tokens
- `.env`
- `.exe` files
- `dist/`
- large generated archives unless the assignment explicitly asks for examples

## Optional Agent Submission

If submitting the whole project as a single agent instead of three standalone skills, add a root-level `AGENTS.md` that explains the full workflow and references the three child skill directories. Then submit the repository root path `.` as the agent path.
