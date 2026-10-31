# Runtime-Anchored Entry-11 Resume V1

- Fixed registration index: 11 only.
- Output: `runtime_anchored_qgf_v1/resume_entry11_v1`.
- Scientific runner and all registered inputs remain byte-identical.
- Existing `remaining_v1/entry_11` is preserved and excluded from analysis.
- Clean success requires `REPORT.json`, `PILOT_RETURNED`, eight real branches,
  and the unchanged runner's fail-closed checks.
- Hard allocation budget: 6,000 GPU seconds, including failure.
- No automatic retry.
