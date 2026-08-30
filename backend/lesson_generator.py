"""Codex-generated, schema-validated lesson manifests per knowledge point."""

from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Callable

try:
    from .curriculum import Chapter, Curriculum, KnowledgePoint
    from .learning_content import SAFE_USER_ID
    from .lesson_manifest import DEFAULT_OUTPUT_PATTERN, InterviewPrompt, LessonBundle, LessonManifest, LessonPage, LessonProgress, OutputRequirement
except ImportError:
    from curriculum import Chapter, Curriculum, KnowledgePoint
    from learning_content import SAFE_USER_ID
    from lesson_manifest import DEFAULT_OUTPUT_PATTERN, InterviewPrompt, LessonBundle, LessonManifest, LessonPage, LessonProgress, OutputRequirement


def _extract_json(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("model lesson is not JSON")
    try:
        payload = json.loads(text[start:end + 1])
    except json.JSONDecodeError as exc:
        raise ValueError("model lesson is invalid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("model lesson must be an object")
    return payload


def _expected_language(topic: str) -> str | None:
    lowered = topic.casefold()
    if re.search(r"\bgo(?:lang)?\b", lowered):
        return "go"
    if "fastapi" in lowered or "python" in lowered:
        return "python"
    if "java" in lowered:
        return "java"
    if "rust" in lowered:
        return "rust"
    return None


def _starter_filename(language: str) -> str:
    return {"go": "main.go", "python": "main.py", "java": "Main.java", "rust": "main.rs"}.get(language, "notes.md")


def _comment_legacy_code(language: str, code: str) -> str:
    """Add concise teaching comments when an old cached sample has none."""
    if not code.strip():
        return code
    effective = _effective_code_lines(code)
    required_comments = 2 if len(effective) >= 8 else 1
    if sum(bool(_CHINESE_COMMENT.search(line)) for line in effective) >= required_comments:
        return code
    marker = "#" if language in {"python", "bash", "shell", "sh"} else ("--" if language == "sql" else "//")
    lines: list[str] = []
    for line in code.splitlines():
        stripped = line.strip()
        comment = ""
        if language == "go":
            if stripped.startswith("package main"):
                comment = "声明这是一个可以直接运行的程序包"
            elif stripped.startswith("import"):
                comment = "导入后面代码需要使用的工具包"
            elif stripped.startswith("func main"):
                comment = "程序从 main 函数开始执行"
            elif "fmt.Print" in stripped:
                comment = "把当前数据打印到终端，方便观察结果"
            elif ":=" in stripped:
                comment = "创建变量并保存右侧的值"
        elif language == "python":
            if stripped.startswith(("from ", "import ")):
                comment = "导入后面代码需要使用的工具"
            elif stripped.startswith("@"):
                comment = "把请求路径连接到下面的处理函数"
            elif stripped.startswith("def "):
                comment = "定义函数，收到调用时执行缩进代码"
            elif stripped.startswith("return "):
                comment = "把处理后的结果返回给调用方"
            elif "print(" in stripped:
                comment = "把当前数据打印到终端，方便观察结果"
            elif "=" in stripped and "==" not in stripped:
                comment = "创建变量并保存右侧的值"
        if comment and stripped:
            lines.append(f"{line} {marker} {comment}")
        else:
            lines.append(line)
    enriched = "\n".join(lines)
    comment_count = sum(bool(_CHINESE_COMMENT.search(line)) for line in _effective_code_lines(enriched))
    missing = max(0, required_comments - comment_count)
    if missing:
        introductions = [
            f"{marker} 教学说明：下面代码展示本页的最小执行步骤",
            f"{marker} 阅读重点：留意数据从入口到结果的变化",
        ][:missing]
        enriched = "\n".join((*introductions, enriched))
    return enriched


_CHINESE_COMMENT = re.compile(r"(?:#|//|/\*|\*|--|<!--).*?[\u4e00-\u9fff]")


def _effective_code_lines(code: str) -> list[str]:
    return [line for line in code.splitlines() if line.strip()]


def _instruction_code_lines(code: str) -> list[str]:
    """Count executable/declarative lines, not explanatory comment-only lines."""
    return [
        line for line in _effective_code_lines(code)
        if re.match(r"^\s*(?://|#|/\*|\*|--|<!--)", line) is None
    ]


def _answer_id(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, list) and len(value) == 1:
        return _answer_id(value[0])
    if isinstance(value, dict):
        for key in ("answer_id", "correct_option_id", "answer", "option_id", "id"):
            answer = _answer_id(value.get(key))
            if answer:
                return answer
    return None


def _repair_generated_wire_format(response: str, topic: str) -> str:
    """Repair only deterministic model wire-format drift before applying strict semantic validation."""
    payload = _extract_json(response)
    language = str(payload.get("language") or _expected_language(topic) or "custom").casefold()
    repaired_pages: list[object] = []
    for raw_page in payload.get("pages") or []:
        if not isinstance(raw_page, dict):
            repaired_pages.append(raw_page)
            continue
        page = dict(raw_page)
        if page.get("type") in {"explain", "example", "mastery"} and page.get("practice_kind") == page.get("type"):
            # A display-only page has no practice category. Correct a model's
            # duplicate page-type field without reclassifying an actual task.
            page["practice_kind"] = None
        code = page.get("code")
        if isinstance(code, str) and code.strip():
            page_language = str(page.get("language") or language).casefold()
            page["code"] = _comment_legacy_code(page_language, code)
        repaired_pages.append(page)
    payload["pages"] = repaired_pages
    raw_keys = payload.get("answer_keys")
    normalized_keys: dict[str, str] = {}
    if isinstance(raw_keys, dict):
        for page_id, value in raw_keys.items():
            answer = _answer_id(value)
            if isinstance(page_id, str) and answer:
                normalized_keys[page_id] = answer
    elif isinstance(raw_keys, list):
        for item in raw_keys:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                page_id, value = item
            elif isinstance(item, dict):
                page_id = item.get("page_id") or item.get("question_id")
                value = item
            else:
                continue
            answer = _answer_id(value)
            if isinstance(page_id, str) and answer:
                normalized_keys[page_id] = answer
    if not normalized_keys:
        for item in repaired_pages:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                continue
            answer = _answer_id(item.get("answer_id") or item.get("correct_option_id") or item.get("answer"))
            if answer:
                normalized_keys[item["id"]] = answer
    if normalized_keys:
        payload["answer_keys"] = normalized_keys
    repaired_interview_prompts: list[object] = []
    for raw_prompt in payload.get("interview_prompts") or []:
        if not isinstance(raw_prompt, dict):
            repaired_interview_prompts.append(raw_prompt)
            continue
        prompt = dict(raw_prompt)
        for field in ("answer_structure", "common_omissions"):
            value = prompt.get(field)
            if isinstance(value, str) and value.strip():
                prompt[field] = [value.strip()]
        repaired_interview_prompts.append(prompt)
    if repaired_interview_prompts:
        payload["interview_prompts"] = repaired_interview_prompts
    return json.dumps(payload, ensure_ascii=False)


def _validate_commented_progressive_code(pages: list[LessonPage]) -> None:
    previous_code_lengths: list[int] = []
    for page in pages:
        if not page.code.strip():
            continue
        lines = _effective_code_lines(page.code)
        comment_count = sum(bool(_CHINESE_COMMENT.search(line)) for line in lines)
        required_comments = 2 if len(lines) >= 8 else 1
        if comment_count < required_comments:
            raise ValueError("every generated code block requires detailed Chinese comments")
        instruction_count = len(_instruction_code_lines(page.code))
        if instruction_count > 12 and not any(
            0 < previous < instruction_count for previous in previous_code_lengths
        ):
            raise ValueError("long generated code requires a progressive build-up page")
        previous_code_lengths.append(instruction_count)


def parse_lesson_response(
    response: str,
    *,
    topic: str,
    route: str,
    knowledge_point_id: str,
    session_minutes: int,
    chapter: Chapter | None = None,
    covered_knowledge_points: list[KnowledgePoint] | None = None,
) -> LessonBundle:
    payload = _extract_json(response)
    normalized_pages = []
    for raw_page in payload.get("pages", []):
        if not isinstance(raw_page, dict):
            raise ValueError("model lesson page must be an object")
        page = dict(raw_page)
        # Models commonly emit JSON null for unused presentation fields. Keep
        # the manifest strict while accepting that harmless wire-format variant.
        for field in ("eyebrow", "markdown", "code"):
            if page.get(field) is None:
                page[field] = ""
        if isinstance(page.get("practice_kind"), str) and page["practice_kind"].strip().casefold() in {"", "null", "none"}:
            page["practice_kind"] = None
        options = []
        for index, option in enumerate(page.get("options") or []):
            if isinstance(option, str):
                label = re.sub(r"^\s*[A-Za-z][.、:)：]\s*", "", option).strip()
                options.append({"id": chr(97 + index), "label": label})
            else:
                options.append(option)
        page["options"] = options
        normalized_pages.append(page)
    pages = [LessonPage.model_validate(page) for page in normalized_pages]
    if not pages or pages[-1].type != "mastery":
        raise ValueError("model lesson must end with a mastery page")
    language = str(payload.get("language") or "custom").casefold()
    expected = _expected_language(topic)
    if expected and language in {"zh", "zh-cn", "chinese", "中文", "custom"}:
        language = expected
    if expected and language != expected:
        raise ValueError(f"model lesson language must be {expected}")
    _validate_commented_progressive_code(pages)
    visible_text = "\n".join(f"{page.markdown}\n{page.code}" for page in pages)
    if "$USER_DIR" in visible_text:
        raise ValueError("model lesson must not expose a user directory placeholder")
    if language == "go":
        referenced = re.findall(r"\bgo\s+run\s+([^\s`]+\.go)\b", visible_text)
        if any(filename != _starter_filename(language) for filename in referenced):
            raise ValueError("model lesson references an unavailable starter filename")
    answer_keys = payload.get("answer_keys") or {}
    if not isinstance(answer_keys, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in answer_keys.items()):
        raise ValueError("answer keys must be a string map")
    answer_keys = {key: value.casefold() for key, value in answer_keys.items()}
    page_id_list = [page.id for page in pages]
    if len(page_id_list) != len(set(page_id_list)):
        raise ValueError("model lesson page ids must be unique")
    page_ids = set(page_id_list)
    if any(page_id not in page_ids for page_id in answer_keys):
        raise ValueError("answer key references an unknown page")
    choice_pages = {page.id: {option.id.casefold() for option in page.options} for page in pages if page.options}
    if any(page_id not in answer_keys for page_id in choice_pages):
        raise ValueError("every choice page must have an answer key")
    if any(page_id not in choice_pages or answer_id not in choice_pages[page_id] for page_id, answer_id in answer_keys.items()):
        raise ValueError("answer id must reference an option on its page")
    practice_path = PurePosixPath(str(payload.get("practice_path") or f"projects/{knowledge_point_id}"))
    if practice_path.is_absolute() or ".." in practice_path.parts:
        raise ValueError("practice path must be a safe learner-relative directory")
    if practice_path.suffix.casefold() in {".go", ".py", ".java", ".rs", ".js", ".ts"}:
        practice_path = practice_path.parent
    completion_mode = str(payload.get("completion_mode") or "self_practice")
    if completion_mode in {"output", "evidence"}:
        completion_mode = "self_practice"
    if route == "concept_clarity" and completion_mode == "choice":
        if any(page.code.strip() or page.type == "practice" for page in pages):
            raise ValueError("choice-only concept lesson must not contain code or practice pages")
    if completion_mode in {"choice", "self_practice"}:
        output_patterns = []
    else:
        output_patterns = payload.get("output_patterns") or []
    if not isinstance(output_patterns, list) or not all(isinstance(pattern, str) and pattern.strip() for pattern in output_patterns):
        raise ValueError("output patterns must be a string list")
    if len(output_patterns) > 6:
        raise ValueError("too many output patterns")
    try:
        for pattern in output_patterns:
            re.compile(pattern)
    except re.error as exc:
        raise ValueError("output pattern must be valid regex") from exc
    raw_requirements = [] if completion_mode in {"choice", "self_practice"} else (payload.get("output_requirements") or [])
    requirements = [OutputRequirement.model_validate(item) for item in raw_requirements]
    if len({item.id for item in requirements}) != len(requirements):
        raise ValueError("output requirement ids must be unique")
    try:
        for requirement in requirements:
            for pattern in requirement.patterns:
                re.compile(pattern)
    except re.error as exc:
        raise ValueError("output requirement pattern must be valid regex") from exc
    if completion_mode == "self_practice":
        practice_indexes = [index for index, page in enumerate(pages) if page.type == "practice"]
        if not practice_indexes:
            raise ValueError("self-practice lesson must include one homework page")
        homework_indexes = [index for index in practice_indexes if pages[index].practice_kind == "homework"]
        if not homework_indexes:
            last_practice = practice_indexes[-1]
            pages[last_practice] = pages[last_practice].model_copy(update={"practice_kind": "homework"})
            homework_indexes = [last_practice]
        if len(homework_indexes) != 1:
            raise ValueError("self-practice lesson must include exactly one homework page")
    raw_interview_prompts = payload.get("interview_prompts") or []
    interview_prompts = [InterviewPrompt.model_validate(item) for item in raw_interview_prompts]
    if len({item.id for item in interview_prompts}) != len(interview_prompts):
        raise ValueError("interview prompt ids must be unique")
    if route == "interview_sprint" and not 2 <= len(interview_prompts) <= 4:
        raise ValueError("interview prompts must contain 2 to 4 answered short-answer cards")
    covered_ids = [point.id for point in covered_knowledge_points] if covered_knowledge_points is not None else ([point.id for point in chapter.knowledge_points] if chapter else [knowledge_point_id])
    if chapter and len(pages) < min(12, len(covered_ids) + 2):
        raise ValueError("chapter deck is too short to cover its knowledge points")
    manifest = LessonManifest(
        lesson_id=f"{knowledge_point_id}-lesson",
        title=str(payload.get("title") or knowledge_point_id),
        topic=topic,
        language=language,
        route=route,
        knowledge_point_id=knowledge_point_id,
        chapter_id=chapter.id if chapter else "",
        chapter_title=chapter.title if chapter else "",
        planned_sessions=chapter.estimated_sessions if chapter else None,
        session_minutes=chapter.session_minutes or session_minutes if chapter else session_minutes,
        homework_minutes=chapter.homework_minutes if chapter else None,
        covered_knowledge_point_ids=covered_ids,
        practice_path=str(practice_path),
        completion_mode=completion_mode,
        completion_prompt=str(payload.get("completion_prompt") or "课堂选择题完成后即可继续；课后练习的代码、结果或问题直接发到右侧输入栏。"),
        output_patterns=output_patterns,
        output_requirements=requirements,
        practice_starter_mode=payload.get("practice_starter_mode") or "provided",
        completion_actions=["submit", "reteach", "stuck"],
        interview_prompts=interview_prompts,
        pages=pages,
        progress=LessonProgress(total_pages=len(pages), remaining_minutes=session_minutes),
    )
    return LessonBundle(manifest=manifest, answer_keys=answer_keys)


def current_point(curriculum: Curriculum) -> KnowledgePoint:
    for point in curriculum.knowledge_points():
        if point.id == curriculum.current_knowledge_point_id:
            return point
    raise ValueError("current knowledge point is missing")


def _structured_scope_concepts(title: str) -> list[str] | None:
    plain = title.replace("`", "").strip()
    if re.fullmatch(r"package main\s*与\s*func main\s*的启动约定", plain):
        return ["package main", "func main", "启动约定"]
    if re.fullmatch(r"go\s*子命令族[：:]\s*version\s*/\s*run\s*/\s*build", plain):
        return ["go version", "go run", "go build"]
    return None


def _scope_concepts(title: str) -> list[str]:
    """Extract literal topic phrases, not a semantic coverage/confidence score.

    Only allowlisted instructional prefixes or an explicit '把「topic」拆成…'
    wrapper can discard outer wording. Other parentheses retain outer concepts.
    No synonym/semantic inference is made.
    """
    # Source attribution is a separate requirement, not part of a phrase the
    # learner must see verbatim. Keep the actual source rather than dropping it.
    structured = _structured_scope_concepts(title)
    if structured:
        return structured
    title = re.sub(r"[（(]官方来源\s*[:：]?\s*([^（）()]+)[）)]", r"、\1、", title)
    listed = re.search(r"[（(]([^（）()]+)[）)]\s*$", title)
    quoted = re.search(r"把[「“]([^」”]+)[」”]\s*拆成", title)
    interview_topic = re.fullmatch(r"(?:附带|补充)(?:一个)?面试点[「“]([^」”]+)[」”]", title)
    source = title
    instructional_prefix = re.fullmatch(
        r"(?:快进)?(?:确认|复习|评估)(?:已掌握区|已掌握内容|已掌握知识点|强项)\s*",
        title[:listed.start()] if listed else "",
    )
    if listed and instructional_prefix and re.search(r"[、；;]|与|\s和\s", listed[1]):
        source = listed[1]
    elif quoted:
        source = quoted[1]
    elif interview_topic:
        source = interview_topic[1]
    elif listed:
        source = title[:listed.start()] + "、" + listed[1]
    concepts = []
    for phrase in re.split(r"[、；;]|\s*与\s*|\s+和\s+|如何", source):
        phrase = re.sub(r"是什么[？?]?$", "", phrase.strip())
        # 'HTTP handler 实现' names the API plus an instructional action.
        # Do not strip arbitrary Chinese suffixes or invent synonyms.
        phrase = re.sub(r"(?<=[A-Za-z])\s+实现$", "", phrase)
        if phrase and phrase not in concepts:
            concepts.append(phrase)
    return concepts or [title]


def _scope_text(text: str) -> str:
    return re.sub(r"[\s`*]+", "", text).casefold()


# Explicit literal subanchors for known compound concepts. They are only used
# for per-page relevance; aggregate coverage still requires the FULL concepts.
# Do not infer arbitrary Latin tokens, CJK n-grams, synonyms or confidence scores.
_SCOPE_PAGE_SUBANCHORS = {
    "HTTP handler": ("handler", "HandleFunc", "ResponseWriter", "http.Request"),
    "表驱动单元测试": ("表驱动", "用例表"),
    "并发取消": ("取消", "ctx.Done", "r.Context"),
    "资源泄漏排查": ("泄漏", "资源句柄", "resp.Body"),
    "Python 版本": ("python3 --version", "python --version", "py --version", "版本验证"),
    "练习目录结构": ("练习目录",),
    "编辑器打开方式": ("打开文件夹", "Open Folder"),
}


def _validate_scope_evidence(payload: dict, bundle: LessonBundle, points: list[KnowledgePoint]) -> None:
    """Check cited-content lexical coverage at every fresh-generation boundary.

    This does not prove factual correctness or semantic teaching quality. Cached
    manifests remain loadable without retroactively inventing scope evidence.
    """
    raw_scope = payload.get("scope_evidence")
    if not isinstance(raw_scope, list):
        raise ValueError("generated lesson must include scope evidence")
    page_by_id = {page.id: page for page in bundle.manifest.pages}
    point_by_id = {point.id: point for point in points}
    evidence_by_point = {}
    for item in raw_scope:
        if not isinstance(item, dict) or not isinstance(item.get("knowledge_point_id"), str):
            raise ValueError("generated lesson scope evidence is invalid")
        point_id = item["knowledge_point_id"]
        if point_id in evidence_by_point:
            raise ValueError("generated lesson scope evidence contains a duplicate knowledge point")
        page_ids = item.get("page_ids")
        if (not isinstance(page_ids, list)
                or not all(isinstance(page_id, str) for page_id in page_ids)
                or len(set(page_ids)) < 2):
            raise ValueError("generated lesson scope evidence needs at least two pages per knowledge point")
        if any(page_id not in page_by_id for page_id in page_ids):
            raise ValueError("generated lesson scope evidence references an unknown page")
        # Titles/eyebrows/IDs alone are not teaching evidence. Use only the
        # cited body, question and code, never the overall deck title.
        bodies = {page_id: f"{page_by_id[page_id].markdown}\n{page_by_id[page_id].question or ''}\n{page_by_id[page_id].code}" for page_id in page_ids}
        if "excerpts" in item:
            excerpts = item["excerpts"]
            if not isinstance(excerpts, list) or not excerpts:
                raise ValueError("generated lesson scope evidence excerpts are invalid")
            for excerpt in excerpts:
                if not isinstance(excerpt, dict):
                    raise ValueError("generated lesson scope evidence excerpt is invalid")
                page_id, quote = excerpt.get("page_id"), excerpt.get("quote")
                if (not isinstance(page_id, str) or page_id not in bodies
                        or not isinstance(quote, str) or not quote.strip()
                        or quote not in bodies[page_id]):
                    raise ValueError("generated lesson scope evidence excerpt is not grounded in its cited page")
        # Explicit ID labels are metadata, but bare IDs such as 'go' and
        # 'goroutine' are also legitimate domain terms and MUST remain intact.
        cleaned_bodies = []
        for body in bodies.values():
            body = re.sub(rf"知识点\s*(?:ID\s*)?[:：]?\s*{re.escape(point_id)}(?![A-Za-z0-9_-])", "", body)
            if "-" in point_id:
                body = re.sub(rf"(?<![\w-]){re.escape(point_id)}(?![\w-])", "", body)
            cleaned_bodies.append(body)
        evidence_by_point[point_id] = cleaned_bodies
    if set(evidence_by_point) != set(bundle.manifest.covered_knowledge_point_ids):
        raise ValueError("generated lesson scope evidence must match covered knowledge points")
    for point_id, narratives in evidence_by_point.items():
        point = point_by_id.get(point_id)
        if point is None:
            raise ValueError("generated lesson scope evidence claimed an out-of-scope knowledge point")
        normalized = [_scope_text(narrative) for narrative in narratives]
        concepts = _scope_concepts(point.title)
        anchors = [
            _scope_text(anchor)
            for concept in concepts
            for anchor in (concept, *_SCOPE_PAGE_SUBANCHORS.get(concept, ()))
        ]
        # Models may cite surplus overview/quiz pages. Discard those citations
        # only after validating ALL raw IDs/excerpts above. Never manufacture a
        # second supporting page, and check every concept on retained pages only.
        normalized = [body for body in normalized if any(anchor in body for anchor in anchors)]
        if len(normalized) < 2:
            raise ValueError(f"generated lesson drifted: scope evidence needs at least two relevant pages for {point_id}")
        # The full-title form remains compatible; the concept-list form accepts
        # paraphrased wrappers but still requires EVERY named concept.
        if ((_structured_scope_concepts(point.title) is not None or not any(_scope_text(point.title) in body for body in normalized))
                and not all(any(_scope_text(concept) in body for body in normalized) for concept in concepts)):
            raise ValueError(f"generated lesson drifted away from a covered knowledge point: {point_id}")


def build_lesson_prompt(
    curriculum: Curriculum,
    *,
    profile: str,
    recent_evidence: list[str],
    session_minutes: int,
    remediation: str = "",
    research_evidence: str = "",
) -> str:
    point = current_point(curriculum)
    chapter = curriculum.current_chapter()
    chapter_points = curriculum.current_chapter_remaining_points()
    revision_skill = (
        "用户正在修改现有讲义：还必须读取 `lesson-revision` Skill，把补救要求当作本次重做的验收条件；旧讲义只有在新 JSON 通过校验后才可替换。"
        if remediation else ""
    )
    concept_meaning_only = curriculum.route == "concept_clarity" and "meaning_only" in profile
    concept_code_walkthrough = curriculum.route == "concept_clarity" and "code_walkthrough" in profile
    requires_environment_setup = (
        curriculum.level.casefold() in {"zero", "beginner", "novice"}
        and chapter.id == curriculum.chapters[0].id
        and not concept_meaning_only
    )
    environment_contract = """
零基础首次代码课环境契约：
- 本章必须在第一次运行代码前安排一张“环境准备”页，并在页面内写清：需要下载的软件、每项用途、官方入口、版本验证命令、课程项目目录、如何用编辑器打开目录，以及首次运行命令。
- 不要猜测操作系统。画像已经给出系统时只展示该系统步骤；系统未知时用 macOS / Windows / Linux 三个短分支，不能把某个平台的命令冒充通用命令。
- 下载地址、版本和安装命令属于版本敏感事实，只能使用研究依据或官方来源；无法确认精确版本时给官方入口与稳定的版本验证方法，不编造链接。
- 环境说明必须出现在 HTML PPT 页面中，不能只写进聊天提示或课后作业。验证通过后记为 environment_ready；后续章节不得重复整套安装，只在运行前给一句先修检查。
""" if requires_environment_setup else ""
    if concept_meaning_only:
        lesson_contract = """这是 `concept_clarity/meaning_only` 概念速学：
- 只生成 3–5 页，从“没有它会怎样”开始，使用生活比喻、最小流程、适用场景和边界。
- 可以读取 `visual-explainer` 并在 markdown 中给 Mermaid；不得给代码、运行命令、项目练习或终端输出。
- 安排 1–2 道点击选择题；最后一页为 mastery，所有必答选择题答对即完成。
- JSON 必须使用 completion_mode=`choice`、output_patterns=[]、output_requirements=[]、practice_starter_mode=`provided`。
- practice_path 只是结构化占位，使用 `concepts/<topic-slug>`；不在页面展示或引导打开它。
"""
    elif concept_code_walkthrough:
        lesson_contract = """这是 `concept_clarity/code_walkthrough` 概念速学：
- 生成 4–7 页，先用比喻与流程讲懂，再读取 `progressive-code-teaching` 逐步拆最小代码。
- 所有陌生代码必须带详细中文注释，说明数据如何流动以及每个 API 为什么存在；不要一上来给大段完整代码。
- 使用 completion_mode=`self_practice`，给出 1 个 practice_kind=homework 的课后练习，不生成输出框。
"""
    else:
        lesson_contract = """这是完整章节讲义：
- 页面数量由知识密度决定：简单章 4–8 页，普通章 8–16 页，概念密集章 12–24 页；completion_mode=`self_practice`，课堂只用点击选择题检查理解。
- 安排且只安排 1 个 practice_kind=homework 的课后独立练习；最后 mastery 页说明练习目录、完成目标和对话提交方式。
"""
    return f"""你是 Learning Agent 的课程设计与讲解模型。为当前学习者生成一个知识点的完整 HTML PPT 数据。

主题：{curriculum.topic}
路线：{curriculum.route}
能力：{curriculum.level}
画像：{profile}
当前知识点 ID：{point.id}
当前知识点：{point.title}
当前章：{chapter.title}
本章必须完整讲完的知识点：{'；'.join(f'{item.id}：{item.title}' for item in chapter_points)}
本章逐项覆盖词组（可分散在引用页正文，不必照抄整句知识点标题）：{json.dumps({item.id: _scope_concepts(item.title) for item in chapter_points}, ensure_ascii=False)}
学习结果：{point.outcome}
先修知识点：{', '.join(point.prerequisites) or '无'}
练习目标：{point.practice}
完成标准：{point.mastery_criteria}
最近学习证据：{'；'.join(recent_evidence) or '暂无'}
研究依据：{research_evidence or '当前主题使用已验证知识库；没有额外版本敏感事实'}
单次时长：{session_minutes} 分钟
整章预计课次：{chapter.estimated_sessions or '尚未估算，不能默认一课'}
课外练习预算：{chapter.homework_minutes if chapter.homework_minutes is not None else '尚未估算'} 分钟
计划中的分次目标：{'；'.join(chapter.session_outline) or '尚未细分，请按整章预算安排并标注为建议'}
这是可分多次阅读的整章课件，不代表所有内容必须在一次学习中完成。若整章超过1课，在开场明确分次目标，并在每次课结束位置写“第N课暂停点”：本次应完成的练习、验收和下次从哪页继续。课外作业另计，不挤进单次时长。不能把浏览完等同于掌握。
补救要求：{remediation or '首次讲解'}
{revision_skill}
{lesson_contract}
{environment_contract}

先读取 workspace 中的 `adaptive-lesson-flow`、`concept-teaching` 与 `knowledge-curator` Skill；如果当前路线是精进或项目实战，必须读取 `practice-drill` 与 `project-practice`，并按该 Skill 路由读取当前主题参考，核对示例与作业验收的一致性。只读取这些明确指定的 Skill/参考，不要扫描用户历史、整份知识库或其他文件。只输出一个 JSON 对象，
研究依据中的事实必须用于校验本章内容；不要编造未被来源支持的版本号或 API。不要 Markdown 围栏和过程说明。字段必须为：
title, language, practice_path, completion_mode(choice/self_practice), completion_prompt, output_patterns, output_requirements,
practice_starter_mode(provided/blank), pages(3–24 页，最后一页 type 必须为 mastery), answer_keys, interview_prompts, scope_evidence。
scope_evidence 必须逐项对应本章知识点，格式为 {{"knowledge_point_id":"原 id","page_ids":["至少两个不同的真实页面 id"]}}。
引用页面的正文、问题或代码合起来必须包含该知识点的全部覆盖词组；只在标题或元数据中点名不算覆盖。
可以附加 excerpts: [{{"page_id":"被引用页 id","quote":"该页正文、问题或代码中的原文片段"}}]，不得编造原文。
page 字段使用 id, type(explain/example/check/practice/mastery), title, eyebrow, markdown,
code, language, question, options, practice_kind(classroom/homework/null)。options 必须是对象数组，例如
[{{"id":"a","label":"选项文字"}},{{"id":"b","label":"选项文字"}}]，answer_keys 的值使用同样的小写 id。
practice_path 必须是用户目录内的文件夹路径，例如 projects/go/package-main，不能以 main.go 等文件名结尾。
除 meaning_only 不创建练习文件外，系统会自动在练习文件夹创建唯一的源文件：Go 一律为 `main.go`、Python 为 `main.py`、Java 为 `Main.java`、Rust 为 `main.rs`。所有代码页、运行命令和最终提交说明必须使用这个文件名；不得杜撰 `hello.go` 等其他文件。讲义里不得写 `$USER_DIR` 或要求学习者自行猜绝对路径。
除 meaning_only 明确禁止代码外，必须覆盖上面列出的本章每个知识点，页面按依赖顺序展开。不得在本章验收后再次生成本章余下的知识点。
每页 markdown 末尾必须用“**本页请做**：...”明确写出这一页的下一步；不得要求学生在聊天框写解释、复述或长文回答。
可用 `**关键结论**` 加粗必记结论，用 `==核心警告==` 高亮容易导致误解或 bug 的边界。每页最多 2 处加粗和 1 处高亮，不得滥用高亮或高亮整段文字。
除 meaning_only 外，所有讲解代码必须提供详细中文注释：解释陌生 API、关键行的目的和数据变化，不能只翻译语法。
首次出现超过 12 个有效行的代码时，必须先在更早的代码页展示一个更短、可运行或可理解的骨架，再逐步增加职责；不能第一张代码页直接倾倒完整长代码。8 行以上代码至少写 2 处中文注释。
choice 与 self_practice 都必须令 output_patterns=[]、output_requirements=[]；不得生成 output_patterns、终端输出框、正则验收或逐项打印结果检查。
代码型课程必须且只能有一个 practice_kind=homework 的课后练习。课堂练习只用 check 点击题；课后练习不作为进入下一章的门禁，完成后把代码、运行结果或问题直接发到右侧输入栏。
practice_starter_mode：第一个非常简单的例子可用 provided；课后需要独立完成时用 blank，给清晰步骤和最多 3 条提示，但不要给答案代码。
讲解、代码、题量和实践必须针对当前能力与当前知识点；不得输出其他语言的固定首课。选择题答案只放 answer_keys，不写进 markdown。
当路线为 interview_sprint 时，interview_prompts 必须有 2–4 项；每项字段为 id, question, reference_answer,
answer_structure, common_omissions, follow_ups。answer_structure 和 common_omissions 必须是字符串数组，不能返回单个字符串。follow_ups 每项字段为 prompt, answer_points，其中 answer_points 也必须是字符串数组。即使用户没有提供面试题也必须生成，答案要适合口述并能应对追问；其他路线可返回空数组。
"""


def _lesson_dir(server_root: Path, user_id: str) -> Path:
    if not SAFE_USER_ID.fullmatch(user_id):
        raise ValueError("invalid user_id")
    return server_root / "userdir" / f"u_{user_id}" / "lessons"


def save_lesson_bundle(server_root: Path, user_id: str, bundle: LessonBundle) -> None:
    from .lesson_versions import LessonVersionStore
    LessonVersionStore(server_root, user_id, bundle.manifest.knowledge_point_id).save(bundle)


def load_lesson_bundle(server_root: Path, user_id: str, knowledge_point_id: str) -> LessonBundle:
    from .generation_transaction import project_lock
    with project_lock(server_root, user_id):
        return _load_lesson_bundle_locked(server_root, user_id, knowledge_point_id)


def _load_lesson_bundle_locked(server_root: Path, user_id: str, knowledge_point_id: str) -> LessonBundle:
    if not re.fullmatch(r"[a-z0-9-]{1,96}", knowledge_point_id):
        raise ValueError("invalid knowledge_point_id")
    folder = _lesson_dir(server_root, user_id)
    from .lesson_versions import LessonVersionStore
    versions = LessonVersionStore(server_root, user_id, knowledge_point_id)
    if versions.pointer.exists():
        return versions.load()
    manifest = LessonManifest.model_validate_json((folder / f"{knowledge_point_id}.json").read_text(encoding="utf-8"))
    answers = json.loads((folder / f"{knowledge_point_id}.answers.json").read_text(encoding="utf-8"))
    # Preserve the untouched validated legacy wire content first. Any teaching
    # contract migration is a distinct reversible revision, not the import.
    versions.save(LessonBundle(manifest=manifest, answer_keys=answers), reason="legacy_import")
    pages = [
        page.model_copy(update={"code": _comment_legacy_code(manifest.language, page.code)})
        if page.code else page
        for page in manifest.pages
    ]
    manifest = manifest.model_copy(update={"pages": pages})
    if manifest.completion_mode in {"output", "evidence"}:
        practice_indexes = [index for index, page in enumerate(pages) if page.type == "practice"]
        if practice_indexes:
            homework_index = practice_indexes[0]
            pages[homework_index] = pages[homework_index].model_copy(update={
                "eyebrow": "课后练习",
                "title": "课后自己练一练",
                "markdown": (
                    "打开本课练习目录，参考课堂中的带注释代码，自己运行并做一个小修改。"
                    "需要独立完成时，可以先把起始代码清空再尝试。\n\n"
                    "完成后的代码、运行结果、报错或问题直接发到右侧对话输入栏；这项练习不阻塞下一章。"
                ),
                "practice_path": manifest.practice_path,
                "practice_kind": "homework",
            })
            for index in practice_indexes[1:]:
                pages[index] = pages[index].model_copy(update={
                    "type": "example",
                    "eyebrow": "课后扩展（选做）",
                    "title": "想多练时再做这一步",
                    "markdown": "这是一项可选扩展，不需要提交打印输出。想继续练时，在右侧对话框告诉我，我会按你当前的代码给提示。",
                    "practice_path": None,
                    "practice_kind": None,
                })
        mastery_index = len(pages) - 1
        pages[mastery_index] = pages[mastery_index].model_copy(update={
            "eyebrow": "课堂结束",
            "title": "课堂讲完了，课后自己练",
            "markdown": "课堂选择题通过后即可继续。课后练习已经放在项目目录；完成后的代码、运行结果或问题直接发到右侧输入栏，有问题就继续讨论。",
        })
        manifest = manifest.model_copy(update={
            "completion_mode": "self_practice",
            "completion_prompt": "课堂选择题完成后即可继续。课后练习完成时，把代码、运行结果或问题直接发到右侧输入栏。",
            "output_patterns": [],
            "output_requirements": [],
            "pages": pages,
        })
    _validate_commented_progressive_code(manifest.pages)
    bundle = LessonBundle(manifest=manifest, answer_keys=answers)
    versions.save(bundle, reason="compatibility_upgrade")
    return bundle


def generate_and_save_lesson(
    server_root: Path,
    user_id: str,
    *,
    curriculum: Curriculum,
    profile: str,
    recent_evidence: list[str],
    session_minutes: int,
    model_call: Callable[[str], str],
    remediation: str = "",
    research_evidence: str = "",
    persist: bool = True,
) -> LessonBundle:
    prompt = build_lesson_prompt(
        curriculum,
        profile=profile,
        recent_evidence=recent_evidence,
        session_minutes=session_minutes,
        remediation=remediation,
        research_evidence=research_evidence,
    )
    response = model_call(prompt)
    parse_kwargs = {
        "topic": curriculum.topic,
        "route": curriculum.route,
        "knowledge_point_id": curriculum.current_knowledge_point_id,
        "session_minutes": session_minutes,
        "chapter": curriculum.current_chapter(),
        "covered_knowledge_points": curriculum.current_chapter_remaining_points(),
    }

    def parse_generated(candidate: str) -> LessonBundle:
        parsed = parse_lesson_response(candidate, **parse_kwargs)
        _validate_scope_evidence(_extract_json(candidate), parsed, curriculum.current_chapter_remaining_points())
        return parsed

    try:
        bundle = parse_generated(response)
    except ValueError:
        try:
            bundle = parse_generated(_repair_generated_wire_format(response, curriculum.topic))
        except ValueError as repaired_error:
            chapter = curriculum.current_chapter()
            remaining_points = curriculum.current_chapter_remaining_points()
            scope = "\n".join(f"- {point.id}: {point.title}" for point in remaining_points)
            repair_prompt = f"""你刚才生成的课程 JSON 没有通过结构校验：{repaired_error}

请完整修正原课程，严格保留以下教学范围，不得换主题、换章节或加入无关课程：
- 主题：{curriculum.topic}
- 路线：{curriculum.route}
- 当前章节：{chapter.id} · {chapter.title}
- 当前知识点：{curriculum.current_knowledge_point_id}
- 本次可覆盖的知识点：
{scope}
逐项覆盖词组：{json.dumps({point.id: _scope_concepts(point.title) for point in remaining_points}, ensure_ascii=False)}

额外输出顶层 `scope_evidence` 数组，必须逐一覆盖上面所有知识点：
`{{"knowledge_point_id":"原 id","page_ids":["至少两个真实页面 id"]}}`。
每个 page_ids 引用的页面必须确实讲该知识点，且这些页面的正文、问题或代码合起来必须包含对应知识点的全部覆盖词组；不必原样重复整句知识点标题。不得只在标题或元数据点名后讲别的内容。
可附加 excerpts: [{{"page_id":"被引用页 id","quote":"该页正文、问题或代码的原文片段"}}]，不得编造原文。
请保留渐进讲解和中文注释。
特别检查：每个含 options 的页面必须在 answer_keys 中有且只有一个答案；答案 id 必须属于该页 options；page id 不得重复。
只输出一个完整 JSON 对象，不要 Markdown 代码围栏，不要解释，也不要省略任何页面。

原课程 JSON：
{response}
""".strip()
            corrected = model_call(repair_prompt)
            try:
                bundle = parse_generated(corrected)
            except ValueError:
                bundle = parse_generated(_repair_generated_wire_format(corrected, curriculum.topic))
    if persist:
        save_lesson_bundle(server_root, user_id, bundle)
    return bundle
