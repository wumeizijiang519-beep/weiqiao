# Action Prefix Encoder V1

## Purpose

Use otherwise idle critic-only GPUs to pretrain an action-prefix encoder while
the sole WAM-compatible GPU finishes collection. This is an engineering
acceleration artifact, not action-value or online QGF evidence.

## Frozen data contract

- Read only `bank.npz` files under the frozen training-only
  `progress_pairwise_qgf_v1` and `paired_action_v1` trees.
- Never read `REPORT`, reward, success, progress, branch outcome, validation,
  formal, or Progress-Pairwise V2 files.
- Deduplicate by `physical_input_group` and retain the lexicographically first
  valid bank. The only model input is the WAM-native `candidates_native`, shape
  `[8, 32, 7]`, finite float32.
- Split whole physical groups by SHA256: buckets 0-7 train, 8-9 validation.

## Frozen optimization

- Seeds: `202642301`, `202642302`, `202642303`.
- Model: 7-to-128 projection, learned mask token and position embedding,
  three-layer four-head Transformer encoder, 7-D reconstruction head.
- Mask probability 0.30; AdamW, learning rate 3e-4, batch 64, 5000 updates.
- Select no seed by validation score. Preserve all three final checkpoints.

The encoder may initialize a later preregistered action-aware critic, but that
critic must still independently pass physical-group-disjoint OOF,
state-only/permutation controls, action sensitivity, and group bootstrap gates.

