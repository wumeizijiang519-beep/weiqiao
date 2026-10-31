"""Freeze outcome-independent prospective scenes after metadata/state audit."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import random

from cohort_audit import ROOT, sha


def rank(namespace, value):
    return hashlib.sha256((namespace + '|' + str(value)).encode()).hexdigest()


def validate_manifest(document):
    parts = document['partitions']
    expected = {'train': 288, 'validation': 64, 'formal': 216}
    seen_groups, seen_seeds = {}, set()
    for partition, entries in parts.items():
        if len(entries) != expected[partition]:
            raise ValueError('Unexpected prospective cohort size')
        for entry in entries:
            group = entry['physical_input_group']
            if group in seen_groups and seen_groups[group] != partition:
                raise ValueError('Physical group crosses partitions')
            seen_groups[group] = partition
            if entry['environment_seed'] in seen_seeds:
                raise ValueError('Environment seed reused')
            seen_seeds.add(entry['environment_seed'])
        if len({entry['category'] for entry in entries}) != 7:
            raise ValueError('Missing perturbation category')
        identities = [(entry['task_id'], entry['initial_state_index']) for entry in entries]
        if len(identities) != len(set(identities)):
            raise ValueError('Repeated task and initial state within partition')
    if len(document['families']) != 4:
        raise ValueError('Wrong task-family count')


def main():
    evidence = ROOT / 'qgf_gradient_v1/evidence'
    source = evidence / 'state_group_audit.json'
    catalogue = json.loads(source.read_text())
    exposure_path = evidence / 'cohort_metadata_audit.json'
    exposure = json.loads(exposure_path.read_text())
    if exposure['unresolved_exposure_records']:
        raise RuntimeError('Unresolved prior task identity')
    families = exposure['proposed_four_families']
    groups, tasks = catalogue['groups'], {x['task_id']: x for x in catalogue['tasks']}
    categories = sorted({x['category'] for x in tasks.values()})
    parts = {key: [] for key in ('train', 'validation', 'formal')}
    group_partition = {}
    per_family = {'train': 72, 'validation': 16, 'formal': 54}
    base_slices = {'train': (0, 24), 'validation': (24, 32), 'formal': (32, 50)}
    caps = {'train': 3, 'validation': 2, 'formal': 3}
    for family_index, family in enumerate(families):
        if family in exposure['exposed_families']:
            raise RuntimeError('Previously exposed family')
        broad = sorted([key for key, g in groups.items() if g['family'] == family
                        and len(g['categories']) == 6], key=lambda key: rank('group202640000', key))
        layout = sorted([key for key, g in groups.items() if g['family'] == family
                         and g['categories'] == ['Objects Layout']],
                        key=lambda key: rank('layout202640000', key))
        if len(broad) != 50:
            raise RuntimeError('Unexpected metadata population; no silent replacement')
        layout_cursor = 0
        for partition_index, (partition, target) in enumerate(per_family.items()):
            start, end = base_slices[partition]
            available = broad[start:end]
            for group in available:
                group_partition[group] = partition
            quotas = {category: target // len(categories) for category in categories}
            offset = (family_index + partition_index) % len(categories)
            for i in range(target % len(categories)):
                quotas[categories[(offset + i) % len(categories)]] += 1
            count_layout = quotas['Objects Layout']
            layout_groups = layout[layout_cursor:layout_cursor + count_layout]
            layout_cursor += count_layout
            if len(layout_groups) != count_layout:
                raise RuntimeError('Not enough layout groups; do not select by outcomes')
            for group in layout_groups:
                group_partition[group] = partition
            used = Counter()
            used_category = set()
            selected = []
            # Interleave categories to distribute repeats across groups.
            remaining = dict(quotas)
            while any(remaining.values()):
                for category in categories:
                    if remaining[category] == 0:
                        continue
                    pool = layout_groups if category == 'Objects Layout' else available
                    pool = [group for group in pool if used[group] < caps[partition]
                            and (group, category) not in used_category]
                    if not pool:
                        raise RuntimeError('Cannot meet category/group design before outcomes')
                    group = min(pool, key=lambda g: (used[g], rank(partition + category, g)))
                    candidates = [(task_id, index) for task_id, index in groups[group]['records']
                                  if tasks[task_id]['category'] == category]
                    task_id, index = min(candidates, key=lambda x: rank('variant202640000', x))
                    task = tasks[task_id]
                    selected.append({
                        'task_id': task_id, 'task_name': task['name'], 'family': family,
                        'category': category, 'initial_state_index': index,
                        'physical_input_group': group, 'state_sha256': groups[group]['state_sha256'],
                        'initial_state_path': task['initial_state_path'],
                        'initial_file_sha256': catalogue['states'][task['initial_state_path']]['file_sha256'],
                        'bddl_path': task['bddl_path'], 'bddl_sha256': sha(Path(task['bddl_path'])),
                    })
                    used[group] += 1
                    used_category.add((group, category))
                    remaining[category] -= 1
            parts[partition].extend(selected)
    arms = ['candidate0', 'random', 'rerank', 'vanilla_qgf', 'supported_qgf']
    env_bases = {'train': 202641000, 'validation': 202643000, 'formal': 202644000}
    selection_bases = {'train': 202642000, 'validation': 202647000, 'formal': 202648000}
    for partition, entries in parts.items():
        entries.sort(key=lambda x: rank('order-' + partition, (x['task_id'], x['initial_state_index'])))
        for index, entry in enumerate(entries):
            entry['episode_id'] = partition + f'_{index:04d}'
            entry['environment_seed'] = env_bases[partition] + index
            entry['selection_seed'] = selection_bases[partition] + index
            entry['group_oof_fold'] = int(rank('oof202640101', entry['physical_input_group']), 16) % 3
            order = list(arms)
            random.Random(202649000 + index).shuffle(order)
            entry['online_arm_order'] = order if partition != 'train' else ['random_logging']
    result = {
        'version': 'qgf_gradient_cohort_v1_20261026',
        'status': 'FROZEN_SCENE_PLAN_COLLECTOR_AND_COST_GATES_STILL_REQUIRED',
        'state_audit_sha256': sha(source), 'exposure_audit_sha256': sha(exposure_path),
        'families': families, 'partitions': parts,
        'split_rule': 'Hash-ranked shared initial-state groups;24/8/18 broad groups per family plus disjoint layout groups.',
        'group_counts': {key: len({x['physical_input_group'] for x in entries}) for key, entries in parts.items()},
        'category_counts': {key: dict(Counter(x['category'] for x in entries)) for key, entries in parts.items()},
        'candidate_seeds': [10000, 11000, 12000, 13000],
        'no_outcome_selection': True, 'new_formal_evidence': False,
        'caveats': ['The exposed-family scan has been cross-checked for known recent LIBERO runs, not checkpoint pretraining.',
                    'Actual initialized simulator state must still be hashed/audited before actions.',
                    'Repeated perturbations remain clustered; do not treat them as independent scenes.',
                    'No collector or robot execution is authorized by this JSON alone.'],
    }
    validate_manifest(result)
    destination = evidence / 'COHORT_MANIFEST.json'
    if destination.exists():
        raise RuntimeError('Frozen manifest already exists; never overwrite')
    destination.write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps({'status': result['status'], 'sha256': sha(destination),
                      'group_counts': result['group_counts'], 'category_counts': result['category_counts']}, indent=2))


if __name__ == '__main__':
    main()
