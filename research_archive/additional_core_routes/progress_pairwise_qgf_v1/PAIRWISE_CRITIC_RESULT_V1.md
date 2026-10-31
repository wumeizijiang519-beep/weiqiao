# Progress-Pairwise Critic V1 Result

Status: `NO_STABLE_PROGRESS_PAIRWISE_CRITIC`.

All 12 fixed workers completed. The action-aware model consistently exceeded
the state-only tie baseline, and its score changed under action replacement,
but it did not consistently outperform the within-group permutation control.
Physical-group bootstrap intervals for both required control differences also
included zero. The preregistered release gate therefore failed.

Qualification REPORT SHA:
`cedc63d8744ab298e211b55ce962f1684206c759536526bd52aa7aaee6573130`.

This is evidence that the current 14-group continuous-progress dataset and
critic specification do not support a stable deployable action ranking model.
It is not an online QGF result and is not a universal impossibility claim.
Online validation remains unrun.
