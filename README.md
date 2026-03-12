# Code Review & Refactor Agent

An AI-powered code review agent that automatically analyzes GitHub pull requests, generates refactoring suggestions, and applies patches upon human approval.

---

## What It Does

The AI-powered code review agent provides automatic code analysis for pull requests and suggests refactoring when necessary. When a PR is opened, the agentic workflow is triggered, generates refactoring suggestions, and evaluates them with LLM-as-Judge before asking for developer approval.

---

## Architecture

The workflow follows a sequential structure where each node depends on the output of the previous one. Code differences are first analyzed by the analyze node, which extracts metrics and identifies issues. The suggestion node then generates refactoring recommendations based on the analysis. Before reaching the developer, the judge node evaluates the suggestion quality using LLM-as-Judge and assigns a score. The human review node pauses the workflow and waits for developer approval via HITL. If approved, the patch node commits and pushes the accepted refactoring to the branch.

```
START → analyze → suggestion → judge → human_review → patch → END
```

---

## Tech Stack

| Tool | Purpose |
|------|---------|
| LangGraph | Agent orchestration — state management, conditional edges, HITL |
| LiteLLM | Unified LLM interface — model switching without code changes |
| LangSmith | Tracing and observability — node-level debugging and latency monitoring |
| FastAPI | Webhook server — receives GitHub PR events and approval requests |
| PyGithub | GitHub API integration — fetches PR files and applies patches |

---

## Project Structure
```
code-review-agent/
├── agent/
│   ├── graph.py
│   ├── nodes.py
│   ├── state.py
│   └── tools/
├── api/
├── eval/
├── config/
├── tests/
└── docs/
```

---

## Setup

### Requirements
- Python 3.11+

### Installation
```bash
git clone ...
cd code-review-agent
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file:
```
GITHUB_TOKEN=
OPENAI_API_KEY=
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=
LANGCHAIN_TRACING_V2=
```

---

## Usage

### 1. Start the server
```bash
uvicorn api.main:app --reload
```

### 2. Trigger a PR review
```bash
POST /webhook
```

Example payload:
```json
{
  "action": "opened",
  "pull_request": {
    "number": 1,
    "html_url": "https://github.com/..."
  }
}
```

### 3. Approve or reject
```bash
POST /approve?thread_id=xxx&approved=true
```

---

## How HITL Works

When the workflow reaches the `human_review_node`, `interrupt()` pauses the graph and saves the current state to the checkpointer. The workflow waits until a request is sent to the `/approve` endpoint with the corresponding `thread_id`. Once the developer approves or rejects via `Command(resume=True/False)`, the graph resumes from where it was paused.

---

## LLM-as-Judge

The `judge_node` evaluates the quality of refactoring suggestions before the human review step. It compares the original code with the suggested refactoring and assesses whether the identified issues are correctly addressed. The judge returns a score between 0 and 1 — scores below 0.5 trigger a warning, indicating that the suggestion may not fully resolve the issues. This gives the developer additional context before making an approval decision.

---

## Error Handling

| Failure | Strategy |
|---------|----------|
| LLM call failure | Retry with exponential backoff (max 3 attempts) |
| Structured output parsing failure | Retry with stricter prompt |
| Invalid credentials | Validated on startup |
| GitHub API failure | Error handling with descriptive messages |
| ast.parse() failure | Skip file with warning |
| Request timeout | Timeout parameter on all external calls |

---

## Retry Mechanism

The `analysis_node`, and `suggestion_node` include retry logic with exponential backoff (max 3 attempts). These nodes make external LLM API calls which are susceptible to transient failures such as network timeouts and rate limits. Retrying automatically prevents the entire workflow from failing due to a temporary API issue.

---

## LangSmith Tracing

Every node execution is automatically traced in LangSmith, including inputs, outputs, and latency. This makes it possible to identify which node failed, inspect the exact prompt sent to the LLM and the response received, and detect bottlenecks by comparing node latencies. Traces can be viewed at [smith.langchain.com](https://smith.langchain.com) under the configured project name.

---

## Testing
```bash
pytest tests/
```

Unit tests cover the core functions including `analyze_code`, `get_pr_files`, `apply_patch`, `judge_code_refactory`, and individual nodes. All external API calls to LLM and GitHub are mocked to ensure tests run without real API dependencies, making them fast, reliable, and cost-free.

---

## Architecture Decisions

See [docs/ADR.md](docs/ADR.md) for detailed architecture decision records.

---

## Known Limitations

- AST analysis only supports Python files — other languages are not parsed
- `MemorySaver` is used as checkpointer, which stores state in memory. Restarting the application loses all pending threads and HITL states. A persistent checkpointer such as PostgreSQL or Redis is required for production use
- File analysis is sequential — large PRs with many files will be slow due to single-threaded LLM calls

---

## What I Learned

- How to build an agentic workflow with LangGraph including state management, conditional edges, and loop control
- How to implement Human-in-the-loop using `interrupt()` and why it is critical for production-level AI systems
- How to trace and debug agent workflows with LangSmith by inspecting node inputs, outputs, and latency
- LLM outputs are not always reliable — structured output validation with Pydantic is necessary to prevent silent failures
- Error handling and retry mechanisms are essential in production systems to reduce failure rates and surface actionable error messages
- How to parse and analyze Python code structure using the built-in `ast` module