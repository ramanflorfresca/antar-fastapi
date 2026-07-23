# Negative result — the Arudha does not predict fame

2026-07-22. Recorded so the rule is not re-derived and believed.

## Two hypotheses, both tested, both dead

### 1. "Planets sitting in the Arudha Lagna = recognition available"

My own inference, not a classical rule. Adopted because it read well on the
first chart it was tried on. It inverts:

    Amitabh Bachchan    world famous          ONE planet (Saturn) in the AL
    Elon Musk           world famous          AL EMPTY  [birth time unverified]
    the product owner   not publicly known    THREE planets in the AL

Withdrawn from `lagna_answer.py`. The occupants describe the CHARACTER of how
someone is read — authority, appeal, scale, gravity — not the REACH.

### 2. "Planets in the upachayas (3, 6, 10, 11) from the Arudha = fame"

The classical alternative. Tested on four charts the product owner identifies as
famous, against eight controls with known non-famous outcomes.

    FAMOUS      Amitabh 3, YH 3, AM 1, AS 2            mean 2.25
    CONTROL     Raman 0, JS 1, Shashi 2, Akash 2,
                Kulbir 1, Rishipal 2, Tatiana 0,
                Naveen 3                                mean 1.38

    observed gap  +0.88

Exact permutation test over all 495 ways to split these twelve charts into
groups of four and eight: **75 splits produce a gap this large or larger.**

    p = 0.152

That is noise. Naveen, who is not famous, scores 3 — tied with the two most
famous charts in the set. AM, who is famous, scores 1 — tied with two controls.

## The temptation that was refused

Dropping AM and AS leaves Amitabh 3 and YH 3 against the same controls, which
computes to p ≈ 0.045. That is cherry-picking: the two were removed only after
their scores were seen. The honest number is 0.152 with all four.

## The labels were checked, and they hold

The obvious escape from a p of 0.152 was to doubt the fame labels — two of the
four were initials. The owner confirmed them afterwards: AM is a world-famous
billionaire, AS is world-famous in politics. Together with a globally known
actor and the founder of an international spiritual movement, all four are
genuinely famous by any measure.

So the labels were right and the rule still failed. That closes the escape
route, and makes this a stronger negative result rather than a weaker one.

## What would make this testable

10+ well-known people with reliable birth times, and a fame measure with more
than two levels — a village reputation and a global one should not share a flag.

## The standing rule this reinforces

State the hypothesis, fix the rule, measure the base rate or run the permutation
test, and report whatever comes out. Two negative results are now recorded in
this directory. Both looked convincing before they were measured.
