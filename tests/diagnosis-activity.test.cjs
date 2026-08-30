const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

test('terminal diagnosis does not keep claiming to generate', () => {
  const source = fs.readFileSync('frontend/js/app.js', 'utf8');
  const fn = source.slice(source.indexOf('  function showDiagnosisActivity(job)'), source.indexOf('  window.LearningActivity ='));
  for (const status of ['failed', 'cancelled', 'interrupted']) {
    const text = {};
    const panel = {hidden:true, classList:{toggle(){}}};
    const ctx = {window:{clearInterval(){}, DiagnosisJobs:{statusText:()=>status}},
      clearTimeout(){}, showActivity:{}, activityPhaseTimer:null, activityProgressTimer:null,
      activityRun:null, $:()=>({...panel, parentElement:{}}), setText:(id,value)=>{text[id]=value;}};
    vm.createContext(ctx);
    vm.runInContext(fn + `\nshowDiagnosisActivity({status:${JSON.stringify(status)}});`, ctx);
    assert.doesNotMatch(text['#activityStatusLabel'], /正在/);
  }
});
