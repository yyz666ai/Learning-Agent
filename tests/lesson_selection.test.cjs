const {test} = require('node:test');
const assert = require('node:assert/strict');
const {createQuoteState} = require('../frontend/js/lesson-selection.js');
const fs = require('node:fs');
const vm = require('node:vm');
const lesson = {lesson_id:'go-1',revision:'a'.repeat(64),pages:[{id:'p1',title:'变量'}]};
test('selection is a draft, cancel preserves unrelated input, failed send retains quote',()=>{
  const state=createQuoteState(); state.setManifest(lesson);
  assert.equal(state.get(),null);
  state.select('p1','  变量  ');
  assert.equal(state.get().quote,'变量');
  const input='为什么'; state.clear();
  assert.equal(state.get(),null); assert.equal(input,'为什么');
  state.select('p1','值');
  assert.equal(state.get().quote,'值'); // no implicit clear until confirmed success
});
test('page flip retains source but content version change invalidates it',()=>{
  const state=createQuoteState(); state.setManifest(lesson);state.select('p1','变量');
  state.setManifest(lesson);assert.equal(state.get().page_id,'p1');
  state.setManifest({...lesson,revision:'b'.repeat(64)});assert.equal(state.get(),null);
  state.select('p1','变量');state.setManifest({...lesson,lesson_id:'other'});assert.equal(state.get(),null);
});
test('empty, over-limit or nonexistent-page quotes are not accepted',()=>{
  const state=createQuoteState();state.setManifest(lesson);
  assert.equal(state.select('p1','   '),false);
  assert.equal(state.select('p1','a'.repeat(2001)),false);
  assert.equal(state.select('missing','字'),false);
});

test('DOM selection button creates removable composer quote without sending or changing input',()=>{
  const nodes=new Map(), handlers={};
  function makeNode(id) {
    return {id,hidden:false,textContent:'',value:'',style:{},handlers:{},
      append(child){nodes.set(child.id,child)},setAttribute(){},focus(){this.focused=true},
      addEventListener(name,fn){this.handlers[name]=fn},contains(node){return node?.parent===this},
    };
  }
  const document={body:makeNode('body'),createElement:()=>makeNode(''),getElementById(id){if(!nodes.has(id))nodes.set(id,makeNode(id));return nodes.get(id)},addEventListener(name,fn){handlers[name]=fn}};
  const content=document.getElementById('pageMarkdown'), input=document.getElementById('chatInput');
  input.value='原来的问题';
  const textNode={parent:content};
  const window={document,innerWidth:1000,getSelection:()=>({anchorNode:textNode,focusNode:textNode,rangeCount:1,toString:()=>'<b>解释器</b>',getRangeAt:()=>({getBoundingClientRect:()=>({left:100,top:100})})})};
  vm.runInNewContext(fs.readFileSync(require.resolve('../frontend/js/lesson-selection.js'),'utf8'),{window});
  handlers['learning-agent:manifest-change']({detail:lesson});
  handlers['learning-agent:page-change']({detail:{page:lesson.pages[0]}});
  handlers.pointerup({target:content});
  const button=nodes.get('askSelectionBtn');
  assert.equal(button.hidden,false);
  assert.equal(window.LessonSelection.get(),null,'selection alone never sends or quotes');
  button.handlers.click();
  assert.equal(window.LessonSelection.get().quote,'<b>解释器</b>');
  assert.equal(document.getElementById('lessonQuote').hidden,false);
  assert.equal(document.getElementById('lessonQuoteText').textContent,'变量 · <b>解释器</b>');
  assert.equal(input.value,'原来的问题');
  document.getElementById('removeLessonQuote').handlers.click();
  assert.equal(window.LessonSelection.get(),null);
  assert.equal(input.value,'原来的问题');
});
