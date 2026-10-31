# ImageWAM randomized intervention pilot task1 v1

Frozen: 2026-10-24 19:31 CST, before any task1 policy query.

Task0 is frozen after a valid 4-episode pilot produced 4 successes and 0
failures. It is not extended and no seed is changed. This protocol permits one
deterministic next-task attempt only: libero_10 task id 1. Task1 was selected by
ascending task id, not by observed task1 outcomes.

All model, action, candidate and audit contracts from
IMAGEWAM_INTERVENTION_PILOT_V1.md remain unchanged. Fresh training-only episodes:

- shard0: initial-state indices [5,6], environment seeds
  [202631101,202631102], selection seeds [202631501,202631502].
- shard1: initial-state indices [7,8], environment seeds
  [202631201,202631202], selection seeds [202631601,202631602].

Budget remains two A800 workers, estimated 8-15 minutes, hard 35 minutes and
1.2 GPU-hours. PASS requires four valid episodes and at least 1 success plus 1
failure. If task1 also fails class diversity, stop ImageWAM randomized-
intervention critic qualification and pivot to Kairos; do not screen task2 or
alter seeds.

