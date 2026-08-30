#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, json, os, sqlite3, subprocess, time, uuid
from pathlib import Path
import yaml
from providers import antigravity, openai_reviewer

ROOT=Path(__file__).resolve().parents[2]
CFG_PATH=ROOT/'.ai/orchestrator/config.yaml'
DB_PATH=ROOT/'.ai/runtime/orchestrator.db'
STATE_DIRS={'READY':'queue','IN_PROGRESS':'active','REVIEW':'review','BLOCKED':'blocked','DONE':'done','ARCHIVED':'archive'}

def now(): return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
def run(*args,cwd=ROOT,check=True): return subprocess.run(list(args),cwd=cwd,text=True,capture_output=True,check=check)
def cfg(): return yaml.safe_load(CFG_PATH.read_text())
def db():
    DB_PATH.parent.mkdir(parents=True,exist_ok=True); c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row; return c

def init_db():
    c=db(); c.executescript((ROOT/'.ai/orchestrator/schema.sql').read_text()); c.commit(); c.close(); print(DB_PATH)

def locate(task_id):
    for state,folder in STATE_DIRS.items():
        p=ROOT/'.ai/tasks'/folder/task_id
        if p.is_dir(): return state,p
    raise RuntimeError(f'task not found: {task_id}')

def task_data(p): return yaml.safe_load((p/'task.yaml').read_text())
def repo_url():
    u=run('git','remote','get-url','origin').stdout.strip()
    if u.startswith('git@github.com:'): u='https://github.com/'+u.split(':',1)[1]
    return u[:-4] if u.endswith('.git') else u

def ensure_runtime(task_id,state,p):
    d=task_data(p); risk=d.get('planning',{}).get('risk','medium'); attempt=int(d.get('attempt',1)); branch=d.get('isolation',{}).get('branch') or f'ai/{task_id}'; t=now(); c=db();
    c.execute('INSERT INTO task_runtime(task_id,fs_state,runtime_state,risk,attempt,branch,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(task_id) DO UPDATE SET fs_state=excluded.fs_state,risk=excluded.risk,attempt=excluded.attempt,branch=excluded.branch,updated_at=excluded.updated_at',(task_id,state,'IDLE',risk,attempt,branch,t,t)); c.commit(); c.close(); return d

def transition(task_id,target):
    run('python',str(ROOT/'.ai/scripts/ai.py'),'transition',task_id,target)

def evidence(task_id):
    _,p=locate(task_id); parts=[]
    for n in ['task.yaml','brief.md','context.md','receipt.executor.yaml','rollback.md']:
        q=p/n
        if q.exists(): parts.append(f'## {n}\n{q.read_text()}')
    try: parts.append('## git diff\n'+run('git','diff','main...HEAD').stdout)
    except Exception: pass
    return '\n\n'.join(parts)

def acquire(task_id,seconds):
    owner=str(uuid.uuid4()); exp=(dt.datetime.now(dt.timezone.utc)+dt.timedelta(seconds=seconds)).replace(microsecond=0).isoformat(); c=db(); r=c.execute('SELECT lease_expires_at FROM task_runtime WHERE task_id=?',(task_id,)).fetchone();
    if r and r['lease_expires_at'] and r['lease_expires_at']>now(): c.close(); return None
    c.execute('UPDATE task_runtime SET lease_owner=?,lease_expires_at=?,runtime_state=?,updated_at=? WHERE task_id=?',(owner,exp,'LEASED',now(),task_id)); c.commit(); c.close(); return owner

def dispatch_one(task_id):
    conf=cfg(); state,p=locate(task_id)
    if state!='READY': return
    d=ensure_runtime(task_id,state,p); lease=acquire(task_id,int(conf['orchestrator']['lease_seconds']))
    if not lease: return
    branch=d.get('isolation',{}).get('branch') or f'ai/{task_id}'; attempt=int(d.get('attempt',1))
    try:
        # Ensure task branch exists remotely. The executor works remotely; local worktree remains optional coordination evidence.
        if run('git','show-ref','--verify','--quiet',f'refs/heads/{branch}',check=False).returncode!=0:
            run('git','branch',branch,'main')
        run('git','push','-u','origin',branch)
        h=antigravity.dispatch(conf['executor'],repo_url=repo_url(),branch=branch,task_id=task_id,attempt=attempt)
        c=db(); c.execute('UPDATE task_runtime SET runtime_state=?,executor_interaction_id=?,executor_environment_id=?,updated_at=? WHERE task_id=?',('EXECUTING',h.interaction_id,h.environment_id,now(),task_id)); c.commit(); c.close()
        while h.status.lower() in {'pending','running','in_progress','queued'}:
            time.sleep(int(conf['orchestrator']['poll_seconds'])); h=antigravity.poll(conf['executor'],h.interaction_id)
        run('git','fetch','origin',branch)
        # Bring task branch evidence into local temporary worktree for review.
        wt=ROOT/'.worktrees'/task_id; wt.parent.mkdir(exist_ok=True)
        if not wt.exists(): run('git','worktree','add',str(wt),f'origin/{branch}')
        ev='';
        for n in ['task.yaml','brief.md','context.md','receipt.executor.yaml','rollback.md']:
            matches=list((wt/'.ai/tasks').glob(f'*/{task_id}/{n}'))
            if matches: ev+=f'\n## {n}\n'+matches[0].read_text()
        ev+='\n## diff\n'+run('git','diff','main...HEAD',cwd=wt).stdout
        rr=openai_reviewer.review(conf['reviewer'],ev[:int(conf['reviewer'].get('max_evidence_chars',180000))])
        # Persist review on task branch.
        tdirs=list((wt/'.ai/tasks').glob(f'*/{task_id}')); tp=tdirs[0]
        (tp/'review.yaml').write_text(yaml.safe_dump({'schema_version':2,'task_id':task_id,'attempt':attempt,'verdict':rr.verdict,'summary':rr.summary,'findings':[{'severity':'high','finding':x,'required_action':x} for x in rr.blocking_findings],'follow_up_tasks':[],'state_transition':'DONE' if rr.verdict in {'PASS','PASS_WITH_NOTES'} else 'READY' if rr.verdict=='REWORK' else 'BLOCKED'},sort_keys=False))
        qa=yaml.safe_load((tp/'receipt.qa.yaml').read_text()); qa['status']='REVIEWED'; qa['reviewed_at']=now(); qa['risk_gate']['result']=rr.risk_gate_result; qa['blocking_findings']=rr.blocking_findings; qa['non_blocking_findings']=rr.non_blocking_findings; qa['verdict']=rr.verdict; (tp/'receipt.qa.yaml').write_text(yaml.safe_dump(qa,sort_keys=False))
        run('git','add','.',cwd=wt); run('git','commit','-m',f'{task_id}: GPT-5.6 review {rr.verdict}',cwd=wt,check=False); run('git','push','origin','HEAD:'+branch,cwd=wt)
        c=db(); c.execute('UPDATE task_runtime SET runtime_state=?,reviewer_response_id=?,updated_at=? WHERE task_id=?',(rr.verdict,rr.response_id,now(),task_id)); c.commit(); c.close()
        print(f'{task_id}: {rr.verdict}')
    except Exception as e:
        c=db(); c.execute('UPDATE task_runtime SET runtime_state=?,last_error=?,updated_at=? WHERE task_id=?',('BLOCKED',str(e),now(),task_id)); c.commit(); c.close(); print(f'{task_id}: BLOCKED: {e}')

def scan_ready():
    base=ROOT/'.ai/tasks/queue'; return sorted(p.name for p in base.iterdir() if p.is_dir()) if base.exists() else []
def status():
    c=db(); rows=c.execute('SELECT task_id,fs_state,runtime_state,risk,attempt,last_error FROM task_runtime ORDER BY task_id').fetchall(); c.close();
    for r in rows: print(dict(r))
def approve(task_id,by,note=''):
    c=db(); c.execute('INSERT INTO approvals(task_id,approval_type,approved_by,note,created_at) VALUES(?,?,?,?,?)',(task_id,'human_merge',by,note,now())); c.commit(); c.close(); print(f'approved {task_id} by {by}')
def doctor():
    print('repo:',ROOT); print('git:',run('git','status','--short',check=False).returncode==0); print('OPENAI_API_KEY:',bool(os.environ.get('OPENAI_API_KEY'))); print('GEMINI_API_KEY:',bool(os.environ.get('GEMINI_API_KEY'))); print('origin:',repo_url())
def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd',required=True); sub.add_parser('init'); sub.add_parser('doctor'); sub.add_parser('status'); p=sub.add_parser('once'); p.add_argument('task_id',nargs='?'); p=sub.add_parser('loop'); p.add_argument('--until-idle',action='store_true'); p=sub.add_parser('approve'); p.add_argument('task_id'); p.add_argument('--by',required=True); p.add_argument('--note',default=''); ns=ap.parse_args()
    if ns.cmd=='init': init_db()
    elif ns.cmd=='doctor': init_db(); doctor()
    elif ns.cmd=='status': init_db(); status()
    elif ns.cmd=='once': init_db(); ids=[ns.task_id] if ns.task_id else scan_ready(); [dispatch_one(x) for x in ids]
    elif ns.cmd=='loop':
        init_db()
        while True:
            ids=scan_ready()
            if not ids: break if ns.until_idle else time.sleep(10)
            for x in ids: dispatch_one(x)
            if ns.until_idle: break
    elif ns.cmd=='approve': init_db(); approve(ns.task_id,ns.by,ns.note)
if __name__=='__main__': main()
