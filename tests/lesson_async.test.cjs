const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync(require.resolve('../frontend/js/artifact.js'),'utf8');
const fn=source.slice(source.indexOf('  async function checkOption('),source.indexOf('  function renderQuestion('));
function harness(){
 let resolve, timer, changed=0;
 const response=new Promise(r=>resolve=r);
 const state={manifest:{lesson_id:'lesson',revision:'old',pages:[{id:'p1'},{id:'p2'}]},pageIndex:0,quizAttempts:[],onResult:()=>changed++};
 const ctx={state,userId:'test',fetch:()=>response,byId:()=>({querySelectorAll:()=>[]}),showQuestionFeedback(){},startActivity(){},finishActivity(){},showPage(){changed++},global:{},window:{setTimeout(fn){timer=fn}}};
 vm.runInNewContext(fn,ctx);
 return {state, run:()=>ctx.checkOption({id:'p1',question:'Q'},{id:'a',label:'A'},{dataset:{}}),resolve:()=>resolve({ok:true,json:async()=>({correct:true})}),tick:()=>timer?.(),changes:()=>changed};
}
test('late quiz response cannot pass the replacement question with the same page id',async()=>{
 const h=harness(), pending=h.run();h.state.manifest={...h.state.manifest,revision:'new'};h.resolve();await pending;
 assert.equal(h.state.quizAttempts.length,0);assert.equal(h.changes(),0);
});
test('scheduled quiz advance does not navigate a newly applied lesson',async()=>{
 const h=harness(),pending=h.run();h.resolve();await pending;const before=h.changes();
 h.state.manifest={...h.state.manifest,revision:'new'};h.tick();assert.equal(h.changes(),before);
});
