# Simple-WAM Visual RL Final Critic Retrain V1

## Purpose

The completed Online V2 result remains frozen as
`NO_SIMPLEWAM_VISUAL_QGF_ONLINE_BENEFIT`. This prospective branch tests the
specific implementation gap identified after that freeze: the deployed critic
was an ensemble of fold models trained for 3,000 updates, while the reference
pipeline trains a final critic on all training data for 50,000 updates.

## Frozen inputs

- Simple-WAM visual feature export, RL-token encoder, token values, rewards,
  transition alignment, action coordinates, K=10 prefix, and corpus are frozen.
- Corpus SHA-256:
  `a2337827258238d6369a0161179491ffe3629b04f113cea9c0ab3d84a56e62b0`.
- Token checkpoint SHA-256:
  `40a436a09e618965642f680bda5d1339f3426ccd735b73aba6629fbbc46a8c97`.
- No validation, formal, or Online V1/V2 outcomes enter training or checkpoint
  selection.

## Training contract

- Train three independent full-data critics with seeds 202644201, 202644202,
  and 202644203.
- Every critic uses all 12,218 training transitions; there is no held-out fold.
- Fixed 50,000 updates, batch size 64, hidden width 512, Adam learning rate
  3e-4, gamma 0.99, expectile 0.7, target EMA rate 0.005, and gradient norm 10.
- Save only the fixed final-step checkpoint for deployment. Training metrics
  are diagnostic and cannot select a seed or checkpoint.
- The frozen deployment ensemble is the mean of the three conservative
  `min(Q1,Q2)` predictions. All seeds are retained regardless of metrics.

## Qualification and later evaluation

- Training is valid only if all three runs finish cleanly, hashes match, losses
  stay finite, action sensitivity is nonzero, and an independent audit passes.
- Existing validation outcomes are consumed and may only be used as historical
  diagnostics. A new online claim requires previously untouched formal/test
  physical scenes with a result-independent registration before execution.
- No change to QGF weight, support bounds, action normalization, WAM, token,
  reward, task selection, or success definition is permitted in this branch.

