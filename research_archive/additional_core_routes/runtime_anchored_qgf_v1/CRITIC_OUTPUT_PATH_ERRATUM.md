# Critic Output Path Erratum

All nine fixed workers completed cleanly, but the registration builder emitted
a relative `run_directory`. Because workers started from the account home, the
30 MiB result tree was written under `/public/home/wangsenbao221` instead of
the registered project storage policy. No model input, update, seed, fold,
control, output byte, or result is changed. The complete tree is copied (not
moved or deleted) to the project and accepted only after a sorted per-file SHA
manifest matches. No worker is retrained.
