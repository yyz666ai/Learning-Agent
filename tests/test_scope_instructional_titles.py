"""Portable lexical-scope cases; fixtures contain no saved learner responses."""

import pytest

from backend.curriculum import KnowledgePoint
from backend.lesson_generator import _scope_concepts, _validate_scope_evidence
from backend.lesson_manifest import build_starter_lesson


INSTALL_TITLE = (
    "Go 官方安装与版本验证：从 go.dev/dl 安装当前稳定版，"
    "`go version` 确认安装成功（版本号以官方页面为准，不写死版本）"
)
INSTALL_BODIES = [
    "Go 官方安装包从 go.dev/dl 下载，选择当前稳定版安装。"
    "版本号以官方页面显示为准，不写死具体版本号。安装完成后运行 `go version`。",
    "运行 `go version`，查看版本输出以验证安装结果。",
]
SKELETON_TITLE = "最小程序骨架：`package main`、`func main`、`go run` 的执行顺序"
SKELETON_BODIES = [
    "package main 声明程序包，func main 是程序入口。",
    "go run 的执行顺序：先编译，再进入 func main 执行语句。",
]
DIRECTORY_TITLE = "课程目录与编辑器工作流：课程根目录、练习目录、用编辑器打开项目"
DIRECTORY_BODIES = [
    "课程目录包含课程根目录及练习目录，练习文件存入练习目录。",
    "编辑器负责修改代码，终端负责运行；这个工作流先用编辑器打开项目。",
]


def validate(title, bodies, *, page_ids=None):
    point = KnowledgePoint(id="scope", title=title, outcome="解释并操作", practice="运行", mastery_criteria="结果正确")
    bundle = build_starter_lesson(topic="Go", language="go", session_minutes=20, goal_route="foundation_engineer")
    bundle.manifest.covered_knowledge_point_ids = [point.id]
    for page, body in zip(bundle.manifest.pages, bodies):
        page.markdown = body
        page.code = ""
        page.question = ""
        page.title = title  # Titles cannot substitute for missing body evidence.
    evidence = {"knowledge_point_id": point.id, "page_ids": page_ids or [p.id for p in bundle.manifest.pages[:len(bodies)]]}
    _validate_scope_evidence({"scope_evidence": [evidence]}, bundle, [point])


@pytest.mark.parametrize("title,bodies", [
    (INSTALL_TITLE, INSTALL_BODIES),
    (SKELETON_TITLE, SKELETON_BODIES),
    (DIRECTORY_TITLE, DIRECTORY_BODIES),
])
def test_explicit_instructional_title_parts_can_be_taught_across_pages(title, bodies):
    validate(title, bodies)


@pytest.mark.parametrize("title,bodies,missing", [
    (INSTALL_TITLE, INSTALL_BODIES, "go version"),
    (INSTALL_TITLE, INSTALL_BODIES, "go.dev/dl"),
    (INSTALL_TITLE, INSTALL_BODIES, "当前稳定版"),
    (INSTALL_TITLE, INSTALL_BODIES, "不写死"),
    (SKELETON_TITLE, SKELETON_BODIES, "package main"),
    (SKELETON_TITLE, SKELETON_BODIES, "func main"),
    (SKELETON_TITLE, SKELETON_BODIES, "执行顺序"),
    (DIRECTORY_TITLE, DIRECTORY_BODIES, "课程根目录"),
    (DIRECTORY_TITLE, DIRECTORY_BODIES, "练习目录"),
    (DIRECTORY_TITLE, DIRECTORY_BODIES, "工作流"),
    (DIRECTORY_TITLE, DIRECTORY_BODIES, "用编辑器打开项目"),
])
def test_instructional_extraction_keeps_every_substantive_requirement(title, bodies, missing):
    with pytest.raises(ValueError, match="drifted"):
        validate(title, [body.replace(missing, "其他内容") for body in bodies])


def test_one_real_page_plus_unrelated_page_is_still_insufficient():
    with pytest.raises(ValueError, match="at least two relevant pages"):
        validate(INSTALL_TITLE, [INSTALL_BODIES[0], "只练习字符串拼接。"])


def test_unknown_colon_prefix_is_not_silently_discarded():
    title = "资源泄漏排查：channel、goroutine"
    assert any("资源泄漏排查" in concept for concept in _scope_concepts(title))
    with pytest.raises(ValueError, match="drifted"):
        validate(title, ["channel 传递值。", "goroutine 执行任务。"])


def test_installation_template_uses_captured_source_and_command():
    title = INSTALL_TITLE.replace("Go", "Python").replace("go.dev/dl", "python.org/downloads").replace("go version", "python --version")
    bodies = [body.replace("Go", "Python").replace("go.dev/dl", "python.org/downloads").replace("go version", "python --version") for body in INSTALL_BODIES]
    validate(title, bodies)
    with pytest.raises(ValueError, match="drifted"):
        validate(title, INSTALL_BODIES)
