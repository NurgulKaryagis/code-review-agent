# ADR-004: LLM-as-Judge Before Human Review

**Status:** Accepted

**Context:** A developer reviewing the agent's suggested changes has no automated baseline to assess quality. Without a quality signal, the developer must read the full diff to decide whether to approve — which defeats the purpose of an automated review tool. At the same time, the agent's suggestions can be subtly wrong: syntactically valid but logically incorrect, or missing one of the identified issues.

**Rejected Alternatives:**

- *No quality gate:* Present the suggested code directly to the developer with no score. The developer becomes the sole quality filter, which increases cognitive load and the likelihood of approving a poor suggestion.
- *Rule-based validation:* Check that suggestion length is within bounds, that file names match, that no syntax errors exist. This catches format issues but cannot assess whether the suggestion actually fixes the identified problems.
- *Post-approval validation:* Run the judge after the developer approves. By this point the patch may already have been applied to GitHub, making the feedback loop too late to be useful.

**Decision:** `judge_node` runs `judge_code_refactory` immediately after `review_node` and before `human_review_node`. The judge receives the original code, the revised code, and the list of identified issues, and returns a `score` between 0 and 1 with a `reasoning` string. Scores below 0.5 set `judge_status` to `"warning"`. Both `judge_scores` and `judge_status` are included in the `/webhook` response, giving the developer a quality signal before they call `/approve`.

**Consequences:** Developers approach the approval step with quantified context rather than raw diffs. The `reasoning` field explains what the judge assessed, helping developers catch cases where the judge itself is wrong. The cost is one additional LLM call per reviewed file, adding latency and API spend proportional to the number of changed files.
