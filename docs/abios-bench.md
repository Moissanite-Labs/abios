# ABIOS benchmark

**Primary accounting** (used in break-even and verdict): total = setup (min, decode-sufficient) + messages.
Secondary: setup (full, committed lexicon + full schema). Tertiary: setup (cached†) = 10% × setup (min). Assumes one-time decoder prefix billed at 10% of min setup tokens (not API-measured).

Minimal setup is **decode-sufficient**: all used cmd/status/kind wire mappings and format tags for the transcript (plus all format tags when `adaptive` appears). Primary setup (min) counts POST ack line plus minimal decoder context (section 8.1).

REFS decode rules overhead (informative, `decode_rules.py` REFS_DECODE_RULES): **367** tokens (o200k_base). PR #36 abbrev was **102** tokens (incomplete alone).

## lifecycle_11 (11 messages)

| Format | setup (min) | messages | total (primary) | setup (full) | total (full setup) | setup (cached†) | total (cached†) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| compact JSON | 0 | 738 | 738 | 0 | 738 | 0.0 | 738.0 |
| pretty JSON | 0 | 938 | 938 | 0 | 938 | 0.0 | 938.0 |
| English (lossy summary) | 0 | 478 | 478 | 0 | 478 | 0.0 | 478.0 |
| English (lossless) | 0 | 686 | 686 | 0 | 686 | 0.0 | 686.0 |
| English (lossless, key=value one-line) | 0 | 691 | 691 | 0 | 691 | 0.0 | 691.0 |
| TOON (approx in-repo fallback) | 0 | 809 | 809 | 0 | 809 | 0.0 | 809.0 |
| Agora envelope (arXiv:2410.11905) | 48 | 979 | 1027 | 48 | 1027 | 4.8 | 983.8 |
| SYM-2P v1 | 0 | 2719 | 2719 | 0 | 2719 | 0.0 | 2719.0 |
| SYM-2P v2 session + handshake (PR #6) — External constants from synbios PR #6 dense pilot (not live-measured in this repo) | 213 | 1202 | 1415 | 213 | 1415 | 21.3 | 1223.3 |
| SYM-2P v2 dense raw (PR #6) — vs compact JSON 683 messages-only (pilot) | 0 | 3386 | 3386 | 0 | 3386 | 0.0 | 3386.0 |
| SYM-2P v1 (PR #6 pilot reference) — pilot transcript; live bench row below uses this repo codec | 0 | 2720 | 2720 | 0 | 2720 | 0.0 | 2720.0 |
| ABIOS delta | 555 | 290 | 845 | 891 | 1181 | 55.5 | 345.5 |
| ABIOS refs — closest prior art: Agora (arXiv:2410.11905) | 554 | 196 | 750 | 890 | 1086 | 55.4 | 251.4 |
| ABIOS positional | 555 | 196 | 751 | 890 | 1086 | 55.5 | 251.5 |
| ABIOS omit | 556 | 298 | 854 | 892 | 1190 | 55.6 | 353.6 |
| ABIOS combined | 554 | 290 | 844 | 890 | 1180 | 55.4 | 345.4 |
| ABIOS adaptive | 554 | 196 | 750 | 890 | 1086 | 55.4 | 251.4 |

### Cumulative crossover (primary accounting: POST + setup min + messages)

| Encoder | msgs before total beats compact JSON | msgs before total beats English (lossless) |
| --- | ---: | ---: |
| adaptive | never | never |
| combined | never | never |
| delta | never | never |
| omit | never | never |
| positional | never | never |
| refs | never | never |

## lifecycle_40 (40 messages)

| Format | setup (min) | messages | total (primary) | setup (full) | total (full setup) | setup (cached†) | total (cached†) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| compact JSON | 0 | 5570 | 5570 | 0 | 5570 | 0.0 | 5570.0 |
| pretty JSON | 0 | 6863 | 6863 | 0 | 6863 | 0.0 | 6863.0 |
| English (lossy summary) | 0 | 2283 | 2283 | 0 | 2283 | 0.0 | 2283.0 |
| English (lossless) | 0 | 5242 | 5242 | 0 | 5242 | 0.0 | 5242.0 |
| English (lossless, key=value one-line) | 0 | 5328 | 5328 | 0 | 5328 | 0.0 | 5328.0 |
| TOON (approx in-repo fallback) | 0 | 6051 | 6051 | 0 | 6051 | 0.0 | 6051.0 |
| Agora envelope (arXiv:2410.11905) | 48 | 6449 | 6497 | 48 | 6497 | 4.8 | 6453.8 |
| SYM-2P v1 | 0 | 12925 | 12925 | 0 | 12925 | 0.0 | 12925.0 |
| ABIOS delta | 558 | 2623 | 3181 | 890 | 3513 | 55.8 | 2678.8 |
| ABIOS refs — closest prior art: Agora (arXiv:2410.11905) | 557 | 1149 | 1706 | 889 | 2038 | 55.7 | 1204.7 |
| ABIOS positional | 563 | 1773 | 2336 | 894 | 2667 | 56.3 | 1829.3 |
| ABIOS omit | 558 | 2631 | 3189 | 890 | 3521 | 55.8 | 2686.8 |
| ABIOS combined | 559 | 1999 | 2558 | 891 | 2890 | 55.9 | 2054.9 |
| ABIOS adaptive | 557 | 1149 | 1706 | 889 | 2038 | 55.7 | 1204.7 |

### Cumulative crossover (primary accounting: POST + setup min + messages)

| Encoder | msgs before total beats compact JSON | msgs before total beats English (lossless) |
| --- | ---: | ---: |
| adaptive | 12 | 12 |
| combined | 13 | 13 |
| delta | 13 | 14 |
| omit | 13 | 14 |
| positional | 12 | 12 |
| refs | 12 | 12 |

## lifecycle_200 (200 messages)

| Format | setup (min) | messages | total (primary) | setup (full) | total (full setup) | setup (cached†) | total (cached†) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| compact JSON | 0 | 28498 | 28498 | 0 | 28498 | 0.0 | 28498.0 |
| pretty JSON | 0 | 34855 | 34855 | 0 | 34855 | 0.0 | 34855.0 |
| English (lossy summary) | 0 | 11439 | 11439 | 0 | 11439 | 0.0 | 11439.0 |
| English (lossless) | 0 | 26754 | 26754 | 0 | 26754 | 0.0 | 26754.0 |
| English (lossless, key=value one-line) | 0 | 27180 | 27180 | 0 | 27180 | 0.0 | 27180.0 |
| TOON (approx in-repo fallback) | 0 | 30799 | 30799 | 0 | 30799 | 0.0 | 30799.0 |
| Agora envelope (arXiv:2410.11905) | 48 | 32897 | 32945 | 48 | 32945 | 4.8 | 32901.8 |
| SYM-2P v1 | 0 | 65273 | 65273 | 0 | 65273 | 0.0 | 65273.0 |
| ABIOS delta | 608 | 13659 | 14267 | 890 | 14549 | 60.8 | 13719.8 |
| ABIOS refs — closest prior art: Agora (arXiv:2410.11905) | 609 | 5589 | 6198 | 891 | 6480 | 60.9 | 5649.9 |
| ABIOS positional | 610 | 9409 | 10019 | 891 | 10300 | 61.0 | 9470.0 |
| ABIOS omit | 611 | 13699 | 14310 | 893 | 14592 | 61.1 | 13760.1 |
| ABIOS combined | 611 | 10039 | 10650 | 893 | 10932 | 61.1 | 10100.1 |
| ABIOS adaptive | 609 | 5589 | 6198 | 891 | 6480 | 60.9 | 5649.9 |

### Cumulative crossover (primary accounting: POST + setup min + messages)

| Encoder | msgs before total beats compact JSON | msgs before total beats English (lossless) |
| --- | ---: | ---: |
| adaptive | 12 | 12 |
| combined | 13 | 14 |
| delta | 13 | 14 |
| omit | 13 | 14 |
| positional | 12 | 13 |
| refs | 12 | 12 |

## lifecycle_11_random (11 messages)

| Format | setup (min) | messages | total (primary) | setup (full) | total (full setup) | setup (cached†) | total (cached†) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| compact JSON | 0 | 694 | 694 | 0 | 694 | 0.0 | 694.0 |
| pretty JSON | 0 | 894 | 894 | 0 | 894 | 0.0 | 894.0 |
| English (lossy summary) | 0 | 367 | 367 | 0 | 367 | 0.0 | 367.0 |
| English (lossless) | 0 | 652 | 652 | 0 | 652 | 0.0 | 652.0 |
| English (lossless, key=value one-line) | 0 | 647 | 647 | 0 | 647 | 0.0 | 647.0 |
| TOON (approx in-repo fallback) | 0 | 772 | 772 | 0 | 772 | 0.0 | 772.0 |
| Agora envelope (arXiv:2410.11905) | 48 | 935 | 983 | 48 | 983 | 4.8 | 939.8 |
| SYM-2P v1 | 0 | 2647 | 2647 | 0 | 2647 | 0.0 | 2647.0 |
| ABIOS delta | 533 | 290 | 823 | 869 | 1159 | 53.3 | 343.3 |
| ABIOS refs — closest prior art: Agora (arXiv:2410.11905) | 530 | 196 | 726 | 866 | 1062 | 53.0 | 249.0 |
| ABIOS positional | 536 | 196 | 732 | 871 | 1067 | 53.6 | 249.6 |
| ABIOS omit | 529 | 298 | 827 | 865 | 1163 | 52.9 | 350.9 |
| ABIOS combined | 529 | 290 | 819 | 865 | 1155 | 52.9 | 342.9 |
| ABIOS adaptive | 530 | 196 | 726 | 866 | 1062 | 53.0 | 249.0 |

### Cumulative crossover (primary accounting: POST + setup min + messages)

| Encoder | msgs before total beats compact JSON | msgs before total beats English (lossless) |
| --- | ---: | ---: |
| adaptive | never | never |
| combined | never | never |
| delta | never | never |
| omit | never | never |
| positional | never | never |
| refs | never | never |

## lifecycle_40_random (40 messages)

| Format | setup (min) | messages | total (primary) | setup (full) | total (full setup) | setup (cached†) | total (cached†) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| compact JSON | 0 | 5879 | 5879 | 0 | 5879 | 0.0 | 5879.0 |
| pretty JSON | 0 | 7172 | 7172 | 0 | 7172 | 0.0 | 7172.0 |
| English (lossy summary) | 0 | 1819 | 1819 | 0 | 1819 | 0.0 | 1819.0 |
| English (lossless) | 0 | 5616 | 5616 | 0 | 5616 | 0.0 | 5616.0 |
| English (lossless, key=value one-line) | 0 | 5637 | 5637 | 0 | 5637 | 0.0 | 5637.0 |
| TOON (approx in-repo fallback) | 0 | 6395 | 6395 | 0 | 6395 | 0.0 | 6395.0 |
| Agora envelope (arXiv:2410.11905) | 48 | 6758 | 6806 | 48 | 6806 | 4.8 | 6762.8 |
| SYM-2P v1 | 0 | 13087 | 13087 | 0 | 13087 | 0.0 | 13087.0 |
| ABIOS delta | 537 | 2623 | 3160 | 869 | 3492 | 53.7 | 2676.7 |
| ABIOS refs — closest prior art: Agora (arXiv:2410.11905) | 536 | 1149 | 1685 | 868 | 2017 | 53.6 | 1202.6 |
| ABIOS positional | 538 | 1773 | 2311 | 869 | 2642 | 53.8 | 1826.8 |
| ABIOS omit | 534 | 2631 | 3165 | 866 | 3497 | 53.4 | 2684.4 |
| ABIOS combined | 538 | 1999 | 2537 | 870 | 2869 | 53.8 | 2052.8 |
| ABIOS adaptive | 536 | 1149 | 1685 | 868 | 2017 | 53.6 | 1202.6 |

### Cumulative crossover (primary accounting: POST + setup min + messages)

| Encoder | msgs before total beats compact JSON | msgs before total beats English (lossless) |
| --- | ---: | ---: |
| adaptive | 12 | 12 |
| combined | 13 | 13 |
| delta | 13 | 13 |
| omit | 13 | 13 |
| positional | 12 | 12 |
| refs | 12 | 12 |

## lifecycle_200_random (200 messages)

| Format | setup (min) | messages | total (primary) | setup (full) | total (full setup) | setup (cached†) | total (cached†) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| compact JSON | 0 | 30043 | 30043 | 0 | 30043 | 0.0 | 30043.0 |
| pretty JSON | 0 | 36400 | 36400 | 0 | 36400 | 0.0 | 36400.0 |
| English (lossy summary) | 0 | 9119 | 9119 | 0 | 9119 | 0.0 | 9119.0 |
| English (lossless) | 0 | 28624 | 28624 | 0 | 28624 | 0.0 | 28624.0 |
| English (lossless, key=value one-line) | 0 | 28725 | 28725 | 0 | 28725 | 0.0 | 28725.0 |
| TOON (approx in-repo fallback) | 0 | 32519 | 32519 | 0 | 32519 | 0.0 | 32519.0 |
| Agora envelope (arXiv:2410.11905) | 48 | 34442 | 34490 | 48 | 34490 | 4.8 | 34446.8 |
| SYM-2P v1 | 0 | 66083 | 66083 | 0 | 66083 | 0.0 | 66083.0 |
| ABIOS delta | 587 | 13659 | 14246 | 869 | 14528 | 58.7 | 13717.7 |
| ABIOS refs — closest prior art: Agora (arXiv:2410.11905) | 587 | 5589 | 6176 | 869 | 6458 | 58.7 | 5647.7 |
| ABIOS positional | 588 | 9409 | 9997 | 869 | 10278 | 58.8 | 9467.8 |
| ABIOS omit | 585 | 13699 | 14284 | 867 | 14566 | 58.5 | 13757.5 |
| ABIOS combined | 585 | 10039 | 10624 | 867 | 10906 | 58.5 | 10097.5 |
| ABIOS adaptive | 587 | 5589 | 6176 | 869 | 6458 | 58.7 | 5647.7 |

### Cumulative crossover (primary accounting: POST + setup min + messages)

| Encoder | msgs before total beats compact JSON | msgs before total beats English (lossless) |
| --- | ---: | ---: |
| adaptive | 12 | 12 |
| combined | 13 | 14 |
| delta | 13 | 14 |
| omit | 13 | 14 |
| positional | 12 | 13 |
| refs | 12 | 12 |

## Verdict (primary accounting, o200k_base)

On lifecycle_11 (fixture hex), ABIOS **refs** total **750** vs compact JSON **738** and lossless English **686** (primary = POST + minimal setup + messages). Same task with **seeded random hex ids** (see `lifecycle_*_random`): refs **726** vs JSON **694**. **Adaptive** total **750**. TOON fallback row **809** (approximation). lifecycle_40/200 repeat many messages verbatim, which inflates refs savings; see transcript notes. SYM-2P v2 rows are external PR #6 constants, not live bench output.
