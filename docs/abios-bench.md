# ABIOS benchmark

**Primary accounting** (used in break-even and verdict): total = setup (min, decode-sufficient) + messages.
Secondary: setup (full, committed lexicon + full schema). Tertiary: setup (cached†) = 10% × setup (min). Assumes one-time decoder prefix billed at 10% of min setup tokens (not API-measured).

Minimal setup is **decode-sufficient**: all used cmd/status/kind wire mappings and format tags for the transcript (plus all format tags when `adaptive` appears). Primary setup (min) counts POST ack line plus minimal decoder context (section 8.1).

REFS decode rules overhead (informative, `decode_rules.py`): **102** tokens (o200k_base).

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
| ABIOS delta | 607 | 290 | 897 | 893 | 1183 | 60.7 | 350.7 |
| ABIOS refs — closest prior art: Agora (arXiv:2410.11905) | 604 | 185 | 789 | 890 | 1075 | 60.4 | 245.4 |
| ABIOS positional | 606 | 196 | 802 | 891 | 1087 | 60.6 | 256.6 |
| ABIOS omit | 605 | 298 | 903 | 891 | 1189 | 60.5 | 358.5 |
| ABIOS combined | 607 | 290 | 897 | 893 | 1183 | 60.7 | 350.7 |
| ABIOS adaptive | 604 | 185 | 789 | 890 | 1075 | 60.4 | 245.4 |

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
| ABIOS delta | 608 | 2623 | 3231 | 890 | 3513 | 60.8 | 2683.8 |
| ABIOS refs — closest prior art: Agora (arXiv:2410.11905) | 609 | 1109 | 1718 | 891 | 2000 | 60.9 | 1169.9 |
| ABIOS positional | 610 | 1773 | 2383 | 891 | 2664 | 61.0 | 1834.0 |
| ABIOS omit | 611 | 2631 | 3242 | 893 | 3524 | 61.1 | 2692.1 |
| ABIOS combined | 611 | 1999 | 2610 | 893 | 2892 | 61.1 | 2060.1 |
| ABIOS adaptive | 609 | 1109 | 1718 | 891 | 2000 | 60.9 | 1169.9 |

### Cumulative crossover (primary accounting: POST + setup min + messages)

| Encoder | msgs before total beats compact JSON | msgs before total beats English (lossless) |
| --- | ---: | ---: |
| adaptive | 12 | 12 |
| combined | 13 | 14 |
| delta | 13 | 14 |
| omit | 13 | 14 |
| positional | 12 | 13 |
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
| ABIOS delta | 583 | 290 | 873 | 869 | 1159 | 58.3 | 348.3 |
| ABIOS refs — closest prior art: Agora (arXiv:2410.11905) | 583 | 185 | 768 | 869 | 1054 | 58.3 | 243.3 |
| ABIOS positional | 583 | 196 | 779 | 868 | 1064 | 58.3 | 254.3 |
| ABIOS omit | 580 | 298 | 878 | 866 | 1164 | 58.0 | 356.0 |
| ABIOS combined | 582 | 290 | 872 | 868 | 1158 | 58.2 | 348.2 |
| ABIOS adaptive | 583 | 185 | 768 | 869 | 1054 | 58.3 | 243.3 |

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
| ABIOS delta | 587 | 2623 | 3210 | 869 | 3492 | 58.7 | 2681.7 |
| ABIOS refs — closest prior art: Agora (arXiv:2410.11905) | 587 | 1109 | 1696 | 869 | 1978 | 58.7 | 1167.7 |
| ABIOS positional | 588 | 1773 | 2361 | 869 | 2642 | 58.8 | 1831.8 |
| ABIOS omit | 585 | 2631 | 3216 | 867 | 3498 | 58.5 | 2689.5 |
| ABIOS combined | 585 | 1999 | 2584 | 867 | 2866 | 58.5 | 2057.5 |
| ABIOS adaptive | 587 | 1109 | 1696 | 869 | 1978 | 58.7 | 1167.7 |

### Cumulative crossover (primary accounting: POST + setup min + messages)

| Encoder | msgs before total beats compact JSON | msgs before total beats English (lossless) |
| --- | ---: | ---: |
| adaptive | 12 | 12 |
| combined | 13 | 14 |
| delta | 13 | 14 |
| omit | 13 | 14 |
| positional | 12 | 13 |
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

On lifecycle_11 (fixture hex), ABIOS **refs** total **789** vs compact JSON **738** and lossless English **686** (primary = POST + minimal setup + messages). Same task with **seeded random hex ids** (see `lifecycle_*_random`): refs **768** vs JSON **694**. **Adaptive** total **789**. TOON fallback row **809** (approximation). lifecycle_40/200 repeat many messages verbatim, which inflates refs savings; see transcript notes. SYM-2P v2 rows are external PR #6 constants, not live bench output.
