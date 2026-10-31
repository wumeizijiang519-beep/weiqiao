# Candidate Bank Contract Clarification V1

The initial protocol said native candidates 0--3 came from the "same frozen WAM
call." The deployed Simple-WAM interface returns one action chunk for one seed;
it has no batched-seed call. Before any pilot execution, this wording is
clarified to mean four calls from the same frozen boundary observation and
policy memory, using seeds `10000`, `11000`, `12000`, and `13000`, with complete
RNG and memory restoration between calls. This is the same native N4 contract
already audited in the frozen collector.

No candidate count, model, observation, seed, denoising schedule, support basis,
branch outcome, compute comparison, or admission threshold changes. Structured
candidates remain deterministic transformations of native candidate 0 and do
not require additional WAM calls. The original protocol remains preserved; this
pre-execution clarification is part of the pilot registration.
