"""Evaluate frozen ensemble-consensus scores after score publication."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def boot(v,seed):
 v=np.asarray(v); r=np.random.default_rng(seed); x=v[r.integers(0,len(v),size=(10000,len(v)))].mean(1); return np.quantile(x,[.025,.975]).tolist()
def main():
 p=argparse.ArgumentParser(); p.add_argument('--scores',type=Path,required=True); p.add_argument('--receipt',type=Path,required=True); p.add_argument('--corpus',type=Path,required=True); p.add_argument('--metadata',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args(); a.output.mkdir(parents=True,exist_ok=False)
 receipt=json.loads(a.receipt.read_text());
 if receipt.get('scientific_outcomes_read') is not False or sha(a.scores)!=receipt.get('scores_sha256'): raise RuntimeError('Score receipt invalid')
 with np.load(a.scores,allow_pickle=False) as s: variance=s['variance'].copy()
 with np.load(a.corpus,allow_pickle=False) as c: target=c['target_scalar'].copy(); groups=c['group_index'].copy(); candidate=c['candidate_index'].copy()
 meta=json.loads(a.metadata.read_text()); d0=[]; dr=[]; fam={}
 for group in range(24):
  rows=np.flatnonzero(groups==group); values=target[rows][np.argsort(candidate[rows])]; chosen=int(np.argmin(variance[group])); a0=float(values[chosen]-values[0]); ar=float(values[chosen]-values.mean()); d0.append(a0); dr.append(ar); fam.setdefault(meta['groups'][group]['family'],[]).append((a0,ar))
 ci0=boot(d0,202642901); cir=boot(dr,202642902); fp={k:bool(np.mean([x[0] for x in v])>0 and np.mean([x[1] for x in v])>0) for k,v in fam.items()}; admitted=ci0[0]>0 and cir[0]>0 and sum(fp.values())>=2
 result={'status':'ENSEMBLE_CONSENSUS_DEVELOPMENT_ADMIT' if admitted else 'NO_STABLE_ENSEMBLE_CONSENSUS_SIGNAL','selected_indices':np.argmin(variance,axis=1).tolist(),'candidate0_improvement_mean':float(np.mean(d0)),'candidate0_improvement_ci95':ci0,'random_improvement_mean':float(np.mean(dr)),'random_improvement_ci95':cir,'family_positive':fp,'positive_families':sum(fp.values()),'bootstrap_draws':10000,'confirmation_labels_read':False,'online_qgf_efficacy_claim':False,'scores_sha256':sha(a.scores)}
 (a.output/'REPORT.json').write_text(json.dumps(result,indent=2,sort_keys=True)); (a.output/result['status']).touch(); print(json.dumps(result,sort_keys=True))
if __name__=='__main__': main()
