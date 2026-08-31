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
test('the onboarding welcome is framework copy and changes with the selected interface language', () => {
  const source=fs.readFileSync(path.join(__dirname,'../frontend/js/app.js'),'utf8');
  assert.match(source,/addFrameworkMessage\(\"想继续以前的内容/);
  assert.match(source,/message\.frameworkKey/);
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
test('English extra-practice requests route explicitly and exclude explanations, negation and conditionals', () => {
  const source=fs.readFileSync(path.join(__dirname,'../frontend/js/app.js'),'utf8');
  const fn=source.slice(source.indexOf('  function isSupplementalPracticeRequest('),source.indexOf('  async function sendMessage('));
  const context={};require('node:vm').runInNewContext(fn,context);
  for(const message of ['Give me another coding exercise','Add a programming project','Can you give me one more practice problem?','I want more exercises'])assert.equal(context.isSupplementalPracticeRequest(message),true,message);
  for(const message of ['What is a coding exercise?','Explain this practice problem',"Don't add another exercise",'If I add another exercise, will progress reset?','Can you explain how to add an exercise?','Remove the exercise from this slide'])assert.equal(context.isSupplementalPracticeRequest(message),false,message);
});
