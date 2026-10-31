"""Dispatch nine Regularized-Linear workers over owned critic GPUs."""
import json, subprocess, time
from pathlib import Path
ROOT=Path('/public/wangsenbao221/pqr/qgf_mainstream_20261022'); CODE=ROOT/'regularized_linear_qgf_v1'; EXEC=CODE/'execution_v1'; RUN=CODE/'dispatch_v1'
SLOTS=[('gpu22',1598338,0,'GPU-f39a66d0-5c4f-f2ca-4e60-5f52ed1b78db'),('gpu22',1598338,1,'GPU-2efca5c1-71db-641d-deb5-617c3e0f4fed'),('gpu4',1673999,0,'GPU-695faae0-f717-5fcc-4323-8fa3d047d117'),('gpu4',1673999,1,'GPU-fc595b1c-c259-ef94-920a-ec825857e82e')]
def main():
 RUN.mkdir(exist_ok=False); pending=sorted((EXEC/'registrations').glob('*.json')); active={}; result=1
 if len(pending)!=9: raise RuntimeError('Expected nine registrations')
 try:
  while pending or active:
   for slot,(_,control) in list(active.items()):
    exit_path=control/'process_exit_code'
    if exit_path.exists():
     if exit_path.read_text().strip()!='0': raise RuntimeError(f'Worker failed: {control.name}')
     del active[slot]
   for slot in SLOTS:
    if pending and slot not in active:
     reg=pending.pop(0); host,job,dev,uuid=slot; control=ROOT/'runs'/f'qgf_regularized_linear_{reg.stem}_process'; log=RUN/f'{reg.stem}.log'
     command=f'nohup bash {CODE}/run_owned_worker.sh {host} {job} {dev} {uuid} {reg} {control} {log} >/dev/null 2>&1 </dev/null & echo $!'
     launch=subprocess.run(['ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=8',host,command],text=True,capture_output=True,timeout=20)
     (RUN/f'{reg.stem}.launch.json').write_text(json.dumps({'host':host,'job':job,'gpu':dev,'uuid':uuid,'ssh_exit':launch.returncode,'stdout':launch.stdout,'stderr':launch.stderr},indent=2))
     if launch.returncode or not launch.stdout.strip().isdigit(): raise RuntimeError('Owned launch not confirmed')
     active[slot]=(reg,control)
     for _ in range(10):
      if control.exists(): break
      time.sleep(1)
     if not control.exists(): raise RuntimeError('Ownership/UUID/idle guard failed')
   if pending or active: time.sleep(5)
  (RUN/'ALL_WORKERS_RETURNED').touch(); result=0
 finally: (RUN/'dispatcher_exit_code').write_text(str(result))
if __name__=='__main__': main()
