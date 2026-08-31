"""Per-request locale: never mutate process-global language or learning identity."""
from __future__ import annotations

import json
import re
from contextlib import contextmanager
from contextvars import ContextVar, copy_context
from pathlib import Path

_locale = ContextVar('learning_locale', default=None)
SUPPORTED = ('zh-CN', 'en')


def normalize_locale(value):
    if value not in SUPPORTED:
        raise ValueError('Unsupported language; use zh-CN or en')
    return value


def current_locale():
    return _locale.get() or 'zh-CN'


def text(zh, en):
    return en if current_locale() == 'en' else zh


@contextmanager
def locale_context(locale):
    token = _locale.set(normalize_locale(locale))
    try:
        yield
    finally:
        _locale.reset(token)


def submit_localized(executor, fn, *args, **kwargs):
    return executor.submit(copy_context().run, fn, *args, **kwargs)


def _preference_path(root, user_id):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', user_id):
        raise ValueError('Invalid user_id')
    return Path(root) / 'userdir' / f'u_{user_id}' / 'preferences.json'


def read_preferences(root, user_id):
    path = _preference_path(root, user_id)
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        value = {}
    if not isinstance(value, dict):
        raise ValueError('Invalid preferences')
    return {**value, 'locale': normalize_locale(value.get('locale', 'zh-CN'))}


def save_preferences(root, user_id, locale):
    from .generation_transaction import project_lock
    from .user_memory import _atomic_json
    normalize_locale(locale)
    path = _preference_path(root, user_id)
    with project_lock(Path(root), user_id):
        value = {**read_preferences(root, user_id), 'locale': locale}
        _atomic_json(path, value)
    return value


def language_instruction(locale=None):
    language = 'English' if (locale or current_locale()) == 'en' else 'Simplified Chinese'
    from .plan_locale import english_plan_contract
    return (f'\n[Application output language: {language}]\n'
            f'Write all learner-facing questions, choices, explanations, feedback, plan headings, '
            f'lessons, exercises and instructional code comments in {language}. '
            'This language setting overrides Chinese-only wording and examples in teaching skills/templates. '
            'Preserve JSON field names, enums, programming-language identifiers, page/question/option IDs, '
            'answer references, executable code, file paths and commands. Do not translate user submissions '
            'or quoted source text. Source material language does not change the output language. '
            'For an English Markdown Plan use equivalent English headings and field labels.\n'
            + (english_plan_contract() if language == 'English' else ''))


def model_language_instruction(root, user_id):
    locale = _locale.get()
    if locale is None:
        locale = read_preferences(root, user_id)['locale']
    return language_instruction(locale)
