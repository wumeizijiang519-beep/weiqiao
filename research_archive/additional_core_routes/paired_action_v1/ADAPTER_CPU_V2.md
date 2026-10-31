# Explicit adapter CPU gate V2

Zero-GPU, zero robot action test after runtime inventory352. It exercises all
local fail-closed tests plus synthetic MuJoCo integration state and exact static
MjModel MJB hashing. Renderer is tested with a fake rebuild/raster adapter only;
real EGL raster restoration remains untested. Passing this gate is necessary but
not sufficient for dynamic robot restoration.

Run once under allocated zero-GPU CPU resources,2CPU/4GB/hard5minutes. Freeze
source hashes and report. No WAM, benchmark environment or training data outcome.
