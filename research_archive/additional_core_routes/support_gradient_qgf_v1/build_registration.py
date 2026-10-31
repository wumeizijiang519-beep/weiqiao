"""Select a new prospective 16-group training-only support-gradient cohort."""
import argparse,hashlib,json,shutil,sys
from pathlib import Path

TAG='support-gradient-qgf-v1:'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(); p.add_argument('--root',type=Path,required=True); p.add_argument('--dataset-result',type=Path,required=True); p.add_argument('--failure',type=Path,required=True); p.add_argument('--v1-final',type=Path,required=True); p.add_argument('--v2-manifest',type=Path,required=True); p.add_argument('--v2-final',type=Path,required=True); p.add_argument('--setwise',type=Path,required=True); p.add_argument('--support-bases',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args(); root=a.root.resolve(); sys.path.insert(0,str((root/'progress_pairwise_qgf_v1').resolve())); from build_registration import DATASET_SHA,inspect_episode
 if sha(a.dataset_result)!=DATASET_SHA: raise RuntimeError('Dataset changed')
 dataset=json.loads(a.dataset_result.read_text()); failure=json.loads(a.failure.read_text()); v1_final=json.loads(a.v1_final.read_text()); v2_manifest=json.loads(a.v2_manifest.read_text()); v2_final=json.loads(a.v2_final.read_text()); setwise=json.loads(a.setwise.read_text()); excluded={row['physical_input_group'] for row in failure['entries']}; excluded.update(row['physical_input_group'] for row in v1_final['results']); excluded.update(v2_manifest['entries'][row['entry_index']]['physical_input_group'] for row in v2_final['receipts']); excluded.update(row['physical_input_group'] for row in setwise['entries'])
 by_group={}
 for entry in sorted(dataset['entries'],key=lambda x:x['episode_id']):
  record,_=inspect_episode(entry,excluded)
  if record is None: continue
  record['selection_rank_sha256']=hashlib.sha256((TAG+record['physical_input_group']).encode()).hexdigest(); by_group.setdefault(record['physical_input_group'],record)
 families=sorted({x['family'] for x in by_group.values()}); selected=[]; inventory={}
 if len(families)!=4: raise RuntimeError('Expected four families')
 for family in families:
  rows=sorted((x for x in by_group.values() if x['family']==family),key=lambda x:x['selection_rank_sha256'])
  if len(rows)<4: raise RuntimeError('Insufficient new groups')
  selected.extend(rows[:4]); inventory[family]={'eligible_groups':len(rows),'selected':4}
 if len(selected)!=16 or excluded.intersection(x['physical_input_group'] for x in selected): raise RuntimeError('Selection overlap')
 a.output.mkdir(parents=True,exist_ok=False); basis=a.output/'SUPPORT_BASES.npz'; shutil.copyfile(a.support_bases,basis)
 if sha(basis)!=setwise['support_bases_sha256']: raise RuntimeError('Support basis changed')
 result={'status':'SUPPORT_GRADIENT_QGF_V1_REGISTERED','groups':16,'pilot_index':0,'entries':selected,'support':setwise['support'],'support_bases_sha256':sha(basis),'excluded_prior_groups':len(excluded),'family_inventory':inventory,'selection_rule':'sha256 support-gradient-qgf-v1 per physical group','selection_reads_candidate_outcomes':False,'validation_or_formal_read':False,'replacement_allowed':False,'bootstrap_seed':202643101,'bootstrap_draws':10000}
 (a.output/'MANIFEST.json').write_text(json.dumps(result,indent=2,sort_keys=True)); print(json.dumps({'status':result['status'],'groups':16,'excluded':len(excluded),'inventory':inventory},indent=2))
if __name__=='__main__': main()
