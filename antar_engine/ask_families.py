"""[ask-families 2026-10-11] Question-specific 'what makes it hold / what breaks it' for the money, business and job decisions people actually ask.

Audit (37 money / business / job questions through the real pipeline): the conditions block came from the topic's channel + a per-concern
`breaks` line, so a dozen DIFFERENT questions got the same sentence ("It holds if you grow income through daily work, service and routines…
It breaks if spending and commitments rise as fast as income does") — a debt question, a pricing question and a funding question read as one
template. Each family below adds the condition that is true of THAT decision; ask_basis.conditions keeps the chart clause (the ruler's channel,
weakened or not) after it, so the answer stays chart-linked as well as question-specific. English only (other languages keep the topic line).

A family is chosen by the first match, most specific first. Pure."""
from __future__ import annotations

import re
from typing import Optional, Tuple

# (family, question regex, holds hook, breaks clause)
_FAMILIES: Tuple[Tuple[str, str, str, str], ...] = (
    ("fire", r"\b(fire|let go|lay ?off|terminate|dismiss)\b.*\b(someone|him|her|them|employee|team|person|staff)\b|\b(fire|let go of|lay off)\b",
     "the expectations were written down and missed before the decision", "the exit is made in frustration or without a written record"),
    ("funding", r"\b(raise (money|funding|capital|a round|funds)|raise from|investors?|funded|funding|bootstrap|venture capital|\bvc\b|seed round|angel)\b",
     "you can show one number an investor can verify", "money is taken before the numbers are clean or the terms are understood"),
    ("loan", r"\b(loan|borrow|credit line|line of credit|mortgage)\b",
     "you borrow only what a lean month can still repay", "the repayment is sized to your best month instead of your worst"),
    ("debt", r"\b(debts?|in debt|debt[- ]free|owe|owing|consolidat\w*|pay(?:ing)? off|clear my (?:loan|debt)s?|out of financial trouble|financial trouble)\b",
     "each repayment fits inside your leanest month's income", "new obligations arrive before the old ones are cleared"),
    ("price", r"\b(raise|increase|change|set)\b.*\b(prices?|rates?|fees?)\b|\bpricing\b",
     "you test the new price on one new client before touching the old ones", "the price rises without the value they can see rising too"),
    ("clients", r"\b(get|find|win|land|attract)\b.*\b(clients?|customers?|leads?)\b|\bmore (clients|customers|leads|sales)\b",
     "each past client is asked for one specific introduction", "outreach is spread thin instead of repeating what already brings people to you"),
    ("hire", r"\b(hire|hiring|recruit)\b|\bfirst employee\b|\bco-?founder\b.*\bsolo\b|\bsolo\b.*\bco-?founder\b",
     "the role is paid from income you can already count on for six months", "you hire to fix a problem you have not yet named in writing"),
    ("job_offer", r"\b(job offer|new offer|the offer|take the (?:new )?(?:job|role|position)|accept the (?:job|offer|role))\b",
     "the terms are in writing before you decide", "you say yes for the title and skip the reporting line, pay and scope"),
    ("promotion", r"\b(promot\w*|ask for a raise|get a raise|salary (?:raise|increase|hike)|pay raise)\b",
     "you bring three measurable results, not a feeling", "the ask comes without evidence the decision-maker can repeat"),
    ("quit", r"\b(quit|resign|leave)\b.*\b(job|work|company|employer)\b|\bstart (?:my|a) (?:own )?business\b.*\bjob\b|\bjob\b.*\bstart (?:my|a) (?:own )?business\b",
     "the smallest version of the business has already earned before you resign", "you leave without a written number of months of runway"),
    ("switch_career", r"\b(switch|change|move to)\b.*\bcareers?\b|\bcareer change\b",
     "you can name the skill you carry across and a first target role", "you leave without a test project or a first target"),
    ("expand", r"\b(expand|scale|grow)\b.*\b(business|company|startup|operation)\b|\bopen (?:a )?(?:second|new) (?:branch|location|office)\b",
     "the current business can fund the next step without new debt", "capacity is added before demand has repeated"),
    ("second_business", r"\b(second|another|new) (?:business|venture|company|startup)\b",
     "the first business can run a month without you", "the second one is started on the first one's cash"),
    ("sell", r"\bsell\b.*\b(business|company|startup|stake|shares)\b",
     "you have written what the business must deliver in the next 12 months to be worth keeping", "you sell on a bad month instead of on the numbers"),
    ("pivot", r"\bpivot\b|\bchange (?:my|our) (?:business )?(?:model|direction|strategy)\b",
     "you test the new direction with a few real customers before moving everything", "you drop what already earns before the new thing does"),
    ("property", r"\b(buy|purchase)\b.*\b(house|home|property|flat|apartment|land)\b|\breal estate\b|\bproperty\b",
     "the ceiling and the must-haves are fixed in writing first", "you commit before the ceiling and the exit are clear"),
    ("income", r"\b(income|earn(?:ings)?|salary|revenue|profit|make more money|more money|savings)\b",
     "each gain is split the day it arrives: part kept, part spent, part reinvested", "spending rises as fast as income does"),
)
_COMPILED = tuple((f, re.compile(rx, re.I), h, b) for f, rx, h, b in _FAMILIES)


def family(question: str) -> Optional[Tuple[str, str, str]]:
    """(name, holds_hook, breaks_clause) for the first matching family, else None."""
    q = (question or "").strip()
    if not q:
        return None
    for name, rx, holds, breaks in _COMPILED:
        if rx.search(q):
            return name, holds, breaks
    return None
