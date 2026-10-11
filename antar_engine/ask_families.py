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


# ── the fallback MOVE for each family (used only when the model's own move is missing / vague) ──────────
# The audit saw the SAME fallback ("put the effort into your network and gains, and launch the smallest version that can earn") on "quit my job",
# "switch careers" and "second business". Each decision gets its own; ask_basis.chart_move adds the chart channel ({ch}) and, when the
# ruler is weakened, the lead / reassess clause.
FAMILY_MOVE = {
    "fire": "write down three specific things this person must change, with a date, and decide the exit from that record \u2014 {ch} is where the fallout lands",
    "price": "quote the new price to one new client this week and keep the old price for existing ones \u2014 trust here is built through {ch}",
    "clients": "ask each past client for one specific introduction \u2014 new work reaches you through {ch}",
    "debt": "list every debt by interest rate and put your spare cash on the highest one, keeping one written number your leanest month can cover \u2014 {ch} drives this",
    "loan": "write your worst-month income and check the repayment fits inside it before you sign \u2014 {ch} is what has to carry it",
    "hire": "write down the one problem the hire would fix and what it costs for six months, before you look at candidates \u2014 {ch} decides who stays",
    "funding": "write the one number an investor can verify and who you would show it to first \u2014 the ask runs through {ch}",
    "job_offer": "get the pay, reporting line and scope in writing before you answer \u2014 this move runs through {ch}",
    "promotion": "write your three biggest measurable results and bring them to the person who decides \u2014 recognition comes through {ch}",
    "quit": "launch the smallest paying version while you are still employed and write your runway in months before you resign \u2014 {ch} carries it",
    "switch_career": "name the one skill you carry across and test it on a small project before you leave \u2014 the new path opens through {ch}",
    "expand": "pay for the next step from current income and add capacity only after demand has repeated \u2014 {ch} is where demand comes from",
    "second_business": "let the first business run a month without you before starting another \u2014 {ch} shows whether it can",
    "sell": "write what the business must deliver in the next 12 months to be worth keeping, then hold any offer up against it \u2014 {ch} sets the price",
    "pivot": "test the new direction with three paying customers before moving everything \u2014 {ch} is where they come from",
    "income": "split every gain the day it arrives: part kept, part spent, part reinvested \u2014 income reaches you through {ch}",
}

# Operational choices ("should I fire / raise prices / consolidate…", "how do I get clients?") are decisions about HOW, not events with a window:
# they get a recommendation, never a "Not yet — the career window is …" verdict.
_OP_START = re.compile(r"(?i)^\s*(should (i|we)|how (do|can|should|would) (i|we)|what should (i|we)|is it better to|would it be better to)\b")
_OP_FAMILIES = ("fire", "price", "clients")
_OP_DEBT = re.compile(r"(?i)\b(consolidat\w*|pay(?:ing)? off|pay down|invest first|before (?:i )?invest\w*|refinanc\w*)\b")


def is_operational(question: str) -> bool:
    """True for an operational choice that should be answered as a recommendation (not a window verdict)."""
    q = (question or "").strip()
    if not q or not _OP_START.match(q):
        return False
    f = family(q)
    if not f:
        return False
    return f[0] in _OP_FAMILIES or (f[0] == "debt" and bool(_OP_DEBT.search(q)))
