"""Freeze all support-gradient group execution receipts before pilot."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(); p.add_argument('--manifest',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args(); manifest=json.loads(a.manifest.read_text())
 if manifest['status']!='ENSEMBLE_DISAGREEMENT_QGF_V1_REGISTERED' or len(manifest['entries'])!=8: raise RuntimeError('Manifest invalid')
 a.output.mkdir(parents=True,exist_ok=False); rows=[]
 for index,source in enumerate(manifest['entries']):
  entry=dict(source); archive=Path(entry['episode_directory']); config_path=archive/'config.json'; config=json.loads(config_path.read_text())
  if config.get('episode_id')!=entry['episode_id']: raise RuntimeError('Episode changed')
  entry['task_name']=config['task_name']; entry['state_sha256']=config['state_sha256']; actions=[]
  for receipt in entry['transition_receipts']:
   path=archive/f"transition_{receipt['index']:04d}/transition.npz"
   if sha(path)!=receipt['sha256']: raise RuntimeError('Transition changed')
   with np.load(path,allow_pickle=False) as d: actions.extend(np.asarray(d['executed_actions'][:int(d['actual_length'])],dtype=np.float32))
  prefix=np.stack(actions)
  if prefix.shape!=(entry['boundary_model_step'],7): raise RuntimeError('Prefix changed')
  entry['prefix_actions_sha256']=hashlib.sha256(prefix.tobytes()).hexdigest(); value={'status':'ENSEMBLE_DISAGREEMENT_QGF_V1_GROUP_AUTHORIZED','manifest_sha256':sha(a.manifest),'entry_index':index,'episode_config_sha256':sha(config_path),'entry':entry}; path=a.output/f'entry_{index:02d}.json'; path.write_text(json.dumps(value,indent=2,sort_keys=True)); rows.append({'entry_index':index,'authorization_sha256':sha(path),'episode_id':entry['episode_id']})
 (a.output/'MANIFEST.json').write_text(json.dumps({'status':'ENSEMBLE_DISAGREEMENT_QGF_V1_8_GROUPS_AUTHORIZED','manifest_sha256':sha(a.manifest),'groups':rows,'replacement_allowed':False},indent=2,sort_keys=True))
if __name__=='__main__': main()
