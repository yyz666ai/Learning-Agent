const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const sourcePath = path.join(__dirname, '../frontend/js/i18n.js');
function create(options = {}) {
  assert.ok(fs.existsSync(sourcePath), 'central explicit i18n module must exist');
  return require(sourcePath).createI18n(options);
}
test('Chinese is default regardless of browser language and keys interpolate safely', () => {
  const i = create({ navigator: { language: 'en-US' } });
  assert.equal(i.getLocale(), 'zh-CN');
  assert.equal(i.t('发送'), '发送');
  assert.equal(i.t('大纲 {0} / {1}', {0: 2, 1: 5}), '大纲 2 / 5');
});
test('English explicit dictionary translates framework, preserving unknown and user text', async () => {
  const i = create();
  await i.setLocale('en');
  assert.equal(i.t('发送'), 'Send');
  assert.equal(i.t('大纲 {0} / {1}', {0: 2, 1: 5}), 'Outline 2 / 5');
  assert.equal(i.t('我的课程原文'), '我的课程原文');
});
test('bound interface updates immediately while unbound history is untouched', async () => {
  const i = create();
  const label = {textContent: '', isConnected: true};
  const history = {textContent: '发送'};
  i.bind(label, 'textContent', () => i.t('发送'));
  await i.setLocale('en');
  assert.equal(label.textContent, 'Send');
  assert.equal(history.textContent, '发送');
  await i.setLocale('zh-CN');
  assert.equal(label.textContent, '发送');
});
test('a generated replacement takes ownership from an old placeholder binding', async () => {
  const i = create();
  const node = {textContent:'', isConnected:true};
  i.bind(node, 'textContent', () => i.t('发送'));
  node.textContent = '课程原文';
  await i.setLocale('en');
  assert.equal(node.textContent, '课程原文');
});
test('unknown legacy Chinese errors get an honest English fallback, not false translation', async () => {
  const i = create();
  await i.setLocale('en');
  assert.doesNotMatch(i.errorText('后台意外旧错误'), /\p{Script=Han}/u);
  assert.match(i.errorText('后台意外旧错误'), /diagnostic/i);
  assert.equal(i.errorText('Network unavailable'), 'Network unavailable');
});
test('preference caches are user-scoped and remote save failure remains visible', async () => {
  const records = new Map();
  const storage = {getItem: k => records.get(k), setItem: (k,v) => records.set(k,v)};
  const first = create({userId:'alice', storage, fetcher: async () => ({ok:false})});
  await first.setLocale('en');
  assert.equal(first.getLocale(), 'en');
  assert.equal(first.persistenceStatus(), 'unsaved');
  assert.equal(create({userId:'bob', storage}).getLocale(), 'zh-CN');
  assert.equal(create({userId:'alice', storage}).getLocale(), 'en');
});
test('a slow preference read cannot overwrite a language the user just chose', async () => {
  let finishRead;
  const i=create({fetcher:async (url,options)=>options?.method==='PUT'?{ok:true}:new Promise(resolve=>{finishRead=()=>resolve({ok:true,json:async()=>({locale:'zh-CN'})})})});
  const pending=i.loadPreference();
  await i.setLocale('en');
  finishRead();await pending;
  assert.equal(i.getLocale(),'en');
});
test('rapid preference saves are ordered so the last selection wins on the server', async () => {
  let finishFirst; const locales=[];
  const i=create({fetcher:async (url,options)=>{
    locales.push(JSON.parse(options.body).locale);
    if(locales.length===1)await new Promise(resolve=>{finishFirst=resolve});
    return {ok:true};
  }});
  const first=i.setLocale('en');
  for(let tick=0;tick<5&&!finishFirst;tick++)await Promise.resolve();
  const second=i.setLocale('zh-CN');
  finishFirst();await Promise.all([first,second]);
  assert.deepEqual(locales,['en','zh-CN']);
  assert.equal(i.getLocale(),'zh-CN');
});
test('API header captures current locale but explicit job snapshot wins', async () => {
  const calls = [];
  const i = create({fetcher: async (...args) => { calls.push(args); return {ok:true,json:async()=>({locale:'en'})}; }});
  await i.setLocale('en');
  await i.fetch('/api/chat', {method:'POST'});
  assert.equal(new Headers(calls.at(-1)[1].headers).get('X-Learning-Locale'), 'en');
  await i.fetch('/api/lesson/generate/start', {headers:{'X-Learning-Locale':'zh-CN'}});
  assert.equal(new Headers(calls.at(-1)[1].headers).get('X-Learning-Locale'), 'zh-CN');
  await i.fetch('https://example.org/api/chat', {});
  assert.equal(new Headers(calls.at(-1)[1].headers).has('X-Learning-Locale'), false);
});
test('a retried diagnosis retains its creation language after the UI switches', async () => {
  const jobs = require('../frontend/js/diagnosis-job.js');
  const starts = [];
  let call = 0;
  await jobs.waitForDiagnosis({payload:{user_id:'test',request_id:'same',locale:'zh-CN'}, sleep:async()=>{},
    fetcher:async (url, options) => {
      starts.push(options);
      if (++call === 1) throw new Error('lost response');
      return {ok:true,json:async()=>({status:'completed',result:{}})};
    }});
  assert.equal(starts.length, 2);
  assert.ok(starts.every(options => new Headers(options.headers).get('X-Learning-Locale') === 'zh-CN'));
});
test('language control is shared and static copy is annotated explicitly', () => {
  const html = fs.readFileSync(path.join(__dirname, '../frontend/index.html'),'utf8');
  assert.match(html, /id="languageMenuButton"/);
  assert.match(html, /bi-globe2/);
  assert.match(html, /data-locale="zh-CN"/);
  assert.match(html, /data-locale="en"/);
  assert.match(html, /data-i18n-aria-label="发送"/);
  assert.ok(html.indexOf('/js/i18n.js') < html.indexOf('/js/onboarding.js'));
});
function translations() {
  const file = path.join(__dirname, '../frontend/js/translations.js');
  assert.ok(fs.existsSync(file), 'explicit translation action module must exist');
  return require(file);
}
test('translation requires confirmation and cancellation never creates a model job', async () => {
  const calls=[];
  await translations().requestTranslation({userId:'test',kind:'lesson',locale:'en',confirm:()=>false,
    fetcher:async url=>{calls.push(url);return {ok:true,json:async()=>({source_hash:'one',locale:'zh-CN'})}}});
  assert.equal(calls.length, 1);
  assert.match(calls[0], /translations\/source/);
});
test('translation snapshot is explicit and stale source results are rejected', async () => {
  const calls=[]; let sources=0;
  await assert.rejects(translations().requestTranslation({userId:'test',kind:'lesson',locale:'en',confirm:()=>true,sleep:async()=>{},
    fetcher:async (url,options)=>{
      calls.push([url,options]);
      return {ok:true,json:async()=>url.includes('/source')?{source_hash:++sources===1?'one':'changed'}:
        url.includes('/start')?{generation_id:'job'}:{status:'completed',result:{ok:true,source_hash:'one',locale:'en',content:{pages:[]}}}};
    }}), /source_changed/);
  const start=calls.find(([url])=>url.includes('/start'));
  assert.equal(JSON.parse(start[1].body).locale, 'en');
  assert.equal(new Headers(start[1].headers).get('X-Learning-Locale'), 'en');
});
test('English lesson-edit and confirmation commands keep the existing explicit-confirmation safety', () => {
  const editor=require('../frontend/js/lesson-editor.js');
  assert.equal(editor.isRevisionRequest('Add an example to this slide'), true);
  assert.equal(editor.isRevisionRequest("Do not edit this slide"), false);
  assert.equal(editor.isRevisionRequest('Explain this slide'), false);
  assert.equal(editor.isRevisionRequest('Can you explain how to add an example to this slide?'), false);
  assert.equal(editor.isRevisionRequest('Can I edit this slide?'), false);
  assert.equal(editor.confirmationAction('Confirm draft generation','proposed'),'generate');
  assert.equal(editor.confirmationAction('Apply changes','candidate'),'apply');
  assert.equal(editor.confirmationAction('Apply changes','proposed'),null);
  assert.equal(editor.confirmationAction('Keep original','candidate'),'cancel');
});
test('deterministic platform notices are explicit English copy, not model-content translation', async () => {
  const i=create();await i.setLocale('en');
  for (const notice of ['系统通知需要保持本机服务运行，并在系统设置中允许通知。','当前平台尚不支持系统通知；提醒偏好仍可保存，但不会发送通知。','当前环境没有可用桌面，请手动打开此路径。']) {
    assert.doesNotMatch(i.t(notice), /\p{Script=Han}/u);
  }
});
test('preference GET and PUT abort promptly even when transport never settles', async () => {
  const signals=[];
  const i=create({preferenceTimeoutMs:5,fetcher:(url,options)=>{signals.push(options?.signal);return new Promise(()=>{})}});
  const timeout=()=>new Promise(resolve=>setTimeout(()=>resolve('hung'),70));
  assert.equal(await Promise.race([i.loadPreference().then(()=>'done'),timeout()]),'done');
  assert.equal(await Promise.race([i.setLocale('en').then(()=>'done'),timeout()]),'done');
  assert.equal(i.persistenceStatus(),'unsaved');
  assert.ok(signals.every(signal=>signal?.aborted));
});
test('completion framework translates exact templates but preserves lesson titles and model feedback', async () => {
  const i=create();await i.setLocale('en');
  assert.equal(i.completionText('查看课程总结'),'View course summary');
  assert.equal(i.completionText('开始下一章：原始标题'),'Start next chapter: 原始标题');
  assert.match(i.completionText('这些选择题还需要先答对：原题A、原题B。回到对应页面直接点击选项，不需要写文字回答。'),/^First answer these questions correctly: 原题A、原题B/);
  assert.equal(i.completionText('模型关于你的特殊问题的原始解释'),'模型关于你的特殊问题的原始解释');
});
test('completed-job locale notice follows UI language without relabeling the result', async () => {
  const nodes={languageJobNotice:{hidden:true,textContent:''}};
  const document={documentElement:{},getElementById:id=>nodes[id],querySelectorAll:()=>[]};
  const i=create({document});await i.setLocale('en');
  const result={locale:'zh-CN',content:'原内容'};
  i.noticeJobLocale('lesson',result.locale);
  assert.equal(nodes.languageJobNotice.hidden,false);
  assert.match(nodes.languageJobNotice.textContent,/Chinese/);
  assert.equal(result.content,'原内容');
  assert.equal(result.locale,'zh-CN');
  await i.setLocale('zh-CN');assert.equal(nodes.languageJobNotice.hidden,true);
});
test('English extra-practice requests route explicitly and exclude explanations, negation and conditionals', () => {
  const source=fs.readFileSync(path.join(__dirname,'../frontend/js/app.js'),'utf8');
  const fn=source.slice(source.indexOf('  function isSupplementalPracticeRequest('),source.indexOf('  async function sendMessage('));
  const context={};require('node:vm').runInNewContext(fn,context);
  for(const message of ['Give me another coding exercise','Add a programming project','Can you give me one more practice problem?','I want more exercises'])assert.equal(context.isSupplementalPracticeRequest(message),true,message);
  for(const message of ['What is a coding exercise?','Explain this practice problem',"Don't add another exercise",'If I add another exercise, will progress reset?','Can you explain how to add an exercise?','Remove the exercise from this slide'])assert.equal(context.isSupplementalPracticeRequest(message),false,message);
});
test('read-only lesson translation renders completion and every interview field while preserving code and source', async () => {
  const api=translations();
  assert.equal(typeof api.renderLessonVariant,'function','production translation renderer must be available');
  const element=tag=>({tagName:tag.toUpperCase(),children:[],dataset:{},textContent:'',innerHTML:'',isConnected:true,append(...items){this.children.push(...items)}});
  const document={createElement:element};
  const body=element('article');
  const i=create();await i.setLocale('en');
  const manifest={completion_prompt:'Complete the final quiz, then reflect.',pages:[{id:'page-1',title:'Translated page',markdown:'Page body.',code:'const text = "<unsafe>原代码";',question:'Which value?',options:[{id:'a',label:'Answer A'}]}],
    interview_prompts:[{question:'Explain a mutex.',reference_answer:'Mutual exclusion. <script>unsafe()</script>',answer_structure:['State the purpose.','Give an example.'],common_omissions:['Ownership details.'],follow_ups:[{prompt:'What about fairness?',answer_points:['Fairness is not guaranteed.','Discuss starvation.']}]}]};
  const snapshot=JSON.stringify(manifest);
  api.renderLessonVariant(body,manifest,{document,markdown:require('../frontend/js/markdown.js'),i18n:i});
  const flatten=node=>[node,...node.children.flatMap(flatten)];
  const all=flatten(body), text=()=>all.map(node=>node.textContent+' '+node.innerHTML).join('\n');
  for(const expected of ['Completion instructions','Complete the final quiz, then reflect.','Interview delivery practice','Explain a mutex.','Reference answer','Mutual exclusion.','Answer structure','State the purpose.','Give an example.','Common omissions','Ownership details.','Follow-up questions','What about fairness?','Answer points','Fairness is not guaranteed.','Discuss starvation.'])assert.ok(text().includes(expected),expected);
  const code=all.find(node=>node.tagName==='CODE');assert.equal(code.textContent,manifest.pages[0].code);assert.equal(code.innerHTML,'');
  assert.ok(!text().includes('<script>unsafe()'));
  assert.ok(!all.some(node=>['INPUT','TEXTAREA','BUTTON'].includes(node.tagName)),'translated lesson has no mutation controls');
  assert.equal(JSON.stringify(manifest),snapshot);
  await i.setLocale('zh-CN');assert.ok(text().includes('结课说明'));assert.ok(text().includes('Explain a mutex.'));
});
