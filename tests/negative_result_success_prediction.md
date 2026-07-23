# Negative result — seven classical success rules, 8 vs 19, nothing

2026-07-23. Rules pre-specified and pushed in `f355b28` BEFORE the cohort was
supplied. Groups assigned from the product owner's own descriptions before any
chart was scored.

## Groups

    B  BUILT OR EARNED SUBSTANTIALLY   8   a 30-year tech and consulting career,
                                           a founder at ~$1M ARR, a services
                                           business built and lost, tech
                                           millions, a Big-5 consultant, a man
                                           100x better off than the family he
                                           was born into, a startup C-suite, a
                                           couple running a POS company

    C  ORDINARY                       19   government job, university job, Uber
                                           driver, accountant, house cleaner in
                                           Miami, marketing, psychologist,
                                           hand-to-mouth, one struggling with
                                           heavy debt

Everyone born 1990 or earlier. Grouped by LIFETIME achievement, not current
balance: two men in group B currently carry debt. A natal chart does not know
what year it is — it shows capacity, and the dasha shows when capacity
manifests. Grouping by present circumstance would ask the natal chart a question
it cannot answer.

## Result

    rule                                        B      C     gap        p
    S1 Dhana yoga (2/5/9/11 lords linked)    1.25   1.53   -0.28   0.7850
    S2 2nd lord dignity                      0.15   0.86   -0.71   0.9599
    S3 11th lord dignity                     0.46   0.88   -0.42   0.8655
    S4 lagna lord dignity                    0.23   0.08   +0.15   0.3670
    S5 10th lord dignity                     0.16   0.79   -0.63   0.8945
    S6 vargottama count (D1=D9)              0.75   0.84   -0.09   0.6588
    S7 Lakshmi yoga                          0.00   0.00   +0.00   1.0000

200,000 sampled permutations per rule, seed fixed at 20260723. Best p = 0.367
against a Bonferroni threshold of 0.0071. **Five of seven inverted.**

## Two failures that are mine, not the data's

**S7 never fires.** It requires the 9th lord dignified AND in a kendra AND a
lagna lord above 1.0 — three simultaneous conditions, and zero of 27 charts
satisfy them. The rule was never testable. That is an implementation error, not
a negative result, and it should not be counted among the seven.

**The dignity rules may be measuring the wrong thing.** S2, S3 and S5 use
contextual_strength, which was built to score a planet's condition — not the
condition of the HOUSE it rules. A debilitated 2nd lord in a strong position may
still deliver wealth. This was not thought through before the rules were fixed.

## What this means for the product, which is the part that matters

Seventeen hypotheses have now been tested across two sessions — ten for fame,
seven for success. Not one survives correction, and the direction is
consistently backwards: on classical strength indicators, the achievers score
lower than the ordinary.

The honest reading is not that Jyotish cannot see achievement. It is that THIS
ENGINE, with these implementations and 27 charts, cannot — and that a product
which ranks people by natal strength would be selling something it does not
have.

What has survived scrutiny in this codebase points elsewhere, and consistently:

  * Shashi's three dated career transitions each landing on the classically
    correct antardasha lord — 7th lord for the partnership he lost, Rahu for the
    disruptive venture, 6th lord for the service business that worked.
  * Malefics in the 2nd from the Upapada across five known marriages, 5/5, at a
    38% base rate.
  * The blind career-mode test, 3 to 3.5 of 4.

Every one of those is about WHICH KIND and WHEN. None is about HOW MUCH. That is
the shape of what this engine can honestly claim: it describes the character of
a life and times its turns. It does not rank people, and it should stop trying.
