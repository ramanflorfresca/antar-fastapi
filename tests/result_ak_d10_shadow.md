# AK x D-10 shadow experiment — result

prereg_hash `7ce2568f8c51de98` · cohort n=7637 timed OGDB rows · primary Bonferroni p < 0.00625 (one-sided, higher)

AK distribution: {'Mercury': 1055, 'Jupiter': 1129, 'Venus': 1075, 'Saturn': 1081, 'Mars': 1102, 'Sun': 1137, 'Moon': 1058}

**karakas.py diagnostic:** sorting by absolute longitude picks a different AK than highest-in-sign-degree in 6209/7637 charts (81.3%).

| test | group | feature=Y (in G / n) | feature=N (in G / n) | rate Y | rate N | lift | p (1-sided) | family? | verdict |
|---|---|---|---|---|---|---|---|---|---|
| T0 | SPORT_MIL | 451/1102 | 2851/6535 | 0.409 | 0.436 | 0.94 | 0.9563 | context | dead |
| T1 | SPORT_MIL | 118/270 | 333/832 | 0.437 | 0.400 | 1.09 | 0.1593 | yes | dead |
| T2 | SPORT_MIL | 544/1299 | 2758/6338 | 0.419 | 0.435 | 0.96 | 0.8678 | yes | dead |
| T0 | ARTS | 118/1075 | 818/6562 | 0.110 | 0.125 | 0.88 | 0.9251 | context | dead |
| T1 | ARTS | 30/300 | 88/775 | 0.100 | 0.114 | 0.88 | 0.7705 | yes | dead |
| T2 | ARTS | 159/1207 | 777/6430 | 0.132 | 0.121 | 1.09 | 0.1560 | yes | dead |
| T0 | WORDS | 133/1055 | 882/6582 | 0.126 | 0.134 | 0.94 | 0.7734 | context | dead |
| T1 | WORDS | 24/158 | 109/897 | 0.152 | 0.122 | 1.25 | 0.1750 | yes | dead |
| T2 | WORDS | 187/1305 | 828/6332 | 0.143 | 0.131 | 1.10 | 0.1216 | yes | dead |
| T0 | SUN_CLASS | 301/1137 | 1845/6500 | 0.265 | 0.284 | 0.93 | 0.9134 | context | dead |
| T1 | SUN_CLASS | 52/192 | 249/945 | 0.271 | 0.263 | 1.03 | 0.4484 | yes | dead |
| T2 | SUN_CLASS | 172/605 | 1974/7032 | 0.284 | 0.281 | 1.01 | 0.4417 | yes | dead |

**Gate:** T0 dead for every group — the AK->work table is itself unsupported; T1/T2 cannot rescue it.

Caveats: eminent-person selection (Gauquelin), French birth times rounded to the hour pre-1920 (no lagna/D-10-house feature was used for that reason), groups overlap (military-personnel can also be politician), occupation = career-defining field, not income or satisfaction.
