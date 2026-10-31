# Action Dynamics Auxiliary V1 Dispatcher Repair

The first dispatcher stopped before launching any worker because its broad
`*.json` inventory counted the registration manifest together with the nine
worker registrations. The failed launcher log and empty dispatch directory are
preserved. The sole repair narrows the inventory pattern to the nine named
`qgf_action_dynamics_seed*_fold*_v1.json` files. No corpus, split, seed, model,
target, update count, threshold, budget, or worker source changes.
