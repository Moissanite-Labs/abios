# ABIOS benchmark

**Primary accounting** (used in break-even and verdict): total = setup (min, decode-sufficient) + messages.
Secondary: setup (full, committed lexicon + full schema). Tertiary: setup (cached†) = 10% × setup (min). Assumes one-time decoder prefix billed at 10% of min setup tokens (not API-measured).

Minimal setup is **decode-sufficient**: all used cmd/status/kind wire mappings and format tags for the transcript (plus all format tags when `adaptive` appears). Primary setup (min) counts POST ack line plus minimal decoder context (section 8.1).

REFS decode rules overhead (informative, `decode_rules.py` REFS_DECODE_RULES): **374** tokens (o200k_base). PR #36 abbrev was **102** tokens (incomplete alone).

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
| ABIOS delta | 571 | 290 | 861 | 907 | 1197 | 57.1 | 347.1 |
| ABIOS refs — closest prior art: Agora (arXiv:2410.11905) | 569 | 196 | 765 | 905 | 1101 | 56.9 | 252.9 |
| ABIOS positional | 569 | 196 | 765 | 904 | 1100 | 56.9 | 252.9 |
| ABIOS omit | 571 | 298 | 869 | 907 | 1205 | 57.1 | 355.1 |
| ABIOS combined | 570 | 290 | 860 | 906 | 1196 | 57.0 | 347.0 |
| ABIOS adaptive | 569 | 196 | 765 | 905 | 1101 | 56.9 | 252.9 |

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
| ABIOS delta | 574 | 2623 | 3197 | 906 | 3529 | 57.4 | 2680.4 |
| ABIOS refs — closest prior art: Agora (arXiv:2410.11905) | 572 | 1149 | 1721 | 904 | 2053 | 57.2 | 1206.2 |
| ABIOS positional | 577 | 1773 | 2350 | 908 | 2681 | 57.7 | 1830.7 |
| ABIOS omit | 575 | 2631 | 3206 | 907 | 3538 | 57.5 | 2688.5 |
| ABIOS combined | 575 | 1999 | 2574 | 907 | 2906 | 57.5 | 2056.5 |
| ABIOS adaptive | 572 | 1149 | 1721 | 904 | 2053 | 57.2 | 1206.2 |

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
| ABIOS delta | 624 | 13659 | 14283 | 906 | 14565 | 62.4 | 13721.4 |
| ABIOS refs — closest prior art: Agora (arXiv:2410.11905) | 623 | 5589 | 6212 | 905 | 6494 | 62.3 | 5651.3 |
| ABIOS positional | 625 | 9409 | 10034 | 906 | 10315 | 62.5 | 9471.5 |
| ABIOS omit | 623 | 13699 | 14322 | 905 | 14604 | 62.3 | 13761.3 |
| ABIOS combined | 623 | 10039 | 10662 | 905 | 10944 | 62.3 | 10101.3 |
| ABIOS adaptive | 623 | 5589 | 6212 | 905 | 6494 | 62.3 | 5651.3 |

### Cumulative crossover (primary accounting: POST + setup min + messages)

| Encoder | msgs before total beats compact JSON | msgs before total beats English (lossless) |
| --- | ---: | ---: |
| adaptive | 12 | 13 |
| combined | 13 | 14 |
| delta | 13 | 14 |
| omit | 14 | 14 |
| positional | 12 | 13 |
| refs | 12 | 13 |

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
| ABIOS delta | 546 | 290 | 836 | 882 | 1172 | 54.6 | 344.6 |
| ABIOS refs — closest prior art: Agora (arXiv:2410.11905) | 547 | 196 | 743 | 883 | 1079 | 54.7 | 250.7 |
| ABIOS positional | 547 | 196 | 743 | 882 | 1078 | 54.7 | 250.7 |
| ABIOS omit | 546 | 298 | 844 | 882 | 1180 | 54.6 | 352.6 |
| ABIOS combined | 546 | 290 | 836 | 882 | 1172 | 54.6 | 344.6 |
| ABIOS adaptive | 547 | 196 | 743 | 883 | 1079 | 54.7 | 250.7 |

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
| ABIOS delta | 550 | 2623 | 3173 | 882 | 3505 | 55.0 | 2678.0 |
| ABIOS refs — closest prior art: Agora (arXiv:2410.11905) | 550 | 1149 | 1699 | 882 | 2031 | 55.0 | 1204.0 |
| ABIOS positional | 554 | 1773 | 2327 | 885 | 2658 | 55.4 | 1828.4 |
| ABIOS omit | 555 | 2631 | 3186 | 887 | 3518 | 55.5 | 2686.5 |
| ABIOS combined | 550 | 1999 | 2549 | 882 | 2881 | 55.0 | 2054.0 |
| ABIOS adaptive | 550 | 1149 | 1699 | 882 | 2031 | 55.0 | 1204.0 |

### Cumulative crossover (primary accounting: POST + setup min + messages)

| Encoder | msgs before total beats compact JSON | msgs before total beats English (lossless) |
| --- | ---: | ---: |
| adaptive | 12 | 12 |
| combined | 13 | 13 |
| delta | 13 | 13 |
| omit | 13 | 14 |
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
| ABIOS delta | 602 | 13659 | 14261 | 884 | 14543 | 60.2 | 13719.2 |
| ABIOS refs — closest prior art: Agora (arXiv:2410.11905) | 600 | 5589 | 6189 | 882 | 6471 | 60.0 | 5649.0 |
| ABIOS positional | 603 | 9409 | 10012 | 884 | 10293 | 60.3 | 9469.3 |
| ABIOS omit | 599 | 13699 | 14298 | 881 | 14580 | 59.9 | 13758.9 |
| ABIOS combined | 602 | 10039 | 10641 | 884 | 10923 | 60.2 | 10099.2 |
| ABIOS adaptive | 600 | 5589 | 6189 | 882 | 6471 | 60.0 | 5649.0 |

### Cumulative crossover (primary accounting: POST + setup min + messages)

| Encoder | msgs before total beats compact JSON | msgs before total beats English (lossless) |
| --- | ---: | ---: |
| adaptive | 12 | 13 |
| combined | 13 | 14 |
| delta | 13 | 14 |
| omit | 13 | 14 |
| positional | 12 | 13 |
| refs | 12 | 13 |

## Verdict (primary accounting, o200k_base)

On lifecycle_11 (fixture hex), ABIOS **refs** total **765** vs compact JSON **738** and lossless English **686** (primary = POST + minimal setup + messages). Same task with **seeded random hex ids** (see `lifecycle_*_random`): refs **743** vs JSON **694**. **Adaptive** total **765**. TOON fallback row **809** (approximation). lifecycle_40/200 repeat many messages verbatim, which inflates refs savings; see transcript notes. SYM-2P v2 rows are external PR #6 constants, not live bench output.
