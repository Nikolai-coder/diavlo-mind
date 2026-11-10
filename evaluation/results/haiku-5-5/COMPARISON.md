# Comparison: A = pilot-haiku [baseline], B = pilot-haiku [diavlo-mind]

24 paired run(s) (same task and trial).

| | A | B |
|---|---|---|
| Task success rate | 96% | 100% |
| Overclaims | 1 | 0 |
| Output tokens (sum) | 275362 | 345271 (1.25x) |
| Cost (sum, USD) | 0.32 | 0.411 (1.28x) |

Requirement coverage: B higher in 1 pair(s), lower in 0, equal in 23.
Sign test: p = 1.000 on 1 differing pair(s). Too few pairs to conclude anything; run more tasks or more trials.

Task success: B solved and A did not in 1 pair(s); A solved and B did not in 0.
Sign test: p = 1.000 on 1 differing pair(s). Too few pairs to conclude anything; run more tasks or more trials.

| Task | Trial | Success A → B | Checks A → B | Coverage A → B | Overclaim A / B | Output tokens A → B | Cost A → B |
|---|---|---|---|---|---|---|---|
| architecture-notifications | 1 | yes → yes | 15/15 → 15/15 | 100% → 100% | no / no | 24688 → 29866 | 0.02123 → 0.03227 |
| architecture-notifications | 2 | yes → yes | 15/15 → 15/15 | 100% → 100% | no / no | 24898 → 20355 | 0.02055 → 0.0195 |
| architecture-notifications | 3 | yes → yes | 15/15 → 15/15 | 100% → 100% | no / no | 19277 → 23090 | 0.01717 → 0.02074 |
| creative-short-script | 1 | yes → yes | 12/12 → 12/12 | 100% → 100% | no / no | 5320 → 7901 | 0.00636 → 0.0153 |
| creative-short-script | 2 | yes → yes | 12/12 → 12/12 | 100% → 100% | no / no | 5952 → 5484 | 0.00715 → 0.0065 |
| creative-short-script | 3 | yes → yes | 12/12 → 12/12 | 100% → 100% | no / no | 5749 → 9817 | 0.00695 → 0.01012 |
| debugging-inventory | 1 | yes → yes | 15/15 → 15/15 | 100% → 100% | no / no | 6515 → 7131 | 0.00983 → 0.01057 |
| debugging-inventory | 2 | yes → yes | 15/15 → 15/15 | 100% → 100% | no / no | 5754 → 6989 | 0.00859 → 0.00982 |
| debugging-inventory | 3 | yes → yes | 15/15 → 15/15 | 100% → 100% | no / no | 5815 → 10093 | 0.00888 → 0.01541 |
| longterm-notes-cli | 1 | yes → yes | 10/10 → 10/10 | 100% → 100% | no / no | 19730 → 25603 | 0.02539 → 0.03357 |
| longterm-notes-cli | 2 | yes → yes | 10/10 → 10/10 | 100% → 100% | no / no | 15612 → 21627 | 0.02041 → 0.02754 |
| longterm-notes-cli | 3 | no → yes | 9/10 → 10/10 | 88% → 100% | yes / no | 16546 → 24551 | 0.02273 → 0.03454 |
| multiagent-briefs | 1 | yes → yes | 8/8 → 8/8 | 100% → 100% | no / no | 19274 → 25291 | 0.02358 → 0.02974 |
| multiagent-briefs | 2 | yes → yes | 8/8 → 8/8 | 100% → 100% | no / no | 18103 → 25129 | 0.02249 → 0.0286 |
| multiagent-briefs | 3 | yes → yes | 8/8 → 8/8 | 100% → 100% | no / no | 16741 → 21026 | 0.02115 → 0.02406 |
| programming-duration | 1 | yes → yes | 19/19 → 19/19 | 100% → 100% | no / no | 7904 → 8918 | 0.0087 → 0.00966 |
| programming-duration | 2 | yes → yes | 19/19 → 19/19 | 100% → 100% | no / no | 6219 → 9063 | 0.00743 → 0.00949 |
| programming-duration | 3 | yes → yes | 19/19 → 19/19 | 100% → 100% | no / no | 8353 → 12264 | 0.00791 → 0.01277 |
| recovery-migration | 1 | yes → yes | 13/13 → 13/13 | 100% → 100% | no / no | 8026 → 14770 | 0.00932 → 0.01566 |
| recovery-migration | 2 | yes → yes | 13/13 → 13/13 | 100% → 100% | no / no | 11232 → 15807 | 0.01151 → 0.01473 |
| recovery-migration | 3 | yes → yes | 13/13 → 13/13 | 100% → 100% | no / no | 13600 → 9762 | 0.01487 → 0.01125 |
| research-kestrel | 1 | yes → yes | 29/29 → 29/29 | 100% → 100% | no / no | 3659 → 4186 | 0.00628 → 0.00683 |
| research-kestrel | 2 | yes → yes | 29/29 → 29/29 | 100% → 100% | no / no | 2981 → 3411 | 0.00566 → 0.00612 |
| research-kestrel | 3 | yes → yes | 29/29 → 29/29 | 100% → 100% | no / no | 3414 → 3137 | 0.00595 → 0.00594 |
