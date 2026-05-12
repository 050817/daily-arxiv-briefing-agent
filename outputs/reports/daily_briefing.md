# Daily arXiv Research Briefing

- Query: all:harness
- Generated at: 2026-05-12 02:54 UTC
- Papers included: 5
- Evidence policy: summaries use only paper titles and abstracts; unsupported fields say "Not mentioned in abstract".

## Top Papers

| Rank | Title | Score | Categories | Link |
|---:|---|---:|---|---|
| 1 | Continual Harness: Online Adaptation for Self-Improving Foundation Agents | 0.1136 | cs.LG, cs.AI | [arXiv](https://arxiv.org/abs/2605.09998v1) |
| 2 | Metal-Sci: A Scientific Compute Benchmark for Evolutionary LLM Kernel Search on Apple Silicon | 0.0569 | cs.LG, cs.AI, cs.DC | [arXiv](https://arxiv.org/abs/2605.09708v1) |
| 3 | SkillMAS: Skill Co-Evolution with LLM-based Multi-Agent System | 0.0179 | cs.MA, cs.CL | [arXiv](https://arxiv.org/abs/2605.09341v1) |
| 4 | Workspace Optimization: How to Train Your Agent | 0.0169 | cs.AI, cs.LG | [arXiv](https://arxiv.org/abs/2605.09650v1) |
| 5 | Towards Generalist Game Players: An Investigation of Foundation Models in the Game Multiverse | 0.0135 | cs.CV | [arXiv](https://arxiv.org/abs/2605.09965v1) |

## Structured Summaries

### 1. Continual Harness: Online Adaptation for Self-Improving Foundation Agents

- One-sentence summary: The paper introduces Continual Harness, a reset-free online self-improving harness for embodied agents that alternates between acting and refining its own prompt, sub-agents, skills, and memory using past trajectory data.
- Topic relevance: Highly relevant because the query is "all:harness" and the title and abstract center on coding harnesses and the proposed Continual Harness.
- Problem: The abstract states that while coding harnesses wrap foundation models with tools, memory, and planning, no equivalent exists for embodied agents' long-horizon partial-observability decision-making.
- Method: Continual Harness is described as a reset-free self-improving harness for embodied agents that, starting from only a minimal environment interface, alternates between acting and refining its own prompt, sub-agents, skills, and memory, drawing on past trajectory data; the paper also describes an online process-reward co-learning loop where an open-source agent's rollouts are relabeled by a frontier teacher and used to update the model.
- Contribution: The paper reports Gemini Plays Pokemon experiments, states that GPP became the first AI system to complete Pokemon Blue, Yellow Legacy on hard mode, and Crystal without a lost battle under iterative human-in-the-loop harness refinement, and then presents Continual Harness as an automated version that removes the human from the refinement loop for embodied agents.
- Experiment or evidence: Evidence in the abstract includes GPP experiments with iterative human-in-the-loop harness refinement; results on Pokemon Red and Emerald across frontier models where Continual Harness from scratch substantially reduces button-press cost relative to a minimalist baseline and recovers a majority of the gap to a hand-engineered expert harness; and an online process-reward co-learning loop that drives sustained in-game milestone progress on Pokemon Red without resetting the environment between training iterations.
- Limitation: Not mentioned in abstract

### 2. Metal-Sci: A Scientific Compute Benchmark for Evolutionary LLM Kernel Search on Apple Silicon

- One-sentence summary: Metal-Sci is a 10-task benchmark and lightweight harness for automatic Apple Silicon Metal kernel search, paired with held-out generalization scoring to evaluate and oversee LLM-driven evolutionary optimization.
- Topic relevance: Highly relevant to the query "all:harness" because the abstract explicitly states that the benchmark is paired with "a lightweight harness for automatic kernel search."
- Problem: The paper addresses how to benchmark and automatically search for optimized scientific Apple Silicon Metal compute kernels, while also detecting cases where in-distribution search performance hides incorrect or non-generalizing results.
- Method: The authors present a 10-task benchmark spanning six optimization regimes, where each task includes a CPU reference, a roofline-anchored fitness function, and a held-out generalization size, and pair it with a lightweight harness that runtime-compiles candidate kernels, scores them against the roofline across multiple sizes, and feeds structured compile and per-size correctness diagnostics back to a frozen LLM driving a (1+1) evolutionary loop.
- Contribution: The paper contributes Metal-Sci as a scientific compute benchmark for Apple Silicon Metal kernels, a lightweight harness for automatic kernel search, and a methodological claim that the held-out gate scoring function Φ_T can serve as a cheap mechanical oversight primitive for the search loop.
- Experiment or evidence: The abstract reports matched single-model sweeps of Claude Opus 4.7, Gemini 3.1 Pro, and GPT 5.5 on M1 Pro, with in-distribution self-speedups spanning 1.00× to 10.7×, and gives examples where the held-out gate catches failures: an Opus HMC kernel that returns wrong samples at unseen dimensions and a GPT FFT3D result that achieves 2.95× in-distribution speedup but drops to 0.23× on a 256^3 held-out cube.
- Limitation: Not mentioned in abstract

### 3. SkillMAS: Skill Co-Evolution with LLM-based Multi-Agent System

- One-sentence summary: SkillMAS is a non-parametric framework for LLM-based multi-agent systems that couples skill evolution with system restructuring to support adaptive post-deployment specialization.
- Topic relevance: Relevant to the query because the abstract explicitly states that SkillMAS is competitive "under the reported harnesses."
- Problem: Existing work often decouples skill evolution and multi-agent system restructuring, which the abstract says can create organization bottlenecks, context pressure, and mis-specialization.
- Method: SkillMAS couples skill evolution with MAS restructuring, using Utility Learning to assign credit from verified execution traces, bounded skill evolution to refine reusable procedures without unfiltered library growth, and evidence-gated MAS restructuring when retained failures and Executor Utility indicate a structural mismatch.
- Contribution: The paper presents SkillMAS, a non-parametric framework for adaptive specialization in multi-agent systems that links how post-deployment specialization is attributed, updated, and applied.
- Experiment or evidence: The abstract reports results across embodied manipulation, command-line execution, and retail workflows, stating that SkillMAS is competitive under the reported harnesses.
- Limitation: Not mentioned in abstract

### 4. Workspace Optimization: How to Train Your Agent

- One-sentence summary: The paper argues that when frontier language-model agents cannot adapt their weights, their structured external workspace can be optimized through interaction, and instantiates this idea in a multi-agent harness called DreamTeam for ARC-AGI-3.
- Topic relevance: Highly relevant to the query because the abstract explicitly describes DreamTeam as "a multi-agent harness for ARC-AGI-3."
- Problem: Modern agents built on frontier language models often cannot adapt their weights, creating a need for another trainable component in hard multi-turn environments where the agent must learn through interaction rather than solve the task in a single shot.
- Method: The paper proposes workspace optimization, which evolves the agent's structured external workspace that it reads, writes, and tests, using a scheme that mirrors weight-space training: artifacts in place of parameters, evidence in place of data, counterexamples in place of losses, and textual feedback in place of gradients; this is instantiated in DreamTeam, whose roles build an executable world model, plan, hypothesize, probe, strategize, and route failures.
- Contribution: The paper introduces the concept of workspace optimization as a principled way to train agents through their external workspace and presents DreamTeam as an instantiation of this idea for ARC-AGI-3.
- Experiment or evidence: On the current 25-game ARC-AGI-3 public set under the official scoring protocol and averaged over two independent runs, DreamTeam improves the score of the SOTA protocol-matched agent from 36% to 38.4% while using 31% fewer environment actions per game.
- Limitation: Not mentioned in abstract

### 5. Towards Generalist Game Players: An Investigation of Foundation Models in the Game Multiverse

- One-sentence summary: The paper presents a unified view of generalist game players based on foundation models, organizing the field around Dataset, Model, Harness, and Benchmark and outlining a roadmap from single-game mastery to a creator stage in a game multiverse.
- Topic relevance: Highly relevant to the query because the abstract explicitly identifies "Harness" as one of the four interdependent pillars of generalist game players.
- Problem: The abstract frames the problem as how to understand and advance generalist game players that can generalize across a multiverse of games with different rules, aesthetics, physics, and objectives, in support of progress toward AGI.
- Method: The paper traces the full lifecycle of a generalist game player across four interdependent pillars: Dataset, Model, Harness, and Benchmark, and interprets advances across these pillars as attempts to break five fundamental trade-offs.
- Contribution: The abstract claims a unified lens on the field, identifies four pillars and five fundamental trade-offs, and charts a five-level roadmap from single-game mastery to a creator stage where the agent creates and evolves within the theoretical game multiverse.
- Experiment or evidence: Evidence in the abstract consists of a conceptual synthesis of the field's four eras and an end-to-end framework with pillars, trade-offs, and roadmap; no empirical experiments or quantitative results are mentioned in the abstract.
- Limitation: Not mentioned in abstract

## Keyword Network Analysis

- Nodes: 41
- Edges: 180
- Density: 0.2195
- Average degree: 8.7805

### Central Keywords

| Keyword | Paper Count | Weighted Degree |
|---|---:|---:|
| harness | 5 | 40 |
| agent | 1 | 8 |
| agent system | 1 | 8 |
| agent systems | 1 | 8 |
| agents | 1 | 8 |
| arc agi | 1 | 8 |
| benchmark | 1 | 8 |
| cannot | 1 | 8 |
| continual harness | 1 | 8 |
| creator stage | 1 | 8 |

### Keyword Communities

- Community 1 (41 keywords): agent, agent system, agent systems, agents, arc agi, benchmark, cannot, continual harness, creator stage, deployment, distribution, dreamteam

## Trend Interpretation

The most connected extracted topics are harness, agent, agent system, agent systems, agents. This indicates recurring vocabulary in the selected abstracts, not a claim about the broader arXiv corpus.

## Recommended Reading Order

1. Continual Harness: Online Adaptation for Self-Improving Foundation Agents - Matches query terms in the title: harness.
2. Metal-Sci: A Scientific Compute Benchmark for Evolutionary LLM Kernel Search on Apple Silicon - Matches query terms in the abstract: all, harness.
3. SkillMAS: Skill Co-Evolution with LLM-based Multi-Agent System - Matches query terms in the abstract: harness.
4. Workspace Optimization: How to Train Your Agent - Matches query terms in the abstract: harness.
5. Towards Generalist Game Players: An Investigation of Foundation Models in the Game Multiverse - Matches query terms in the abstract: harness.

## Figures

- outputs/figures/keyword_graph.svg
- outputs/figures/top_keywords.svg

## Limitations

- This report only uses title, abstract, metadata, and ranking fields supplied to Skill 3.
- It does not read full PDFs, citations, experiments, or external web pages.
- Keyword communities are based on co-occurrence in the selected Top-K papers, so they are descriptive rather than causal.
