"""Outcome-blind registration and static inventory; never imports simulator/ML."""
import argparse
import ast
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def key(text):
    return hashlib.sha256(text.encode()).hexdigest()


def select(manifest):
    partitions = manifest['partitions']
    train = partitions['train']
    forbidden = {e['physical_input_group'] for p in ('validation', 'formal')
                 for e in partitions[p]}
    selected = []
    for family in sorted({e['family'] for e in train}):
        entries = [e for e in train if e['family'] == family]
        groups = sorted({e['physical_input_group'] for e in entries},
                        key=lambda g: key('paired-action-v1|' + family + '|' + g))[:4]
        if len(groups) != 4:
            raise ValueError('Insufficient physical groups')
        for group in groups:
            if group in forbidden:
                raise ValueError('Partition overlap')
            entry = min((e for e in entries if e['physical_input_group'] == group),
                        key=lambda e: key('paired-entry-v1|' + e['episode_id']))
            selected.append(dict(entry, paired_boundary_model_step=100))
    if len(selected) != 16:
        raise ValueError('Expected four families and16states')
    return selected


def inventory(path):
    tree = ast.parse(path.read_text())
    assignments = set()
    methods = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods.append({'name': node.name, 'line': node.lineno})
        if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store):
            if isinstance(node.value, ast.Name) and node.value.id == 'self':
                assignments.add(node.attr)
    return {'path': str(path), 'sha256': sha(path), 'methods': methods,
            'self_assigned_fields': sorted(assignments)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False)
    root = args.root
    manifest_path = root / 'qgf_gradient_v1/evidence/COHORT_MANIFEST.json'
    expected = '7194f02c8dba2c9ae01fddab1d0c48c169e28f6778e3926a0386dfeff0307af9'
    if sha(manifest_path) != expected:
        raise ValueError('Frozen cohort hash differs')
    manifest = json.loads(manifest_path.read_text())
    registration = {'status': 'METADATA_REGISTERED_NOT_ACTION_ADMITTED',
                    'parent_manifest_sha256': expected, 'selection_uses_outcomes': False,
                    'entries': select(manifest), 'source_sha256': sha(Path(__file__)),
                    'protocol_sha256': sha(root / 'paired_action_v1/PROTOCOL.md')}
    (args.output / 'REGISTRATION.json').write_text(json.dumps(registration, indent=2, sort_keys=True))
    site = root / 'runtime/simplewam_inference_py310_v2/lib/python3.10/site-packages'
    source = root / 'backbones/Simple-WAM-396cba18c318bc33a1ef42513b85298e3016e28a'
    paths = [source / 'third_party/LIBERO-plus/libero/libero/envs/env_wrapper.py']
    for directory in ('controllers', 'robots', 'environments', 'utils'):
        paths.extend(sorted((site / 'robosuite' / directory).rglob('*.py')))
    report = {'status': 'STATIC_INVENTORY_COMPLETE_DYNAMIC_RESTORE_REQUIRED',
              'gpu_work': False, 'environment_actions': 0, 'imports_simulator': False,
              'files': [inventory(p) for p in paths],
              'limitations': ['AST does not establish full mutable/native state coverage',
                             'No restoration or causal-action result exists yet']}
    (args.output / 'SOURCE_INVENTORY.json').write_text(json.dumps(report, indent=2, sort_keys=True))
    (args.output / 'STATIC_INVENTORY_COMPLETE').touch()
    print(json.dumps({'status': report['status'], 'states': len(registration['entries']),
                      'source_files': len(report['files'])}), flush=True)


if __name__ == '__main__':
    main()
