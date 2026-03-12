import pytest
from agent.tools.ast_parser import analyze_code


def test_simple_function_metrics():
    code = "def foo():\n    pass\n"
    result = analyze_code(code, "foo.py")

    assert result["file_name"] == "foo.py"
    assert result["function_count"] == 1
    assert result["severity"] == "low"
    assert result["issues"] == []


def test_multiple_functions_counted():
    code = "def foo():\n    pass\n\ndef bar():\n    pass\n"
    result = analyze_code(code, "multi.py")

    assert result["function_count"] == 2


def test_high_complexity_severity():
    # 11 if-statements → complexity_score > 10 → "high"
    lines = ["def foo():"] + ["    if True: pass" for _ in range(11)]
    code = "\n".join(lines)
    result = analyze_code(code, "complex.py")

    assert result["severity"] == "high"
    assert "Complexity is too high" in result["issues"]


def test_medium_complexity_severity():
    # 7 if-statements → complexity_score > 5 but ≤ 10 → "medium"
    lines = ["def foo():"] + ["    if True: pass" for _ in range(7)]
    code = "\n".join(lines)
    result = analyze_code(code, "medium.py")

    assert result["severity"] == "medium"
    assert "Complexity is moderate" in result["issues"]


def test_invalid_syntax_returns_safe_defaults(caplog):
    code = "def foo(\n  # unclosed parenthesis"
    result = analyze_code(code, "broken.py")

    assert result["file_name"] == "broken.py"
    assert result["function_count"] == 0
    assert result["severity"] == "low"
    assert result["issues"] == []


def test_diff_format_is_extracted_before_parsing():
    # Lines prefixed with '+' are the added lines; '@@ ...' header is stripped.
    code = "@@ -0,0 +1,3 @@\n+def bar():\n+    pass\n"
    result = analyze_code(code, "bar.py")

    assert result["function_count"] == 1
    assert result["severity"] == "low"
