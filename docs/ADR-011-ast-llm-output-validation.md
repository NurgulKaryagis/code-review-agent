# ADR-011: AST vs LLM Output Semantic Validation

**Status:** Accepted

**Context:** The `code_analyst` node runs both deterministic AST analysis (`ast.parse`) and LLM-based analysis on the same file. The two can produce conflicting results: the AST reports 5 functions and high complexity, while the LLM reports 1 function and low severity. When this happens, downstream nodes (`implementation`, `judge`) receive incorrect metadata that leads to wrong refactoring decisions. LLM hallucination is the primary cause — models sometimes generate plausible-sounding but factually wrong numbers.

**Rejected Alternatives:**

- *Trust LLM output unconditionally:* Simpler — only one source of truth. But LLMs hallucinate numeric values (function counts, severity scores) more often than they hallucinate code structure, making this unreliable for metadata fields.
- *Trust AST unconditionally, discard LLM metadata:* Safe but wastes the LLM's architectural pattern detection and dependency mapping, which AST cannot provide.
- *Average or blend the two:* Ambiguous for categorical fields like `severity`. Averaging `"high"` and `"low"` has no clear meaning.

**Decision:** `validate_llm_output` in `agent/tools/security.py` compares three fields between AST and LLM output: `function_count` (exact match required), `severity` (conflict flagged when ranks differ by 2 or more on a 4-level scale), and `issues` (conflict flagged when AST-detected issues are entirely absent from LLM output). When a conflict is detected, a warning is logged and the AST value overwrites the LLM value for that field. The LLM's non-overlapping contributions — `dependencies`, `patterns`, `architecture` — are kept unchanged. This implements a **trust hierarchy**: deterministic analysis wins over probabilistic analysis for fields where both produce a value.

**Consequences:** State fields that flow into downstream nodes (`analysis_results`) are always grounded in AST output for measurable properties. LLM hallucinations on function counts or severity are silently corrected with a warning rather than propagated. The conflict threshold for severity (rank difference ≥ 2) is a judgment call — a difference of 1 level (e.g., `low` vs `medium`) is tolerated to avoid excessive false positives from legitimate LLM disagreements with AST heuristics.