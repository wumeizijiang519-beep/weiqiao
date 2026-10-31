"""Evaluate frozen support energies only after their outcome-blind receipt exists."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bootstrap(values,seed,draws=10000):
 values=np.asarray(values,dtype=np.float64); rng=np.random.default_rng(seed); sampled=values[rng.integers(0,len(values),size=(draws,len(values)))].mean(1); return np.quantile(sampled,[.025,.975]).tolist()
def main():
 p=argparse.ArgumentParser(); p.add_argument('--scores',type=Path,required=True); p.add_argument('--receipt',type=Path,required=True); p.add_argument('--corpus',type=Path,required=True); p.add_argument('--metadata',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args(); a.output.mkdir(parents=True,exist_ok=False)
 receipt=json.loads(a.receipt.read_text())
 if receipt.get('scientific_outcomes_read') is not False or sha(a.scores)!=receipt.get('scores_sha256'): raise RuntimeError('Outcome-blind score receipt invalid')
 with np.load(a.scores,allow_pickle=False) as s: energy=s['energy'].copy(); score_groups=s['physical_input_group'].copy()
 with np.load(a.corpus,allow_pickle=False) as c: target=c['target_scalar'].copy(); group_index=c['group_index'].copy(); candidate_index=c['candidate_index'].copy()
 meta=json.loads(a.metadata.read_text()); deltas0=[]; deltas_random=[]; family_rows={}
 for group in range(24):
  rows=np.flatnonzero(group_index==group); order=np.argsort(candidate_index[rows]); values=target[rows][order]; chosen=int(np.argmin(energy[group])); selected=float(values[chosen]); d0=selected-float(values[0]); dr=selected-float(values.mean()); deltas0.append(d0); deltas_random.append(dr); family=meta['groups'][group]['family']; family_rows.setdefault(family,[]).append((d0,dr))
 ci0=bootstrap(deltas0,202642801); cir=bootstrap(deltas_random,202642802); family_positive={k:bool(np.mean([x[0] for x in v])>0 and np.mean([x[1] for x in v])>0) for k,v in family_rows.items()}; positive=sum(family_positive.values()); admitted=ci0[0]>0 and cir[0]>0 and positive>=2
 result={'status':'SUPPORT_ENERGY_DEVELOPMENT_ADMIT' if admitted else 'NO_STABLE_SUPPORT_ENERGY_SIGNAL','selected_indices':np.argmin(energy,axis=1).tolist(),'candidate0_improvement_mean':float(np.mean(deltas0)),'candidate0_improvement_ci95':ci0,'random_improvement_mean':float(np.mean(deltas_random)),'random_improvement_ci95':cir,'positive_families':positive,'family_positive':family_positive,'bootstrap_draws':10000,'confirmation_labels_read':False,'online_qgf_efficacy_claim':False,'scores_sha256':sha(a.scores)}
 (a.output/'REPORT.json').write_text(json.dumps(result,indent=2,sort_keys=True)); (a.output/result['status']).touch(); print(json.dumps(result,sort_keys=True))
if __name__=='__main__': main()
