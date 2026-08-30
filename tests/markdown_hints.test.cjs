const {test} = require('node:test');
const assert = require('node:assert/strict');
const renderer = require('../frontend/js/markdown.js');

test('generated programming hints render as closed details with escaped contents', () => {
  const html = renderer.render('目标：取消请求\n\n<details>\n<summary>需要提示时展开</summary>\n\n- 先追踪 `ctx.Done()`\n- <img src=x onerror=alert(1)>\n\n</details>');
  assert.match(html, /<details class="markdown-hints"><summary>需要提示时展开<\/summary>/);
  assert.doesNotMatch(html, /<details[^>]*open/);
  assert.match(html, /<code>ctx.Done\(\)<\/code>/);
  assert.match(html, /&lt;img/);
  assert.doesNotMatch(html, /<img/);
});

test('arbitrary details attributes and unclosed blocks remain escaped', () => {
  for (const input of ['<details open onclick="alert(1)">\n<summary>X</summary>\n</details>', '<details>\n<summary>X</summary>']) {
    assert.doesNotMatch(renderer.render(input), /<details/);
    assert.match(renderer.render(input), /&lt;details/);
  }
});
