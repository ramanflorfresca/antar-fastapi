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

## What would make this testable

The fame LABELS need checking before the rule does. Two of the four charts are
initials the author of this file cannot identify, so their fame is taken on the
owner's word without knowing the degree — "famous" spans a local reputation and
a global one, and a binary label collapses that.

A real test needs 10+ genuinely well-known people with reliable birth times, and
a fame measure with more than two levels.

## The standing rule this reinforces

State the hypothesis, fix the rule, measure the base rate or run the permutation
test, and report whatever comes out. Two negative results are now recorded in
this directory. Both looked convincing before they were measured.
