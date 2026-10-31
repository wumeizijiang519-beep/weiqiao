# Current-only R+1 feature blocks preparation

feature_corpus.py implements measured-observation R+1 encoding and immutable
per-episode NPZ/provenance receipts. Callback receives only current cameras,
proprio,task text and known remaining time. Prior actual execution lengths
advance remaining time for the NEXT observation, never reveal future length.
Zero-transition episodes still produce one real observation feature/ledger row.

extract_feature_blocks.py provides a gated first-two fixed training episode
cost-pilot entry point. Do not run before full288ADMIT and real GPU encoder
audit. Its registration must pin dataset/report/resource-cost/source SHA,
fixed train0000/0001 and new run directory; hard<=1200seconds. Deployment must
add an outer timeout and verified idle GPU/allocation owner/UUID/RAM and process
cost accounting. The Python per-observation deadline alone is not a process
hard timeout. No registered launch is claimed and no real features exist yet.

Future first-two pilot blocks count ONCE in eventual288-feature corpus. Do not
re-encode them for full extraction; reconcile receipts and freeze a new bounded
remaining286 extraction registration from measured p90/frame count, with full
load/I/O overhead and8GPUh shared feature/critic cap20percent reserve. Pilot
failure preserves completed blocks for audited infrastructure recovery rather
than silent re-extraction. A full corpus INDEX/finalizer and trainer are still
needed. This pilot entry point intentionally cannot claim all288features done.

Six pure-CPU synthetic feature-codec tests cover input mutation too, plus prior
8reader/7corpus tests(total21). No actual WAM feature, performance or critic claim. Full entry
point syntax and registration-rejection tests must pass before deployment;
real GPU encoder audit and exact source/cost registration remain mandatory.
