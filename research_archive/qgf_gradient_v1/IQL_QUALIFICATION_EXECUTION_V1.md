# Frozen IQL qualification execution plan before real fitting

Use only full FEATURE_CORPUS_AUDIT_PASS plus clean independentCPUstep. No
validation/formal data files. Dataset288/188S100F and featuredimension5641 are
frozen. Current fitted critic count remains0at registration. train_rl_fold.py
provides one worker; live WAM and collection sources stay unchanged.

OOF qualification:3bootstrapseeds202640101/102/103 x heldfold0/1/2 =9workers.
Each trains matched action/state-only/within-bank permutation/MC action models
using identical primary detached TDtargets,group bootstrap draws and batches,
fixed20000updates/final checkpoint only,Adam3e-4,batch128,width256,tau.005,
expectile.7,gamma1. Float32,noAMP,TF32false,4CPUthreads. Torch/random/NumPy seeds
use the registered bootstrap seed. Separate within-bank uniform identity stream
seed=bootstrapseed+10000+heldfold (full refit uses+10000), includes identity at1/4.
No seed/fold/checkpoint selection. All traces and failures included.

Only training-fold current-state rows fit FoldScaler. GroupEpisodeSampler uses
the same frozen group->episode->transition sampler and episode-count weights.
Known plannedL=min10remaining mask is Qinput; actualm/reward/terminal only
targets. Zero-transition episodes retained in288scientific metadata but never
receive synthetic action labels or silently disappear from denominator.

Final held-out predictions atupdate20000: all models against SAME actual
finite logged MCreturn, shared final primary TDtarget, and action-model response
to within-bank permutation. Save raw predictions and episode-equal errors,
fixed training-fold episode-equal prevalence reference, full model/SPLIT/scaler
hashes. Calibration computed from final saved predictions only with fixed bins;
not model selection. Main offline gate remains all3seeds actionMSE lower than
both learned controls, pooled pairedphysicalgroupbootstrap improvementsCI>0,
and permutation sensitivity. These are necessary screens,not same-state causal
value or online benefit. MCmodel is labelled ablation,not RL substitute.

After ALL9worker clean completion, independentOOF aggregation must cover exactly
one heldprediction per nonempty training episode per seed with no group leakage.
Only if full preregistered offline gate passes, do3additionalall-training refits
at same20000updates,seeds,width/controls and train-only scaler. This creates the
3-member final deployed ensemble; never deploy a favored OOFfold. Formal and
validation remain untouched. Final refits are conditional,not authorized early.

First worker is deterministically seed202640101/fold0. Its first200updates count
toward20000; only timing afterwarm50estimates p90 cost,never performance stopping.
Conservative budget forecasts12complete matched fits incl conditionalrefits;
if forecast exceeds8GPUh*80percent incl feature/failure costs,stop for resource
decision before launching rest. Perworkerhard1200sinner/22minouter; worst12x1320
+currentfeaturephase3526=19366GPU seconds,below23040usable. No unbounded retry.
Only FINAL_20000 used for evaluation. No early loss/heldout performance tuning.

Register actual dataset/corpusreport/sourceSHA and allocation before firstfit.
gpu22/job1598338two kernel-qualified idleA800 may run independent workers with
4CPU/20GB each,one per verified freeGPU; no WAM/EGLdependency. First cost-gated
worker before parallel release. Record real Slurm/PID/UUID/wall/cost and errors.
Current resource/backup/deadline/audiooffconstraints and all old science stops
remain. Worker report alone is not critic qualification or QGF efficacy.
