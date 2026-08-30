"""Immutable lesson/answer snapshots, published by one atomic current pointer."""

from __future__ import annotations

import json
import os
import re
import secrets
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from .generation_transaction import GenerationStaleError, project_lock
from .learning_content import SAFE_USER_ID
from .lesson_context import lesson_revision
from .lesson_manifest import LessonBundle, LessonManifest


def render_lesson_markdown(bundle: LessonBundle) -> str:
    """Deterministic public projection; never serialize grading/private fields."""
    lines = [f'# {bundle.manifest.title}', '', f'版本：`{lesson_revision(bundle.manifest)}`', '']
    for page in bundle.manifest.pages:
        lines.extend([f'## {page.title}', '', f'页面 ID：`{page.id}`', '', page.markdown, ''])
        if page.code:
            fence = '`' * max(3, max((len(match) + 1 for match in re.findall(r'`+', page.code)), default=3))
            lines.extend([f'{fence}{page.language or bundle.manifest.language}', page.code, fence, ''])
        if page.question:
            lines.extend([page.question, ''])
        lines.extend(f'- {option.id}. {option.label}' for option in page.options)
        lines.append('')
    return '\n'.join(lines)


def _write_markdown(path: Path, bundle: LessonBundle) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as handle:
        handle.write(render_lesson_markdown(bundle))
        handle.flush()
        os.fsync(handle.fileno())


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.write-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class LessonVersionStore:
    def __init__(self, server_root: Path, user_id: str, point: str):
        if not SAFE_USER_ID.fullmatch(user_id) or not re.fullmatch(r'[a-z0-9-]{1,96}', point):
            raise ValueError('invalid lesson owner or knowledge point')
        self.server_root, self.user_id, self.point = Path(server_root), user_id, point
        self.lessons = self.server_root / 'userdir' / f'u_{user_id}' / 'lessons'
        self.root = self.lessons / '.versions' / point
        self.pointer = self.root / 'current.json'

    def metadata(self) -> dict:
        return json.loads(self.pointer.read_text(encoding='utf-8'))

    def snapshot(self, revision: str) -> dict:
        if not re.fullmatch(r'[a-f0-9]{64}', revision):
            raise ValueError('invalid revision')
        return json.loads((self.root / f'{revision}.json').read_text(encoding='utf-8'))

    def load(self, revision: str | None = None) -> LessonBundle:
        value = self.snapshot(revision or self.metadata()['revision'])
        return LessonBundle(LessonManifest.model_validate(value['manifest']), value['answer_keys'], value.get('explanations', {}))

    def save(self, bundle: LessonBundle, *, reason: str = 'generated', base_revision: str | None = None,
             proposal_id: str | None = None, force_version: bool = False) -> LessonBundle:
        with project_lock(self.server_root, self.user_id):
            current = self.metadata() if self.pointer.exists() else None
            if base_revision is not None and (not current or current['revision'] != base_revision):
                raise GenerationStaleError('stale lesson revision; reload before changing it')
            if current and not force_version:
                existing = self.load()
                before, after = existing.manifest.model_dump(), bundle.manifest.model_dump()
                before.pop('content_version', None)
                after.pop('content_version', None)
                if before == after and existing.answer_keys == bundle.answer_keys and existing.explanations == bundle.explanations:
                    bundle.manifest.content_version = existing.manifest.content_version
                    return bundle
            original_token = bundle.manifest.content_version
            bundle.manifest.content_version = secrets.token_hex(16)
            revision = lesson_revision(bundle.manifest)
            metadata = {'revision': revision, 'reason': reason, 'created_at': datetime.now(UTC).isoformat(),
                        'proposal_id': proposal_id}
            try:
                _atomic_json(self.root / f'{revision}.json', {
                    **metadata, 'manifest': bundle.manifest.model_dump(), 'answer_keys': bundle.answer_keys, 'explanations': bundle.explanations,
                })
                _write_markdown(self.root / revision / 'lesson.md', bundle)
                _atomic_json(self.pointer, {**metadata, 'history': [*(current or {}).get('history', []), metadata]})
            except Exception:
                bundle.manifest.content_version = original_token
                raise
            # Compatibility exports are not authoritative. Readers always use
            # the paired snapshot above, even if a process stops during export.
            try:
                _atomic_json(self.lessons / f'{self.point}.json', bundle.manifest.model_dump())
                _atomic_json(self.lessons / f'{self.point}.answers.json', bundle.answer_keys)
            except OSError:
                pass
            return bundle

    def history(self) -> list[dict]:
        return [{key: entry[key] for key in ('revision', 'reason', 'created_at')}
                for entry in self.metadata()['history']]
