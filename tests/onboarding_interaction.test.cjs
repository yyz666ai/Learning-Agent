const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../frontend/js/onboarding.js'), 'utf8');
function setup(decisions) {
  const nodes = new Map(), calls = [], messages = [];
  function node(tag = 'div') {
    return {tag, hidden:false, value:'', children:[], handlers:{}, disabled:false,
      classList:{add(){},remove(){},toggle(){}}, setAttribute(){}, focus(){},
      append(...xs){this.children.push(...xs)}, replaceChildren(...xs){this.children=xs},
      addEventListener(k, fn){this.handlers[k]=fn},
      querySelectorAll(tags){return this.children.flatMap(c=>[...(tags.includes(c.tag)?[c]:[]),...c.querySelectorAll(tags)])},
    };
  }
  const document={getElementById(id){if(!nodes.has(id))nodes.set(id,node());return nodes.get(id)},createElement:node,addEventListener(){}};
  let n=0;
  const window={location:{search:'?user_id=test'},crypto:{randomUUID:()=>`id-${++n}`},LearningActivity:{start(){},finish(){}}};
  const fetch=async(url, options)=>{
    calls.push({url, body: options?.body && JSON.parse(options.body)});
    if(url==='/api/onboarding/intent') {
      const next=decisions.shift();
      return typeof next==='function' ? next() : {ok:true,json:async()=>next};
    }
    return {ok:false,json:async()=>({detail:{message:'unexpected route'}})};
  };
  vm.runInNewContext(source,{window,document,fetch,URLSearchParams,setTimeout,console});
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
