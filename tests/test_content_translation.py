import json
import pytest
from backend import content_translation as tr


def test_lesson_translation_preserves_ids_code_and_answers():
    original = {'lesson_id':'one','locale':'zh-CN','title':'变量', 'pages':[
        {'id':'p1','type':'check','title':'选择','code':'print("你好")', 'question':'是什么？',
         'options':[{'id':'a','label':'变量'},{'id':'b','label':'函数'}]}], 'answer_keys':{'p1':'a'}}
    units = tr.translation_units(original, 'lesson')
    assert 'print("你好")' not in units.values() and 'p1' not in units.values()
    translated = tr.apply_translation(original, 'lesson', {key:'English text' for key in units}, 'en')
    assert translated['pages'][0]['id'] == 'p1'
    assert translated['pages'][0]['code'] == original['pages'][0]['code']
    assert translated['answer_keys'] == original['answer_keys']
    assert original['title'] == '变量'
    assert translated['locale'] == 'en'
    with pytest.raises(ValueError):
        tr.apply_translation(original, 'lesson', {}, 'en')


def test_plan_translation_cannot_change_code():
    original = '# 计划\n### 阶段 1：变量\n```python\nprint(1)\n```\n'
    translated = '# Plan\n### Stage 1: Variables\n```python\nprint(1)\n```\n'
    assert tr.apply_translation(original, 'plan', {'document':translated}, 'en') == translated
    with pytest.raises(ValueError):
        tr.apply_translation(original, 'plan', {'document':translated.replace('print(1)','print(2)')}, 'en')


def test_source_hash_changes_with_content():
    assert tr.content_hash({'a':1}) == tr.content_hash({'a':1})
    assert tr.content_hash({'a':1}) != tr.content_hash({'a':2})


def test_plan_variant_keeps_original_and_becomes_unavailable_after_edit(tmp_path):
    from backend.localization import locale_context
    folder = tmp_path / 'userdir/u_alice'
    folder.mkdir(parents=True)
    original = '# 原计划\n### 阶段 1：变量\n'
    (folder / 'plan.md').write_text(original)
    (folder / 'learning-state.json').write_text('{"active_plan":"plan.md"}')
    active = tr.source(tmp_path, 'alice', 'plan')
    responses = iter([json.dumps({'translations':{'document':'# Plan\n### Stage 1: Variables\n'}}), '{"approved":true}'])
    with locale_context('en'):
        result = tr.translate(tmp_path, 'alice', 'plan', active['source_hash'], lambda _:next(responses))
    assert result['ok'] and result['locale'] == 'en'
    assert (folder / 'plan.md').read_text() == original
    assert tr.read_variant(tmp_path,'alice','plan','en')['content'].startswith('# Plan')
    (folder / 'plan.md').write_text(original + '\n原文已修改')
    with pytest.raises(FileNotFoundError):
        tr.read_variant(tmp_path,'alice','plan','en')
    with locale_context('en'), pytest.raises(ValueError):
        tr.translate(tmp_path,'alice','plan',active['source_hash'],lambda _:pytest.fail('stale source must not call model'))
