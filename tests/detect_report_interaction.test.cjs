// Offline JS contract tests with a small fake DOM; NOT browser/visual acceptance.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');

function mount({storageThrows=false}={}) {
  const ids={},saved={},downloads=[];
  class Element {
    constructor(tag='div'){this.tag=tag;this.children=[];this.events={};this.value='';this.textContent='';this.hidden=false;this.dataset={};this.isConnected=true;}
    append(...nodes){this.children.push(...nodes);}
    replaceChildren(){this.children=[];}
    addEventListener(name,fn){this.events[name]=fn;}
    click(){if(this.tag==='a')downloads.push(this.download);this.events.click?.();}
    remove(){} focus(){this.focused=true;} scrollIntoView(){}
    querySelector(tag){for(const child of this.children){if(child.tag===tag)return child;const nested=child.querySelector(tag);if(nested)return nested;}return null;}
  }
  const get=id=>ids[id]??=(new Element());
  const batch={batch_id:'mock-only',baseline:'baseline',candidate:'candidate',generated_at:'2026-08-30',limitations:['No browser acceptance'],cases:[
    {id:'__proto__',gt_id:'g1',title:'Windows Unicode',module:'platform',platform:'Windows simulated',risk:'high',input:'中文路径',expected:'UTF8',fix:'stdin',runs:[{id:'r0',status:'FAIL',actual:'old failure',rationale:'old',evidence:'mock evidence',seconds:null},{id:'r1',status:'PASS',actual:'fixed',rationale:'new',evidence:'mock evidence',seconds:1}]},
    {id:'c2',gt_id:'g2',title:'Browser',module:'report',platform:'Mac',risk:'low',input:'Open report',expected:'Visible',runs:[{id:'r2',status:'BLOCKED',actual:'policy blocked',rationale:'not tested',seconds:null}]}
  ]};
  get('batch').textContent=JSON.stringify(batch);
  const exports=['cases','ground_truth','runs','scores'].map(key=>{const e=new Element('button');e.dataset.export=key;return e;});
  const source=fs.readFileSync('tools/detect_report.html','utf8').match(/<script>\s*([\s\S]*?)<\/script>/)[1];
  const ctx={document:{getElementById:get,createElement:t=>new Element(t),body:new Element('body'),querySelectorAll:()=>exports},
    localStorage:{getItem:k=>saved[k],setItem:(k,v)=>{if(storageThrows)throw Error('disabled');saved[k]=v;}},
    Blob,URL:{createObjectURL:()=> 'blob:mock',revokeObjectURL:()=>{}},setTimeout:()=>{},Date};
  vm.runInNewContext(source,ctx);
  return {ids,get,batch,saved,downloads,exports};
}

test('filters combine and search includes platform metadata; clearing restores rows',()=>{
  const {get}=mount();assert.equal(get('rows').children.length,2);
  get('search').value='windows simulated';get('search').events.input();assert.equal(get('rows').children.length,1);
  get('status').value='BLOCKED';get('status').events.input();assert.equal(get('rows').children.length,0);assert.equal(get('empty').hidden,false);
  get('search').value='';get('status').value='';get('search').events.input();assert.equal(get('rows').children.length,2);
});
test('detail preserves failure and retest; prototype-like ID draft saves without changing evidence',()=>{
  const {get,saved,batch}=mount();get('rows').children[0].querySelector('button').click();
  assert.equal(get('detail-input').textContent,'中文路径');assert.equal(get('runs').children.length,2);
  get('review-text').value='Need native Windows evidence';get('save-review').click();
  const draft=JSON.parse(Object.values(saved)[0]);assert.equal(draft.__proto__.note,'Need native Windows evidence');
  assert.equal(batch.cases[0].runs[1].status,'PASS');assert.equal(draft.__proto__.review_status,'draft');
  get('close-detail').click();assert.equal(get('detail').hidden,true);assert.equal(get('rows').children[0].querySelector('button').focused,true);
});
test('storage failure is explicit and review/data download actions remain available',()=>{
  const {get,downloads,exports}=mount({storageThrows:true});get('rows').children[0].querySelector('button').click();
  get('review-text').value='unsaved note';get('save-review').click();assert.match(get('review-status').textContent,/保存失败/);
  get('export-review').click();get('download-batch').click();exports.forEach(e=>e.click());
  assert.deepEqual(downloads,['mock-only-review-drafts.json','mock-only.json','cases.jsonl','ground_truth.jsonl','runs.jsonl','scores.jsonl']);
});
