# Negative result — six classical fame rules, three groups, nothing

2026-07-23. Rules pre-specified and pushed in `752ecb4` BEFORE any control
chart was supplied. `tests/fame_rules_prespecified.py` carries the timestamp.

## Design

Three groups, assigned on the product owner's own descriptions before scoring:

    A  FAMOUS                  4    a globally known actor, the founder of an
                                    international spiritual movement, a
                                    world-famous billionaire, a world-famous
                                    politician
    B  SUCCESSFUL, NOT FAMOUS  6    a Big-5 consultant, a founder at ~$1M ARR,
                                    a thirty-year tech and consulting career,
                                    tech millions, a man financially 100x better
                                    off than the family he was born into
    C  ORDINARY               12    steady modest work, unknown — government
                                    job, university job, Uber driver, marketing,
                                    hand-to-mouth

The three-group split separates two questions the earlier run conflated: a rule
scoring B ≈ A > C measures SUCCESS and is useless for fame; a rule scoring
A > B ≈ C measures FAME.

AGE FILTER, and it was the product owner who raised it. Everyone in C is 34 or
older. "Not famous" is only a fact once a person is old enough for it to be
settled — Amitabh Bachchan was 31 when Zanjeer made him, after a decade of
flops, so scoring him at 26 would have placed him in the control group. Five
supplied charts were discarded on age alone.

## Result

    rule                          A fam   B succ   C ord     A vs C    B vs C
    R1 Sun digbala                 0.00     0.33     0.42     1.0000    0.8009
    R2 Sun exalted/own             0.50     0.17     0.33     0.4890    0.9076
    R3 Raja yoga count             0.75     1.33     1.50     0.9885    0.8258
    R4 Amala yoga                  0.50     0.33     0.58     0.8077    0.9344
    R5 benefics in kendras         0.50     1.67     1.58     0.9885    0.5364
    R6 10th lord kendra/trikona    0.00     0.33     0.58     1.0000    0.9344

Best p = 0.489 against a Bonferroni threshold of 0.0083. Exact permutation
tests throughout.

**The famous score LOWER than the ordinary on four of six rules.** A billionaire,
a world politician, a global spiritual leader and a globally known actor carry
fewer Raja yogas, fewer benefics in kendras and worse 10th-lord placements than
an Uber driver's peer group.

**B vs C shows nothing either.** That kills the excuse offered after the first
run — that these rules measure success rather than fame. On this data they
measure neither.

## What is wrong, honestly, in order of likely size

1. **n = 4 famous.** Perfect separation would have reached p = 0.0005, so
   significance was achievable — the data simply does not separate. But four
   people cannot represent fame.
2. **Two of the four famous charts are shaky.** YH's birth time was never
   supplied; the 19:00 used comes from an unverifiable stored record. AS is at
   05:25, near sunrise, where the ascendant moves fastest.
3. **The rule implementations are simplified, and that is mine.** Raja yoga
   forms three ways — conjunction, mutual aspect, and exchange (parivartana) —
   and only conjunction was coded. Sun's digbala is specifically the 10th house;
   widening it to 9/10/11 diluted it.

## The standing conclusion

Ten fame hypotheses have now been tested across two sessions — three invented,
seven classical. Every one dead, several inverted. The honest engineering answer
is no longer "try another rule": **this engine cannot predict fame, and shipping
anything that claims to would be dishonest.**

What the exercise bought instead is real: a three-group design, an age filter,
and a negative recorded with its rules timestamped before the data arrived.
