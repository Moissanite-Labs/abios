# ABIOS benchmark

**Primary accounting** (used in break-even and verdict): total = setup (min, decode-sufficient) + messages.
Secondary: setup (full, committed lexicon + full schema). Tertiary: setup (cached†) = 10% × setup (min). Assumes one-time decoder prefix billed at 10% of min setup tokens (not API-measured).

Minimal setup is **decode-sufficient**: all used cmd/status/kind wire mappings and format tags for the transcript (plus all format tags when `adaptive` appears). Primary setup (min) counts POST ack line plus minimal decoder context (section 8.1).

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
| ABIOS delta | 525 | 345 | 870 | 799 | 1144 | 52.5 | 397.5 |
| ABIOS refs — closest prior art: Agora (arXiv:2410.11905) | 525 | 236 | 761 | 799 | 1035 | 52.5 | 288.5 |
| ABIOS positional | 525 | 251 | 776 | 798 | 1049 | 52.5 | 303.5 |
| ABIOS omit | 523 | 353 | 876 | 797 | 1150 | 52.3 | 405.3 |
| ABIOS combined | 524 | 330 | 854 | 798 | 1128 | 52.4 | 382.4 |
| ABIOS adaptive | 525 | 236 | 761 | 799 | 1035 | 52.5 | 288.5 |

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
| ABIOS delta | 531 | 3350 | 3881 | 801 | 4151 | 53.1 | 3403.1 |
| ABIOS refs — closest prior art: Agora (arXiv:2410.11905) | 527 | 1456 | 1983 | 797 | 2253 | 52.7 | 1508.7 |
| ABIOS positional | 527 | 2500 | 3027 | 796 | 3296 | 52.7 | 2552.7 |
| ABIOS omit | 530 | 3358 | 3888 | 800 | 4158 | 53.0 | 3411.0 |
| ABIOS combined | 529 | 2306 | 2835 | 799 | 3105 | 52.9 | 2358.9 |
| ABIOS adaptive | 527 | 1456 | 1983 | 797 | 2253 | 52.7 | 1508.7 |

### Cumulative crossover (primary accounting: POST + setup min + messages)

| Encoder | msgs before total beats compact JSON | msgs before total beats English (lossless) |
| --- | ---: | ---: |
| adaptive | 12 | 12 |
| combined | 13 | 14 |
| delta | 14 | 15 |
| omit | 14 | 15 |
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
| ABIOS delta | 531 | 17294 | 17825 | 801 | 18095 | 53.1 | 17347.1 |
| ABIOS refs — closest prior art: Agora (arXiv:2410.11905) | 527 | 7264 | 7791 | 797 | 8061 | 52.7 | 7316.7 |
| ABIOS positional | 527 | 13044 | 13571 | 796 | 13840 | 52.7 | 13096.7 |
| ABIOS omit | 530 | 17334 | 17864 | 800 | 18134 | 53.0 | 17387.0 |
| ABIOS combined | 529 | 11514 | 12043 | 799 | 12313 | 52.9 | 11566.9 |
| ABIOS adaptive | 527 | 7264 | 7791 | 797 | 8061 | 52.7 | 7316.7 |

### Cumulative crossover (primary accounting: POST + setup min + messages)

| Encoder | msgs before total beats compact JSON | msgs before total beats English (lossless) |
| --- | ---: | ---: |
| adaptive | 12 | 12 |
| combined | 13 | 14 |
| delta | 14 | 15 |
| omit | 14 | 15 |
| positional | 12 | 13 |
| refs | 12 | 12 |

## Verdict (primary accounting, o200k_base)

On lifecycle_11, ABIOS **refs** total **761** vs compact JSON **738** and lossless English **686** (primary = POST + minimal setup + messages). **Adaptive** total **761**. TOON fallback row **809** (approximation). lifecycle_40/200 repeat many messages verbatim, which inflates refs savings; see transcript notes. SYM-2P v2 rows are external PR #6 constants, not live bench output.
