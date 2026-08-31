const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const read = name => fs.readFileSync(require.resolve(`../frontend/${name}`), 'utf8');

function harness() {
  const nodes = new Map(), events = new Map(), storage = new Map();
  const effects = [];
  function node(id) {
    if (!nodes.has(id)) {
      const classes = new Set(), handlers = new Map(), attrs = new Map();
      nodes.set(id, {
        hidden: false, value: '', textContent: '', dataset: {}, children: [],
        classList: {add: (...names) => names.forEach(n => classes.add(n)), remove: (...names) => names.forEach(n => classes.delete(n)), contains: n => classes.has(n), toggle(n, force) {const on = force ?? !classes.has(n); on ? classes.add(n) : classes.delete(n); return on;}},
        setAttribute: (k, v) => attrs.set(k, v), getAttribute: k => attrs.get(k),
        addEventListener: (name, fn) => handlers.set(name, fn), dispatch: (name, event = {}) => handlers.get(name)?.(event),
        querySelectorAll: () => [], querySelector: () => node(`${id}-icon`),
        append(...items) {this.children.push(...items);}, replaceChildren(...items) {this.children = items;},
        focus() {effects.push(`focus:${id}`);}, showModal() {effects.push(`open:${id}`);}, close() {effects.push(`close:${id}`);},
      });
    }
    return nodes.get(id);
  }
  const document = {querySelector: selector => node(selector.replace(/^#/, '')), querySelectorAll: () => [], getElementById: node, createElement: tag => node(`new-${tag}-${nodes.size}`), addEventListener: (name, fn) => events.set(name, fn)};
  const window = {document, location: {search: '?user_id=test%20user', href: ''}, addEventListener() {}, confirm: () => false, MarkdownRenderer: {render: text => text, hydrate() {}}};
  const context = {window, document, URLSearchParams, localStorage: {getItem: key => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value), removeItem: key => storage.delete(key)}, fetch: async path => {effects.push(`fetch:${path}`); return {ok: true, json: async () => ({lesson: {lesson_id: 'l1'}, history: [], can_undo: false})};}, console};
  // Run real event binding, excluding only asynchronous startup/network hydration.
  vm.runInNewContext(read('js/app.js').replace('bind(); initialize();', 'bind();'), context);
  events.get('DOMContentLoaded')();
  vm.runInNewContext(read('js/lesson-editor.js'), context);
  node('reopenArtifactBtn').hidden = true;
  return {node, window, storage, effects, emit: (name, detail) => events.get(name)?.({detail})};
}

test('close and reopen preserve the current page and dirty editor without reset or requests', async () => {
  const h = harness(), page = {id: 'p2', title: '第二页', markdown: '原文', code: ''};
  h.emit('learning-agent:manifest-change', {lesson_id: 'l1', revision: 'r1', pages: [page]});
  h.emit('learning-agent:page-change', {page, index: 1, total: 3});
  await Promise.resolve(); await Promise.resolve();
  h.node('lessonEditBtn').dispatch('click');
  h.node('editorMarkdown').value = '未保存草稿';
  h.node('editorMarkdown').dispatch('input');
  const saved = [...h.storage]; h.effects.length = 0;
  h.node('collapseArtifactBtn').dispatch('click');
  assert.equal(h.node('appShell').classList.contains('is-artifact-collapsed'), true);
  assert.equal(h.node('appShell').classList.contains('is-chat-first'), false);
  assert.equal(h.node('appShell').classList.contains('is-onboarding'), false);
  assert.equal(h.node('reopenArtifactBtn').hidden, false);
  h.node('reopenArtifactBtn').dispatch('click');
  assert.equal(h.node('appShell').classList.contains('is-artifact-collapsed'), false);
  assert.equal(h.node('reopenArtifactBtn').hidden, true);
  assert.equal(h.node('editorMarkdown').value, '未保存草稿');
  assert.equal(h.node('editorTitle').value, '第二页');
  assert.equal(h.window.LessonEditor.hasDraft(), true);
  assert.deepEqual([...h.storage], saved);
  assert.equal(h.effects.some(effect => !effect.startsWith('focus:')), false);
});

test('edit lock and pencil expose state and preserve dirty confirmation', () => {
  const h = harness(), page = {id: 'p1', title: '标题', markdown: '正文'};
  h.emit('learning-agent:manifest-change', {lesson_id: 'l1', revision: 'r1', pages: [page]});
  h.emit('learning-agent:page-change', {page});
  const button = h.node('lessonEditBtn');
  assert.match(button.getAttribute('aria-label') || '', /只读/);
  assert.match(h.node('lessonEditBtn-icon').className || '', /bi-lock/);
  button.dispatch('click');
  assert.equal(button.getAttribute('aria-expanded'), 'true');
  assert.match(h.node('lessonEditBtn-icon').className, /bi-pencil/);
  h.node('editorMarkdown').value = '新草稿'; h.node('editorMarkdown').dispatch('input');
  button.dispatch('click');
  assert.equal(h.window.LessonEditor.hasDraft(), true);
  h.window.confirm = () => true; button.dispatch('click');
  assert.equal(button.getAttribute('aria-expanded'), 'false');
  assert.match(h.node('lessonEditBtn-icon').className, /bi-lock/);
  assert.equal(h.window.LessonEditor.isOpen(), false);
});

test('history closes settings first and bug export works without a generated lesson', async () => {
  const h = harness();
  await h.node('lessonHistoryBtn').dispatch('click');
  assert.deepEqual(h.effects, ['close:settingsDialog', 'open:lessonHistoryDialog']);
  h.node('bugReportExportBtn').dispatch('click');
  assert.equal(h.window.location.href, '/api/support/bug-report?user_id=test%20user');
});

test('infrequent controls live only in settings and editing icons live in topbar', () => {
  const html = read('index.html');
  const settings = html.slice(html.indexOf('id="settingsDialog"'), html.indexOf('id="reminderDialog"'));
  const topbar = html.slice(html.indexOf('<header class="artifact-topbar"'), html.indexOf('<p id="editorStatus"'));
  for (const id of ['lessonHistoryBtn', 'lessonExportBtn', 'bugReportExportBtn']) {
    assert.match(settings, new RegExp(`id="${id}"`));
    assert.equal(html.split(`id="${id}"`).length, 2);
    assert.doesNotMatch(topbar, new RegExp(`id="${id}"`));
  }
  for (const id of ['lessonEditBtn', 'lessonUndoBtn']) {
    assert.match(topbar, new RegExp(`<button[^>]*id="${id}"[^>]*aria-label="[^"]+"[^>]*><i[^>]*aria-hidden="true"[^>]*></i></button>`));
  }
  assert.match(html, /id="reopenArtifactBtn"[^>]*aria-controls="artifactPane"[^>]*hidden/);
});
