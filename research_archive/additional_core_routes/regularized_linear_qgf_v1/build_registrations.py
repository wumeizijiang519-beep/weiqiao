"""Freeze nine Regularized-Linear development workers."""
import argparse, hashlib, json
from pathlib import Path

SEEDS=(202642301,202642302,202642303)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(); p.add_argument('--root',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
 root=a.root.resolve(); code=root/'regularized_linear_qgf_v1'; out=a.output.resolve(); out.mkdir(parents=True,exist_ok=False); regs=out/'registrations'; regs.mkdir()
 corpus=root/'runtime_delta_qgf_v1/development_corpus_v1'; audit=root/'runtime_delta_qgf_v1/development_corpus_audit_v1/REPORT.json'; workers=[]
 for seed in SEEDS:
  for fold in range(3):
   stem=f'seed_{seed}_fold_{fold}'; reg={'seed':seed,'held_fold':fold,'updates':3000,'hard_gpu_seconds':900,
    'corpus':str(corpus/'CORPUS.npz'),'corpus_sha256':sha(corpus/'CORPUS.npz'),'metadata':str(corpus/'METADATA.json'),
    'metadata_sha256':sha(corpus/'METADATA.json'),'corpus_audit':str(audit),'corpus_audit_sha256':sha(audit),
    'source_sha256':sha(code/'train_fold.py'),'run_directory':str(out/'runs'/stem),'confirmation_labels_read':False}
   path=regs/f'{stem}.json'; path.write_text(json.dumps(reg,indent=2,sort_keys=True)); workers.append({'worker':stem,'registration_sha256':sha(path)})
 (out/'MANIFEST.json').write_text(json.dumps({'status':'REGULARIZED_LINEAR_9_WORKERS_AUTHORIZED','seeds':list(SEEDS),'folds':3,
  'workers':workers,'updates':3000,'models':['proposed','state_only','permutation','action_only'],
  'confirmation_labels_read':False,'scientific_early_stopping':False},indent=2,sort_keys=True))
if __name__=='__main__': main()
