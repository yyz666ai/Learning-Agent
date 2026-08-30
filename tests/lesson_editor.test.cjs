const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
let editor={}; try { editor=require('../frontend/js/lesson-editor.js'); } catch(e) { if(e.code!=='MODULE_NOT_FOUND') throw e; }
test('format toolbar supports headings and inline formats without changing selected text',()=>{
 assert.equal(typeof editor.formatSelection,'function');
 for(const [kind,expected] of Object.entries({h1:'# 标题',h2:'## 标题',h3:'### 标题',bold:'**标题**',italic:'*标题*',highlight:'==标题==',underline:'<u>标题</u>'})) {
  assert.equal(editor.formatSelection('标题',0,2,kind).text,expected);
 }
});
test('formatting does not modify inline or fenced code and does not corrupt empty selection',()=>{
 assert.equal(typeof editor.formatSelection,'function');
 const source='```go\na*b\n```';
 assert.equal(editor.formatSelection(source,6,9,'bold').text,source);
 assert.equal(editor.formatSelection('使用 `a*b`',4,7,'bold').text,'使用 `a*b`');
 const empty=editor.formatSelection('',0,0,'bold');
 assert.equal(empty.text,'**文字**'); assert.equal(empty.end-empty.start,2);
});
test('revision classification requires explicit action, respects negation and quoted selection',()=>{
 assert.equal(typeof editor.isRevisionRequest,'function');
 for(const s of ['请修改这页的解释','把PPT的代码改成异步','在选中的这段补充一个例子','给课件加一张图']) assert.equal(editor.isRevisionRequest(s,true),true,s);
 for(const s of ['这页看不懂','不要修改课件，解释一下','课件不用重做','修改是什么意思','如果修改课件会怎样']) assert.equal(editor.isRevisionRequest(s,true),false,s);
});
test('draft tracks dirty state, failed persistence keeps draft and cancellation restores original',()=>{
 assert.equal(typeof editor.createDraft,'function');
 const d=editor.createDraft({id:'p1',title:'原题',markdown:'原文',code:''},'revision');
 assert.equal(d.dirty(),false); d.update('markdown','新文'); assert.equal(d.dirty(),true);
 assert.equal(d.payload('u').base_revision,'revision');
 assert.equal(d.payload('u').markdown,'新文'); d.cancel(); assert.equal(d.dirty(),false);
 assert.equal(d.payload('u').markdown,'原文');
});
const md=require('../frontend/js/markdown.js');
test('text confirmation is bound to the current pending phase only',()=>{
 assert.equal(editor.confirmationAction('确认','proposed'),'generate');
 assert.equal(editor.confirmationAction('确认','candidate'),'apply');
 assert.equal(editor.confirmationAction('取消','candidate'),'cancel');
 assert.equal(editor.confirmationAction('确认','applied'),null);
 assert.equal(editor.confirmationAction('确认生成修改稿','candidate'),null);
 assert.equal(editor.confirmationAction('应用修改','proposed'),null);
 assert.equal(editor.confirmationAction('确认这个概念是什么意思','proposed'),null);
});
test('underline is a strict extension and combined code emphasis stays coherent',()=>{
 assert.equal(md.render('<u>下划线</u>'),'<p><u>下划线</u></p>');
 assert.match(md.render('**调用 `main` 函数**'),/<strong>调用 <code>main<\/code> 函数<\/strong>/);
 assert.match(md.render('<u onclick="alert(1)">x</u>'),/&lt;u onclick=/);
 assert.doesNotMatch(md.render('<script>alert(1)</script>'),/<script>/);
 assert.match(md.render('`<u>x</u>`'),/<code>&lt;u&gt;x&lt;\/u&gt;<\/code>/);
});
test('restore uses an accessible explicit confirmation before writing a version',()=>{
 const html=fs.readFileSync(require.resolve('../frontend/index.html'),'utf8');
 const source=fs.readFileSync(require.resolve('../frontend/js/lesson-editor.js'),'utf8');
 assert.match(html,/<dialog[^>]+id="lessonRestoreDialog"[^>]+aria-labelledby="lessonRestoreTitle"/);
 assert.match(html,/id="lessonRestoreConfirm"/);
 assert.match(html,/id="lessonRestoreCancel"/);
 assert.match(source,/lessonRestoreConfirm[^\n]+addEventListener/);
 assert.match(source,/base_revision:pendingRestore\.baseRevision/);
 assert.match(source,/byId\("lessonRestoreCancel"\)\.disabled=true/);
 assert.match(source,/lessonRestoreDialog"\)\.addEventListener\("cancel",event=>\{if\(busy\)event\.preventDefault\(\)/);
});
