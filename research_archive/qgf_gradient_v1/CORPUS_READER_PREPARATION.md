# Admitted corpus filesystem reader preparation

CPU development only while final training shard collects. No real trajectory
read, feature extraction, admission, critic fitting or online result is implied.
corpus_reader.py joins a pinned ADMIT_FOR_RL_QUALIFICATION dataset certificate
with a future pinned current-only feature index, encoder report and288-entry
union. It rejects group/fold leakage, missing R+1 observations, changed summary/
transition/observation/feature hashes, feature path escapes and unexpected fields.
Actual-length rewards/MC/TD inputs use existing rl_corpus.py; critic plan masks
remain known predecision length, not future termination. No unexecuted labels.

Zero-transition episodes return no fitting arrays but an explicit retained ledger
entry, including success and fold/group. They must remain in all scientific
population counts; do not invent macro-actions or silently drop those episodes.
Production training batching must record the separate nonempty-transition subset.

Future INDEX.json schema (not yet produced/qualified):
status=CURRENT_ONLY_CORPUS_FEATURES_COMPLETE,dataset_result_sha256,
encoder_report (relative),encoder_report_sha256,episodes (all288 exactly once).
Each episode row has episode_id,file (relative NPZ),sha256,and ordered
observation_file_sha256 for all R+1 measured observation files. Each NPZ has
only current_features float32[R+1,D]; D must equal audited encoder spec.
Encoder report must be CURRENT_FEATURE_ENCODER_AUDIT_PASS for the same dataset,
future_frames0 and matching features.py source. Callers freeze the feature-index
SHA before read/fit. The future extractor still must generate this evidence and
pass registered GPU current-only A-B-A/cache/RNG/source/cost audits first.

The low-level read_episode codec is for already-certified inputs/tests only;
production workers use load_admitted_episode, not a codec bypass. No new field
from future reward/actual length may be added to decision-time features. No
full production extractor/OOF trainer/online dispatcher is claimed complete.

Local synthetic codec tests8/8 and existing RL corpus tests7/7 pass. Test counts
are software preparation, not method evidence. Source SHA list is frozen before
remote CPU tests. Live collector/registered aggregator sources remain unchanged.
