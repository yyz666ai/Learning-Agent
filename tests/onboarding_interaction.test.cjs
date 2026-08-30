const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../frontend/js/onboarding.js'), 'utf8');
function setup(decisions, extraFetch = null) {
  const nodes = new Map(), calls = [], messages = [];
  function node(tag = 'div') {
    return {tag, hidden:false, value:'', children:[], handlers:{}, disabled:false,
      classList:{add(){},remove(){},toggle(){}}, setAttribute(){}, focus(){},
      append(...xs){this.children.push(...xs)}, replaceChildren(...xs){this.children=xs},
      addEventListener(k, fn){this.handlers[k]=fn},
      querySelectorAll(tags){return this.children.flatMap(c=>[...(tags.includes(c.tag)?[c]:[]),...c.querySelectorAll(tags)])},
    };
  }
  const document={getElementById(id){if(!nodes.has(id))nodes.set(id,node());return nodes.get(id)},createElement:node,addEventListener(event,callback){if(event==='DOMContentLoaded')callback()}};
  let n=0;
  const window={location:{search:'?user_id=test'},crypto:{randomUUID:()=>`id-${++n}`},setTimeout:fn=>setTimeout(fn,0),LearningActivity:{start(){},finish(){},diagnosis(){},startPlanGeneration(){}}};
  const fetch=async(url, options)=>{
    calls.push({url, body: options?.body && JSON.parse(options.body)});
    if(url==='/api/onboarding/intent') {
      const next=decisions.shift();
      return typeof next==='function' ? next() : {ok:true,json:async()=>next};
    }
    return extraFetch ? extraFetch(url, options) : {ok:false,json:async()=>({detail:{message:'unexpected route'}})};
  };
  vm.runInNewContext(source,{window,document,fetch,URLSearchParams,setTimeout,console});
  window.DiagnosisJobs={...require('../frontend/js/diagnosis-job.js'),waitForDiagnosis:options=>require('../frontend/js/diagnosis-job.js').waitForDiagnosis({...options,fetcher:fetch,sleep:async()=>{}})};
  window.OnboardingController.begin({addUser:x=>messages.push(['user',x]),addAgent:x=>messages.push(['agent',x])});
  return {c:window.OnboardingController,nodes,calls,messages,window};
}
const clarification=(slot='desired_outcome', options=[])=>({action:'clarify',summary:'继续',slots:{topic:'Go'},
  session_id:'session',revision:1,question:{slot,prompt:'想达成什么？',options}});
const options=[{id:'a',label:'读代码',detail:'阅读'},{id:'b',label:'写项目',detail:'实现'}];
test('free-text last row sends once, no preselection and respects IME',async()=>{
  const x=setup([clarification('desired_outcome',options),clarification()]);
  await x.c.handleText('学Go');
  assert.equal(x.calls.length,1);
  const row=x.nodes.get('inlineChoices').children.at(-1);
  const input=row.children.find(n=>n.tag==='textarea');
  assert.ok(input,'last row must be directly editable');
  input.value='先读懂现有项目';
  await input.handlers.keydown({key:'Enter',isComposing:true,preventDefault(){}});
  assert.equal(x.calls.length,1);
  await input.handlers.keydown({key:'Enter',shiftKey:false,isComposing:false,preventDefault(){}});
  assert.equal(x.calls.length,2);
  assert.equal(x.calls[1].body.message,'先读懂现有项目');
  assert.equal(x.messages.filter(m=>m[0]==='user'&&m[1]==='先读懂现有项目').length,1);
});
test('natural no-material reply always uses semantic intent path',async()=>{
  const x=setup([clarification('interview_question_source'),clarification()]);
  await x.c.handleText('面试前端');
  await x.c.handleText('暂时没有，你先按常见题准备');
  assert.equal(x.calls[1].url,'/api/onboarding/intent');
});
test('first message material already ingested does not ask for another paste',async()=>{
  const x=setup([{action:'interview_bank_intake',summary:'收到',slots:{topic:'Java',interview_question_count:2},
    session_id:'session',revision:1},clarification()]);
  await x.c.handleText('题目：1. 什么是锁？2. 什么是事务？');
  assert.equal(x.calls.length,2,'continue with authoritative ingested count');
  assert.equal(x.calls[1].body.continue_after_intake,true);
  assert.equal(x.messages.some(m=>m[1].includes('直接粘贴到输入框即可')),false);
});

test('empty input and stale choice do not submit',async()=>{
  const x=setup([clarification('desired_outcome',options),clarification()]);
  await x.c.handleText('学Go');
  const row=x.nodes.get('inlineChoices').children.at(-1);
  const input=row.children.find(n=>n.tag==='textarea');
  input.value='   ';
  await input.handlers.keydown({key:'Enter',preventDefault(){}});
  assert.equal(x.calls.length,1);
  x.c.stop();
  input.value='旧答案';
  await input.handlers.keydown({key:'Enter',preventDefault(){}});
  assert.equal(x.calls.length,1);
});

test('late transport error cannot overwrite new onboarding',async()=>{
  let reject;
  const x=setup([()=>new Promise((resolve,no)=>{reject=no})]);
  const pending=x.c.handleText('旧请求');
  x.c.stop();
  x.c.begin({});
  x.nodes.get('onboardingError').hidden=true;
  reject(new Error('late failure'));
  await pending;
  assert.equal(x.nodes.get('onboardingError').hidden,true);
});

test('self-hosted plain HTTP without randomUUID still sends',async()=>{
  const x=setup([clarification()]);
  x.window.crypto={};
  x.c.begin({});
  await x.c.handleText('学Go');
  assert.match(x.calls[0].body.request_id,/^intent-/);
});

const ready=()=>({action:'ready_for_plan',summary:'开始',slots:{topic:'Go'},session_id:'session',revision:1,
  onboarding:{topic_type:'custom',goal_route:'gap_upgrade',level_claim:'some',learning_mode:'systematic',session_minutes:25,concept_scope:'not_applicable'}});
const diag={session_id:'diagnostic',complete:false,answered_count:0,question:{id:'q1',prompt:'问题必须保留',options:[{id:'a',label:'答案A'}]}};
test('diagnosis uses short job endpoint and retains preface and question',async()=>{
  const x=setup([ready()],async url=>({ok:true,json:async()=>url.startsWith('/api/projects/match')?{project:null}:{status:'completed',result:diag}}));
  await x.c.handleText('我有Go基础');
  assert.ok(x.calls.some(c=>c.url==='/api/onboarding/diagnosis/start'));
  assert.ok(!x.calls.some(c=>c.url==='/api/onboarding/start'));
  assert.ok(x.messages.some(m=>m[1].includes('一定基础')));
  assert.ok(x.messages.some(m=>m[1]==='问题必须保留'));
});
test('late diagnosis completion cannot render into a stopped session',async()=>{
  let release;
  const x=setup([ready()],async url=>url.startsWith('/api/projects/match')||url.endsWith('/cancel')?{ok:true,json:async()=>({project:null})}:new Promise(resolve=>{release=()=>resolve({ok:true,json:async()=>({status:'completed',result:diag})});}));
  const pending=x.c.handleText('我有Go基础');
  for(let i=0;i<40&&!release;i++)await Promise.resolve();
  assert.ok(release);x.c.stop();release();await pending;
  assert.ok(!x.messages.some(m=>m[1]==='问题必须保留'));
});

test('refresh after cancellation starts a fresh job for the persisted intent',async()=>{
  const old={request_id:'cancelled-old',status:'cancelled',retryable:false,intent_session_id:'session',intent_revision:1};
  const x=setup([],async(url,options)=>{
    const value=url.startsWith('/api/onboarding/intent-state')?ready():url.endsWith('/cancel')?old:
      JSON.parse(options.body).request_id==='cancelled-old'?old:{status:'completed',result:diag};
    return {ok:true,json:async()=>value};
  });
  x.window.DiagnosisJobs.readJob=async()=>old;
  x.c.begin({restorePersistedIntent:true,addAgent:text=>x.messages.push(['agent',text])});
  for(let i=0;i<60;i++)await Promise.resolve();
  const starts=x.calls.filter(c=>c.url==='/api/onboarding/diagnosis/start');
  assert.equal(starts.length,1);
  assert.notEqual(starts[0].body.request_id,'cancelled-old');
  assert.ok(x.messages.some(m=>m[1]==='问题必须保留'));
});

test('retry on a cancelled old page revalidates intent before choosing a new id',async()=>{
  let starts=0;
  const old={request_id:'cancelled-old',status:'cancelled',retryable:false,intent_session_id:'session',intent_revision:1};
  const x=setup([ready()],async url=>({ok:true,json:async()=>
    url.startsWith('/api/projects/match')?{project:null}:
    url.startsWith('/api/onboarding/intent-state')?ready():
    ++starts===1?old:{status:'completed',result:diag}}));
  x.window.DiagnosisJobs.readJob=async()=>old;
  await x.c.handleText('我有Go基础');
  const initial=x.calls.find(c=>c.url==='/api/onboarding/diagnosis/start').body.request_id;
  await x.nodes.get('retryOnboardingBtn').handlers.click();
  assert.ok(x.calls.some(c=>c.url.startsWith('/api/onboarding/intent-state')));
  const attempts=x.calls.filter(c=>c.url==='/api/onboarding/diagnosis/start');
  assert.notEqual(attempts.at(-1).body.request_id,initial);
});

for(const delayed of ['confirm','plan'])test(`late ${delayed} response cannot affect a new onboarding session`,async()=>{
  let release,planReady=0;
  const x=setup([ready()],async url=>{
    let value;
    if(url.startsWith('/api/projects/match'))value={project:null};
    else if(url==='/api/onboarding/diagnosis/start')value={status:'completed',result:{...diag,complete:true}};
    else if(url==='/api/onboarding/confirm')value={generation_id:'generation'};
    else if(url==='/api/plans/personalize/start')value={status:'queued'};
    else value={status:'completed',result:{personalized:true,plan_markdown:'old plan'}};
    if((delayed==='confirm'&&url==='/api/onboarding/confirm')||(delayed==='plan'&&url.startsWith('/api/plans/personalize/status')))
      return new Promise(resolve=>{release=()=>resolve({ok:true,json:async()=>value})});
    return {ok:true,json:async()=>value};
  });
  const pending=x.c.handleText('我有Go基础');
  for(let i=0;i<40&&!release;i++)await new Promise(resolve=>setTimeout(resolve,1));
  assert.ok(release);
  x.c.stop();x.c.begin({onPlanReady:()=>planReady++});
  x.nodes.get('sendBtn').disabled=true;
  release();await pending;
  assert.equal(planReady,0);
  assert.equal(x.nodes.get('sendBtn').disabled,true,'old finally cannot unlock new UI');
  if(delayed==='confirm')assert.ok(!x.calls.some(c=>c.url==='/api/plans/personalize/start'));
});
