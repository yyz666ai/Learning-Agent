"""Technical titles are passed intact; model verdicts determine coverage."""

import pytest

from backend.lesson_review import LessonCoverageError
from tests.test_scope_instructional_titles import validate


@pytest.mark.parametrize("title,concepts,bodies", [
    ("Proxy 代理", ["Proxy", "代理"], [
        "Vue 用 Proxy 包装原始对象，拦截属性读取。",
        "访问代理对象时，Proxy 的 get 会记录读取。",
    ]),
    ("track / trigger 依赖收集", ["track", "trigger", "依赖收集"], [
        "track 执行依赖收集，把当前副作用记录在集合中。",
        "trigger 通知集合中的副作用重新运行。",
    ]),
    ("`track` / `trigger` 依赖收集", ["track", "trigger", "依赖收集"], [
        "// track / trigger 完整依赖收集\nfunction track() {}",
        "读取时执行 track，写入时执行 trigger。",
    ]),
    ("Promise 异步结果", ["Promise", "异步结果"], [
        "Promise 表示未来才完成的操作，其异步结果可成功也可失败。",
        "调用 Promise.resolve 可以创建已兑现的对象。",
    ]),
    ("shallowRef / shallowReactive", ["shallowRef", "shallowReactive"], [
        "shallowRef 仅跟踪 .value 替换，内部对象保持原样。",
        "shallowReactive 只代理对象第一层属性。",
    ]),
])
def test_technical_titles_are_not_split_into_keyword_obligations(title, concepts, bodies):
    # concepts was the old lexical policy: deliberately no longer evaluated.
    report = validate(title, bodies)
    assert report.coverage[0].status == "covered"


@pytest.mark.parametrize("title", ["track / trigger 依赖收集", "命令行 / 终端", "Proxy 代理与边界"])
def test_title_presence_cannot_overrule_a_negative_semantic_verdict(title):
    with pytest.raises(LessonCoverageError):
        validate(title, [title, "仅点名，尚未讲解"], status="missing")
