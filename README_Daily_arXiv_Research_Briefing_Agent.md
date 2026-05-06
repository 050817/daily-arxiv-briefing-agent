# Daily arXiv Research Briefing Agent

A three-skill AI Agent system for automatically generating daily arXiv research briefings in the area of social network analysis, graph learning, and related research topics.

This project is designed for the final project of **Social Network Analysis, Spring 2026**. The system follows an **Agent + Skills** architecture: each team member develops one independently testable Skill, and the group integrates all Skills into a unified Agent.

---

## 1. Project Overview

Researchers often need to screen many new arXiv papers every day. Manually checking titles, abstracts, relevance, methods, and research trends is time-consuming. This project builds a **Daily arXiv Research Briefing Agent** that automates this workflow.

Given a user query such as:

```text
graph neural networks for misinformation detection in social networks
```

the Agent will:

1. retrieve recent arXiv papers;
2. parse paper metadata;
3. rank papers by relevance to the query;
4. select the Top-K most relevant papers;
5. generate structured research summaries;
6. construct a keyword co-occurrence network;
7. analyze central research topics;
8. generate a final Markdown research briefing.

The project is especially focused on topics related to:

- social network analysis;
- graph neural networks;
- community detection;
- link prediction;
- misinformation detection;
- influence analysis;
- graph mining;
- recommendation on networks.

---

## 2. Team Skill Division

The project is divided into three independent Skills.

| Member | Skill | Main Responsibility | Main Output |
|---|---|---|---|
| Member 1 | Paper Retrieval & Metadata Parsing Skill | Retrieve papers from arXiv and parse metadata | Raw paper list in JSON format |
| Member 2 | Relevance Ranking & Filtering Skill | Rank papers according to user query and select Top-K papers | Ranked paper list with relevance scores |
| Member 3 | Briefing Generation & Research Graph Analysis Skill | Generate structured summaries, build keyword graph, and create final report | Markdown briefing and network visualizations |

Each Skill must be independently executable, testable, and reusable.

---

## 3. System Workflow

```text
User Query
   ↓
[Skill 1] Paper Retrieval & Metadata Parsing
   ↓
Raw Paper Metadata
   ↓
[Skill 2] Relevance Ranking & Filtering
   ↓
Top-K Relevant Papers
   ↓
[Skill 3] Briefing Generation & Research Graph Analysis
   ↓
Daily arXiv Research Briefing
```

Example input:

```json
{
  "query": "graph neural networks for misinformation detection in social networks",
  "date_range": "last 7 days",
  "max_results": 50,
  "top_k": 5
}
```

Example final output:

```text
outputs/reports/daily_briefing.md
outputs/figures/keyword_graph.png
outputs/figures/top_keywords.png
```

---

## 4. Repository Structure

```text
daily-arxiv-briefing-agent/
│
├── README.md
├── requirements.txt
├── config.yaml
├── main.py
│
├── agent/
│   ├── orchestrator.py
│   └── schema.py
│
├── skills/
│   ├── paper_retrieval/
│   │   ├── skill.py
│   │   ├── README.md
│   │   └── test_retrieval.py
│   │
│   ├── relevance_ranking/
│   │   ├── skill.py
│   │   ├── README.md
│   │   └── test_ranking.py
│   │
│   └── briefing_graph/
│       ├── skill.py
│       ├── README.md
│       └── test_briefing_graph.py
│
├── data/
│   ├── raw/
│   └── processed/
│
├── outputs/
│   ├── reports/
│   └── figures/
│
├── tests/
│   └── test_agent.py
│
└── docs/
    ├── group_report.tex
    ├── individual_report_template.tex
    └── slides.pptx
```

---

## 5. Installation

Create a Python environment:

```bash
conda create -n arxiv-agent python=3.10 -y
conda activate arxiv-agent
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Suggested dependencies:

```text
arxiv
pandas
numpy
scikit-learn
sentence-transformers
networkx
matplotlib
python-louvain
nltk
tqdm
pyyaml
```

Optional dependencies:

```text
openai
anthropic
keybert
spacy
markdown
```

---

## 6. Quick Start

Run the complete Agent:

```bash
python main.py \
  --query "graph neural networks for misinformation detection in social networks" \
  --date_range "last 7 days" \
  --max_results 50 \
  --top_k 5
```

Expected output:

```text
outputs/reports/daily_briefing.md
outputs/figures/keyword_graph.png
outputs/figures/top_keywords.png
data/raw/arxiv_papers.json
data/processed/ranked_papers.json
```

---

## 7. Skill 1: Paper Retrieval & Metadata Parsing Skill

### 7.1 Purpose

This Skill retrieves papers from arXiv based on a user query and parses paper metadata into a unified JSON format.

### 7.2 Input

```json
{
  "query": "graph neural networks misinformation detection",
  "date_range": "last 7 days",
  "max_results": 50
}
```

### 7.3 Output

```json
{
  "papers": [
    {
      "title": "Paper title",
      "authors": ["Author A", "Author B"],
      "abstract": "Paper abstract",
      "published_date": "2026-04-30",
      "arxiv_id": "2604.xxxxx",
      "url": "https://arxiv.org/abs/2604.xxxxx",
      "categories": ["cs.SI", "cs.LG"]
    }
  ]
}
```

### 7.4 Required Functions

Suggested file: `skills/paper_retrieval/skill.py`

```python
class PaperRetrievalSkill:
    def run(self, input_data: dict) -> dict:
        pass

    def search_arxiv(self, query: str, max_results: int) -> list:
        pass

    def filter_by_date(self, papers: list, date_range: str) -> list:
        pass

    def parse_metadata(self, raw_paper) -> dict:
        pass

    def save_results(self, papers: list, output_path: str) -> None:
        pass
```

### 7.5 Implementation Tasks

- Use the arXiv API or the `arxiv` Python package.
- Support keyword search.
- Support `max_results`.
- Support simple date filtering such as `last 7 days` and `last 30 days`.
- Parse title, authors, abstract, published date, arXiv ID, URL, and categories.
- Clean abstracts by removing unnecessary line breaks and extra spaces.
- Save raw results to `data/raw/arxiv_papers.json`.
- Handle errors such as empty results, missing fields, or network issues.
- Provide an independent demo command.

### 7.6 Independent Demo

```bash
python skills/paper_retrieval/skill.py \
  --query "graph neural networks misinformation detection" \
  --max_results 50
```

### 7.7 Evaluation

Suggested evaluation metrics:

| Metric | Description |
|---|---|
| Fetch success rate | Whether the Skill returns valid paper results |
| Metadata completeness | Percentage of papers with all required fields |
| Query latency | Time used for retrieval |
| Number of returned papers | Number of papers after filtering |

---

## 8. Skill 2: Relevance Ranking & Filtering Skill

### 8.1 Purpose

This Skill ranks retrieved papers according to the user query and selects the Top-K most relevant papers.

### 8.2 Input

```json
{
  "query": "graph neural networks for misinformation detection",
  "papers": [
    {
      "title": "Paper title",
      "abstract": "Paper abstract",
      "categories": ["cs.SI", "cs.LG"]
    }
  ],
  "top_k": 5
}
```

### 8.3 Output

```json
{
  "ranked_papers": [
    {
      "title": "Paper title",
      "abstract": "Paper abstract",
      "relevance_score": 0.87,
      "rank": 1,
      "ranking_reason": "This paper directly studies GNN-based misinformation detection."
    }
  ],
  "top_k_papers": []
}
```

### 8.4 Required Functions

Suggested file: `skills/relevance_ranking/skill.py`

```python
class RelevanceRankingSkill:
    def run(self, input_data: dict) -> dict:
        pass

    def build_document_text(self, paper: dict, mode: str = "title_abstract") -> str:
        pass

    def rank_with_tfidf(self, query: str, papers: list) -> list:
        pass

    def rank_with_sbert(self, query: str, papers: list) -> list:
        pass

    def apply_category_filter(self, papers: list, allowed_categories: list) -> list:
        pass

    def select_top_k(self, ranked_papers: list, top_k: int) -> list:
        pass
```

### 8.5 Implementation Tasks

- Convert each paper into a ranking document using `title + abstract`.
- Implement a TF-IDF + cosine similarity baseline.
- Implement a Sentence-BERT + cosine similarity method if possible.
- Support `top_k`.
- Support optional category filtering, such as `cs.SI`, `cs.LG`, `cs.CL`, and `stat.ML`.
- Output a relevance score for each paper.
- Generate a short ranking reason for Top-K papers.
- Save ranked results to `data/processed/ranked_papers.json`.

### 8.6 Independent Demo

```bash
python skills/relevance_ranking/skill.py \
  --input data/raw/arxiv_papers.json \
  --query "graph neural networks for misinformation detection" \
  --method tfidf \
  --top_k 5
```

### 8.7 Evaluation

Suggested evaluation metrics:

| Metric | Description |
|---|---|
| Precision@5 | Percentage of relevant papers in Top-5 |
| Precision@10 | Percentage of relevant papers in Top-10 |
| NDCG@5 | Ranking quality with graded relevance |
| NDCG@10 | Ranking quality with graded relevance |
| Ranking latency | Time used for ranking |

### 8.8 Suggested Ablation Study

| Setting | Description |
|---|---|
| TF-IDF | Keyword-based baseline |
| SBERT | Semantic embedding-based ranking |
| Title only | Rank using only paper titles |
| Title + Abstract | Rank using titles and abstracts |
| With category filter | Rank after filtering by arXiv category |
| Without category filter | Rank without category filtering |

---

## 9. Skill 3: Briefing Generation & Research Graph Analysis Skill

### 9.1 Purpose

This Skill generates structured summaries for Top-K papers, constructs a research keyword network, performs basic network analysis, and produces the final Markdown research briefing.

### 9.2 Input

```json
{
  "query": "graph neural networks for misinformation detection",
  "top_k_papers": [
    {
      "title": "Paper title",
      "abstract": "Paper abstract",
      "authors": ["Author A"],
      "url": "https://arxiv.org/abs/xxxx.xxxxx",
      "relevance_score": 0.87
    }
  ]
}
```

### 9.3 Output

```json
{
  "report_markdown": "outputs/reports/daily_briefing.md",
  "summaries": [
    {
      "title": "Paper title",
      "one_sentence_summary": "This paper studies ...",
      "problem": "...",
      "method": "...",
      "contribution": "...",
      "experiment_or_evidence": "...",
      "limitation": "Not mentioned in abstract"
    }
  ],
  "graph_analysis": {
    "num_nodes": 20,
    "num_edges": 45,
    "density": 0.23,
    "central_keywords": [],
    "communities": []
  },
  "figures": [
    "outputs/figures/keyword_graph.png",
    "outputs/figures/top_keywords.png"
  ]
}
```

### 9.4 Required Functions

Suggested file: `skills/briefing_graph/skill.py`

```python
class BriefingGraphSkill:
    def run(self, input_data: dict) -> dict:
        pass

    def generate_structured_summary(self, paper: dict) -> dict:
        pass

    def extract_keywords(self, papers: list) -> dict:
        pass

    def build_keyword_graph(self, paper_keywords: dict):
        pass

    def analyze_graph(self, graph) -> dict:
        pass

    def visualize_graph(self, graph, output_path: str) -> None:
        pass

    def generate_markdown_report(
        self,
        query: str,
        papers: list,
        summaries: list,
        graph_analysis: dict
    ) -> str:
        pass
```

### 9.5 Implementation Tasks

#### A. Structured Paper Summaries

For each Top-K paper, generate a research card containing:

- one-sentence summary;
- problem;
- method;
- key contribution;
- experiment or evidence;
- limitation.

Important rule:

```text
If the abstract does not mention a field, write "Not mentioned in abstract".
Do not invent information that is not supported by the title or abstract.
```

#### B. Keyword Co-occurrence Graph

Build a keyword network from retrieved papers.

- Node: keyword or research phrase.
- Edge: two keywords appear in the same paper.
- Edge weight: co-occurrence count.

Suggested keyword extraction methods:

- TF-IDF keywords;
- KeyBERT;
- RAKE;
- noun phrase extraction;
- simple controlled vocabulary for graph/social network topics.

#### C. Network Analysis

Use NetworkX to compute:

- number of nodes;
- number of edges;
- density;
- average degree;
- degree centrality;
- betweenness centrality;
- PageRank;
- communities using Louvain or Label Propagation.

#### D. Visualization

Generate at least one meaningful visualization:

- keyword co-occurrence network;
- top central keywords bar chart;
- community visualization.

Save figures to:

```text
outputs/figures/
```

#### E. Markdown Briefing

The final Markdown report should contain:

1. query and date;
2. number of retrieved papers;
3. Top-K paper table;
4. structured summaries;
5. top research keywords;
6. keyword graph analysis;
7. trend interpretation;
8. recommended reading order;
9. limitations.

### 9.6 Independent Demo

```bash
python skills/briefing_graph/skill.py \
  --input data/processed/ranked_papers.json \
  --top_k 5 \
  --output outputs/reports/daily_briefing.md
```

### 9.7 Evaluation

Suggested evaluation metrics:

| Metric | Description |
|---|---|
| Summary faithfulness | Whether the summary is supported by title/abstract |
| Summary completeness | Whether required fields are filled |
| Graph modularity | Quality of detected keyword communities |
| Central keyword quality | Whether top keywords are meaningful |
| Report completeness | Whether the report contains all required sections |

---

## 10. Agent Orchestrator

The Agent orchestrator integrates all three Skills into one pipeline.

Suggested file: `agent/orchestrator.py`

```python
from skills.paper_retrieval.skill import PaperRetrievalSkill
from skills.relevance_ranking.skill import RelevanceRankingSkill
from skills.briefing_graph.skill import BriefingGraphSkill

class DailyArxivBriefingAgent:
    def __init__(self):
        self.retrieval_skill = PaperRetrievalSkill()
        self.ranking_skill = RelevanceRankingSkill()
        self.briefing_skill = BriefingGraphSkill()

    def run(self, user_input: dict) -> dict:
        retrieval_output = self.retrieval_skill.run(user_input)

        ranking_output = self.ranking_skill.run({
            "query": user_input["query"],
            "papers": retrieval_output["papers"],
            "top_k": user_input.get("top_k", 5)
        })

        briefing_output = self.briefing_skill.run({
            "query": user_input["query"],
            "top_k_papers": ranking_output["top_k_papers"]
        })

        return {
            "retrieval": retrieval_output,
            "ranking": ranking_output,
            "briefing": briefing_output
        }
```

---

## 11. Main Program

Suggested file: `main.py`

```python
import argparse
from agent.orchestrator import DailyArxivBriefingAgent

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", type=str, required=True)
    parser.add_argument("--date_range", type=str, default="last 7 days")
    parser.add_argument("--max_results", type=int, default=50)
    parser.add_argument("--top_k", type=int, default=5)
    return parser.parse_args()

def main():
    args = parse_args()

    user_input = {
        "query": args.query,
        "date_range": args.date_range,
        "max_results": args.max_results,
        "top_k": args.top_k
    }

    agent = DailyArxivBriefingAgent()
    output = agent.run(user_input)

    print("Daily arXiv Research Briefing generated successfully.")
    print("Report path:", output["briefing"]["report_markdown"])

if __name__ == "__main__":
    main()
```

---

## 12. Data Format

### 12.1 Raw Paper JSON

Saved by Skill 1:

```text
data/raw/arxiv_papers.json
```

Format:

```json
{
  "papers": [
    {
      "title": "...",
      "authors": ["..."],
      "abstract": "...",
      "published_date": "...",
      "arxiv_id": "...",
      "url": "...",
      "categories": ["cs.SI", "cs.LG"]
    }
  ]
}
```

### 12.2 Ranked Paper JSON

Saved by Skill 2:

```text
data/processed/ranked_papers.json
```

Format:

```json
{
  "ranked_papers": [
    {
      "title": "...",
      "abstract": "...",
      "relevance_score": 0.87,
      "rank": 1,
      "ranking_reason": "..."
    }
  ],
  "top_k_papers": []
}
```

### 12.3 Final Report

Saved by Skill 3:

```text
outputs/reports/daily_briefing.md
```

---

## 13. Testing Plan

### 13.1 Unit Tests

Each Skill should have its own test file.

```bash
python skills/paper_retrieval/test_retrieval.py
python skills/relevance_ranking/test_ranking.py
python skills/briefing_graph/test_briefing_graph.py
```

### 13.2 Integration Test

Test the complete Agent pipeline:

```bash
python tests/test_agent.py
```

### 13.3 Suggested Test Queries

```text
graph neural networks for misinformation detection
community detection in social networks
link prediction with graph neural networks
influence maximization in social networks
social recommendation systems
```

---

## 14. Evaluation Plan

The project should include both system-level and Skill-level evaluation.

### 14.1 System-Level Evaluation

| Evaluation Item | Description |
|---|---|
| End-to-end success | Whether the Agent can complete the full pipeline |
| Report completeness | Whether the final report contains all required sections |
| Runtime | Total time from query to report |
| Visualization quality | Whether generated figures are meaningful |

### 14.2 Skill-Level Evaluation

| Skill | Evaluation |
|---|---|
| Paper Retrieval | Fetch success rate, metadata completeness, query latency |
| Ranking | Precision@5, Precision@10, NDCG@5, NDCG@10 |
| Briefing & Graph | Summary faithfulness, graph modularity, central keyword quality |

### 14.3 Manual Relevance Labeling

For ranking evaluation, manually label Top-10 papers for each query:

```text
2 = highly relevant
1 = partially relevant
0 = irrelevant
```

Then compute Precision@K and NDCG@K.

---

## 15. Suggested Minimum Viable Product

The minimum viable system should support the following:

1. user inputs a research query;
2. Skill 1 retrieves recent arXiv papers;
3. Skill 2 ranks papers by relevance;
4. Skill 2 selects Top-5 papers;
5. Skill 3 generates structured summaries;
6. Skill 3 builds a keyword co-occurrence graph;
7. Skill 3 generates a Markdown briefing;
8. the Agent runs the complete pipeline from one command;
9. each Skill can run independently;
10. at least one meaningful visualization is generated.

---

## 16. Final Project Deliverables

The group should submit:

1. Group report, 4 pages, NeurIPS format.
2. Individual report, 3 pages per member, NeurIPS format.
3. Code submission: Agent and all Skills published to StudyClawHub.
4. Presentation during Week 14.

Each individual report should focus on the member's own Skill.

The group report should focus on the overall Agent design, Skill integration, evaluation, analysis, and visualization.

---

## 17. Suggested Demo Script

Run:

```bash
python main.py \
  --query "graph neural networks for misinformation detection in social networks" \
  --date_range "last 7 days" \
  --max_results 50 \
  --top_k 5
```

Show the following outputs:

1. retrieved paper count;
2. Top-5 ranked papers;
3. relevance scores;
4. structured paper summaries;
5. keyword co-occurrence network;
6. top central keywords;
7. final Markdown briefing.

---

## 18. Future Improvements

Possible extensions:

- add citation network analysis;
- add author collaboration network;
- personalize ranking based on user reading history;
- add novelty score for each paper;
- support full-PDF parsing instead of abstract-only summaries;
- support daily scheduled briefing;
- support interactive follow-up questions;
- export report to HTML or PDF;
- add web UI with Streamlit or Gradio.

---

## 19. StudyClawHub Submission Notes

Each member should publish one Skill:

1. `Paper Retrieval & Metadata Parsing Skill`
2. `Relevance Ranking & Filtering Skill`
3. `Briefing Generation & Research Graph Analysis Skill`

The group should also publish the integrated Agent:

```text
Daily arXiv Research Briefing Agent
```

For each Skill and Agent, prepare metadata:

- name;
- description;
- version;
- tags;
- GitHub repository URL;
- author;
- input format;
- output format;
- example usage.

---

## 20. License

This project is for educational use in Social Network Analysis, Spring 2026.
