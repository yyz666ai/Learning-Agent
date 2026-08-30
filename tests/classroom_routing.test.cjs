const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require.resolve('../frontend/js/app.js'),'utf8');
const fn = source.match(/function isSupplementalPracticeRequest\(message\) \{[\s\S]*?\n  \}/)[0];
const context = {};
vm.runInNewContext(fn,context);
test('explicit extra programming project requests reach the supplemental endpoint',()=>{
  for (const text of ['再给我一个编程项目','追加一个更难的并发项目，要分三步','多出两道选择题','再练一个作业','帮我出一道编程练习']) assert.equal(context.isSupplementalPracticeRequest(text),true,text);
  for (const text of ['这个项目是什么意思','我要面试前端','这道题怎么解','我已经完成项目了']) assert.equal(context.isSupplementalPracticeRequest(text),false,text);
});
