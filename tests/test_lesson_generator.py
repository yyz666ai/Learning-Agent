from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from backend.curriculum import curriculum_from_plan
from backend.lesson_generator import (
    generate_and_save_lesson,
    load_lesson_bundle,
    parse_lesson_response,
)

from tests.test_curriculum import GO_PLAN


def model_lesson_json(knowledge_point_id: str, title: str = "package main 的作用") -> str:
    return json.dumps(
        {
            "title": title,
            "language": "go",
            "practice_path": f"projects/go-course/{knowledge_point_id}",
            "completion_mode": "evidence",
            "completion_prompt": "请贴出 go run 的结果，并解释 package main。",
            "pages": [
                {"id": "intuition", "type": "explain", "title": "先理解程序入口", "markdown": "把 package main 想成程序的门牌。"},
                {"id": "example", "type": "example", "title": "看最小代码", "markdown": "读代码。", "code": "package main // 声明可运行程序包\nfunc main() {} // 程序从这里开始", "language": "go"},
                {"id": "check", "type": "check", "title": "确认理解", "question": "哪个包可以直接运行？", "options": [{"id": "a", "label": "package util"}, {"id": "b", "label": "package main"}]},
                {"id": "practice", "type": "practice", "title": "亲手运行", "markdown": "运行并保存输出。"},
                {"id": "mastery", "type": "mastery", "title": "提交本课成果", "markdown": "现在提交证据。"},
            ],
            "answer_keys": {"check": "b"},
        },
        ensure_ascii=False,
    )


def test_generator_prompt_contains_profile_point_prerequisites_evidence_and_time(tmp_path: Path) -> None:
    curriculum = curriculum_from_plan(GO_PLAN, topic="Go", route="foundation_engineer", level="zero")
    captured: dict[str, str] = {}

    def fake_model(prompt: str) -> str:
        captured["prompt"] = prompt
        return model_lesson_json(curriculum.current_knowledge_point_id)

    bundle = generate_and_save_lesson(
        tmp_path,
        "learner",
        curriculum=curriculum,
        profile="零基础；喜欢边做边学",
        recent_evidence=["上一题把编译和运行混淆了"],
        session_minutes=25,
        model_call=fake_model,
    )

    prompt = captured["prompt"]
    assert curriculum.current_knowledge_point_id in prompt
    assert "零基础" in prompt
    assert "上一题把编译和运行混淆了" in prompt
    assert "25 分钟" in prompt
    assert "adaptive-lesson-flow" in prompt
    assert "knowledge-curator" in prompt
    assert "concept-teaching" in prompt
    assert "先读取上述 Skill" in prompt
    assert "不要扫描用户历史、知识库或其他文件" in prompt
    assert bundle.manifest.knowledge_point_id == curriculum.current_knowledge_point_id
    assert load_lesson_bundle(tmp_path, "learner", curriculum.current_knowledge_point_id) == bundle


def test_generator_builds_one_complete_chapter_and_discards_legacy_output_rules(tmp_path: Path) -> None:
    curriculum = curriculum_from_plan(GO_PLAN, topic="Go", route="foundation_engineer", level="zero")
    chapter = curriculum.current_chapter()
    payload = json.loads(model_lesson_json(curriculum.current_knowledge_point_id))
    payload["output_requirements"] = [
        {"id": "run", "label": "运行程序输出", "instruction": "粘贴 go run 的输出", "patterns": [r"Hello"]},
        {"id": "build", "label": "构建结果", "instruction": "粘贴 go build 的输出", "patterns": [r"^$"]},
    ]

    bundle = parse_lesson_response(
        json.dumps(payload, ensure_ascii=False), topic="Go", route="foundation_engineer",
        knowledge_point_id=curriculum.current_knowledge_point_id, session_minutes=25,
        chapter=chapter,
    )

    assert bundle.manifest.chapter_id == chapter.id
    assert bundle.manifest.covered_knowledge_point_ids == [point.id for point in chapter.knowledge_points]
    assert bundle.manifest.completion_mode == "self_practice"
    assert bundle.manifest.output_requirements == []


def test_parser_tolerates_string_null_and_counts_instructions_not_comment_lines_for_progression() -> None:
    curriculum = curriculum_from_plan(GO_PLAN, topic="Go", route="foundation_engineer", level="zero")
    payload = json.loads(model_lesson_json(curriculum.current_knowledge_point_id))
    payload["pages"][0]["practice_kind"] = "null"
    payload["pages"][1]["code"] = """// main.go：第一个 Go 程序
// 声明这是可运行程序
package main

// 导入终端输出工具
import \"fmt\"

// 程序从 main 开始
func main() {
    // 打印问候语
    fmt.Println(\"你好，Go\")
}"""

    bundle = parse_lesson_response(
        json.dumps(payload, ensure_ascii=False),
        topic="Go",
        route="foundation_engineer",
        knowledge_point_id=curriculum.current_knowledge_point_id,
        session_minutes=25,
        chapter=curriculum.current_chapter(),
    )

    assert bundle.manifest.pages[0].practice_kind is None
    assert "程序从 main 开始" in bundle.manifest.pages[1].code
    assert bundle.manifest.output_patterns == []


def test_generated_legacy_output_requirement_is_not_exposed_to_the_learner() -> None:
    curriculum = curriculum_from_plan(GO_PLAN, topic="Go", route="foundation_engineer", level="zero")
    payload = json.loads(model_lesson_json(curriculum.current_knowledge_point_id))
    payload["output_requirements"] = [{
        "id": "run_success", "label": "运行输出", "instruction": "粘贴输出", "patterns": [r"Hello"],
    }]

    bundle = parse_lesson_response(
        json.dumps(payload, ensure_ascii=False), topic="Go", route="foundation_engineer",
        knowledge_point_id=curriculum.current_knowledge_point_id, session_minutes=25,
        chapter=curriculum.current_chapter(),
    )

    assert bundle.manifest.completion_mode == "self_practice"
    assert bundle.manifest.output_requirements == []


def test_complete_chapter_rejects_a_deck_too_short_to_cover_its_points() -> None:
    curriculum = curriculum_from_plan(GO_PLAN, topic="Go", route="foundation_engineer", level="zero")
    payload = json.loads(model_lesson_json(curriculum.current_knowledge_point_id))
    payload["pages"] = [payload["pages"][0], payload["pages"][2], payload["pages"][3], payload["pages"][4]]

    with pytest.raises(ValueError, match="too short"):
        parse_lesson_response(
            json.dumps(payload, ensure_ascii=False), topic="Go", route="foundation_engineer",
            knowledge_point_id=curriculum.current_knowledge_point_id, session_minutes=25,
            chapter=curriculum.current_chapter(),
        )


@pytest.mark.parametrize("bad_reference", ["运行 go run hello.go", "在 $USER_DIR/workspace/demos 中运行"])
def test_generated_chapter_rejects_unavailable_file_or_placeholder_paths(bad_reference: str) -> None:
    curriculum = curriculum_from_plan(GO_PLAN, topic="Go", route="foundation_engineer", level="zero")
    payload = json.loads(model_lesson_json(curriculum.current_knowledge_point_id))
    payload["pages"][3]["markdown"] = bad_reference

    with pytest.raises(ValueError, match="filename|placeholder"):
        parse_lesson_response(
            json.dumps(payload, ensure_ascii=False), topic="Go", route="foundation_engineer",
            knowledge_point_id=curriculum.current_knowledge_point_id, session_minutes=25,
            chapter=curriculum.current_chapter(),
        )


def test_model_lesson_has_adaptive_completion_contract() -> None:
    payload = parse_lesson_response(
        model_lesson_json("package-main"),
        topic="Go",
        route="foundation_engineer",
        knowledge_point_id="package-main",
        session_minutes=25,
    )

    assert payload.manifest.completion_mode == "self_practice"
    assert payload.manifest.completion_actions == ["submit", "reteach", "stuck"]
    assert 3 <= len(payload.manifest.pages) <= 12
    assert payload.answer_keys == {"check": "b"}


def test_model_lesson_migrates_output_regex_to_optional_blank_homework() -> None:
    payload = json.loads(model_lesson_json("package-main"))
    payload["completion_mode"] = "output"
    payload["output_patterns"] = [r"Hello,\s+."]
    payload["practice_starter_mode"] = "blank"

    bundle = parse_lesson_response(
        json.dumps(payload, ensure_ascii=False), topic="Go", route="foundation_engineer",
        knowledge_point_id="package-main", session_minutes=25,
    )

    assert bundle.manifest.completion_mode == "self_practice"
    assert bundle.manifest.output_patterns == []
    assert bundle.manifest.output_requirements == []
    assert bundle.manifest.practice_starter_mode == "blank"


def test_code_lesson_becomes_self_practice_with_one_after_class_homework() -> None:
    payload = json.loads(model_lesson_json("package-main"))
    payload["completion_mode"] = "self_practice"
    payload["output_patterns"] = []
    payload["output_requirements"] = []
    payload["pages"][1]["code"] = (
        "package main // 声明这是可以直接运行的程序包\n"
        "func main() { // 程序从 main 函数开始执行\n"
        "}"
    )
    payload["pages"][3]["practice_kind"] = "homework"
    payload["pages"][3]["markdown"] = "课后独立完成：修改 main.go。提示：先找到 main 函数。"

    bundle = parse_lesson_response(
        json.dumps(payload, ensure_ascii=False), topic="Go", route="foundation_engineer",
        knowledge_point_id="package-main", session_minutes=25,
    )

    assert bundle.manifest.completion_mode == "self_practice"
    assert bundle.manifest.output_patterns == []
    assert bundle.manifest.output_requirements == []
    homework = [page for page in bundle.manifest.pages if page.practice_kind == "homework"]
    assert len(homework) == 1
    assert "//" in bundle.manifest.pages[1].code


def test_generated_lesson_prompt_requires_commented_code_and_optional_homework_not_output_checks() -> None:
    curriculum = curriculum_from_plan(GO_PLAN, topic="Go", route="foundation_engineer", level="zero")
    from backend.lesson_generator import build_lesson_prompt

    prompt = build_lesson_prompt(
        curriculum, profile="零基础", recent_evidence=[], session_minutes=25,
    )

    assert "详细中文注释" in prompt
    assert "practice_kind=homework" in prompt
    assert "completion_mode=`self_practice`" in prompt
    assert "不得生成 output_patterns" in prompt
    assert "**关键结论**" in prompt
    assert "==核心警告==" in prompt
    assert "不得滥用高亮" in prompt


def test_zero_beginner_first_chapter_prompt_requires_environment_setup_page() -> None:
    curriculum = curriculum_from_plan(GO_PLAN, topic="Go", route="foundation_engineer", level="zero")
    from backend.lesson_generator import build_lesson_prompt

    prompt = build_lesson_prompt(
        curriculum, profile="零基础；macOS", recent_evidence=[], session_minutes=25,
    )

    assert "本章必须在第一次运行代码前安排一张“环境准备”页" in prompt
    for requirement in (
        "需要下载的软件",
        "官方入口",
        "版本验证命令",
        "课程项目目录",
        "首次运行命令",
    ):
        assert requirement in prompt
    assert "不要猜测操作系统" in prompt


def test_generated_code_without_chinese_comments_is_rejected() -> None:
    payload = json.loads(model_lesson_json("package-main"))
    payload["pages"][1]["code"] = "package main\n\nfunc main() {\n    println(\"hello\")\n}"

    with pytest.raises(ValueError, match="Chinese comments"):
        parse_lesson_response(
            json.dumps(payload, ensure_ascii=False), topic="Go", route="foundation_engineer",
            knowledge_point_id="package-main", session_minutes=25,
        )


def test_generator_repairs_missing_chinese_comments_before_persisting(tmp_path: Path) -> None:
    curriculum = curriculum_from_plan(GO_PLAN, topic="Go", route="foundation_engineer", level="zero")
    payload = json.loads(model_lesson_json(curriculum.current_knowledge_point_id))
    payload["pages"][1]["code"] = 'package main\nimport "fmt"\nfunc main() {\n    fmt.Println("Hello")\n}'

    bundle = generate_and_save_lesson(
        tmp_path,
        "learner",
        curriculum=curriculum,
        profile="零基础",
        recent_evidence=[],
        session_minutes=25,
        model_call=lambda _prompt: json.dumps(payload, ensure_ascii=False),
    )

    code = bundle.manifest.pages[1].code
    assert "// 声明这是一个可以直接运行的程序包" in code
    assert "// 程序从 main 函数开始执行" in code


def test_generator_normalizes_common_model_answer_key_list_before_validation(tmp_path: Path) -> None:
    curriculum = curriculum_from_plan(GO_PLAN, topic="Go", route="foundation_engineer", level="zero")
    payload = json.loads(model_lesson_json(curriculum.current_knowledge_point_id))
    payload["answer_keys"] = [{"page_id": "check", "answer_id": "b"}]

    bundle = generate_and_save_lesson(
        tmp_path,
        "learner",
        curriculum=curriculum,
        profile="零基础",
        recent_evidence=[],
        session_minutes=25,
        model_call=lambda _prompt: json.dumps(payload, ensure_ascii=False),
    )

    assert bundle.answer_keys == {"check": "b"}


def test_first_long_code_dump_without_progressive_build_up_is_rejected() -> None:
    payload = json.loads(model_lesson_json("package-main"))
    payload["pages"][1]["code"] = "\n".join(
        ["package main // 声明程序包", "import \"fmt\" // 导入输出工具", "func main() { // 程序入口"]
        + [f"    fmt.Println({index}) // 展示第 {index} 个步骤" for index in range(1, 13)]
        + ["} // 程序结束"]
    )

    with pytest.raises(ValueError, match="progressive build-up"):
        parse_lesson_response(
            json.dumps(payload, ensure_ascii=False), topic="Go", route="foundation_engineer",
            knowledge_point_id="package-main", session_minutes=25,
        )


def test_lesson_prompt_receives_validated_research_evidence() -> None:
    curriculum = curriculum_from_plan(GO_PLAN, topic="Go", route="foundation_engineer", level="zero")
    from backend.lesson_generator import build_lesson_prompt

    prompt = build_lesson_prompt(
        curriculum,
        profile="零基础",
        recent_evidence=[],
        session_minutes=25,
        research_evidence="[spec] Go Specification：Go 的并发模型包含 goroutine 与 channel。",
    )

    assert "Go Specification" in prompt
    assert "goroutine" in prompt
    assert "研究依据" in prompt


def test_dense_chapter_accepts_more_than_twelve_progressive_pages() -> None:
    payload = json.loads(model_lesson_json("package-main"))
    extra_pages = [
        {"id": f"explain-{index}", "type": "explain", "title": f"拆解 {index}", "markdown": f"只讲第 {index} 个动作。"}
        for index in range(1, 9)
    ]
    payload["pages"] = payload["pages"][:-1] + extra_pages + [payload["pages"][-1]]

    bundle = parse_lesson_response(
        json.dumps(payload, ensure_ascii=False), topic="Go", route="foundation_engineer",
        knowledge_point_id="package-main", session_minutes=45,
    )

    assert len(bundle.manifest.pages) == 13


def test_loading_a_legacy_output_lesson_rewrites_old_submission_pages(tmp_path: Path) -> None:
    payload = json.loads(model_lesson_json("package-main"))
    payload["completion_mode"] = "output"
    payload["pages"][3]["markdown"] = "运行 main.go，把结果粘贴到输出框 1。"
    payload["pages"].insert(4, {
        "id": "second-practice", "type": "practice", "title": "再提交一次",
        "markdown": "把第二个结果粘贴到输出框 2。",
    })
    payload["pages"][-1]["title"] = "全部完成，逐项提交"
    payload["pages"][-1]["markdown"] = "两个输出框全部匹配才进入下一章。"
    bundle = parse_lesson_response(
        json.dumps(payload, ensure_ascii=False), topic="Go", route="foundation_engineer",
        knowledge_point_id="package-main", session_minutes=25,
    )
    saved = bundle.manifest.model_copy(update={
        "completion_mode": "output",
        "output_patterns": [r"成功"],
    })
    folder = tmp_path / "userdir/u_learner/lessons"
    folder.mkdir(parents=True)
    (folder / "package-main.json").write_text(saved.model_dump_json(), encoding="utf-8")
    (folder / "package-main.answers.json").write_text(json.dumps(bundle.answer_keys), encoding="utf-8")

    migrated = load_lesson_bundle(tmp_path, "learner", "package-main").manifest
    visible = "\n".join(f"{page.title}\n{page.markdown}" for page in migrated.pages)

    assert migrated.completion_mode == "self_practice"
    assert len([page for page in migrated.pages if page.practice_kind == "homework"]) == 1
    assert len([page for page in migrated.pages if page.type == "practice"]) == 1
    assert "输出框" not in visible
    assert migrated.pages[-1].title == "课堂讲完了，课后自己练"
    assert "//" in next(page.code for page in migrated.pages if page.code)


def test_loading_self_practice_lesson_enriches_legacy_code_with_chinese_comments(tmp_path: Path) -> None:
    payload = json.loads(model_lesson_json("package-main"))
    payload["completion_mode"] = "self_practice"
    payload["pages"][1]["code"] = "package main\n\nfunc main() {\n    println(\"hello\")\n}"
    payload["pages"][3]["practice_kind"] = "homework"
    folder = tmp_path / "userdir/u_learner/lessons"
    folder.mkdir(parents=True)
    (folder / "package-main.json").write_text(json.dumps({
        "lesson_id": "package-main-lesson",
        "title": "旧课",
        "topic": "Go",
        "language": "go",
        "route": "foundation_engineer",
        "knowledge_point_id": "package-main",
        "practice_path": "projects/go/package-main",
        "completion_mode": "self_practice",
        "completion_prompt": "课堂后自己练",
        "pages": payload["pages"],
        "progress": {"total_pages": len(payload["pages"]), "remaining_minutes": 25},
    }, ensure_ascii=False), encoding="utf-8")
    (folder / "package-main.answers.json").write_text(json.dumps(payload["answer_keys"]), encoding="utf-8")

    loaded = load_lesson_bundle(tmp_path, "learner", "package-main")

    code = next(page.code for page in loaded.manifest.pages if page.code)
    assert re.search(r"(?:#|//).*?[\u4e00-\u9fff]", code)


def test_loading_legacy_long_first_code_dump_requires_regeneration(tmp_path: Path) -> None:
    payload = json.loads(model_lesson_json("package-main"))
    payload["completion_mode"] = "self_practice"
    payload["pages"][1]["code"] = "\n".join(
        ["package main", "import \"fmt\"", "func main() {"]
        + [f"    fmt.Println({index})" for index in range(1, 13)]
        + ["}"]
    )
    payload["pages"][3]["practice_kind"] = "homework"
    folder = tmp_path / "userdir/u_learner/lessons"
    folder.mkdir(parents=True)
    (folder / "package-main.json").write_text(json.dumps({
        "lesson_id": "package-main-lesson",
        "title": "旧长课",
        "topic": "Go",
        "language": "go",
        "route": "foundation_engineer",
        "knowledge_point_id": "package-main",
        "practice_path": "projects/go/package-main",
        "completion_mode": "self_practice",
        "completion_prompt": "课堂后自己练",
        "pages": payload["pages"],
        "progress": {"total_pages": len(payload["pages"]), "remaining_minutes": 25},
    }, ensure_ascii=False), encoding="utf-8")
    (folder / "package-main.answers.json").write_text(json.dumps(payload["answer_keys"]), encoding="utf-8")

    with pytest.raises(ValueError, match="progressive build-up"):
        load_lesson_bundle(tmp_path, "learner", "package-main")


def test_meaning_only_concept_lesson_allows_choice_completion_without_outputs() -> None:
    payload = json.loads(model_lesson_json("rag-core"))
    payload["language"] = "custom"
    payload["completion_mode"] = "choice"
    payload["output_patterns"] = []
    payload["output_requirements"] = []
    payload["practice_path"] = "projects/rag-concept"
    payload["pages"] = [payload["pages"][0], payload["pages"][2], payload["pages"][-1]]

    bundle = parse_lesson_response(
        json.dumps(payload, ensure_ascii=False), topic="RAG 是什么", route="concept_clarity",
        knowledge_point_id="rag-core", session_minutes=15,
    )

    assert bundle.manifest.completion_mode == "choice"
    assert bundle.manifest.output_requirements == []
    assert bundle.manifest.output_patterns == []


def test_choice_only_concept_rejects_code_or_practice_pages() -> None:
    payload = json.loads(model_lesson_json("rag-core"))
    payload["language"] = "custom"
    payload["completion_mode"] = "choice"
    payload["output_patterns"] = []
    payload["output_requirements"] = []

    with pytest.raises(ValueError, match="choice-only"):
        parse_lesson_response(
            json.dumps(payload, ensure_ascii=False), topic="RAG 是什么", route="concept_clarity",
            knowledge_point_id="rag-core", session_minutes=15,
        )


def test_model_may_use_null_for_unused_optional_page_fields() -> None:
    payload = json.loads(model_lesson_json("rag-core"))
    payload["language"] = "python"
    payload["completion_mode"] = "choice"
    payload["output_patterns"] = []
    payload["output_requirements"] = []
    payload["pages"] = [payload["pages"][0], payload["pages"][2], payload["pages"][-1]]
    for page in payload["pages"]:
        page["code"] = None
        page["language"] = None
        if page["type"] != "check":
            page["question"] = None
            page["options"] = None

    bundle = parse_lesson_response(
        json.dumps(payload, ensure_ascii=False), topic="RAG 是什么", route="concept_clarity",
        knowledge_point_id="rag-core", session_minutes=15,
    )

    assert all(page.code == "" for page in bundle.manifest.pages)


def test_wrong_language_or_missing_mastery_page_is_rejected() -> None:
    wrong = json.loads(model_lesson_json("package-main"))
    wrong["language"] = "python"
    with pytest.raises(ValueError, match="language"):
        parse_lesson_response(json.dumps(wrong), topic="Go", route="foundation_engineer", knowledge_point_id="package-main", session_minutes=25)

    missing = json.loads(model_lesson_json("package-main"))
    missing["pages"] = missing["pages"][:-1]
    with pytest.raises(ValueError, match="mastery"):
        parse_lesson_response(json.dumps(missing), topic="Go", route="foundation_engineer", knowledge_point_id="package-main", session_minutes=25)


def test_content_language_label_is_normalized_to_the_programming_language() -> None:
    payload = json.loads(model_lesson_json("go-run"))
    payload["language"] = "zh"

    bundle = parse_lesson_response(
        json.dumps(payload, ensure_ascii=False),
        topic="Go",
        route="foundation_engineer",
        knowledge_point_id="go-run",
        session_minutes=25,
    )

    assert bundle.manifest.language == "go"


def test_common_model_option_and_file_path_variants_are_normalized() -> None:
    payload = json.loads(model_lesson_json("package-main"))
    payload["practice_path"] = "projects/go-course/package-main/main.go"
    payload["pages"][2]["options"] = ["A. package util", "B. package main"]
    payload["answer_keys"] = {"check": "B"}

    bundle = parse_lesson_response(
        json.dumps(payload, ensure_ascii=False), topic="Go", route="foundation_engineer",
        knowledge_point_id="package-main", session_minutes=25,
    )

    assert bundle.manifest.practice_path == "projects/go-course/package-main"
    assert [option.id for option in bundle.manifest.pages[2].options] == ["a", "b"]
    assert bundle.manifest.pages[2].options[1].label == "package main"
    assert bundle.answer_keys == {"check": "b"}


@pytest.mark.parametrize("mutation", ["missing", "unknown_option", "duplicate_page"])
def test_malformed_model_answer_contract_is_rejected(mutation: str) -> None:
    payload = json.loads(model_lesson_json("package-main"))
    if mutation == "missing":
        payload["answer_keys"] = {}
    elif mutation == "unknown_option":
        payload["answer_keys"]["check"] = "z"
    else:
        payload["pages"][1]["id"] = payload["pages"][0]["id"]

    with pytest.raises(ValueError, match="answer|page id"):
        parse_lesson_response(
            json.dumps(payload, ensure_ascii=False), topic="Go", route="foundation_engineer",
            knowledge_point_id="package-main", session_minutes=25,
        )
