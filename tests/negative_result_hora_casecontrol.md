# DEFINITIVE NEGATIVE RESULT — the D-2 Hora chart does not separate wealthy from ordinary
2026-07-23. The proper test, with a control group, that was asked for.

## The design that was finally possible

Every prior D-2 test compared the wealthy against the whole 93-chart base, which
mixes the successful and the ordinary. The owner supplied a matched CONTROL: a
group C of eight people he described, before any chart was cast, as struggling,
normal, or getting by — "cleans houses in Miami", "lots of debt", "above the
poverty line", "a job". That turns a one-sample comparison into a case-control,
which is the only design that can actually answer the question.

    GROUP A — wealth built (owner's word: wealthy / billionaire)   n = 8
      Akash, Vijay Mallya, Lalit Modi, Patricia, Jessica, Channa,
      Saket Burman, Jaipuria
    GROUP C — ordinary means (owner's word: struggling / normal)   n = 8
      Andres Botero, Larissa, Claudia, Sudhakar, Alan Robert,
      Arnulfo, Vishal, Taran

Groups assigned from the owner's descriptions BEFORE any score was seen. All six
pre-registered rules from hora_rules_prespecified.py, one-tailed in the
pre-registered direction (wealthy score higher). Two-sample permutation,
100k-200k shuffles. Bonferroni threshold 0.0083 for six tests.

## Result — all six rules dead, three pointing the wrong way

    rule                                  A     C    A-C    p(A>C)
    H1 grahas in the Sun's hora         3.88  4.50  -0.62   0.831   wrong direction
    H2 2nd lord in the Sun's hora       0.38  0.50  -0.12   0.843   wrong direction
    H3 11th lord in the Sun's hora      0.62  0.25  +0.38   0.156
    H4 lagna in the Sun's hora          0.50  0.50  +0.00   0.688
    H5 2nd lord nature-matched          0.50  0.62  -0.12   0.842   wrong direction
    H6 Sri Lagna lord in the Sun's hora 0.38  0.38  +0.00   0.695

Best result across the whole battery is H3 at p=0.156, nineteen times the
threshold. The headline rule H1 — the one the three-billionaire pilot made look
like p=0.038 — comes in at p=0.831 with the WEALTHY scoring LOWER than the
ordinary. The split was 3.88 for the rich, 4.50 for the strugglers.

    group A H1: [7, 5, 5, 5, 3, 3, 2, 1]
    group C H1: [6, 5, 5, 5, 4, 4, 4, 3]

The wealthy group is more spread out and its low end (Jessica 1, Jaipuria 2)
sits below every single ordinary chart. There is no signal here in either
direction.

## What actually happened, stated for the record

I proposed the Sun-hora direction from three billionaires I chose already
knowing they were billionaires. It hit p=0.038 — one lucky coin in a drawer.
Given a real control group it did not merely fail to replicate; it inverted, and
so did two of the other five rules. The owner's original intuition (wealth sits
in the MOON'S hora because it arrives rather than is forged) is the direction
the data weakly leans, but at these p-values that is a lean, not a finding.

This is the twenty-fourth dead hypothesis in this directory. It died the right
way: pre-registered, controlled, and reported at full strength against my own
proposal.

## Consequence, and it is firm

The Hora chart does NOT predict wealth level and must never be presented as
doing so, in any rule, in either direction. What survives is only the
DESCRIPTIVE reading in antar_engine/hora_chart.py — the CHARACTER of a wealth
channel (generated vs received), which is a classical statement about kind and
was never a claim about amount. Nothing in the product depended on the
direction being real, because the timing claim was already removed (0062742)
and the descriptive layer never asserted size.

## Where the effort should go instead

Sixteen charts now carry verified-enough data and owner-assigned wealth groups.
The ONE thing in this codebase that has survived testing is dasha timing —
Shashi's three dated career transitions each landing on the classically correct
antardasha lord. The wealthy/ordinary split is a far better test bed for a
TIMING rule (does a dhana-yoga dasha coincide with each person's actual wealth
inflection?) than for a static structural one. Static D-2 structure has now been
tested exhaustively and does not separate these groups.
