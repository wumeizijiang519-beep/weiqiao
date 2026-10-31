"""Freeze outcome-blind ensemble disagreement scores for candidate banks."""
import argparse,hashlib,importlib.util,json
from pathlib import Path
import numpy as np
SEEDS=(202642301,202642302,202642303)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(); p.add_argument('--root',type=Path,required=True); p.add_argument('--metadata',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args(); root=a.root.resolve(); a.output.mkdir(parents=True,exist_ok=False)
 meta=json.loads(a.metadata.read_text());
 if meta.get('confirmation_labels_read') is not False or len(meta['groups'])!=24: raise RuntimeError('Metadata contract changed')
 import torch
 spec=importlib.util.spec_from_file_location('action_prefix_train',root/'action_prefix_pretrain_v1/train.py'); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
 models=[]; checkpoints=[]
 for seed in SEEDS:
  path=root/f'action_prefix_pretrain_v1/checkpoints_retry1/seed_{seed}/encoder.pt'; payload=torch.load(path,map_location='cpu'); model=mod.ActionEncoder(); model.load_state_dict(payload['model']); model.eval().cuda(); models.append(model); checkpoints.append({'seed':seed,'sha256':sha(path)})
 mask=torch.zeros((8,32),dtype=torch.bool,device='cuda'); mask[:,::3]=True; variance=[]; per_seed=[]; receipts=[]; families=[]; episodes=[]; groups=[]
 for group in meta['groups']:
  route='runtime_anchored_qgf_v1' if group['source']=='runtime_anchored_v1' else 'setwise_contrastive_qgf_v1'; found=[]
  for path in (root/route).glob(f"**/{group['episode_id']}/bank.npz"):
   with np.load(path,allow_pickle=False) as s:
    key='candidates_executed_normalized' if 'candidates_executed_normalized' in s.files else ('candidates_native' if 'candidates_native' in s.files else None)
    if key: bank=s[key].astype(np.float32)
    else: continue
   if bank.shape==(8,32,7): found.append((path,bank))
  unique={hashlib.sha256(bank.tobytes()).hexdigest():(path,bank) for path,bank in found}
  if len(unique)!=1: raise RuntimeError(f"Bank inventory for {group['episode_id']}: {len(unique)}")
  digest,(path,bank)=next(iter(unique.items())); actions=torch.as_tensor(bank,device='cuda'); energies=[]
  with torch.no_grad():
   for model in models:
    prediction=model(actions,mask); energies.append(((prediction[mask]-actions[mask])**2).reshape(8,-1).mean(1).cpu().numpy())
  energies=np.stack(energies); per_seed.append(energies); variance.append(energies.var(0)); receipts.append({'path':str(path),'file_sha256':sha(path),'bank_sha256':digest}); families.append(group['family']); episodes.append(group['episode_id']); groups.append(group['physical_input_group'])
 np.savez_compressed(a.output/'SCORES.npz',variance=np.asarray(variance,dtype=np.float32),per_seed_energy=np.asarray(per_seed,dtype=np.float32),family=np.asarray(families),episode_id=np.asarray(episodes),physical_input_group=np.asarray(groups))
 receipt={'status':'ENSEMBLE_CONSENSUS_SCORES_FROZEN','scientific_outcomes_read':False,'groups':24,'candidates_per_group':8,'mask_positions':list(range(0,32,3)),'checkpoint_receipts':checkpoints,'bank_receipts':receipts,'scores_sha256':sha(a.output/'SCORES.npz'),'metadata_sha256':sha(a.metadata)}
 (a.output/'RECEIPT.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)); (a.output/'OUTCOME_BLIND_SCORES_COMPLETE').touch(); print(json.dumps(receipt,sort_keys=True))
if __name__=='__main__': main()
