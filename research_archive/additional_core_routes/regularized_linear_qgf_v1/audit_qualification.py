"""Structural independent audit for Regularized-Linear qualification."""
import argparse,hashlib,json
from pathlib import Path
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(); p.add_argument('--qualification',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args(); a.output.mkdir(parents=True,exist_ok=False)
 source=a.qualification/'REPORT.json'; report=json.loads(source.read_text()); errors=[]
 if report.get('confirmation_labels_read') is not False: errors.append('confirmation seal violated')
 if report.get('bootstrap_draws')!=10000: errors.append('bootstrap mismatch')
 if set(report.get('seed_reports',{}))!={'202642301','202642302','202642303'}: errors.append('seed inventory mismatch')
 if set(report.get('group_bootstrap',{}))!={'state_only','permutation','action_only'}: errors.append('control inventory mismatch')
 status=report.get('status')
 if status not in {'REGULARIZED_LINEAR_DEVELOPMENT_ADMIT','NO_STABLE_REGULARIZED_LINEAR_DEVELOPMENT_CRITIC'}: errors.append('unexpected status')
 if not (a.qualification/str(status)).exists(): errors.append('marker missing')
 result={'status':'REGULARIZED_LINEAR_QUALIFICATION_AUDIT_PASS' if not errors else 'REGULARIZED_LINEAR_QUALIFICATION_AUDIT_FAIL','errors':errors,'qualification_status':status,'qualification_report_sha256':sha(source)}
 (a.output/'REPORT.json').write_text(json.dumps(result,indent=2,sort_keys=True)); (a.output/result['status']).touch(); print(json.dumps(result,sort_keys=True))
if __name__=='__main__': main()
