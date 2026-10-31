# Proposed Official Native Gripper Contract V2

Status: PROPOSED_NOT_AUTHORIZED_NOT_EXECUTED. V1 collection stays stopped.
This is a reviewable amendment,not a retrospective V1 pass or method result.
The exact zero-action replay report must be examined before deciding.

## Evidence to Verify

The frozen official evaluator computes dataset gripper back to native via
inversion of2*g-1,and applies np.sign when binarize_gripper=true. Thus an exact
datasetg=0.5 produces native0,while the V1 audit accepts only{-1,+1}. Installed
official robosuite PandaGripper.format_action updates current_action by
speed*np.sign(action); an input0leaves its current target unchanged. This is
source evidence of a neutral command,not permission to alter the frozen gate.
The original failed bank was not saved by the exception path; cross-process
replay of exact observation/RNG is diagnostic reproduction,not recovered data.

## Proposed Changes for a Separate Version

1. Keep the official model,checkpoint,all action computation,seed streams,
   simulator,task,success,remaining-time rules and full fixed288cohort exactly
   as registered. Never round0to an endpoint or inject an action perturbation.
2. Replace only the mistaken strict endpoint-only gripper expectation by exact
   agreement with the unchanged official postprocessor,allowing native-1,0,+1.
   All bank-shape/finite/unique/diversity/candidate0/selected-repeat/commit/RNG
   and observation/video gates remain; no arbitrary intermediate value passes.
3. Inverse-map actual native gripper to dataset(1-native)/2,so native0maps to
   dataset0.5 before the same affine normalizer. Gradients still mask this
   discrete coordinate. Record zero locations/selected-vs-unselected and prefix
   vs suffix,and verify the raw sampler/native/canonical affine roundtrip.
4. Persist raw/native candidate proposals BEFORE any contract check,including
   a failing inverse mapping. This preserves future failure evidence. Do not
   pretend the old original missing bank has been recovered.
5. Before further policy execution,run a preregistered zero-action V2 contract
   audit on retained observations including the failure point. Preserve its
   report,arrays,SHA,exact process status and all costs. Stop on any other
   scientific failure; do not extend the tolerance or change seeds.

## Data Preservation and Conditional Continuation

Four integrity episodes plus26completed shard episodes remain on disk. Only
independently valid completed episodes may be reused,once,under the explicitly
new dataset-version contract. Do not call V1 successful or rerun those episodes.
The incomplete train_0030has210real steps and no terminal outcome. It cannot be
counted as a policy failure,success or completed training entry.

Continuation of that partial episode requires exact reconstruction from its
frozen initial state by replaying its recorded actual actions and saved caller
RNG,checking all retained simulator states,observations and controller history
before the next real policy decision. This is simulator-state reconstruction,
not an extra accepted trajectory. A raw MuJoCo flattened state alone does not
prove controller-memory restoration. If exact reconstruction fails,stop and
report; no silent reinitialization,replacement scene or invented outcome.

Only after those gates,freeze a V2 remaining-entry dispatcher within the
unchanged24GPUh cap and prescribed reserve,including failed316and diagnostic
costs. Keep the final12S12F/8physical-groups-per-class/OOFcoverage thresholds and
critic/online gates unchanged. No outcome-driven expansion or task screening.

Approval of this proposal would authorize preparation/validation of these exact
changes and conditional continuation; it would not guarantee that reconstruction,
data qualification,RL evidence or online improvement succeeds.
