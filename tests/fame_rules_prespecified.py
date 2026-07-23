"""
tests/fame_rules_prespecified.py
Six classical fame indicators, FIXED 2026-07-23 before the control cohort exists.

Committed deliberately ahead of the data. Four fame hypotheses have already died
in this repository, and one of them (planets in the Arudha) died because it was
invented after looking at a chart that made it look good. The defence against
that is a timestamp: these six were written, committed and pushed BEFORE the
product owner sent a single control chart.

WHY A NEW COHORT IS NEEDED. The first run used eight "controls" who were, on
inspection, a Big-5 consultant, a founder at $1M ARR, a man with thirty years in
tech and consulting, someone who made millions in tech, and an established
spiritual teacher. Those are successful people who are not famous. Raja yoga,
Amala yoga and benefics in kendras are classically indicators of SUCCESS, so the
test was asking whether successful people have success yogas more than other
successful people. Three of six rules came back inverted, which is what that
question deserves.

The real control is someone who never made money, never built anything, and is
not known. That cohort is the one no astrology dataset ever contains, because
nobody volunteers the chart of a life that did not work.

SCORING PROTOCOL, also fixed in advance:
  - exact permutation test per rule
  - Bonferroni threshold for six tests: p < 0.0083
  - every rule reported, including the failures
  - no rule added, removed or adjusted after the data arrives

KNOWN WEAKNESS TO FIX BEFORE THE RERUN: YH's birth time was never supplied. The
19:00 used in the first run came from a stored record that cannot be verified,
and AS at 05:25 sits near sunrise where the ascendant moves fastest. Two of four
famous charts rest on shaky foundations.
"""
import sys; sys.path.insert(0,"/Users/ramandeepsinghchadha/antarai")
SIGNS=["Aries","Taurus","Gemini","Cancer","Leo","Virgo","Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
SIGN_LORD=["Mars","Venus","Mercury","Moon","Sun","Mercury","Venus","Mars","Jupiter","Saturn","Saturn","Jupiter"]
EX={"Sun":"Aries","Moon":"Taurus","Mars":"Capricorn","Mercury":"Virgo","Jupiter":"Cancer","Venus":"Pisces","Saturn":"Libra"}
OWN={"Sun":["Leo"],"Moon":["Cancer"],"Mars":["Aries","Scorpio"],"Mercury":["Gemini","Virgo"],
     "Jupiter":["Sagittarius","Pisces"],"Venus":["Taurus","Libra"],"Saturn":["Capricorn","Aquarius"]}
BEN={"Jupiter","Venus","Mercury","Moon"}
KENDRA={1,4,7,10}; TRIKONA={1,5,9}

def li(cd): return cd["lagna"]["sign_index"]
def lord(cd,h): return SIGN_LORD[(li(cd)+h-1)%12]
def house(cd,p): return (cd["planets"].get(p) or {}).get("house")
def sign(cd,p): return (cd["planets"].get(p) or {}).get("sign")
def occ(cd,h): return [p for p,d in cd["planets"].items() if isinstance(d,dict) and d.get("house")==h]

# R1 — Sun digbala: Sun in or adjacent to the 10th (directional strength there)
def r1_sun_digbala(cd): return 1 if house(cd,"Sun") in (9,10,11) else 0
# R2 — Sun dignity: exalted or own sign
def r2_sun_dignity(cd):
    s=sign(cd,"Sun"); return 1 if (s==EX["Sun"] or s in OWN["Sun"]) else 0
# R3 — Raja yoga: a kendra lord and a trikona lord sharing a house
def r3_rajayoga(cd):
    kl={lord(cd,h) for h in KENDRA}; tl={lord(cd,h) for h in TRIKONA}
    n=0
    for h in range(1,13):
        here=set(occ(cd,h))
        if (here & kl) and (here & tl) and len(here)>=2: n+=1
    return n
# R4 — Amala yoga: a benefic in the 10th from lagna OR from the Moon
def r4_amala(cd):
    if any(p in BEN for p in occ(cd,10)): return 1
    mh=house(cd,"Moon")
    if mh:
        tenth_from_moon=((mh-1+9)%12)+1
        if any(p in BEN for p in occ(cd,tenth_from_moon)): return 1
    return 0
# R5 — benefics in kendras from the lagna
def r5_benefic_kendra(cd):
    return sum(1 for h in KENDRA for p in occ(cd,h) if p in BEN)
# R6 — 10th lord in a kendra or trikona
def r6_tenth_lord_placed(cd):
    return 1 if house(cd,lord(cd,10)) in (KENDRA|TRIKONA) else 0
RULES=[("R1 Sun digbala (9/10/11)",r1_sun_digbala),("R2 Sun exalted/own",r2_sun_dignity),
       ("R3 Raja yoga count",r3_rajayoga),("R4 Amala yoga",r4_amala),
       ("R5 benefics in kendras",r5_benefic_kendra),("R6 10th lord kendra/trikona",r6_tenth_lord_placed)]
