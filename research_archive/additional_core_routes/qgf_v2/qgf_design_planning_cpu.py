"""Prospective QGF design calculations; no model, simulator, fit, or rollout.

Exact power is conditional on hypothetical iid paired Bernoulli outcomes.
Inventory reads pinned source metadata only; it is NOT a collection manifest.
"""

import argparse
import ast
from collections import Counter
import hashlib
import json
import math
from pathlib import Path


def binomial_pmf(n, p):
    if not isinstance(n, int) or n < 0 or not 0 <= p <= 1:
        raise ValueError("Require integer n >= 0 and probability in [0, 1]")
    if p in (0, 1):
        result = [0.0] * (n + 1)
        result[n if p else 0] = 1.0
        return result
    # Start at the mode rather than underflowing at an extreme tail.
    mode = min(n, math.floor((n + 1) * p))
    result = [0.0] * (n + 1)
    result[mode] = 1.0
    for k in range(mode, 0, -1):
        result[k - 1] = result[k] * k / (n - k + 1) * (1 - p) / p
    for k in range(mode, n):
        result[k + 1] = result[k] * (n - k) / (k + 1) * p / (1 - p)
    total = math.fsum(result)
    return [value / total for value in result]


def mcnemar_p(rescues, regressions):
    if min(rescues, regressions) < 0:
        raise ValueError("Counts cannot be negative")
    d = rescues + regressions
    return min(1.0, 2 * math.fsum(binomial_pmf(d, 0.5)[:min(rescues, regressions) + 1]))


def positive_rejection_threshold(d, alpha=0.05):
    if not 0 < alpha < 1:
        raise ValueError("Invalid alpha")
    pmf = binomial_pmf(d, 0.5)
    tail = 0.0
    threshold = d + 1
    for k in range(d, d // 2, -1):
        tail += pmf[k]
        if 2 * tail <= alpha:
            threshold = k
        else:
            break
    return threshold


def paired_power(n, delta, discordance, thresholds=None, alpha=0.05):
    """P(two-sided exact rejection AND positive direction), not all rejection."""
    if not 0 <= delta <= discordance <= 1:
        raise ValueError("Require 0 <= delta <= discordance <= 1")
    if discordance == 0:
        return 0.0
    probability_rescue_given_discordance = (discordance + delta) / (2 * discordance)
    d_pmf = binomial_pmf(n, discordance)
    terms = []
    for d in range(n + 1):
        threshold = thresholds[d] if thresholds is not None else positive_rejection_threshold(d, alpha)
        conditional = math.fsum(binomial_pmf(d, probability_rescue_given_discordance)[threshold:])
        terms.append(d_pmf[d] * conditional)
    return math.fsum(terms)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(source):
    root = source / 'third_party/LIBERO-plus/libero/libero'
    task_path = root / 'benchmark/libero_suite_task_map.py'
    category_path = root / 'benchmark/task_classification.json'
    tree = ast.parse(task_path.read_text())
    assignment = next(node for node in tree.body if isinstance(node, ast.Assign)
                      and any(isinstance(target, ast.Name) and target.id == 'libero_task_map'
                              for target in node.targets))
    names = ast.literal_eval(assignment.value)['libero_10']
    records = json.loads(category_path.read_text())['libero_10']
    by_name = {item['name']: item for item in records}
    assert len(names) == len(set(names)) == len(records) == len(by_name)
    assert set(names) == set(by_name)
    bases = sorted(path.name.removesuffix('.pruned_init')
                   for path in (root / 'init_files/libero_10').glob('*.pruned_init'))
    annotated = []
    for name in names:
        matches = [base for base in bases if name == base or name.startswith(base + '_')]
        if len(matches) != 1:
            raise ValueError('Ambiguous/missing base-task family: ' + name)
        annotated.append({**by_name[name], 'base_task_family': matches[0]})
    source_paths = [task_path, category_path, root / 'benchmark/__init__.py']
    return {
        'status': 'READ_ONLY_METADATA_NOT_A_COHORT_OR_EXECUTION_GATE',
        'source': str(source), 'suite': 'libero_10',
        'variant_count': len(names), 'base_task_family_count': len(bases),
        'task0': annotated[0],
        'category_counts': dict(sorted(Counter(item['category'] for item in annotated).items())),
        'family_counts': dict(sorted(Counter(item['base_task_family'] for item in annotated).items())),
        'family_category_counts': {
            base: dict(sorted(Counter(item['category'] for item in annotated
                                      if item['base_task_family'] == base).items()))
            for base in bases
        },
        'source_sha256': {str(path): sha256(path) for path in source_paths},
        'caveats': [
            'Variant count is not independent scene count.',
            'Names can share physical initial states and differ only by observation/language.',
            'No environment initialization, model import, or outcomes were evaluated.',
            'Official metadata difficulty is not a measured QGF effect and does not select tasks.',
        ],
    }


def plan():
    grid = list(range(10, 1201, 10))
    thresholds = [positive_rejection_threshold(d) for d in range(max(grid) + 1)]
    scenarios = []
    for delta in (0.05, 0.10):
        for q in (0.10, 0.20, 0.30):
            rescue_p = (q + delta) / (2 * q)
            conditional = [math.fsum(binomial_pmf(d, rescue_p)[thresholds[d]:])
                           for d in range(max(grid) + 1)]
            powers = {n: math.fsum(p * cond for p, cond in zip(binomial_pmf(n, q), conditional))
                      for n in grid}
            scenarios.append({
                'delta': delta, 'discordance': q,
                'rescue_probability': (q + delta) / 2,
                'regression_probability': (q - delta) / 2,
                'power_n30': powers[30], 'power_n100': powers[100],
                'power_n300': powers[300],
                'first_grid_n_power_ge_80pct': next((n for n in grid if powers[n] >= 0.8), None),
                'power_grid': powers,
            })
    # For a fixed deterministic selector pi vs uniform logging mu=1/4:
    # D = (4*1[A=pi(X)] - 1)*Y lies in {-1,0,3}; E[D^2|X] <= 3.
    # The normal planning half-width below is NOT a finite-sample guarantee.
    ipw = [{'n': n, 'expected_selector_matches': n / 4,
            'normal_planning_halfwidth_upper_variance_3': 1.959963984540054 * math.sqrt(3 / n)}
           for n in (32, 112, 224, 400, 1200, 5000)]
    return {
        'status': 'HYPOTHETICAL_DESIGN_CALCULATION_NOT_ROBOT_RESULTS',
        'paired_test': 'two-sided exact binomial McNemar, alpha=.05, positive direction only',
        'assumptions': [
            'Independent identically distributed paired binary outcomes; fixed N and no interim efficacy peeking.',
            'Delta and discordance are hypothetical planning inputs, not estimates from old formal data.',
            'One shared fresh scene per pair; repeated scene/variant groups are not additional independent pairs.',
            'Primary comparison is QGF versus equal-compute random; no multiplicity correction in this table.',
            'Task dependence, exclusions, model selection, and fixed-stratum mixtures are not modeled here.',
            'First adequate N is on a 10-scene grid, not a globally minimal N.',
        ],
        'scenarios': scenarios,
        'local_ipw_precision_illustration': ipw,
        'ipw_caveats': [
            'Single randomized intervention, fixed continuation, binary eventual reward, logged propensity=.25.',
            'Selector fixed independently of evaluation episodes. No whole-trajectory/sequential policy claim.',
            'Worst-case variance planning scale only, not a confidence interval or necessity bound.',
            'A useful cross-fitted outcome model may reduce variance; no reduction is assumed.',
        ],
        'small_count_checks': {'5_rescues_0_regressions': mcnemar_p(5, 0),
                               '6_rescues_0_regressions': mcnemar_p(6, 0),
                               '5_rescues_2_regressions': mcnemar_p(5, 2)},
        'script_sha256': sha256(Path(__file__)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source', type=Path)
    args = parser.parse_args()
    result = plan()
    if args.source:
        result['pinned_population_inventory'] = inventory(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write('\n')
    print(json.dumps({'output': str(args.output), 'sha256': sha256(args.output),
                      'scenarios': [{key: value for key, value in item.items() if key != 'power_grid'}
                                    for item in result['scenarios']]}, indent=2))


if __name__ == '__main__':
    main()
