# Comparison: A = pilot-haiku45 [baseline], B = pilot-haiku45 [diavlo-mind]

24 paired run(s) (same task and trial).

| | A | B |
|---|---|---|
| Task success rate | 58% | 75% |
| Overclaims | 10 | 6 |
| Output tokens (sum) | 348784 | 323000 (0.93x) |
| Cost (sum, USD) | 5.47 | 5.227 (0.96x) |

Requirement coverage: B higher in 6 pair(s), lower in 3, equal in 15.
Sign test (exact, two-sided): p = 0.508 on 9 differing pairs; a difference this large is expected by chance alone often enough that it proves nothing.

Task success: B solved and A did not in 5 pair(s); A solved and B did not in 1.
Sign test (exact, two-sided): p = 0.219 on 6 differing pairs; a difference this large is expected by chance alone often enough that it proves nothing.

| Task | Trial | Success A → B | Checks A → B | Coverage A → B | Overclaim A / B | Output tokens A → B | Cost A → B |
|---|---|---|---|---|---|---|---|
| architecture-notifications | 1 | no → no | 13/15 → 13/15 | 78% → 78% | yes / yes | 32794 → 13370 | 0.47078 → 0.20432 |
| architecture-notifications | 2 | no → yes | 14/15 → 15/15 | 89% → 100% | yes / no | 21514 → 17626 | 0.25542 → 0.17749 |
| architecture-notifications | 3 | no → no | 14/15 → 12/15 | 89% → 67% | yes / yes | 19932 → 15407 | 0.20859 → 0.16955 |
| creative-short-script | 1 | yes → yes | 12/12 → 12/12 | 100% → 100% | no / no | 14645 → 9717 | 0.18748 → 0.15851 |
| creative-short-script | 2 | yes → yes | 12/12 → 12/12 | 100% → 100% | no / no | 13031 → 11590 | 0.11573 → 0.10632 |
| creative-short-script | 3 | yes → yes | 12/12 → 12/12 | 100% → 100% | no / no | 7550 → 9138 | 0.07694 → 0.09117 |
| debugging-inventory | 1 | no → yes | 14/15 → 15/15 | 89% → 100% | yes / no | 7353 → 7341 | 0.18969 → 0.18331 |
| debugging-inventory | 2 | no → yes | 13/15 → 15/15 | 78% → 100% | yes / no | 7457 → 7288 | 0.19683 → 0.17417 |
| debugging-inventory | 3 | yes → yes | 15/15 → 15/15 | 100% → 100% | no / no | 6846 → 6208 | 0.1731 → 0.15945 |
| longterm-notes-cli | 1 | no → no | 9/10 → 8/10 | 88% → 75% | yes / yes | 33474 → 26774 | 0.59161 → 0.61909 |
| longterm-notes-cli | 2 | no → no | 8/10 → 8/10 | 75% → 75% | yes / yes | 23318 → 25956 | 0.53607 → 0.58733 |
| longterm-notes-cli | 3 | no → no | 8/10 → 9/10 | 75% → 88% | yes / yes | 25425 → 30930 | 0.50986 → 0.55503 |
| multiagent-briefs | 1 | yes → no | 8/8 → 7/8 | 100% → 83% | no / yes | 15768 → 12442 | 0.23788 → 0.21548 |
| multiagent-briefs | 2 | yes → yes | 8/8 → 8/8 | 100% → 100% | no / no | 12141 → 12189 | 0.17243 → 0.15968 |
| multiagent-briefs | 3 | yes → yes | 8/8 → 8/8 | 100% → 100% | no / no | 15950 → 15394 | 0.22882 → 0.23288 |
| programming-duration | 1 | yes → yes | 19/19 → 19/19 | 100% → 100% | no / no | 14042 → 14568 | 0.17365 → 0.16613 |
| programming-duration | 2 | yes → yes | 19/19 → 19/19 | 100% → 100% | no / no | 13603 → 18985 | 0.15635 → 0.18406 |
| programming-duration | 3 | yes → yes | 19/19 → 19/19 | 100% → 100% | no / no | 13987 → 16364 | 0.13237 → 0.15919 |
| recovery-migration | 1 | no → yes | 12/13 → 13/13 | 90% → 100% | yes / no | 13066 → 17214 | 0.25329 → 0.29343 |
| recovery-migration | 2 | no → yes | 11/13 → 13/13 | 80% → 100% | yes / no | 15803 → 9030 | 0.22355 → 0.18086 |
| recovery-migration | 3 | yes → yes | 13/13 → 13/13 | 100% → 100% | no / no | 9596 → 12939 | 0.18115 → 0.2032 |
| research-kestrel | 1 | yes → yes | 29/29 → 29/29 | 100% → 100% | no / no | 4059 → 4335 | 0.06505 → 0.0695 |
| research-kestrel | 2 | yes → yes | 29/29 → 29/29 | 100% → 100% | no / no | 3926 → 3936 | 0.0689 → 0.07886 |
| research-kestrel | 3 | yes → yes | 29/29 → 29/29 | 100% → 100% | no / no | 3504 → 4259 | 0.06487 → 0.09802 |
