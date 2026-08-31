"""Technical labels need literal coverage, not artificial contiguous wording."""

import pytest

from backend.lesson_generator import _scope_concepts
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
def test_technical_terms_and_description_can_be_separated(title, concepts, bodies):
    assert _scope_concepts(title) == concepts
    validate(title, bodies)


@pytest.mark.parametrize("bodies", [
    ["track 执行依赖收集。", "再次调用 track 记录副作用。"],  # missing trigger
    ["track 记录副作用。", "trigger 通知副作用。"],  # missing description
    ["track / trigger 完整依赖收集。", "这里仅讨论数组排序。"],  # one page
    ["页面里只有 CSS 样式。", "页面里只有数组排序。"],  # title is not evidence
    ["contract / trigger 依赖收集。", "trigger 执行副作用。"],  # not track
    ["track / triggerLater 依赖收集。", "track 执行副作用。"],  # not trigger
])
def test_separated_terms_do_not_relax_required_coverage(bodies):
    with pytest.raises(ValueError, match="drifted"):
        validate("track / trigger 依赖收集", bodies)


def test_false_identifier_does_not_make_second_page_relevant():
    with pytest.raises(ValueError, match="at least two relevant pages"):
        validate("Proxy 代理", ["Proxy 是代理对象。", "NonProxy 返回普通对象。"])


def test_technical_title_still_rejects_unknown_citations():
    with pytest.raises(ValueError, match="unknown page"):
        validate("Proxy 代理", ["Proxy 是代理对象。", "Proxy 拦截读取。"], page_ids=["fake-1", "fake-2"])


def test_unrecognized_description_is_not_guessed_or_discarded():
    with pytest.raises(ValueError, match="drifted"):
        validate("Proxy 代理与边界", ["Proxy 拦截读取，是代理对象。", "Proxy 拦截写入。"])


def test_slash_list_requires_both_identifiers():
    with pytest.raises(ValueError, match="drifted"):
        validate("shallowRef / shallowReactive", ["shallowRef 保留内部对象。", "shallowRef.value 替换对象。"])


def test_single_page_error_explains_per_page_requirement_not_just_aggregate():
    with pytest.raises(ValueError) as error:
        validate("解构失响应", ["解构失响应是要检查的现象。", "普通变量不会自动更新。"])
    assert "每页至少自然出现一个覆盖词组" in str(error.value)
    assert "解构失响应" in str(error.value)
