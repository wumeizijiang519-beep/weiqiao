"""Frozen QGF-v3 OOF condition grid."""


def conditions():
    return [{'fold': fold, 'seed': seed, 'state_only': kind == 'state_only', 'kind': kind,
             'name': f'fold{fold}_{kind}_seed{seed}'}
            for fold in range(4) for kind in ('action', 'state_only') for seed in range(3)]
