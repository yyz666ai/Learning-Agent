const test = require('node:test');
const assert = require('node:assert/strict');
const { waitForDiagnosis, readJob, statusText } = require('../frontend/js/diagnosis-job.js');

const response = (body, status=200) => ({ok:status<400,status,json:async()=>body});
test('lost start response retries same id then polls without duplicate creation', async()=>{
  const calls=[]; let start=0;
  const result=await waitForDiagnosis({payload:{request_id:'same'},fetcher:async(url,options)=>{
    calls.push([url,options]);
    if(url.endsWith('/start')) {if(++start===1)throw new TypeError('offline'); return response({status:'running'});}
    return response({status:'completed',result:{question:{prompt:'Hello'}}});
  },sleep:async()=>{},onStatus:()=>{}});
  assert.equal(result.question.prompt,'Hello');
  const starts=calls.filter(c=>c[0].endsWith('/start'));
  assert.equal(starts.length,2);
  assert.ok(starts.every(c=>JSON.parse(c[1].body).request_id==='same'));
});
test('network uncertainty is not represented as model failure or still generating',async()=>{
  const seen=[];let n=0;
  await waitForDiagnosis({payload:{request_id:'one'},fetcher:async url=>{
    if(url.endsWith('/start'))return response({status:'running',phase:'generating',elapsed_seconds:1});
    if(++n===1)throw new TypeError('offline');
    return response({status:'completed',result:{ok:true}});
  },sleep:async()=>{},onStatus:job=>seen.push(statusText(job))});
  assert.ok(seen.some(s=>s.includes('重连')));
  assert.ok(!seen.some(s=>s.includes('92%')||s.includes('剩余')));
});
test('terminal failed state is retryable and does not loop forever',async()=>{
  await assert.rejects(waitForDiagnosis({payload:{},fetcher:async()=>response({status:'failed',error:'中断',retryable:true}),sleep:async()=>{}}),error=>error.message==='中断'&&error.terminal===true);
});
test('stale UI cancels polling without returning a result',async()=>{
  await assert.rejects(waitForDiagnosis({payload:{},isCurrent:()=>false,fetcher:()=>{throw Error('should not fetch');}}),error=>error.name==='AbortError');
});
test('individual fetch has abort timeout including body read',async()=>{
  const fake=async(_url,{signal})=>({ok:true,json:()=>new Promise((_,reject)=>signal.addEventListener('abort',()=>reject(Object.assign(new Error('timeout'),{name:'AbortError'}))))});
  await assert.rejects(readJob('/example',{},fake,5),error=>error.name==='AbortError');
});
test('HTTP validation errors do not retry as transient disconnects',async()=>{
  let calls=0;
  await assert.rejects(waitForDiagnosis({payload:{},fetcher:async()=>{calls++;return response({detail:{message:'会话过期'}},409);},sleep:async()=>{}}),/会话过期/);
  assert.equal(calls,1);
});
test('overall waiting bounded while server state remains unknown',async()=>{
  let clock=0;
  await assert.rejects(waitForDiagnosis({payload:{},fetcher:async()=>{throw TypeError('offline');},sleep:async()=>{clock+=10;},now:()=>clock,maxWaitMs:20}),/暂时无法确认/);
});
