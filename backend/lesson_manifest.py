"""Structured learner-facing lesson manifests and safe practice workspaces."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from pydantic import BaseModel, Field

from .learning_content import SAFE_USER_ID

PageType = Literal["explain", "example", "check", "practice", "mastery"]
# Legacy lessons without a course-specific pattern may accept any non-empty
# terminal output. Runtime failure words are rejected by the evaluator.
DEFAULT_OUTPUT_PATTERN = r"(?s)^\S.*$"


class LessonOption(BaseModel):
    id: str = Field(min_length=1, max_length=32)
    label: str = Field(min_length=1, max_length=240)


class LessonPage(BaseModel):
    id: str = Field(min_length=1, max_length=96)
    type: PageType
    title: str = Field(min_length=1, max_length=240)
    eyebrow: str = Field(default="", max_length=80)
    markdown: str = Field(default="", max_length=20_000)
    code: str = Field(default="", max_length=20_000)
    language: str | None = Field(default=None, max_length=32)
    question: str | None = Field(default=None, max_length=2_000)
    options: list[LessonOption] = Field(default_factory=list, max_length=10)
    practice_path: str | None = Field(default=None, max_length=240)
    practice_kind: Literal["classroom", "homework"] | None = None
    completion_criteria: str | None = Field(default=None, max_length=1_000)


class LessonProgress(BaseModel):
    current_page: int = Field(default=1, ge=1)
    total_pages: int = Field(ge=1)
    mastery_percent: int = Field(default=0, ge=0, le=100)
    remaining_minutes: int = Field(ge=1, le=240)


class OutputRequirement(BaseModel):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_-]+$")
    label: str = Field(min_length=1, max_length=160)
    instruction: str = Field(min_length=1, max_length=1_000)
    patterns: list[str] = Field(min_length=1, max_length=6)


class InterviewFollowUp(BaseModel):
    prompt: str = Field(min_length=1, max_length=1_000)
    answer_points: list[str] = Field(min_length=1, max_length=8)


class InterviewPrompt(BaseModel):
    id: str = Field(min_length=1, max_length=96, pattern=r"^[a-z0-9-]+$")
    question: str = Field(min_length=1, max_length=2_000)
    reference_answer: str = Field(min_length=1, max_length=8_000)
    answer_structure: list[str] = Field(min_length=1, max_length=8)
    common_omissions: list[str] = Field(default_factory=list, max_length=8)
    follow_ups: list[InterviewFollowUp] = Field(default_factory=list, max_length=5)


class LessonManifest(BaseModel):
    content_version: str = Field(default="", max_length=64)
    lesson_id: str = Field(min_length=1, max_length=96)
    title: str = Field(min_length=1, max_length=240)
    topic: str = Field(min_length=1, max_length=240)
    language: str = Field(min_length=1, max_length=32)
    route: str = Field(min_length=1, max_length=64)
    knowledge_point_id: str = Field(default="starter", min_length=1, max_length=96)
    chapter_id: str = Field(default="", max_length=64)
    chapter_title: str = Field(default="", max_length=240)
    planned_sessions: int | None = Field(default=None, ge=1, le=100)
    session_minutes: int | None = Field(default=None, ge=5, le=240)
    homework_minutes: int | None = Field(default=None, ge=0, le=10000)
    covered_knowledge_point_ids: list[str] = Field(default_factory=list, max_length=30)
    practice_path: str = Field(min_length=1, max_length=240)
    completion_mode: Literal["choice", "self_practice", "text", "evidence", "output"] = "self_practice"
    completion_prompt: str = Field(default="请提交本课成果。", min_length=1, max_length=2000)
    output_patterns: list[str] = Field(default_factory=list, max_length=6)
    output_requirements: list[OutputRequirement] = Field(default_factory=list, max_length=6)
    practice_starter_mode: Literal["provided", "blank"] = "provided"
    completion_actions: list[Literal["submit", "reteach", "stuck"]] = Field(
        default_factory=lambda: ["submit", "reteach", "stuck"], min_length=3, max_length=3
    )
    interview_prompts: list[InterviewPrompt] = Field(default_factory=list, max_length=4)
    pages: list[LessonPage] = Field(min_length=3, max_length=24)
    progress: LessonProgress


@dataclass(frozen=True)
class LessonBundle:
    manifest: LessonManifest
    answer_keys: dict[str, str]
    explanations: dict[str, str] = field(default_factory=dict)

    def public_manifest(self) -> dict[str, Any]:
        """Return only learner-facing fields; grading keys remain server-side."""
        from .lesson_context import lesson_revision
        return {**self.manifest.model_dump(), "revision": lesson_revision(self.manifest)}


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return (slug or "learning-topic")[:48]


def _safe_relative_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError("practice path must stay inside the learner directory")
    return path


def _language_material(language: str, topic: str = "") -> dict[str, str]:
    if "fastapi" in topic.casefold() or "发 api" in topic.casefold():
        return {
            "filename": "main.py",
            "concept": "发 API 的最小闭环只有三件事：客户端发出请求，服务端匹配路径并处理，最后返回响应。先把它想成去窗口点餐：你说清要哪个窗口和什么内容，窗口把结果交回来。",
            "code": 'from fastapi import FastAPI  # 导入 FastAPI，用它创建 Web 服务\n\napp = FastAPI()  # 创建应用对象，后面的接口都会注册到这里\n\n@app.get("/hello")  # 收到 GET /hello 请求时，调用下面的函数\ndef hello():  # 处理请求的函数；返回值会自动转换成 JSON\n    return {"message": "你好，API"}  # 返回给浏览器或调用方的数据\n',
            "question": "浏览器访问 `/hello` 时，哪一行负责把这个路径交给 `hello` 函数处理？",
            "a": "app = FastAPI()",
            "b": '@app.get("/hello")',
            "c": "return {...}",
            "correct": "b",
            "task": "把返回消息换成你自己的内容，启动服务并访问 `/hello`，再把看到的 JSON 响应贴给学习教练。",
            "run": "uvicorn main:app --reload",
            "output_pattern": r'"message"\s*:\s*".+"',
            "concept_title": "一次 API 调用，就是请求走进去、响应走回来",
            "example_title": "先做一个真的能访问的 GET API",
            "check_title": "找到请求路径的入口",
            "practice_title": "启动服务，亲手发一次请求",
            "mastery_title": "你已经跑通了第一个 API 请求",
            "mastery_prompt": "完成后，用自己的话说一句：请求路径、处理函数和响应分别在哪里。教练会根据运行证据决定继续讲参数还是先补讲。",
        }
    if language == "go":
        return {
            "filename": "main.go",
            "concept": "变量是一个带名字、可以取用的值容器。先把它想成贴了标签的盒子：标签帮你找到盒子，盒子里装着数据。",
            "code": 'package main // 声明这是一个可以直接运行的程序包\n\nimport "fmt" // 导入格式化输出工具\n\nfunc main() { // Go 程序从 main 函数开始执行\n    name := "小林" // 创建字符串变量，保存要问候的人\n    fmt.Println("你好，" + name) // 读取变量，并把问候打印到终端\n}\n',
            "question": "在 `name := \"小林\"` 里，哪一部分最像盒子上的标签？",
            "a": "\"小林\"",
            "b": "name",
            "c": ":=",
            "correct": "b",
            "task": "把名字换成你自己的名字，运行程序，并把终端输出贴给学习教练。",
            "run": "go run main.go",
            "output_pattern": r"你好，.+",
        }
    if language == "python":
        return {
            "filename": "main.py",
            "concept": "变量是一个带名字、可以取用的值容器。先把它想成贴了标签的盒子：标签帮你找到盒子，盒子里装着数据。",
            "code": 'name = "小林"  # 创建字符串变量，保存要问候的人\nprint("你好，" + name)  # 读取变量并把完整问候打印到终端\n',
            "question": "在 `name = \"小林\"` 里，哪一部分最像盒子上的标签？",
            "a": "\"小林\"",
            "b": "name",
            "c": "=",
            "correct": "b",
            "task": "把名字换成你自己的名字，运行程序，并把终端输出贴给学习教练。",
            "run": "python main.py",
            "output_pattern": r"你好，.+",
        }
    return {
        "filename": "notes.md",
        "concept": "我们先抓住一个最小核心概念，再用自己的话解释它解决了什么问题。",
        "code": "# 写下你的最小示例\n",
        "question": "学习新概念时，第一步最值得确认什么？",
        "a": "先背下所有术语",
        "b": "它解决了什么具体问题",
        "c": "先找最多的资料",
        "correct": "b",
        "task": "写一个生活中的例子，再说明这个概念在真实场景里解决了什么问题。",
        "run": "打开 notes.md 完成任务",
        "output_pattern": r".+",
    }


def build_starter_lesson(
    *,
    topic: str,
    language: str,
    session_minutes: int,
    goal_route: str,
) -> LessonBundle:
    """Build the first small lesson without spending model tokens."""
    selected_language = language if language in {"go", "python"} else "custom"
    if selected_language == "custom" and ("fastapi" in topic.casefold() or "发 api" in topic.casefold()):
        selected_language = "python"
    material = _language_material(selected_language, topic)
    topic_slug = _slug(topic)
    practice_path = f"projects/{topic_slug}-first-steps/lesson-01"
    pages = [
        LessonPage(
            id="concept",
            type="explain",
            eyebrow="先建立直觉",
            title=material.get("concept_title", "变量像贴了标签的盒子"),
            markdown=material["concept"],
        ),
        LessonPage(
            id="example",
            type="example",
            eyebrow="看一个最小例子",
            title=material.get("example_title", "名字放进变量，再把它取出来"),
            markdown="先读代码，不急着记语法。试着指出：标签在哪里，盒子里的值在哪里。",
            code=material["code"],
            language=selected_language,
        ),
        LessonPage(
            id="check-label",
            type="check",
            eyebrow="随堂一问",
            title=material.get("check_title", "找到变量的名字"),
            question=material["question"],
            options=[
                LessonOption(id="a", label=material["a"]),
                LessonOption(id="b", label=material["b"]),
                LessonOption(id="c", label=material["c"]),
            ],
            completion_criteria="选出变量名，并能用一句话说出理由。",
        ),
        LessonPage(
            id="practice",
            type="practice",
            eyebrow="课后练习",
            title=material.get("practice_title", "在真实文件里独立改一次"),
            markdown=f"课后自己完成：{material['task']}\n\n运行方式：`{material['run']}`\n\n完成后，把代码、结果或问题直接发到右侧对话输入栏。",
            practice_path=practice_path,
            practice_kind="homework",
            completion_criteria="程序成功运行，并提交真实输出或自己的解释。",
        ),
        LessonPage(
            id="mastery",
            type="mastery",
            eyebrow="完成这一小步",
            title=material.get("mastery_title", "你已经会用变量保存一个值"),
        markdown="课堂到这里就讲完了。课后练习已经放进真实项目目录；你可以自己慢慢完成，有问题就直接在右侧对话框继续问。",
        ),
    ]
    manifest = LessonManifest(
        lesson_id=f"{topic_slug}-lesson-01",
        title=f"{topic} · 第一个核心概念",
        topic=topic,
        language=selected_language,
        route=goal_route,
        practice_path=practice_path,
        completion_mode="self_practice",
        completion_prompt="课堂选择题完成后即可继续。课后练习完成时，把代码、运行结果或问题直接发到右侧输入栏，不做输出格式验收。",
        output_patterns=[],
        output_requirements=[],
        pages=pages,
        progress=LessonProgress(
            total_pages=len(pages),
            remaining_minutes=max(10, session_minutes),
        ),
    )
    return LessonBundle(manifest=manifest, answer_keys={"check-label": material["correct"]})


def ensure_practice_workspace(
    server_root: Path,
    user_id: str,
    manifest: LessonManifest,
) -> Path:
    """Create starter files once, always inside the selected learner directory."""
    if not SAFE_USER_ID.fullmatch(user_id):
        raise ValueError("invalid user_id")
    if manifest.completion_mode == "choice":
        return (server_root / "userdir" / f"u_{user_id}").resolve()
    relative = _safe_relative_path(manifest.practice_path)
    user_dir = (server_root / "userdir" / f"u_{user_id}").resolve()
    target = user_dir.joinpath(*relative.parts).resolve()
    if target != user_dir and user_dir not in target.parents:
        raise ValueError("practice path escaped learner directory")
    target.mkdir(parents=True, exist_ok=True)

    filename = {
        "go": "main.go",
        "python": "main.py",
        "java": "Main.java",
        "rust": "main.rs",
    }.get(manifest.language, "notes.md")
    if manifest.practice_starter_mode == "blank":
        code = ""
    else:
        language = manifest.language.casefold()
        matching_examples = [
            page.code
            for page in manifest.pages
            if page.code.strip() and (page.language or "").casefold() == language
        ]
        if matching_examples:
            # A lesson may show a minimal skeleton before the runnable example.
            # The longest same-language block is the safest starter file.
            code = max(matching_examples, key=len)
        elif language not in {"go", "python", "java", "rust"}:
            code = max(
                (page.code for page in manifest.pages if page.code.strip()),
                key=len,
                default="",
            )
        else:
            code = ""
    practice = next(
        (page.markdown for page in manifest.pages if page.type == "practice" and page.markdown.strip()),
        manifest.completion_prompt,
    )
    readme = target / "README.md"
    starter = target / filename
    if not readme.exists():
        readme.write_text(
            f"# {manifest.title}\n\n## 任务\n\n{practice}\n\n## 提交标准\n\n{manifest.completion_prompt}\n",
            encoding="utf-8",
        )
    if not starter.exists():
        starter.write_text(code, encoding="utf-8")
    return target


def resolve_practice_folder(server_root: Path, user_id: str, relative_path: str) -> Path:
    """Resolve an existing practice directory without leaving this learner's folder."""
    if not SAFE_USER_ID.fullmatch(user_id):
        raise ValueError("invalid user_id")
    relative = _safe_relative_path(relative_path)
    user_dir = (server_root / "userdir" / f"u_{user_id}").resolve()
    target = user_dir.joinpath(*relative.parts).resolve()
    if target != user_dir and user_dir not in target.parents:
        raise ValueError("practice path must stay inside the learner directory")
    if not target.is_dir():
        raise FileNotFoundError("practice folder does not exist")
    return target
