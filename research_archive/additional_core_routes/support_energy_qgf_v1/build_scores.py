"""Build outcome-blind masked reconstruction energies for frozen candidate banks."""
import argparse, hashlib, importlib.util, json
from pathlib import Path
import numpy as np

SEEDS=(202642301,202642302,202642303)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load_encoder_class(root):
 spec=importlib.util.spec_from_file_location('action_prefix_train',root/'action_prefix_pretrain_v1/train.py'); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod.ActionEncoder
def main():
 p=argparse.ArgumentParser(); p.add_argument('--root',type=Path,required=True); p.add_argument('--metadata',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args(); root=a.root.resolve(); a.output.mkdir(parents=True,exist_ok=False)
 meta=json.loads(a.metadata.read_text())
 if meta.get('confirmation_labels_read') is not False or len(meta['groups'])!=24: raise RuntimeError('Development metadata contract changed')
 import torch
 Encoder=load_encoder_class(root); models=[]; checkpoint_receipts=[]
 for seed in SEEDS:
  path=root/f'action_prefix_pretrain_v1/checkpoints_retry1/seed_{seed}/encoder.pt'; payload=torch.load(path,map_location='cpu'); model=Encoder(); model.load_state_dict(payload['model']); model.eval().cuda(); models.append(model); checkpoint_receipts.append({'seed':seed,'sha256':sha(path)})
 mask=torch.zeros((8,32),dtype=torch.bool,device='cuda'); mask[:,::3]=True
 scores=[]; banks=[]; families=[]; episodes=[]; groups=[]
 for index,group in enumerate(meta['groups']):
  route='runtime_anchored_qgf_v1' if group['source']=='runtime_anchored_v1' else 'setwise_contrastive_qgf_v1'
  candidates=[]
  for path in (root/route).glob(f"**/{group['episode_id']}/bank.npz"):
   with np.load(path,allow_pickle=False) as saved:
    if 'candidates_executed_normalized' in saved.files:
     bank=saved['candidates_executed_normalized'].astype(np.float32)
    elif 'candidates_native' in saved.files:
     bank=saved['candidates_native'].astype(np.float32)
    else: continue
   if bank.shape==(8,32,7): candidates.append((sha(path),path,bank))
  if not candidates: raise RuntimeError(f"No full candidate bank for {group['episode_id']}")
  unique={hashlib.sha256(item[2].tobytes()).hexdigest():item for item in candidates}
  if len(unique)!=1: raise RuntimeError(f"Ambiguous candidate banks for {group['episode_id']}")
  _,path,bank=next(iter(unique.values())); actions=torch.as_tensor(bank,device='cuda'); seed_energy=[]
  with torch.no_grad():
   for model in models:
    prediction=model(actions,mask); seed_energy.append(((prediction[mask]-actions[mask])**2).reshape(8,-1).mean(1).cpu().numpy())
  scores.append(np.stack(seed_energy).mean(0)); banks.append({'path':str(path),'file_sha256':sha(path),'bank_sha256':hashlib.sha256(bank.tobytes()).hexdigest()}); families.append(group['family']); episodes.append(group['episode_id']); groups.append(group['physical_input_group'])
 np.savez_compressed(a.output/'SCORES.npz',energy=np.asarray(scores,dtype=np.float32),family=np.asarray(families),episode_id=np.asarray(episodes),physical_input_group=np.asarray(groups))
 receipt={'status':'SUPPORT_ENERGY_SCORES_FROZEN','scientific_outcomes_read':False,'groups':24,'candidates_per_group':8,'mask_positions':list(range(0,32,3)),'checkpoint_receipts':checkpoint_receipts,'bank_receipts':banks,'scores_sha256':sha(a.output/'SCORES.npz'),'metadata_sha256':sha(a.metadata)}
 (a.output/'RECEIPT.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)); (a.output/'OUTCOME_BLIND_SCORES_COMPLETE').touch(); print(json.dumps(receipt,sort_keys=True))
if __name__=='__main__': main()
