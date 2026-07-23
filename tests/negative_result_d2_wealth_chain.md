# NEGATIVE RESULT — the D-2 / Sri Lagna wealth chain does not time wealth
2026-07-23

The product owner challenged the D-2 logic: "your d two, which is the Hora
chart, wealth chart, logic is not correct... it has to do with the Nakshatra
lord." He was right that the previous rule was broken (see f94764d — "own sign"
is meaningless in a two-sign chart). This file tests the replacement he
proposed, and one more.

## Cohort
Billionaires with usable birth times. Mark Zuckerberg was EXCLUDED: his birth
time is not on record, and Sri Lagna moves ~30 degrees per hour — a whole sign —
because it compounds the ascendant's motion with the Moon's nakshatra traverse.
A nakshatra claim on an unknown time is fiction.

    Bill Gates      1955-10-28 22:00 Seattle      [Rodden A]
    Mukesh Ambani   1957-04-19 19:53 Aden         [owner-supplied]
    Elon Musk       1971-06-28 06:30 Pretoria     [widely cited, UNVERIFIED]

11 dated wealth events between them. Base rates are PERSON-SPECIFIC: the share
of that individual's own age 20-70 timeline the rule would have been true.

## RULE 1 — the Sri Lagna's nakshatra lord runs at MD or AD on the event
The reasoning was that Sri Lagna is computed FROM the Moon's nakshatra fraction,
the same quantity that seeds the Vimshottari balance — so its nakshatra lord
should be the planet whose dasha delivers prosperity. Promise from the varga,
date from the dasha, which is the Rao method.

    Gates   (Moon)     0/4        base rate 27%
    Ambani  (Venus)    0/3        base rate 16%
    Musk    (Jupiter)  1/4        base rate 32%
    -------------------------------------------
    TOTAL              1/11       expected 2.8 (26%)      binomial p = 0.962

WORSE than chance. The single hit is Musk's Zip2 sale, on the one birth time
that is not verified. The chain is dead — and it was MY inference, not a
classical rule, which is the third time in this repository that a
nice-sounding inference has failed a test.

## RULE 2 — the 2nd lord or 11th lord runs at MD or AD on the event
The mainstream classical dhana rule, taught by K.N. Rao's school.

    Gates   (Sun/Venus)      2/4    base rate 62%
    Ambani  (Jupiter/Mercury) 1/3   base rate 38%
    Musk    (Moon/Mars)      3/4    base rate 39%
    -------------------------------------------
    TOTAL                    6/11   expected 5.2 (47%)    binomial p = 0.425

THIS IS THE DANGEROUS ONE. 6 of 11 reads as a success — more than half, and it
catches Gates's IPO, his richest-man year, and three of Musk's four. Reported
without the base rate it would have been believed. But "2nd lord OR 11th lord,
at MD OR AD" is true for roughly half an adult life, so 6/11 is exactly chance.

Same failure mode as negative_result_separation_timing.md. The standing rule
holds: never report a timing pattern without its base rate.

## What did NOT get claimed
All three of Ambani's events fall in Rahu mahadasha. That is not a finding —
his Rahu MD is 18 years long and the three events span five of them. Any rule
would "hit" there.

## The one direction still open — UNTESTED, do not ship
Planets in the Sun's hora (the forged side) vs the Moon's (the received side):

    Gates 7   Musk 6   Ambani 5        billionaire mean 6.00
    cohort n=93                        mean 4.27, sd 1.47
    permutation p = 0.038

Points the OPPOSITE way from the intuition that wealth comes easy in the Moon's
hora. All three sit on the difficult, self-generating side. But n=3, the names
were chosen already knowing they were billionaires, and no n=3 result can
survive correction. It is a direction to test against a pre-specified cohort,
not a finding.

## Consequence for the product
D-2 describes the CHARACTER of a wealth channel — forged versus received. It
does not time wealth and it does not size it. Nothing here licenses a date.
The wealth reading must not imply otherwise.
