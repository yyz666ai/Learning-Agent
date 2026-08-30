const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
test('HTTP 200 with opened false never announces successful folder opening',async()=>{
  const source=fs.readFileSync(require.resolve('../frontend/js/artifact.js'),'utf8');
  const code=source.slice(source.indexOf('  async function openPracticeFolder('),source.indexOf('  function bind()'));
  const feedback=[],button={disabled:false,textContent:''};
  const ctx={fetch:async()=>({ok:true,json:async()=>({opened:false,message:'没有桌面',resolved_path:'/srv/练习'})}),userId:'test',state:{onResult:x=>feedback.push(x)},window:{setTimeout(){}}};
  vm.runInNewContext(code,ctx);await ctx.openPracticeFolder('projects/demo',button);
  assert.ok(!button.textContent.includes('已打开'));
  assert.ok(feedback.some(f=>f.feedback.includes('/srv/练习')&&f.feedback.includes('没有桌面')));
});
