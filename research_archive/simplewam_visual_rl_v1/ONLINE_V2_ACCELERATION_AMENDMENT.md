# Online V2 Execution Acceleration Amendment

- The registered 60 scenes, 240 tasks, models, seeds, actions, support policy,
  horizons, endpoints, and statistical thresholds are unchanged.
- Hardware audit on gpu21 measured about 15.5GB device memory per active WAM
  process on an 80GB A800. The job owns four cards, 16 CPUs, and 256GB RAM.
- Replace four logical lanes with eight logical lanes, two processes per GPU.
  Each GPU step keeps four CPUs and 60GB RAM; each process uses two OpenMP
  threads. Logical lane `i` executes task indices `i mod 8`.
- Completed task directories are immutable and skipped. A directory without a
  completion receipt at cutover is archived as infrastructure-partial, then
  that task is executed once from scratch under unchanged scientific bytes.
- This amendment changes throughput only and is frozen before accelerated
  execution begins.
