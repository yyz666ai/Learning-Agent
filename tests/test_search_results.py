import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("lesson_web_search", Path(__file__).parents[1] / "workspace/dev/tools/web_search.py")
search = importlib.util.module_from_spec(spec)
spec.loader.exec_module(search)


def test_does_not_return_first_planning_message():
    result = search.extract_search_result({"status": "completed", "output": [
        {"type": "message", "content": [{"type": "output_text", "text": "I'll research this. Let me search."}]},
        {"type": "message", "content": [{"type": "output_text", "text": "Go docs https://go.dev/doc/ explain installation and modules."}]},
    ]})
    assert result.startswith("Go docs")
    assert "I'll research" not in result


def test_no_sources_and_incomplete_results_are_explicit_failures():
    assert search.extract_search_result({"status":"completed", "output":[{"type":"message","content":[{"type":"output_text","text":"Let me search."}]}]}).startswith("[搜索失败]")
    assert search.extract_search_result({"status":"incomplete","output":[]}).startswith("[搜索失败]")
