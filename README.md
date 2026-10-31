# Weiqiao Simple-WAM Visual RL/QGF Research Archive

This repository preserves the code and compact scientific record for the
Simple-WAM Visual RL/QGF study conducted on the Weiqiao server before its
shutdown on 2026-10-31.

## Scope

The archived research path is:

```text
frozen Simple-WAM LIBERO backbone
  -> outcome-blind RL token
  -> TwinQ/IQL critic
  -> shared candidate reranking / QGF guidance
  -> untouched formal online evaluation
```

The repository intentionally contains no model weights, checkpoints, feature
arrays, videos, caches, virtual environments, or per-step binary traces.
Paths, byte sizes, hashes, package versions, protocols, source code,
registrations, audits, and final results are retained instead.

## Contents

- `research_archive/simplewam_visual_rl_v1/`: project code, protocols,
  registrations, audits, and frozen reports.
- `research_archive/qgf_gradient_v1/`: relevant QGF source and handoff record.
- `research_archive/additional_core_routes/`: compact server-sourced,
  scientifically distinct QGF route implementations. Its manifest records the
  original relative path, byte size, and SHA256 for every included file.
- `research_archive/backbones/`: compact Simple-WAM source snapshot without
  model weights or the large public LIBERO corpus.
- `research_archive/SERVER_SHUTDOWN_BACKUP_METADATA_20261031/`: environment,
  dependency, path, model-size, and SHA256 records.
- `records/SERVER_SHUTDOWN_RECORD.md`: canonical shutdown and recovery record.
- `records/evidence_snapshot/`: directly readable final protocols and reports.

## Frozen Result

- Full-data final critic: three fixed seeds, 50,000 updates each; independent
  audit passed.
- Untouched formal evaluation: 103 physical groups, 412/412 tasks, zero failed
  receipts; independent audit passed.
- Success rates: candidate0 74.76%, uniform random 76.70%, critic rerank
  71.84%, visual QGF 73.79%.
- Frozen conclusion: `NO_SIMPLEWAM_VISUAL_QGF_FINAL_FORMAL_BENEFIT`.
- Final report SHA256:
  `ab8ffbd1dafabc4e2493ed867d14a7759e27f71a5614c8782f2446ebf6fca86d`.

This negative result is preserved as-is. It must not be rewritten as a
positive QGF result, and the consumed validation/formal outcomes must not be
used for post-hoc checkpoint selection.

## Recovery Boundary

This archive is sufficient to inspect the implementation and audit the
scientific record. It is not a self-contained offline runtime. Large WAM,
VAE, text-encoder, RL-token, and corpus files were not uploaded by design.
Their exact original paths, sizes, and SHA256 values are recorded in
`records/SERVER_SHUTDOWN_RECORD.md` so that future downloads can be checked
against the original experiment.

## Upstream References

- OpenWAM: <https://github.com/OpenWAM-Official/OpenWAM>
- Tau0-QGF visual RL design reference:
  <https://github.com/lanlankilkil/tau0-qgf/blob/main/docs/visual_rl.md>
- openpi-RLT: <https://github.com/Yyshadow/openpi-RLT>
- QGF: <https://github.com/zhouzypaul/qgf>


