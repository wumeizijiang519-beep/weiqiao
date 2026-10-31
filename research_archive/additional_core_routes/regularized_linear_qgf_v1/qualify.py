"""Fail-closed OOF qualification for Regularized-Linear development."""
import argparse, json
from pathlib import Path
import numpy as np

SEEDS=(202642301,202642302,202642303); CONTROLS=('state_only','permutation','action_only'); MODELS=('proposed',*CONTROLS)
BOOTSTRAP_SEED=202642701; BOOTSTRAP_DRAWS=10000
def loss(logits,target): return np.logaddexp(0.0,logits)-target*logits
def main():
 p=argparse.ArgumentParser(); p.add_argument('--execution',type=Path,required=True); p.add_argument('--corpus',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args(); a.output.mkdir(parents=True,exist_ok=False)
 with np.load(a.corpus,allow_pickle=False) as f: fg=f['group_index'].copy(); ft=f['target_scalar'].copy()
 expected=set()
 for group in np.unique(fg):
  v=ft[fg==group]
  if any(abs(float(v[i]-v[j]))>1e-6 for i in range(len(v)) for j in range(i+1,len(v))): expected.add(int(group))
 errors=[]; seed_reports={}; deltas={c:[] for c in CONTROLS}
 for seed in SEEDS:
  rows=[]
  for fold in range(3):
   run=a.execution/'runs'/f'seed_{seed}_fold_{fold}'
   if not (run/'WORKER_COMPLETE').exists(): errors.append(f'incomplete worker {seed}/{fold}'); continue
   report=json.loads((run/'REPORT.json').read_text())
   if report.get('status')!='REGULARIZED_LINEAR_WORKER_COMPLETE' or report.get('confirmation_labels_read') is not False or report.get('updates')!=3000:
    errors.append(f'invalid receipt {seed}/{fold}'); continue
   with np.load(run/'HELD_PREDICTIONS.npz',allow_pickle=False) as f:
    required={'target','group_index','left_index','right_index',*MODELS}
    if set(f.files)!=required: errors.append(f'inventory {seed}/{fold}'); continue
    rows.append({k:f[k].copy() for k in f.files})
  if len(rows)!=3: continue
  payload={k:np.concatenate([r[k] for r in rows]) for k in rows[0]}; groups=payload['group_index']; covered=set(np.unique(groups).tolist())
  if covered!=expected: errors.append(f'seed {seed} informative inventory mismatch'); continue
  group_losses={name:[] for name in MODELS}
  for group in sorted(covered):
   mask=groups==group
   for name in MODELS: group_losses[name].append(float(loss(payload[name][mask],payload['target'][mask]).mean()))
  proposed=np.asarray(group_losses['proposed']); improvements={}
  for control in CONTROLS:
   delta=np.asarray(group_losses[control])-proposed; improvements[control]=float(delta.mean()); deltas[control].append(delta)
  seed_reports[str(seed)]={'group_equal_log_loss':{n:float(np.mean(v)) for n,v in group_losses.items()},'improvement_vs_control':improvements,'passes':all(v>0 for v in improvements.values())}
 bootstrap={}
 for idx,control in enumerate(CONTROLS):
  if len(deltas[control])!=3: errors.append(f'missing deltas {control}'); continue
  values=np.stack(deltas[control]).mean(0); rng=np.random.default_rng(BOOTSTRAP_SEED+idx); n=len(values); sampled=values[rng.integers(0,n,size=(BOOTSTRAP_DRAWS,n))].mean(1); lo,hi=np.quantile(sampled,[.025,.975])
  bootstrap[control]={'mean_improvement':float(values.mean()),'ci95':[float(lo),float(hi)],'physical_groups':n,'passes':bool(lo>0)}
 admitted=not errors and len(seed_reports)==3 and all(r['passes'] for r in seed_reports.values()) and len(bootstrap)==3 and all(r['passes'] for r in bootstrap.values())
 result={'status':'REGULARIZED_LINEAR_DEVELOPMENT_ADMIT' if admitted else 'NO_STABLE_REGULARIZED_LINEAR_DEVELOPMENT_CRITIC','errors':errors,'seed_reports':seed_reports,'group_bootstrap':bootstrap,'informative_groups':sorted(expected),'bootstrap_seed_base':BOOTSTRAP_SEED,'bootstrap_draws':BOOTSTRAP_DRAWS,'confirmation_labels_read':False,'online_qgf_efficacy_claim':False}
 (a.output/'REPORT.json').write_text(json.dumps(result,indent=2,sort_keys=True)); (a.output/result['status']).touch(); print(json.dumps(result,sort_keys=True))
if __name__=='__main__': main()
