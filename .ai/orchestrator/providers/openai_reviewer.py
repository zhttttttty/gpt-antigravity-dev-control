from __future__ import annotations
import json, os, re
from dataclasses import dataclass
from .http_utils import request_json

@dataclass
class ReviewResult:
    verdict:str; summary:str; blocking_findings:list[str]; non_blocking_findings:list[str]; acceptance:list[dict]; risk_gate_result:str; cross_family_review_result:str; response_id:str|None=None

def _text(r):
    if isinstance(r.get('output_text'),str): return r['output_text']
    out=[]
    for item in r.get('output',[]) or []:
        if item.get('type')=='message':
            for c in item.get('content',[]) or []:
                if isinstance(c.get('text'),str): out.append(c['text'])
    return '\n'.join(out)

def review(config,evidence):
    env=config.get('api_key_env','OPENAI_API_KEY'); key=os.environ.get(env)
    if not key: raise RuntimeError(f'Missing {env}')
    prompt='''Act as the independent reviewer. Fail closed. Return ONLY JSON with verdict, summary, blocking_findings, non_blocking_findings, acceptance, risk_gate_result, cross_family_review_result. verdict is PASS, PASS_WITH_NOTES, REWORK, or BLOCKED.\n\nEVIDENCE:\n'''+evidence
    schema={'type':'object','properties':{'verdict':{'type':'string','enum':['PASS','PASS_WITH_NOTES','REWORK','BLOCKED']},'summary':{'type':'string'},'blocking_findings':{'type':'array','items':{'type':'string'}},'non_blocking_findings':{'type':'array','items':{'type':'string'}},'acceptance':{'type':'array','items':{'type':'object'}},'risk_gate_result':{'type':'string','enum':['PASS','FAIL']},'cross_family_review_result':{'type':'string','enum':['PASS','WAIVED','NOT_REQUIRED']}},'required':['verdict','summary','blocking_findings','non_blocking_findings','acceptance','risk_gate_result','cross_family_review_result'],'additionalProperties':False}
    payload={'model':config.get('model','gpt-5.6-sol'),'input':prompt,'reasoning':{'effort':config.get('reasoning_effort','high')},'store':False,'text':{'format':{'type':'json_schema','name':'v3_task_review','strict':True,'schema':schema}}}
    r=request_json('POST','https://api.openai.com/v1/responses',headers={'Authorization':f'Bearer {key}','Content-Type':'application/json'},payload=payload,timeout=600)
    t=_text(r).strip(); m=re.search(r'\{.*\}',t,re.S); d=json.loads(m.group(0) if m else t)
    return ReviewResult(d['verdict'],d['summary'],list(d['blocking_findings']),list(d['non_blocking_findings']),list(d['acceptance']),d['risk_gate_result'],d['cross_family_review_result'],r.get('id'))
