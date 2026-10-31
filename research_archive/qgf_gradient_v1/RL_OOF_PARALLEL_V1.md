# Bounded fixed OOF parallel release

After full feature341cleanPASS, first actual worker1598338.21seed202640101fold0
has measured200update timingp90.034084845s, conservative predicted each761.315s,
12fitphaseforecast12661.778s incl completedfeatures3526s. Both phase reserve and
perfit1200s bounds pass. Timing only, no loss/heldout outcomes used for release.
The200updates count toward final20000, not a separate restarted attempt.

Register exactly8remaining seed/fold files from the frozen first registration,
all3seedsx3OOFfolds once. Two owned gpu22A800 maximum concurrent workers,
including first21. Each4CPU/20GB/oneGPU/22minouter+1200inner. Generic worker
uses absolute SLURM_STEP_GPUS then pins verified UUID, refuses busy/wrong GPU.
No actor or simulator is loaded. Slurm states/cost/UUID/exit retained. Sources
and dispatcher SHA frozen before activation. No final3all-training refits yet.

dispatch_remaining_rl_oof.py starts only after measured first COST_GATE_PASS,
keeps at most2active fits including first, never chooses seed/fold by outcome.
Any nonclean worker stops new dispatch and waits already-owned fits to finish;
no killing unrelated processes, auto replacement or silent retry. ALL_NINE
PROCESSES_RETURNED is not criticqualification: independent matched heldout
aggregation over all folds/seeds and science gates must still be implemented
and pass before final refits/deployment. Do not repeat first21orvalid fits.

Joint maximum12x1320+3526=19366GPU seconds leaves20percent of8GPUh phase,
including potential final3refits but not authorizing them before qualification.
ActualGPU seconds remain authoritative. Existing deadlines/audiooff/science
stops unchanged; no QGF online benefit inferred from fitting or training loss.
