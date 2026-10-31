"""CPU source/metadata inventory. Does NOT admit a rollout cohort or read rewards."""

import ast
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re


ROOT = Path('/public/wangsenbao221/pqr/qgf_mainstream_20261022')
SOURCE = ROOT / 'backbones/Simple-WAM-396cba18c318bc33a1ef42513b85298e3016e28a'
LIBERO = SOURCE / 'third_party/LIBERO-plus/libero/libero'
OUT = ROOT / 'qgf_gradient_v1/evidence/cohort_metadata_audit.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(value):
    value = re.sub(r'^(KITCHEN|LIVING_ROOM|STUDY)_SCENE\d+_', '', value)
    return re.sub(r'[^a-z0-9]+', ' ', value.lower()).strip()


def relevant_strings(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in ('task', 'task_name', 'task_description', 'base_task_family') and isinstance(child, str):
                yield child
            elif isinstance(child, (dict, list)):
                yield from relevant_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from relevant_strings(child)


def initial_path(task_name):
    # Mirrors the inspected pinned Benchmark.get_task_init_states path rules.
    name = task_name + '.pruned_init'
    if '_language_' in name:
        name = name.split('_language_')[0] + '.pruned_init'
    elif '_view_' in name:
        name = name.split('_view_')[0] + '.pruned_init'
    else:
        if '_table_' in name:
            name = re.sub(r'_table_\d+', '', name)
        if '_tb_' in name:
            name = re.sub(r'_tb_\d+', '', name)
        if '_light_' in name:
            name = name.split('_light_')[0] + '.pruned_init'
        if '_add_' in task_name or '_level' in task_name:
            return LIBERO / 'init_files/libero_newobj/libero_10' / (task_name + '.pruned_init')
    return LIBERO / 'init_files/libero_10' / name


def bddl_path(task_name):
    # OffScreenRenderEnv.__init__ decodes these virtual names before exists().
    if '_view_' in task_name and '_initstate_' in task_name:
        task_name = task_name.split('_view_')[0]
    return LIBERO / 'bddl_files/libero_10' / (task_name + '.bddl')


def main():
    mapping_path = LIBERO / 'benchmark/libero_suite_task_map.py'
    classification_path = LIBERO / 'benchmark/task_classification.json'
    tree = ast.parse(mapping_path.read_text())
    node = next(node for node in tree.body if isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == 'libero_task_map' for t in node.targets))
    all_names = ast.literal_eval(node.value)
    names = all_names['libero_10']
    metadata = {record['name']: record for record in json.loads(classification_path.read_text())['libero_10']}
    families = sorted(p.name.removesuffix('.pruned_init')
                      for p in (LIBERO / 'init_files/libero_10').glob('*.pruned_init'))
    exposed, inspected, unresolved, outside_suite = {}, [], [], []
    for run in sorted((ROOT / 'runs').iterdir()):
        if not run.is_dir() or not run.name.startswith(('simplewam_', 'imagewam_', 'kairos_')):
            continue
        for directory, subdirectories, files in os.walk(run):
            subdirectories[:] = [name for name in subdirectories
                                 if name not in ('cache', '__pycache__', 'site-packages', '.git')]
            if len(Path(directory).relative_to(run).parts) >= 3:
                subdirectories[:] = []
            for filename in files:
                if not filename.endswith('.json') or not any(x in filename.lower() for x in ('summary', 'result', 'report')):
                    continue
                path = Path(directory) / filename
                if path.stat().st_size > 5 * 1024 * 1024:
                    continue
                try:
                    data = json.loads(path.read_text())
                except (ValueError, UnicodeError):
                    unresolved.append(str(path))
                    continue
                strings = list(relevant_strings(data))
                if not strings:
                    continue
                inspected.append({'path': str(path), 'sha256': sha(path), 'task_strings': sorted(set(strings))})
                for text in strings:
                    matches = [family for family in families if normalize(family) in normalize(text)]
                    if not matches:
                        foreign = [(suite, name) for suite, values in all_names.items()
                                   if suite != 'libero_10' for name in values
                                   if normalize(text) == normalize(name)]
                        if foreign:
                            outside_suite.append({'path': str(path), 'task': text,
                                                  'other_suite_matches': foreign})
                        else:
                            unresolved.append({'path': str(path), 'unmapped_task': text})
                    for family in matches:
                        exposed.setdefault(family, set()).add(str(path))
    eligible = [family for family in families if family not in exposed]
    ranked = sorted(eligible, key=lambda family: hashlib.sha256(
        ('qgf-gradient-family-202640000|' + family).encode()).hexdigest())
    proposed = ranked[:4]
    records, path_hashes = [], {}
    for task_id, name in enumerate(names):
        candidates = [family for family in families if name == family or name.startswith(family + '_')]
        if len(candidates) != 1:
            raise ValueError('Ambiguous task family: ' + name)
        if candidates[0] not in proposed:
            continue
        path = initial_path(name)
        if path.exists() and str(path) not in path_hashes:
            path_hashes[str(path)] = sha(path)
        records.append({'task_id': task_id, 'name': name, 'family': candidates[0],
                        'category': metadata[name]['category'], 'initial_state_path': str(path),
                        'initial_state_file_exists': path.exists(),
                        'bddl_path': str(bddl_path(name)), 'bddl_exists': bddl_path(name).exists()})
    counts = Counter(record['initial_state_path'] for record in records)
    result = {
        'status': 'METADATA_AUDIT_ONLY_NOT_A_LAUNCH_MANIFEST',
        'outcomes_read_for_selection': False, 'new_backbones': False,
        'mapping_sha256': sha(mapping_path), 'classification_sha256': sha(classification_path),
        'benchmark_source_sha256': sha(LIBERO / 'benchmark/__init__.py'),
        'environment_wrapper_sha256': sha(LIBERO / 'envs/env_wrapper.py'),
        'exposed_families': {key: sorted(value) for key, value in exposed.items()},
        'inspected_exposure_sources': inspected, 'unresolved_exposure_records': unresolved,
        'exposures_in_other_suites': outside_suite,
        'eligible_family_count': len(eligible), 'proposed_four_families': proposed,
        'category_counts': dict(Counter(record['category'] for record in records)),
        'initial_file_alias_groups': {key: count for key, count in counts.items() if count > 1},
        'initial_file_sha256': path_hashes, 'records': records,
        'blockers_before_collection': [
            'Cross-check all source benchmarks and historical exposure logs; the JSON scan is not exhaustive.',
            'Load state vectors and group identical physical states across files, not only same-path aliases.',
            'Resolve unmatched historical task strings and missing official asset paths.',
            'Freeze actual episode seed/init/perturbation lists and verify all split/group invariants.',
            'Finish collector/reward/RNG contract tests and measured budget forecast.',
        ],
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps({key: result[key] for key in ('status', 'eligible_family_count', 'proposed_four_families',
                                                 'category_counts')}, indent=2))
    print('unresolved_records', len(unresolved), 'alias_paths', len(result['initial_file_alias_groups']))
    print('missing_assets', sum(not x['initial_state_file_exists'] or not x['bddl_exists'] for x in records))


if __name__ == '__main__':
    main()
