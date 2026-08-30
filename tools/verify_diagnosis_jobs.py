"""Isolated short-request probe. controlled = 35s fake model; live = paid Codex call.

Only synthetic users. No real learner directory is read or modified. Writes a
sanitized evidence JSON; does not retain keys, process stderr, or private reasoning.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def source_hashes():
    return {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in (
        'backend/diagnosis_jobs.py', 'backend/codex_driver.py', 'backend/main.py',
        'backend/platform_runtime.py', 'frontend/js/diagnosis-job.js', 'frontend/js/onboarding.js')}


def run(mode='controlled', delay=35):
    from fastapi.testclient import TestClient
    from backend import main as api
    from backend.codex_driver import load_secrets
    from backend.user_memory import _atomic_json
    with tempfile.TemporaryDirectory(prefix='learning-diagnosis-probe-') as directory:
        root=Path(directory)
        shutil.copytree(ROOT/'templates',root/'templates')
        api.SERVER_ROOT=root
        api.latest_release=lambda:ROOT/'workspace/dev'
        _atomic_json(root/'userdir/u_probe/onboarding/intent-state.json',{
            'session_id':'probe-intent','revision':1,'action':'ready_for_plan','slots':{'topic':'AI 前端'},
            'onboarding':{'topic_type':'custom','goal_route':'interview_sprint','level_claim':'some',
                          'learning_mode':'practice','session_minutes':25,'concept_scope':'not_applicable'}})
        calls=[];real_chat=api.chat
        def traced(*args,**kwargs):
            started=time.monotonic()
            try:
                if mode=='live':return real_chat(*args,**kwargs)
                time.sleep(delay)
                return json.dumps({'topic':'AI 前端','questions':[
                    {'id':f'q{i}','dimension':'AI 前端','prompt':prompt,
                     'options':[{'id':'a','label':a},{'id':'b','label':b}],'correct_option_id':'a'}
                    for i,(prompt,a,b) in enumerate([
                        ('AI前端页面中，DOM事件的传播顺序是什么？','先捕获，再目标，再冒泡','只冒泡'),
                        ('AI前端调用模型API，密钥应保存在什么位置？','后端环境变量','浏览器公开脚本'),
                        ('AI前端流式回答中，如何处理返回的增量？','按顺序追加内容','每段都替换整个答案')])]},ensure_ascii=False)
            finally:calls.append({'seconds':round(time.monotonic()-started,3),'sandbox':kwargs.get('sandbox')})
        api.chat=traced
        old_key=os.environ.get('DEEPSEEK_API_KEY')
        if mode=='live':
            key=load_secrets(ROOT/'.secrets.env').get('DEEPSEEK_API_KEY')
            if key:os.environ['DEEPSEEK_API_KEY']=key
        try:
            client=TestClient(api.app)
            payload={'user_id':'probe','request_id':'probe-request','intent_session_id':'probe-intent','intent_revision':1,
                'topic':{'type':'custom','value':'AI 前端'},'level_claim':'some','learning_mode':'practice',
                'goal_route':'interview_sprint','session_minutes':25}
            started=time.monotonic()
            response=client.post('/api/onboarding/diagnosis/start',json=payload)
            start_seconds=time.monotonic()-started
            response.raise_for_status()
            duplicate=client.post('/api/onboarding/diagnosis/start',json=payload)
            duplicate.raise_for_status()
            durations=[];phases=[];job=response.json()
            while job['status'] in {'queued','running'} and time.monotonic()-started<310:
                tick=time.monotonic()
                response=client.get('/api/onboarding/diagnosis/status',params={'user_id':'probe','request_id':'probe-request'})
                durations.append(time.monotonic()-tick);response.raise_for_status();job=response.json()
                if job.get('phase') not in phases:phases.append(job.get('phase'))
                if job['status'] in {'queued','running'}:time.sleep(.5)
            return {'mode':mode,'transport':'local ASGI TestClient (not proxy or Windows benchmark)',
                'source_sha256':source_hashes(),
                'start_http_status':duplicate.status_code,'start_seconds':round(start_seconds,4),
                'max_poll_seconds':round(max(durations,default=0),4),'total_seconds':round(time.monotonic()-started,3),
                'model_calls':calls,'phases':phases,'job':job,
                'input':{k:v for k,v in payload.items() if k!='user_id'}}
        finally:
            api.diagnosis_registry().shutdown()
            if old_key is None:os.environ.pop('DEEPSEEK_API_KEY',None)
            else:os.environ['DEEPSEEK_API_KEY']=old_key


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=['controlled','live'],default='controlled')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise SystemExit('Refusing to overwrite evidence; choose a new output file.')
    result=run(args.mode)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in {'job','input'}},ensure_ascii=False))
    print(json.dumps({'status':result['job']['status'],'question':result['job'].get('result',{}).get('question')},ensure_ascii=False))
    raise SystemExit(0 if result['job']['status']=='completed' else 1)
