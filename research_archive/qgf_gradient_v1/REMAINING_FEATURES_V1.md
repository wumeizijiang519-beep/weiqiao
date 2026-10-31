# Fixed remaining286feature extraction and complete288index

Encoder338completed0:0/370s; actual current-only A-B-A maxerror0, inputs/RNG/
buffers unchanged, no actor gradient. Pilot339completed0:0/356s, first2blocks
71observations each,featuredimension5641. Real encoder p90 perframe0.04413425s.
Zero-GPU fixed14boundary I/O benchmark p90includinghash/read/hash0.12102731s.

Do not re-encode pilot142observations. Validate/copy their exact immutable
NPZbytes into new run/blocks; inherit receipts with source paths. Generate only
fixedtrain0002..0287,286episodes,12364current/next-observation frames. No robot
actions, no new labels or actor update. Same current-only WAM pooling/device
repair, remaining-time inputs and RNG/buffer/frozen-model checks.

Prelaunch register_remaining_features.py freezes dataset/encoder/pilot/source/
resource/IObenchmark SHA and exactstepcosts439+370+356=1165GPU seconds. Shared
feature/critic8GPUh leaves20percentreserve. Cumulative34710+1165=35875before
this run. Forecast=600load+1.5*N*(measuredencoderp90+sampleIOp90)+80prompt+
120publicationseconds,~3863s; sample/cache limitations explicit. Hard5400sinner/
5520sSlurm,1GPU/8CPU/45GB. Remain well below6.4phaseGPUh usable, retain failures.

New source/registration before dispatch; fresh ownedgpu1GPU0idle check. One run,
no automatic retries or partial-block overwrite. Every new episode receipt
immutable. FullINDEX only after exact288union,R+1finitefloat32dimension,rawblock
SHA,encoderhash and frozen-model checks. Output status extraction complete but
pending independent CPU audit; not critic training or online success.

After clean extraction, independently verify full288index/provenance/corpus
against admitted actual transition rewards/prefixes/observations and source SHA,
then freeze CPUcorpus and train-only normalizers/OOF plan. Do not train merely
because INDEXexists. Add all actualGPU costs, never double-count pilot copying.
