# Real-runtime A-B-A restoration gate V4

V4 is the single bounded repair for V3's post-checkpoint cache-digest failure.
V3 passed the frozen 792-node coverage gate and entered A0, then a cache value
created by the first audit action had no frozen graph path. The recorder raised
`KeyError` before it could save a branch trace. This is not an A-B-A numerical
comparison failure.

The repair changes only the diagnostic digest. Frozen graph objects keep their
original alias paths. Arrays, exact dictionaries, lists, tuples, callbacks and
ordinary Python cache objects created after checkpoint capture receive a
recursive content digest with traversal-local alias labels. Memory addresses
are never serialized. Object arrays, unknown native types, renderer handles,
modules, classes and unsupported dictionary keys still fail closed. Thirty-
seven CPU tests pass, including content mutation and address-independent cycle
tests.

The frozen train_0205 scene, 30 dummy waits, 100 archived prefix actions,
candidate-0 A actions, candidate-1 B actions, branch order, full restore state,
live dual-camera raster, exact comparisons and `1e-6` action threshold are
unchanged. No WAM or critic is loaded. V1, V2 and V3 evidence and all GPU costs
remain charged.

One allocated idle A800, 8CPU/45GB, inner 1200 seconds and Slurm hard 1300
seconds. There is no automatic retry. A scientific mismatch after restoration
is frozen without threshold relaxation.
