"""Frozen, result-independent small-data experiment grid."""


def conditions():
    return [{'fold': fold, 'seed': seed, 'variant': 'td099' if kind == 'td099' else 'calibrated1',
             'state_only': kind == 'state_only', 'kind': kind,
             'name': f'fold{fold}_{kind}_seed{seed}'}
            for fold in range(4) for kind in ('td099', 'calibrated1', 'state_only') for seed in range(3)]
