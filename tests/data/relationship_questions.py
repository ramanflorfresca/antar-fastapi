"""The 55 love / relationship / marriage questions people ask an astrologer, each tagged with the
lane Ask should handle it in. Source: owner-pasted list 2026-10-12.

Lanes (see product-positioning-decision-intelligence: everything is the asker's decision):
  serve    — about the asker's own chart: promise + timing window, answered directly.
  pattern  — about the partner's nature: answer as "the kind of partner your chart is drawn to",
             never as hard facts about a specific future person.
  reframe  — about another person's feelings/behaviour, but the real question is the asker's move:
             answer with the asker's season, pattern, window and move; never predict the third party.
  people   — needs the OTHER person's chart: point to People/compatibility, don't guess from the asker's chart.
  decline  — a claim about a third party's secret behaviour (affairs, calls, caste, looks): never assert it
             from a chart; answer with the asker's own pattern/boundary and what to do about the doubt.

`key` is the classical key from the list — documentation for whoever builds the matching signal.
"""
from __future__ import annotations

LANES = ("serve", "pattern", "reframe", "people", "decline")
GROUPS = {"A": "identity & compatibility", "B": "timing of marriage", "C": "breakup & separation",
          "D": "affairs & secret relationships", "E": "spouse nature", "F": "married life", "X": "emergency"}

# (id, group, lane, question, key)
_ROWS = [
    (1, "A", "serve", "Will I ever get married?", "7th house, 7th lord, Venus/Jupiter, dasha of 7th lord"),
    (2, "A", "serve", "When will I get married?", "dasha of 7th lord/Venus/Jupiter, Varshphal Muntha in 7th"),
    (3, "A", "serve", "Will I have a love marriage or an arranged marriage?", "5th-7th link, Venus-Rahu, 7th lord in 5th/11th"),
    (4, "A", "people", "Is my partner compatible with me?", "Kuta, navamsa comparison, Moon sign"),
    (5, "A", "serve", "Will my marriage last?", "7th strength, Mangal Dosha, 2nd house"),
    (6, "A", "people", "Does my partner truly love me?", "Venus, Moon, 5th, Darakaraka"),
    (7, "A", "reframe", "Am I meant to be with this person?", "7th-lord dasha, navamsa 7th, Darakaraka"),
    (8, "A", "reframe", "Will I marry the person I love?", "5th lord in 7th, Venus-Jupiter, dasha overlap"),
    (9, "A", "people", "Is my partner the right one for me?", "Ashtakoota, 7th aspects, dasha compatibility"),
    (10, "A", "serve", "Will I have a second marriage?", "7th and 2nd, 9th, dasha of 2nd/9th lord"),
    (11, "B", "serve", "What is the exact year of my marriage?", "Muntha in 7th, dasha of 7th lord"),
    (12, "B", "serve", "Why is my marriage getting delayed?", "Saturn on 7th, 7th lord in 6/8/12"),
    (13, "B", "serve", "Will I marry before 30?", "Saturn transit, 7th-lord dasha timing"),
    (14, "B", "serve", "Is there a love marriage in my chart?", "5th-7th exchange, Venus in 5th/11th"),
    (15, "B", "serve", "Will I marry in this dasha or the next?", "MD-AD of 7th lord, Venus, Jupiter"),
    (16, "B", "serve", "What month will I get engaged?", "PD/SD of 7th lord, Varshphal 7th lord"),
    (17, "B", "serve", "Will my marriage happen this year?", "Muntha, annual 7th lord strength"),
    (18, "B", "serve", "Why is everyone else married but not me?", "7th affliction, Saturn-Rahu on 7th"),
    (19, "B", "serve", "Will I have a court marriage or a traditional one?", "7th lord in 6th, Rahu in 7th"),
    (20, "B", "serve", "Is marriage destined for me or will I remain single?", "empty 7th + 7th lord in 6/8/12, sanyasa yoga"),
    (21, "C", "reframe", "Will my breakup be permanent?", "MD-AD in 6/8/12, Venus retrograde"),
    (22, "C", "reframe", "Will he or she come back?", "next AD/PD of 7th lord/Venus, Varshphal 7th"),
    (23, "C", "decline", "When will he or she contact me?", "SD lord transiting 7th, PD of Venus"),
    (24, "C", "decline", "Is he or she cheating on me?", "7th lord in 6th, Venus-Rahu, 12th"),
    (25, "C", "reframe", "Will we patch up?", "Jupiter transit 7th, PD of 7th lord"),
    (26, "C", "reframe", "Is this a temporary fight or a final break?", "dasha stack, Muntha"),
    (27, "C", "reframe", "Will I get over him or her?", "6th-house dasha, Ketu AD, Saturn transit"),
    (28, "C", "decline", "Is there a third person in my relationship?", "7th lord with Rahu, 5th-7th-12th"),
    (29, "C", "decline", "Will my ex marry someone else?", "ex's 7th-lord dasha, transit"),
    (30, "C", "reframe", "Should I wait for him or her, or move on?", "next AD lord, Varshphal 7th lord, navamsa"),
    (31, "D", "decline", "Am I having an affair?", "5th-7th-12th, Venus-Rahu"),
    (32, "D", "decline", "Will my affair be exposed?", "6th-house dasha, Rahu transit 7th"),
    (33, "D", "reframe", "Will I marry my affair partner?", "7th-lord dasha, navamsa 7th"),
    (34, "D", "decline", "Is my husband or wife having an affair?", "7th lord in 12th, Venus-Mars-Rahu"),
    (35, "D", "reframe", "Will I have a secret relationship?", "12th-house Venus, Rahu in 7th"),
    (36, "E", "decline", "What will my spouse look like?", "7th sign, 7th lord, Venus"),
    (37, "E", "pattern", "Will my spouse be rich?", "7th lord in 2nd/11th, Venus in 2nd"),
    (38, "E", "decline", "Will my spouse be from a different caste or religion?", "Rahu in 7th, 7th lord in 12th"),
    (39, "E", "pattern", "Will my spouse be older or younger than me?", "Saturn in 7th (older), Mercury (younger)"),
    (40, "E", "pattern", "What will my spouse's profession be?", "7th lord's house, 10th from 7th"),
    (41, "E", "pattern", "Will my spouse be dominating?", "Mars/Saturn in 7th, 7th lord in Aries/Scorpio"),
    (42, "E", "people", "Will my spouse love me?", "Venus strength, 7th lord in 1st/5th"),
    (43, "F", "serve", "Will I have a happy married life?", "7th, 2nd, 4th strength"),
    (44, "F", "serve", "Will I get divorced?", "7th lord in 6/8/12, Mangal Dosha, dasha"),
    (45, "F", "serve", "Will I have children after marriage?", "5th, Jupiter, dasha of 5th lord"),
    (46, "F", "people", "Is my spouse's dasha affecting our marriage?", "spouse's MD-AD, Saturn transit"),
    (47, "F", "serve", "Is a love marriage or an arranged one more likely for me?", "5th-7th link, Venus-Rahu (paraphrase of #3)"),
    (48, "F", "serve", "Will my in-laws be supportive?", "7th lord in 4th, 2nd house"),
    (49, "F", "serve", "Will I marry a foreigner?", "7th lord in 9th/12th, Rahu in 7th"),
    (50, "F", "serve", "What remedies help my marriage problems?", "7th-lord mantra, Venus remedies, dasha-specific"),
    (51, "X", "decline", "Will he call me today?", "SD lord transiting 7th"),
    (52, "X", "decline", "Does he love me or is he just using me?", "Venus-Moon, 5th house"),
    (53, "X", "decline", "Will we meet this month?", "PD of 7th lord, Varshphal 7th"),
    (54, "X", "people", "Is he the one?", "Darakaraka, navamsa 7th"),
    (55, "X", "reframe", "Should I propose?", "5th-lord dasha, Venus transit"),
]

QUESTIONS = [{"id": i, "group": g, "lane": l, "q": q, "key": k} for i, g, l, q, k in _ROWS]
