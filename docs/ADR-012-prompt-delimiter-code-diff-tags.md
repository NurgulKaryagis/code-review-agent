# ADR-012: Code Isolation with `<code_diff>` Delimiter Tags

**Status:** Accepted

**Context:** Every LLM prompt in this system contains two kinds of content: trusted instructions written by the developer, and untrusted user-supplied content (the code diff from the GitHub PR). Without a clear boundary between them, the model cannot reliably distinguish where instructions end and data begins. This ambiguity is what makes prompt injection effective — the model treats the attacker's text as a continuation of the developer's instructions.

**Rejected Alternatives:**

- *No delimiter:* Concatenate instructions and code diff as plain text. The model has no structural signal to separate data from instructions. Injection attacks are maximally effective in this setup.
- *Markdown code fences (` ``` `):* Widely recognised by models but also widely used in legitimate code, making them easy to escape. A diff containing ` ``` ` closes the fence prematurely and resumes in instruction context.
- *Base64-encode the diff:* Prevents injection completely since instructions cannot survive encoding. But the model cannot read base64 as code — all code-level reasoning (pattern detection, issue identification) is lost.

**Decision:** All prompts that include user-supplied code use `<code_diff>` XML-style tags to wrap the content. The tags are applied consistently in `config/prompts.py` for every prompt that accepts a code argument (`get_code_analyst_prompts`, `get_implementation_prompts`, `get_test_agent_prompts`, `get_security_agent_prompts`, `get_review_prompts`). Each system prompt that uses these tags includes a statement that content inside `<code_diff>` is user-provided source code to be analysed as data, not followed as instructions. This is the delimiter layer of a defence-in-depth strategy: it does not replace injection detection (ADR-010) but reduces the attack surface for injections that evade regex detection.

**Consequences:** Models with instruction-following training respond well to XML-style delimiters — they treat tagged content as data more reliably than undelimited text. The tags must be applied consistently; a prompt that omits them for one code argument while using them for others creates an inconsistent boundary that weakens the protection. The `<code_diff>` tag name is meaningful: it signals to the model what type of content to expect, which also improves analysis quality independent of the security benefit.