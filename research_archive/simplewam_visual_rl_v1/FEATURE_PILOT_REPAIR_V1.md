# Feature Pilot Infrastructure Repair V1

Step `1593640.429` completed frozen Simple-WAM construction and wrote
`FEATURES.npz`, then failed while hashing the prompt context because NumPy does
not support PyTorch `bfloat16`. No robot action or critic update occurred.

The single repair converts only the detached prompt-context hash input to
canonical float32. It does not change the observation, model, layer 29,
spatial stride 4, camera order, hidden features, positions, seed, or gate. The
failed directory and 249-second allocation remain preserved. Retry1 writes a
new directory and is the only automatic retry for this pilot.
