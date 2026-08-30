from __future__ import annotations
import base64, os
from dataclasses import dataclass
from .http_utils import request_json

@dataclass
class AgentHandle:
    interaction_id: str
    environment_id: str | None
    status: str
    output_text: str = ''

def _headers(config):
    env=config.get('api_key_env','GEMINI_API_KEY'); key=os.environ.get(env)
    if not key: raise RuntimeError(f'Missing {env}')
    h={'x-goog-api-key':key,'Content-Type':'application/json'}
    if config.get('api_revision'): h['Api-Revision']=str(config['api_revision'])
    return h

def _text(resp):
    if isinstance(resp.get('output_text'),str): return resp['output_text']
    out=[]
    for item in resp.get('outputs',[]) or resp.get('output',[]) or []:
        if isinstance(item,dict) and isinstance(item.get('text') or item.get('output_text'),str): out.append(item.get('text') or item.get('output_text'))
    return '\n'.join(out)

def _environment(config, repo_url):
    target=config.get('remote_target','/workspace/repo'); env={'type':'remote','sources':[{'type':'repository','source':repo_url,'target':target}]}; rules=[]
    pat=os.environ.get(config.get('github_pat_env','ANTIGRAVITY_GITHUB_PAT'))
    if pat:
        token=base64.b64encode(f'x-oauth-basic:{pat}'.encode()).decode(); rules=[{'domain':'github.com','transform':{'Authorization':f'Basic {token}'}},{'domain':'api.github.com','transform':{'Authorization':f'Basic {token}'}}]
    elif not config.get('allow_public_repo_without_pat',True): raise RuntimeError('GitHub PAT required')
    rules.append({'domain':'*'}); env['network']={'allowlist':rules}; return env

def dispatch(config, *, repo_url, branch, task_id, attempt, rework_context=None, previous_interaction_id=None, environment_id=None):
    target=config.get('remote_target','/workspace/repo'); environment=environment_id if previous_interaction_id and environment_id else _environment(config,repo_url)
    prompt=f'''You are the bounded Antigravity Executor for {task_id}, attempt {attempt}.\nRepository: {target}\nBranch: {branch}\nRead AGENTS.md, GEMINI.md and the assigned task contract. Implement only authorized scope, run required checks, fill receipt.executor.yaml, commit and push the task branch. Never self-approve or widen task authority. If architecture authority is insufficient return ARCHITECTURE_DECISION_REQUIRED.\n'''
    if rework_context: prompt += '\nReviewer findings:\n'+rework_context
    payload={'agent':config.get('agent','antigravity-preview-05-2026'),'input':prompt,'environment':environment,'background':bool(config.get('background',True)),'agent_config':{'type':'antigravity','model':config.get('model','gemini-3.7-flash')}}
    if previous_interaction_id: payload['previous_interaction_id']=previous_interaction_id
    r=request_json('POST','https://generativelanguage.googleapis.com/v1beta/interactions',headers=_headers(config),payload=payload)
    return AgentHandle(str(r.get('id') or ''),r.get('environment_id'),str(r.get('status','completed')),_text(r))

def poll(config, interaction_id):
    r=request_json('GET',f'https://generativelanguage.googleapis.com/v1beta/interactions/{interaction_id}',headers=_headers(config),timeout=120)
    return AgentHandle(str(r.get('id') or interaction_id),r.get('environment_id'),str(r.get('status','unknown')),_text(r))
