"""Original title/body fixtures now go intact to a semantic reviewer."""

import pytest

import json
from backend.curriculum import Chapter, Curriculum, KnowledgePoint
from backend.lesson_review import LessonCoverageError, LessonReviewUnavailable, review_lesson
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


def validate(title, bodies, *, page_ids=None, status="covered"):
    point = KnowledgePoint(id="scope", title=title, outcome="解释并操作", practice="运行", mastery_criteria="结果正确")
    curriculum = Curriculum(topic="Go", route="concept_clarity", level="zero",
        current_knowledge_point_id="scope", chapters=[Chapter(id="chapter", title="本课", knowledge_points=[point])])
    bundle = build_starter_lesson(topic="Go", language="go", session_minutes=20, goal_route="foundation_engineer")
    bundle.manifest.covered_knowledge_point_ids = [point.id]
    for page, body in zip(bundle.manifest.pages, bodies):
        page.markdown, page.code, page.question, page.title = body, "", "", title
    captured = []
    def model(prompt):
        captured.append(prompt)
        return json.dumps({"coverage": [{"knowledge_point_id": point.id, "status": status,
            "reason": "审阅者报告：已有充分讲解" if status == "covered" else "审阅者报告：缺少必要讲解",
            "page_ids": page_ids if page_ids is not None else [bundle.manifest.pages[0].id]}]})
    report = review_lesson(bundle, curriculum, profile="零基础", model_call=model)
    data = json.loads(captured[0].split("待审数据：\n", 1)[1])
    assert data["knowledge_points"][0]["title"] == title
    assert data["pages"][0]["markdown"] == bodies[0]
    assert len(captured) == 1
    return report


@pytest.mark.parametrize("title,bodies", [
    (INSTALL_TITLE, INSTALL_BODIES),
    (SKELETON_TITLE, SKELETON_BODIES),
    (DIRECTORY_TITLE, DIRECTORY_BODIES),
])
def test_original_instructional_title_and_body_reach_reviewer_intact(title, bodies):
    validate(title, bodies)


@pytest.mark.parametrize("title,bodies", [
    (INSTALL_TITLE, INSTALL_BODIES),
    (SKELETON_TITLE, SKELETON_BODIES),
    (DIRECTORY_TITLE, DIRECTORY_BODIES),
])
def test_reviewer_can_reject_content_even_with_matching_titles(title, bodies):
    with pytest.raises(LessonCoverageError):
        validate(title, bodies, status="missing")


def test_untrusted_reviewer_cannot_cite_unknown_page():
    with pytest.raises(LessonReviewUnavailable):
        validate(INSTALL_TITLE, INSTALL_BODIES, page_ids=["invented"])
