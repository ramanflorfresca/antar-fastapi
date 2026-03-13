"""
antar_engine/astrological_rules.py  — v2

RULE PHILOSOPHY:
  IF [condition is TRUE for this chart right now] → fire the rule
  Rules are FILTERED by concern, RANKED by strength, TOP 5 only sent to LLM

FILTERING PIPELINE:
  500+ possible rules
    → ACTIVE FILTER: only rules where condition is currently true
    → CONCERN FILTER: boost rules that match what user asked about
    → STRENGTH RANKER: natal > dasha > transit, confluence > single
    → RARITY BOOST: GK active, 6/8/12 transit, Rahu/Ketu over natal planet
    → TOP 5 → LLM

NEW RULES ADDED v2:
  - GK (Gnatikaraka) — pain/obstacle giver when active in dasha or transited
  - Transit to 6H/8H/12H → problems/transformation signals
  - Rahu/Ketu transiting over natal planets → change markers
  - Rahu/Ketu transiting over each other (nodes axis) → major life shift
  - Saturn Sade Sati (full 3-phase)
  - 8H transit = transformation/investigation window
"""

from __future__ import annotations
from collections import Counter, defaultdict
from datetime import datetime, date
from typing import Optional


# ═══════════════════════════════════════════════════════════════
# REMEDY STRUCTURE
# ═══════════════════════════════════════════════════════════════

def make_remedy(mantra, mantra_count, mantra_timing, india_action, global_action, solves):
    return {
        "mantra": mantra, "mantra_count": mantra_count,
        "mantra_timing": mantra_timing, "india_action": india_action,
        "global_action": global_action, "solves": solves,
    }

REMEDIES = {
    "Sun": make_remedy("Om Suryaya Namaha","108 times","Sunday morning facing east at sunrise",
        "Offer water (arghya) to the rising Sun. Donate wheat and jaggery on Sundays.",
        "Sit in morning sunlight for 10 minutes. Write one gratitude to a father figure weekly.",
        "Strengthens authority, clarity of purpose, and career recognition."),
    "Moon": make_remedy("Om Chandraya Namaha","108 times","Monday evening or full moon night",
        "Offer milk to Shiva on Mondays. Keep silver in wallet. Fast on Mondays.",
        "Drink water from a silver cup. Meditate on full moon nights. Call your mother Mondays.",
        "Stabilizes emotions, mental peace, and financial steadiness."),
    "Mars": make_remedy("Om Mangalaya Namaha","108 times","Tuesday morning",
        "Donate red lentils on Tuesdays. Feed stray dogs.",
        "21 minutes of vigorous physical exercise every Tuesday. Donate to veterans charity.",
        "Channels aggression constructively, prevents accidents, reduces hidden financial losses."),
    "Mercury": make_remedy("Om Budhaya Namaha","108 times","Wednesday morning",
        "Feed green grass to a cow on Wednesdays. Donate green vegetables.",
        "Write in a journal every Wednesday — stream of consciousness. Donate books.",
        "Sharpens intellect, improves communication, prevents deception."),
    "Jupiter": make_remedy("Om Gurave Namaha","108 times","Thursday morning",
        "Donate yellow items on Thursdays. Respect your guru. Plant a banana tree.",
        "Teach or mentor someone weekly. Read wisdom literature 15 min every Thursday.",
        "Expands prosperity, wisdom, opportunity. Removes obstacles from education and growth."),
    "Venus": make_remedy("Om Shukraya Namaha","108 times","Friday morning",
        "Donate white items on Fridays. Offer white flowers to Goddess Lakshmi.",
        "Create something beautiful weekly — write, paint, cook. Express appreciation to loved ones.",
        "Strengthens relationships, creativity, and financial flow. Reduces relationship conflicts."),
    "Saturn": make_remedy("Om Shanaischaraya Namaha","19 times","Saturday evening",
        "Donate black sesame, mustard oil, and iron on Saturdays. Feed crows.",
        "Do one act of service for elderly or marginalized people every Saturday. Practice patience.",
        "Reduces Saturn's delays and obstacles. Builds endurance, discipline, and karmic credit."),
    "Rahu": make_remedy("Om Rahave Namaha","18 times","Saturday night or during Rahu kaal",
        "Donate blue or black items on Saturdays. Feed fish.",
        "10-minute digital detox daily. Donate to an immigrant or marginalized community.",
        "Reduces obsessive thinking, foreign obstacles, and sudden reversals."),
    "Ketu": make_remedy("Om Ketave Namaha","18 times","Tuesday or Saturday morning",
        "Donate blankets to the poor. Feed stray dogs. Worship Lord Ganesha.",
        "Spend 15 minutes daily in complete silence — no phone, no music.",
        "Reduces detachment, brings spiritual clarity, resolves karmic patterns."),
}


# ═══════════════════════════════════════════════════════════════
# LAL KITAB RULES — Planet in House (natal)
# ═══════════════════════════════════════════════════════════════

LAL_KITAB_RULES = {
    ("Sun", 1):  {"domain":"career","confidence":0.80,"prediction":"Natural authority — your identity IS your career. Visibility and public recognition are your path.","warning":"Ego-driven decisions drain power. Arrogance creates sudden falls.","remedy_planet":"Sun"},
    ("Sun", 4):  {"domain":"family","confidence":0.78,"prediction":"Home and family carry Sun's authority — real estate and family legacy are important themes.","warning":"Do not be domineering in family matters.","remedy_planet":"Sun"},
    ("Sun", 10): {"domain":"career","confidence":0.88,"prediction":"One of the strongest career positions — government, authority, and recognition are your natural domain.","warning":"Overreach in career can affect father. Don't neglect family for ambition.","remedy_planet":"Sun"},
    ("Moon", 2): {"domain":"wealth","confidence":0.80,"prediction":"Wealth fluctuates with emotional cycles — income rises when mind is calm, dips when anxious.","warning":"Never make major financial decisions when emotionally disturbed.","remedy_planet":"Moon"},
    ("Moon", 4): {"domain":"family","confidence":0.82,"prediction":"Deep emotional bond with mother and homeland. Real estate and home-based ventures are strongly favored.","warning":"Excessive attachment to mother can create relationship imbalances.","remedy_planet":"Moon"},
    ("Moon", 7): {"domain":"marriage","confidence":0.82,"prediction":"Your emotional world IS your partnership world — a sensitive, intuitive partner is essential.","warning":"Emotional neediness in partnerships creates instability. Learn to self-soothe.","remedy_planet":"Moon"},
    ("Mars", 7): {"domain":"marriage","confidence":0.82,"prediction":"Intense, passionate partnerships. You need a strong, independent partner who matches your fire.","warning":"CRITICAL: Manage aggression in partnerships. Do not rush into legal commitments.","remedy_planet":"Mars"},
    ("Mars", 10):{"domain":"career","confidence":0.85,"prediction":"Mars in 10th — driven, ambitious career. Built for leadership, execution, and making things happen at scale.","warning":"Aggression with superiors can derail an otherwise stellar career.","remedy_planet":"Mars"},
    ("Mars", 12):{"domain":"wealth","confidence":0.75,"prediction":"Your strength operates behind the scenes. Expenses can be sudden and large; foreign connections financially significant.","warning":"Do NOT lend money — it rarely returns. Control hidden expenditures.","remedy_planet":"Mars"},
    ("Mercury", 1):{"domain":"career","confidence":0.80,"prediction":"Intelligence and communication are your identity. Business, writing, trading, consulting come naturally.","warning":"Overthinking weakens Mercury. Do NOT lie — punishes through speech and business problems.","remedy_planet":"Mercury"},
    ("Mercury", 7):{"domain":"marriage","confidence":0.78,"prediction":"Intellectual compatibility essential in marriage. Business partnerships highly fruitful.","warning":"Don't over-analyze partner. Mercury in 7th can create missed emotional connection.","remedy_planet":"Mercury"},
    ("Mercury", 10):{"domain":"career","confidence":0.85,"prediction":"Exceptional for business, media, communications, intellectual professions. Reputation built on intelligence.","warning":"Be careful with contracts — read everything. Mercury in 10th punishes careless agreements.","remedy_planet":"Mercury"},
    ("Jupiter", 1):{"domain":"general","confidence":0.88,"prediction":"Jupiter in ascendant — wisdom, prosperity, and grace mark your entire personality. Teaching and advisory work align with highest purpose.","warning":"Do NOT waste Jupiter's grace through arrogance or greed. Never disrespect a teacher.","remedy_planet":"Jupiter"},
    ("Jupiter", 11):{"domain":"wealth","confidence":0.88,"prediction":"One of the best wealth positions. Networks, elder connections, and desire-fulfilment are Jupiter's gifts here.","warning":"Never break a promise to a friend or elder.","remedy_planet":"Jupiter"},
    ("Venus", 1): {"domain":"marriage","confidence":0.85,"prediction":"Venus in ascendant — charm, artistic ability, magnetic personality. Love, beauty, creativity are woven through your life path.","warning":"Overindulgence weakens Venus. Guard relationships through genuine commitment.","remedy_planet":"Venus"},
    ("Venus", 4): {"domain":"wealth","confidence":0.82,"prediction":"Beautiful home, property gains, domestic happiness. Real estate and luxury goods financially favorable.","warning":"Don't sacrifice relationships for material comfort.","remedy_planet":"Venus"},
    ("Venus", 7): {"domain":"marriage","confidence":0.88,"prediction":"Venus in 7th — partnership is deeply important and brings beauty and creative collaboration. Business partnerships equally blessed.","warning":"Excessive dependency on partner weakens this Venus. Maintain your own creative identity.","remedy_planet":"Venus"},
    ("Venus", 11):{"domain":"wealth","confidence":0.85,"prediction":"Gains through beauty, art, relationships. Your network is a source of income. Female connections bring important opportunities.","warning":"Don't mix romantic feelings with professional networks.","remedy_planet":"Venus"},
    ("Saturn", 1):{"domain":"health","confidence":0.80,"prediction":"Saturn in ascendant — life is built slowly but unbreakably. Discipline, endurance, and service are your power.","warning":"Avoid pessimism and self-limitation. Saturn here teaches through persistence, not speed.","remedy_planet":"Saturn"},
    ("Saturn", 7):{"domain":"marriage","confidence":0.85,"prediction":"Saturn in 7th — partnerships are karmic and serious. What you build in relationships is built to last. Delay before commitment is actually protection.","warning":"Do NOT rush into marriage or business partnerships. Saturn delays but NEVER denies. Wait for the right one — not just the available one.","remedy_planet":"Saturn"},
    ("Saturn", 10):{"domain":"career","confidence":0.90,"prediction":"Saturn in 10th — the career rises slowly but becomes a towering achievement. Hard work compounds into legacy. Your professional reputation is built over decades, not years.","warning":"No shortcuts. Integrity in career is non-negotiable — Saturn in 10th exposes dishonesty.","remedy_planet":"Saturn"},
    ("Rahu", 10): {"domain":"career","confidence":0.82,"prediction":"Rahu in 10th — unconventional path to career success. Sudden rises possible. Foreign or technology-related careers are favored.","warning":"Build genuine expertise. Rahu in 10th exposes those who rise too fast without foundations.","remedy_planet":"Rahu"},
    ("Ketu", 4):  {"domain":"family","confidence":0.75,"prediction":"Ketu in 4th — past-life connection to homeland and mother. Spiritual depth in home life. Relocation is a recurring theme.","warning":"Don't let detachment become emotional withdrawal from family.","remedy_planet":"Ketu"},
    ("Ketu", 11): {"domain":"spiritual","confidence":0.78,"prediction":"Ketu in 11th — complex relationship with material gains. Spiritual richness over material accumulation. Income comes but holding it requires conscious detachment.","warning":"Do NOT make wealth your primary purpose.","remedy_planet":"Ketu"},
    ("Ketu", 12): {"domain":"spiritual","confidence":0.85,"prediction":"Ketu in 12th — the placement of liberation. Spiritual depth, mystical experiences, and direct connection to the unseen world.","warning":"Avoid escapism through substances or excessive withdrawal.","remedy_planet":"Ketu"},
    # ══════════════════════════════════════════════════════════
    # 6TH HOUSE NATAL — Loans, Borrowed Capital, Institutional Debt
    # 6H = what you BORROW: bank loans, credit lines, institutional debt
    # Also governs: enemies, health, daily work, legal disputes, service
    # ══════════════════════════════════════════════════════════
    ("Sun", 6):   {"domain":"finance","confidence":0.75,
                   "prediction":"Sun in the loan/service zone — government-backed funding, authority-linked credit lines, and institutional grants are the primary capital channel. Professional reputation directly unlocks borrowing capacity.",
                   "warning":"Ego conflicts with lenders or bureaucracy delay approvals. Stay humble in loan processes.",
                   "remedy_planet":"Sun","funding_signal":"government_institutional"},
    ("Moon", 6):  {"domain":"finance","confidence":0.75,
                   "prediction":"Moon in the loan zone — borrowing capacity fluctuates with emotional cycles. Funding is reliably easier during stable, confident periods. Community lending, women-led investment, and crowdfunding are well-aligned channels.",
                   "warning":"Never take loans when emotionally distressed — terms negotiated in anxious states are consistently unfavorable.",
                   "remedy_planet":"Moon","funding_signal":"community_crowdfunding"},
    ("Mars", 6):  {"domain":"finance","confidence":0.80,
                   "prediction":"Mars in the loan zone — strong, aggressive borrowing capacity. Loans arrive through direct action, asset-backed security, or male-dominated industries. Real estate and infrastructure debt are natural fits.",
                   "warning":"Avoid loans for speculative ventures. Mars in 6H amplifies both debt gains and debt traps equally.",
                   "remedy_planet":"Mars","funding_signal":"asset_backed_loan"},
    ("Mercury", 6):{"domain":"finance","confidence":0.78,
                   "prediction":"Mercury in the loan zone — funding through documentation, contracts, and communication-heavy channels. Government grants, technology sector credit, and written-agreement-based capital work strongly for this placement.",
                   "warning":"Read every loan document word by word. Mercury in 6H punishes careless contract signing.",
                   "remedy_planet":"Mercury","funding_signal":"grant_documentation"},
    ("Jupiter", 6):{"domain":"finance","confidence":0.82,
                   "prediction":"Jupiter in the loan zone — institutional lenders favor you. Wisdom and reputation make banks and established financial institutions willing lenders. Borrowing capacity is real but requires disciplined repayment structures.",
                   "warning":"Never default on institutional debt — it permanently damages Jupiter's grace and future creditworthiness.",
                   "remedy_planet":"Jupiter","funding_signal":"institutional_loan"},
    ("Venus", 6):  {"domain":"finance","confidence":0.80,
                   "prediction":"Venus in the loan zone — borrowing arrives through partnerships and creative ventures. Funding channels include female connections, business co-founders, and industries in beauty, hospitality, arts, and luxury.",
                   "warning":"Never mix borrowed money with romantic relationships. Venus in 6H creates financial entanglement when heart and capital combine.",
                   "remedy_planet":"Venus","funding_signal":"relationship_partner_funding"},
    ("Saturn", 6): {"domain":"finance","confidence":0.82,
                   "prediction":"Saturn in the loan zone — loans and borrowed capital are achievable but arrive slowly with conditions attached. Banks will lend, but only after extensive due diligence. The delay is the mechanism, not a block — funding arrives after a demonstrated track record.",
                   "warning":"Do NOT rush loan applications before preparation is complete. Saturn in 6H rewards patience — the application made after proper groundwork nearly always succeeds.",
                   "remedy_planet":"Saturn","funding_signal":"delayed_institutional"},
    ("Rahu", 6):   {"domain":"finance","confidence":0.80,
                   "prediction":"Rahu in the loan zone — unconventional funding sources are the strength here. Foreign investors, non-traditional lenders, fintech credit, international grants, and tech-sector VCs align with this pattern. Rahu removes standard obstacles to borrowing through unconventional channels.",
                   "warning":"Read ALL fine print on Rahu-sourced loans. Unconventional lenders carry hidden clauses that surface at inconvenient moments.",
                   "remedy_planet":"Rahu","funding_signal":"foreign_unconventional_loan"},
    ("Ketu", 6):   {"domain":"finance","confidence":0.72,
                   "prediction":"Ketu in the loan zone — complex relationship with borrowed money. Loans arrive but often carry unexpected conditions. Prefer self-funding, revenue-based financing, or equity over traditional debt during active Ketu periods.",
                   "warning":"Avoid complex multi-party debt structures entirely. Keep borrowing simple, short-term, and meticulously documented.",
                   "remedy_planet":"Ketu","funding_signal":"avoid_complex_debt"},

    # ══════════════════════════════════════════════════════════
    # 8TH HOUSE NATAL — OPM: Investors, Inheritance, Joint Capital
    # 8H = OTHER PEOPLE'S MONEY: VC, angels, inheritance, joint ventures
    # Also governs: transformation, hidden matters, research, longevity
    # ══════════════════════════════════════════════════════════
    ("Sun", 8):    {"domain":"finance","confidence":0.75,
                   "prediction":"Sun in the OPM zone — government grants, public sector backing, and investment from established authority figures are the primary external capital channel. Professional authority and documented track record unlock institutional support.",
                   "warning":"Ego conflicts with investors or co-funders collapse deals. Remain genuinely open to shared control.",
                   "remedy_planet":"Sun","funding_signal":"authority_government_grant"},
    ("Moon", 8):   {"domain":"finance","confidence":0.78,
                   "prediction":"Moon in the OPM zone — access to external capital fluctuates with cycles. Investment arrives through emotional connection and community trust. Crowdfunding, consumer-facing brand investment, and community bonds are well-aligned. Investors who believe in you personally outperform institutional sources.",
                   "warning":"Investor relationships formed during emotionally turbulent periods are consistently unreliable. Wait for stable ground before pitching.",
                   "remedy_planet":"Moon","funding_signal":"community_consumer_funding"},
    ("Mars", 8):   {"domain":"finance","confidence":0.82,
                   "prediction":"Mars in the OPM zone — bold, competitive access to external capital. Asset-backed investment, real estate joint ventures, and inheritance through legal resolution are strong channels. Investors who value execution capacity and aggressive delivery timelines are the right match.",
                   "warning":"Disputes over shared resources or inheritance are likely without documentation. Formalize all joint financial arrangements in writing.",
                   "remedy_planet":"Mars","funding_signal":"competitive_asset_capital"},
    ("Mercury", 8):{"domain":"finance","confidence":0.82,
                   "prediction":"Mercury in the OPM zone — funding through intellectual property, data systems, and tech contracts. Investors who value analytical depth, communication infrastructure, and scalable knowledge systems are the right fit. Tech startup and IP-backed funding are strongly indicated.",
                   "warning":"Protect IP legally before pitching. Mercury in 8H creates vulnerability to idea appropriation without proper legal structures.",
                   "remedy_planet":"Mercury","funding_signal":"tech_ip_funding"},
    ("Jupiter", 8):{"domain":"finance","confidence":0.88,
                   "prediction":"Jupiter in the OPM zone — one of the strongest investor and inheritance placements. Other people's money flows toward wisdom, reputation, and trusted judgment. VC funding, angel investment, inheritance, and joint venture capital are all strongly indicated. Investors back credibility, not just the idea.",
                   "warning":"Never misuse investor trust. Jupiter in 8H applies severe karmic consequences for financial misrepresentation.",
                   "remedy_planet":"Jupiter","funding_signal":"investor_windfall"},
    ("Venus", 8):  {"domain":"finance","confidence":0.85,
                   "prediction":"Venus in the OPM zone — funding through partners, co-founders, and wealthy relationship networks. Inheritance from female family members and investment through business partnerships are strong channels. Real estate joint ventures and consumer-facing brand co-investments are particularly favored.",
                   "warning":"Separate personal and financial relationships clearly. Venus in 8H blurs lines that need to remain legally distinct.",
                   "remedy_planet":"Venus","funding_signal":"partner_cofounder_funding"},
    ("Saturn", 8): {"domain":"finance","confidence":0.80,
                   "prediction":"Saturn in the OPM zone — delayed but eventually substantial access to external capital. Patient institutional investors, family offices, and long-horizon funds are the match. Funding comes only after demonstrated longevity — investors must share a 5-10 year timeline.",
                   "warning":"Avoid fast-cycle investors entirely. They will consistently exit before value is realized, damaging the business.",
                   "remedy_planet":"Saturn","funding_signal":"patient_institutional_capital"},
    ("Rahu", 8):   {"domain":"finance","confidence":0.82,
                   "prediction":"Rahu in the OPM zone — sudden, unexpected access to large external capital. Foreign investors, cross-border funding rounds, unconventional equity structures, and windfall capital from unexpected sources. The money can arrive quickly and in unusual ways when timing aligns.",
                   "warning":"Vet ALL investors with extreme care. Rahu in 8H attracts both genuine windfalls and sophisticated fraudulent arrangements — the two are sometimes indistinguishable at the pitch stage.",
                   "remedy_planet":"Rahu","funding_signal":"sudden_foreign_capital"},
    ("Ketu", 8):   {"domain":"finance","confidence":0.72,
                   "prediction":"Ketu in the OPM zone — detached relationship with external capital. Windfalls and inheritance may arrive but carry unexpected complications. Mission-driven investors, impact funds, and purpose-aligned capital are the most natural match.",
                   "warning":"Standard profit-first investors create constant friction with Ketu in 8H. Align capital with purpose from the beginning.",
                   "remedy_planet":"Ketu","funding_signal":"mission_impact_funding"},

    # ══════════════════════════════════════════════════════════
    # 12TH HOUSE NATAL — Investments, Expenses, Foreign, Liberation
    # 12H = where money LEAVES and RETURNS from foreign/hidden channels
    # Also governs: foreign countries, bed pleasures, hospital, retreat
    # ══════════════════════════════════════════════════════════
    ("Sun", 12):   {"domain":"finance","confidence":0.72,
                   "prediction":"Sun in the investment/expenditure zone — money flows toward behind-the-scenes work, foreign markets, and institutional causes. Returns come from foreign connections and government-adjacent investments. Public visibility is lower but private financial work accumulates quietly.",
                   "warning":"Avoid spending on ego-driven projects with no financial return. Sun in 12H spends on status without proportional material gain.",
                   "remedy_planet":"Sun","investment_signal":"foreign_institutional"},
    ("Moon", 12):  {"domain":"finance","confidence":0.75,
                   "prediction":"Moon in the investment/expenditure zone — emotional spending patterns require conscious systems. Money flows toward home, nurturing, and private emotional needs. Foreign real estate, care-sector investments, and privacy-preserving expenditures yield quiet long-term returns. Cross-border activity is a natural financial channel.",
                   "warning":"Emotionally-driven spending is the primary financial risk. Build a pause mechanism before major expenditures.",
                   "remedy_planet":"Moon","investment_signal":"foreign_real_estate_care"},
    ("Mercury", 12):{"domain":"finance","confidence":0.78,
                   "prediction":"Mercury in the investment/expenditure zone — spending on information, communication systems, and foreign intellectual ventures. Returns from behind-the-scenes analysis, foreign tech work, and contractual arrangements abroad. Investments in media, software, or publishing with foreign exposure are aligned.",
                   "warning":"Foreign contracts need meticulous legal protection. Mercury in 12H is vulnerable to information theft and contract disputes across borders.",
                   "remedy_planet":"Mercury","investment_signal":"foreign_tech_media"},
    ("Jupiter", 12):{"domain":"finance","confidence":0.78,
                   "prediction":"Jupiter in the investment/expenditure zone — money flows generously toward spiritual causes, higher education, and foreign wisdom. Returns arrive slowly through dharmic investments, educational ventures, and foreign knowledge partnerships.",
                   "warning":"Avoid over-giving to causes at the expense of financial foundation. Jupiter in 12H creates genuine poverty through generosity without boundaries.",
                   "remedy_planet":"Jupiter","investment_signal":"education_spiritual_foreign"},
    ("Venus", 12): {"domain":"finance","confidence":0.80,
                   "prediction":"Venus in the investment/expenditure zone — spending on luxury and comfort is natural and recurring. Returns through foreign partnerships, hospitality abroad, beauty and arts investments, and relationship-driven cross-border business. A partner may be the source of key foreign financial connection.",
                   "warning":"Luxury spending can structurally exceed income without conscious systems. Venus in 12H requires budgeting discipline to prevent beautiful expenditures from draining long-term wealth.",
                   "remedy_planet":"Venus","investment_signal":"luxury_hospitality_foreign"},
    ("Saturn", 12):{"domain":"finance","confidence":0.82,
                   "prediction":"Saturn in the investment/expenditure zone — expenses and losses are deliberate teachers. Returns through service-based ventures, institutional investments abroad, and long-horizon discipline. The investment horizon is always long — 10+ year positions outperform short trades consistently.",
                   "warning":"Control expenditures as primary financial discipline. Never accumulate lifestyle debt.",
                   "remedy_planet":"Saturn","investment_signal":"long_horizon_service_foreign"},
    ("Rahu", 12):  {"domain":"finance","confidence":0.80,
                   "prediction":"Rahu in the investment/expenditure zone — strong foreign financial connections. Cross-border investments, foreign currency gains, immigration-linked financial activity, and unconventional investment vehicles are natural territory. What is being built in foreign markets is the actual financial story.",
                   "warning":"Hidden financial activity carries proportional legal risk. Ensure full regulatory compliance in all foreign structures.",
                   "remedy_planet":"Rahu","investment_signal":"foreign_unconventional_hidden"},

    # ══════════════════════════════════════════════════════════
    # KARAKA RULES FOR 6H / 8H / 12H — Soul-level finance signals
    # ══════════════════════════════════════════════════════════
    ("AK", 8):    {"domain":"finance","confidence":0.85,
                   "prediction":"Soul's core signal in the OPM zone — the soul's mission involves managing, stewarding, or transforming other people's resources. Investment capital, inheritance, or shared wealth is part of the karmic contract this lifetime."},
    ("AmK", 8):  {"domain":"finance","confidence":0.82,
                   "prediction":"Career path signal in the OPM zone — professional rise is directly tied to managing external capital. Fund management, investment advisory, venture building, or asset stewardship are the highest-aligned career expressions."},
    ("AmK", 6):  {"domain":"finance","confidence":0.78,
                   "prediction":"Career path signal in the loan zone — professional advancement comes through service, debt management, or resolving financial conflicts for others. Financial advisory, legal finance, or institutional lending roles carry high alignment."},
    ("GK", 12):  {"domain":"finance","confidence":0.82,
                   "prediction":"Obstacle energy in the investment/expenditure zone — hidden expenditures, unexpected losses, and foreign-related financial complications are recurring themes.",
                   "warning":"Maintain comprehensive insurance, emergency reserves, and meticulous documentation of all foreign financial arrangements.",
                   "is_pain_signal":True},

    # ══════════════════════════════════════════════════════════
    # 5TH HOUSE — Love, Romance, Speculation, Children
    # ══════════════════════════════════════════════════════════
    ("Sun", 5):    {"domain":"love","confidence":0.80,"prediction":"Sun in the romance zone — you attract partners through authority, recognition, and leadership. Love comes when you are most visible and accomplished. Ego-dominated relationships create separation.","warning":"Ego in romance creates power struggles. Lead with warmth, not dominance.","remedy_planet":"Sun","love_signal":"authority_attraction"},
    ("Moon", 5):   {"domain":"love","confidence":0.82,"prediction":"Moon in the romance zone — deeply emotional love affairs and strong attraction to nurturing partners. You fall in love through emotional connection first.","warning":"Emotional intensity can become possessiveness. Moon in 5H benefits from conscious boundaries.","remedy_planet":"Moon","love_signal":"emotional_romance"},
    ("Mars", 5):   {"domain":"love","confidence":0.80,"prediction":"Mars in the romance zone — intense, passionate love affairs. You pursue what you love with full force. Mars here also activates speculative energy — stock trading, sports betting, and high-risk ventures are active impulses.","warning":"Impulsive romantic decisions and speculative gambles both carry regret risk. Channel Mars into creative action rather than reckless bets.","remedy_planet":"Mars","love_signal":"passionate_pursuit","speculation_signal":"high_risk_active"},
    ("Mercury", 5):{"domain":"love","confidence":0.78,"prediction":"Mercury in the romance zone — intellectual connection is the foundation of attraction. You fall in love through conversation, wit, and shared ideas.","warning":"Overthinking romantic decisions creates distance. Trust feeling as well as analysis.","remedy_planet":"Mercury","love_signal":"intellectual_romance"},
    ("Jupiter", 5):{"domain":"love","confidence":0.85,"prediction":"Jupiter in the romance zone — one of the most blessed love placements. Generous, expansive romantic connections. Luck in creative speculation and investments. Children are especially blessed.","warning":"Over-idealization of partners creates disappointment when reality arrives.","remedy_planet":"Jupiter","love_signal":"blessed_romance","speculation_signal":"luck_active"},
    ("Venus", 5):  {"domain":"love","confidence":0.90,"prediction":"Venus in the romance zone — the most natural placement for love and romance. Highly magnetic to romantic partners. Love affairs are a central life theme. Beauty, arts, and creative expression are all favored.","warning":"Multiple romantic attractions can create instability. Venus in 5H requires choosing depth over variety.","remedy_planet":"Venus","love_signal":"magnetic_romance"},
    ("Saturn", 5): {"domain":"love","confidence":0.80,"prediction":"Saturn in the romance zone — love arrives late but lasts. Early romantic disappointments are Saturn's teaching, not sentence. Speculation and gambling are strongly contraindicated — Saturn in 5H consistently produces financial loss through speculative ventures.","warning":"AVOID ALL SPECULATION, GAMBLING, AND LOTTERY. Saturn in 5H makes speculative loss nearly certain and recurring. Invest only in slow, structured assets.","remedy_planet":"Saturn","love_signal":"delayed_lasting_love","speculation_signal":"avoid_permanently"},
    ("Rahu", 5):   {"domain":"love","confidence":0.78,"prediction":"Rahu in the romance zone — unconventional, cross-cultural, or taboo romantic attractions. Love with someone very different from family expectations. Speculation instincts are amplified — both wins and losses.","warning":"Speculative instincts are amplified but unreliable. Treat speculation as entertainment with a hard limit, not a wealth strategy.","remedy_planet":"Rahu","love_signal":"unconventional_romance","speculation_signal":"amplified_risky"},
    ("Ketu", 5):   {"domain":"love","confidence":0.75,"prediction":"Ketu in the romance zone — detached relationship with romance and speculation. Past-life romantic karmas are completing. Love connections feel karmic or fated.","warning":"Avoid speculation entirely during active Ketu periods. The karmic pattern here is release, not accumulation.","remedy_planet":"Ketu","love_signal":"karmic_romance","speculation_signal":"avoid_during_ketu"},

    # ══════════════════════════════════════════════════════════
    # 9TH HOUSE — Foreign Travel, Higher Luck, Dharma, Fortune
    # ══════════════════════════════════════════════════════════
    ("Sun", 9):    {"domain":"foreign","confidence":0.82,"prediction":"Sun in the fortune/foreign zone — authority and recognition in foreign countries. Government, law, and public sector work abroad are natural. Fortune follows visible leadership internationally.","remedy_planet":"Sun","foreign_signal":"authority_abroad"},
    ("Moon", 9):   {"domain":"foreign","confidence":0.80,"prediction":"Moon in the fortune/foreign zone — emotional connection to foreign cultures. You feel at home in foreign lands. International business, hospitality, and care-sector work abroad are aligned.","remedy_planet":"Moon","foreign_signal":"emotional_abroad"},
    ("Mars", 9):   {"domain":"foreign","confidence":0.80,"prediction":"Mars in the fortune/foreign zone — active, driven travel and foreign work. Physical industries, engineering, real estate, and defense-related international work are aligned.","remedy_planet":"Mars","foreign_signal":"active_foreign_work"},
    ("Mercury", 9):{"domain":"foreign","confidence":0.80,"prediction":"Mercury in the fortune/foreign zone — foreign languages, international publishing, cross-border communication, and education abroad. Writing and teaching in international contexts brings fortune.","remedy_planet":"Mercury","foreign_signal":"communication_abroad"},
    ("Jupiter", 9):{"domain":"foreign","confidence":0.90,"prediction":"Jupiter in the fortune/foreign zone — one of the most powerful placements for dharma, wisdom, and foreign fortune. International education, spiritual pilgrimage, law, and advisory work in foreign contexts all carry strong karmic support.","remedy_planet":"Jupiter","foreign_signal":"dharma_fortune_abroad"},
    ("Venus", 9):  {"domain":"foreign","confidence":0.85,"prediction":"Venus in the fortune/foreign zone — beauty, arts, luxury, and hospitality in international contexts. A foreign-connected partner is possible. Creative and diplomatic work abroad is highly favored.","remedy_planet":"Venus","foreign_signal":"creative_luxury_abroad"},
    ("Saturn", 9): {"domain":"foreign","confidence":0.82,"prediction":"Saturn in the fortune/foreign zone — slow, serious work abroad building lasting structures. Law, infrastructure, and institutional work in foreign countries. Fortune arrives later in life through disciplined foreign engagement.","remedy_planet":"Saturn","foreign_signal":"structured_delayed_abroad"},
    ("Rahu", 9):   {"domain":"foreign","confidence":0.82,"prediction":"Rahu in the fortune/foreign zone — powerful pull toward foreign cultures, unconventional spiritual paths, and cross-border work. Strong material fortune through foreign connections. Immigration and long-term relocation are recurring possibilities.","warning":"Foreign engagements activated by Rahu carry hidden complications — visa issues, cultural friction, or commitments harder to exit than to enter.","remedy_planet":"Rahu","foreign_signal":"unconventional_fortune_abroad"},
    ("Ketu", 9):   {"domain":"foreign","confidence":0.75,"prediction":"Ketu in the fortune/foreign zone — past-life connection to foreign lands and spiritual knowledge. A mysterious pull toward ancient traditions and places that feel strangely familiar. Material fortune from foreign sources is possible but not the primary gift.","remedy_planet":"Ketu","foreign_signal":"spiritual_karmic_abroad"},

    # ══════════════════════════════════════════════════════════
    # DIVORCE / SEPARATION — 7H stress & Mangal Dosh signals
    # ══════════════════════════════════════════════════════════
    ("Sun", 7):    {"domain":"marriage","confidence":0.75,"prediction":"Sun in the partnership zone — ego-driven relationships where partnership mirrors your authority and identity. Separation risk increases when power becomes the primary dynamic rather than mutual respect.","warning":"Do NOT dominate your partner. Sun in 7H teaches through relationship — resistance to this lesson is what creates separation.","remedy_planet":"Sun","divorce_signal":"ego_power_dynamic"},
    ("Rahu", 7):   {"domain":"marriage","confidence":0.78,"prediction":"Rahu in the partnership zone — karmic, unusual, or cross-cultural partnerships with strong initial attraction and hidden complications. Relationship instability increases if the karmic lesson goes unlearned.","warning":"Ensure relationship foundations are built on genuine compatibility, not just intensity or novelty.","remedy_planet":"Rahu","divorce_signal":"karmic_instability"},
    ("Ketu", 7):   {"domain":"marriage","confidence":0.72,"prediction":"Ketu in the partnership zone — detached relationship with conventional partnership. Relationships feel karmic and completing. Emotional withdrawal is the primary risk pattern.","warning":"Partnership requires presence — build deliberate emotional availability practices.","remedy_planet":"Ketu","divorce_signal":"detachment_pattern"},

    # ══════════════════════════════════════════════════════════
    # WEALTH ACCUMULATION — H2, H11 (positive wealth signals)
    # ══════════════════════════════════════════════════════════
    ("Venus", 2):  {"domain":"wealth","confidence":0.82,"prediction":"Venus in the wealth zone — beautiful accumulation of assets, luxury goods, and artistic wealth. Family wealth and aesthetic investments are favorable. Income through beauty, arts, and relationships.","remedy_planet":"Venus","wealth_signal":"aesthetic_wealth"},
    ("Mars", 2):   {"domain":"wealth","confidence":0.80,"prediction":"Mars in the wealth zone — aggressive, bold wealth accumulation through real estate, construction, manufacturing, and physical industries. Wealth comes through action and ownership.","warning":"Impulsive financial decisions and aggression in money matters can create loss. Control speech around money.","remedy_planet":"Mars","wealth_signal":"aggressive_accumulation"},
    ("Mercury", 2):{"domain":"wealth","confidence":0.80,"prediction":"Mercury in the wealth zone — wealth through business, communication, and intellectual trade. Multiple income streams are natural. Trading, consulting, and information businesses are primary channels.","warning":"Do not deceive in financial dealings — Mercury in 2H punishes dishonesty through financial reversals.","remedy_planet":"Mercury","wealth_signal":"intellectual_trade"},
    ("Saturn", 2): {"domain":"wealth","confidence":0.82,"prediction":"Saturn in the wealth zone — slow, disciplined, delayed but eventually substantial wealth. Frugality and systematic saving outperform all speculation for this placement. Wealth builds in the second half of life.","warning":"Do NOT pursue quick wealth schemes or speculation. Saturn in 2H makes get-rich-quick attempts nearly always end in loss.","remedy_planet":"Saturn","wealth_signal":"slow_disciplined","speculation_signal":"avoid_strongly"},
    ("Rahu", 2):   {"domain":"wealth","confidence":0.78,"prediction":"Rahu in the wealth zone — unconventional wealth channels, foreign income, and technology-related gains. Income is irregular and often sudden. Rahu creates both unexpected windfalls and unexpected financial voids.","warning":"Never speculate with borrowed money when Rahu is in 2H. Losses are amplified.","remedy_planet":"Rahu","wealth_signal":"unconventional_irregular"},
    ("Ketu", 2):   {"domain":"wealth","confidence":0.72,"prediction":"Ketu in the wealth zone — complex, detached relationship with material accumulation. Money comes but is held loosely. Spiritual richness over material focus is the karmic teaching.","warning":"Wealth hoarding creates karmic friction. Ketu in 2H benefits from conscious giving.","remedy_planet":"Ketu","wealth_signal":"detached_giving"},
    ("Sun", 11):   {"domain":"wealth","confidence":0.80,"prediction":"Sun in the gains zone — income through government, authority, and public recognition. Networks of powerful individuals are the primary wealth channel.","remedy_planet":"Sun","wealth_signal":"authority_network_gains"},
    ("Mars", 11):  {"domain":"wealth","confidence":0.82,"prediction":"Mars in the gains zone — strong income through physical industries, real estate, engineering, and competitive fields. Desires are fulfilled through bold action.","remedy_planet":"Mars","wealth_signal":"competitive_gains"},
    ("Saturn", 11):{"domain":"wealth","confidence":0.82,"prediction":"Saturn in the gains zone — delayed but significant income gains. The gains in the second half of career are disproportionately large compared to slow early accumulation.","remedy_planet":"Saturn","wealth_signal":"delayed_large_gains"},
    ("Mercury", 11):{"domain":"wealth","confidence":0.82,"prediction":"Mercury in the gains zone — multiple income streams, business network gains, and intellectual property income. Your ideas and communication skills are the primary wealth channel.","remedy_planet":"Mercury","wealth_signal":"multiple_streams"},
    ("Moon", 11):  {"domain":"wealth","confidence":0.82,"prediction":"Moon in the gains zone — income from nurturing others and networks built on trust. Gains come through relationships and emotional intelligence.","warning":"Don't mix emotions with financial dealings.","remedy_planet":"Moon","wealth_signal":"trust_network_gains"},

    # ══════════════════════════════════════════════════════════
    # LOSS SIGNALS — Financial drain indicators
    # ══════════════════════════════════════════════════════════
}


# ═══════════════════════════════════════════════════════════════
# JAIMINI KARAKA RULES
# ═══════════════════════════════════════════════════════════════

JAIMINI_KARAKA_RULES = {
    ("AK", 1):  {"domain":"spiritual","confidence":0.88,"prediction":"Soul's mission is self-mastery and identity. Personal growth IS the dharma — your presence itself is the teaching."},
    ("AK", 4):  {"domain":"family","confidence":0.85,"prediction":"Soul grows through home, mother, and emotional rootedness. Creating a sanctuary is core to your dharma."},
    ("AK", 7):  {"domain":"marriage","confidence":0.88,"prediction":"Soul grows through relationship. Partnership is not optional — it is the soul's curriculum. Choose your partner as you would choose your teacher."},
    ("AK", 9):  {"domain":"spiritual","confidence":0.90,"prediction":"Soul's mission is dharma, wisdom, and higher teaching. You are meant to be a teacher or guide in some form."},
    ("AK", 10): {"domain":"career","confidence":0.90,"prediction":"Soul's purpose and career are the same path. Work is not separate from dharma. What you do professionally must feel like a calling."},
    ("AK", 12): {"domain":"spiritual","confidence":0.88,"prediction":"Soul seeks liberation and spiritual depth. Meditation, service, and withdrawal from ego-driven ambition are your highest path."},
    ("AmK", 1): {"domain":"career","confidence":0.85,"prediction":"Career path signal in 1st — your personality IS your career strategy. Personal brand and authentic self-expression drive professional outcomes."},
    ("AmK", 7): {"domain":"career","confidence":0.85,"prediction":"Career rises through partnerships and collaborations. Professional success is tied to who you align with."},
    ("AmK", 9): {"domain":"career","confidence":0.88,"prediction":"Career in teaching, publishing, law, spirituality, or foreign work is indicated. Higher education directly advances professional standing."},
    ("AmK", 10):{"domain":"career","confidence":0.92,"prediction":"Career path signal in 10th — Jaimini's strongest indicator for career success and public recognition. Professional rise is written clearly in the chart."},
    ("AmK", 11):{"domain":"wealth","confidence":0.85,"prediction":"Career brings steady gains. Professional network is a direct income source. Multiple income streams through expertise are indicated."},
    ("DK", 1):  {"domain":"marriage","confidence":0.80,"prediction":"Marriage significator in 1st — spouse mirrors your own qualities. The partnership is a profound personal development journey."},
    ("DK", 7):  {"domain":"marriage","confidence":0.88,"prediction":"Natural and strong marriage placement. Partnership brings stability, status, and mutual support."},
    ("DK", 9):  {"domain":"marriage","confidence":0.82,"prediction":"Spouse may be deeply philosophical, spiritual, or from a different background. Marriage expands your worldview."},
    ("DK", 12): {"domain":"marriage","confidence":0.80,"prediction":"Spouse may come from foreign place or very different background. Marriage has a spiritual or karmic quality."},
    # GK — THE PAIN GIVER — always flag this
    ("GK", 2):  {"domain":"wealth","confidence":0.82,"prediction":"Obstacle energy in wealth zone — income faces competition, legal disputes, or family interference. Financial documentation is essential.","warning":"Never skip legal formalities in financial dealings. Protect assets formally.","is_pain_signal":True},
    ("GK", 6):  {"domain":"health","confidence":0.80,"prediction":"Obstacle energy in health/conflict zone — workplace conflicts and health issues require conscious management.","warning":"Don't ignore health signals. Proactive medical checkups are protective.","is_pain_signal":True},
    ("GK", 7):  {"domain":"marriage","confidence":0.82,"prediction":"Obstacle energy in partnership zone — competition or interference in key relationships. Vet partners carefully.","warning":"Legal and formal agreements in all partnerships are essential.","is_pain_signal":True},
    ("GK", 8):  {"domain":"health","confidence":0.85,"prediction":"Obstacle energy in transformation zone — health crises, sudden changes, or legal/inheritance complications are possible.","warning":"Regular medical checkups and comprehensive insurance are protective. Maintain legal documents.","is_pain_signal":True},
    ("GK", 10): {"domain":"career","confidence":0.82,"prediction":"Obstacle energy in career zone — competition, enemies in workplace, or sudden career disruptions. Build strong documentation and professional alliances.","warning":"Don't take shortcuts. Competition in career is intense — excellence is the only protection.","is_pain_signal":True},
    ("GK", 11): {"domain":"wealth","confidence":0.80,"prediction":"Obstacle energy in gains zone — misplaced trust or betrayal within your own network can disrupt income.","warning":"Never mix deep friendship with business without written agreements.","is_pain_signal":True},
    ("PK", 1):  {"domain":"family","confidence":0.80,"prediction":"Legacy signal in 1st — what you create personally is your most enduring contribution. Children or creative works carry your identity forward."},
    ("PK", 5):  {"domain":"family","confidence":0.85,"prediction":"Strong indication of children and creative legacy. Your children or creative works will carry forward what you've built."},
    ("MK", 4):  {"domain":"family","confidence":0.85,"prediction":"Mother is the most significant figure in your emotional development. Property and home life are tied to her blessings."},
}


# ═══════════════════════════════════════════════════════════════
# DASHA ACTIVATION RULES
# ═══════════════════════════════════════════════════════════════

DASHA_ACTIVATION_RULES = {
    ("Sun", 1):    {"domain":"career","confidence":0.85,"prediction":"Authority, recognition, and identity come powerfully to the fore. Government, leadership, and public roles surface."},
    ("Sun", 10):   {"domain":"career","confidence":0.90,"prediction":"Peak career recognition period. Government, leadership, and public authority are at maximum strength."},
    ("Moon", 4):   {"domain":"family","confidence":0.82,"prediction":"Emotional focus on home, mother, and real estate. Property matters are highlighted."},
    ("Moon", 11):  {"domain":"wealth","confidence":0.82,"prediction":"Gains through networks, elder connections, and emotionally intelligent work."},
    ("Mars", 10):  {"domain":"career","confidence":0.88,"prediction":"Peak ambition and career drive. Leadership roles and bold professional moves are available."},
    ("Mercury", 1):{"domain":"career","confidence":0.82,"prediction":"Communication, business, writing, and networking define this period. Your words carry unusual weight."},
    ("Mercury", 10):{"domain":"career","confidence":0.88,"prediction":"Business, media, communications, and intellectual work are highlighted."},
    ("Jupiter", 1):{"domain":"general","confidence":0.88,"prediction":"Expansion of personality, wisdom, and opportunity across all life areas. A period of genuine grace and growth."},
    ("Jupiter", 11):{"domain":"wealth","confidence":0.88,"prediction":"One of the strongest gain periods. Income expands, desires are fulfilled, network brings significant opportunities."},
    ("Venus", 11): {"domain":"wealth","confidence":0.85,"prediction":"Income from beauty, art, and relationships. Your network brings financial opportunity."},
    ("Saturn", 10):{"domain":"career","confidence":0.90,"prediction":"Pinnacle career-building period. Slow but exceptional results. Hard honest work now creates a legacy that outlasts the dasha by decades."},
    ("Rahu", 10):  {"domain":"career","confidence":0.85,"prediction":"Sudden career acceleration. Foreign opportunities and unconventional roles bring unexpected advancement."},
    ("Ketu", 11):  {"domain":"spiritual","confidence":0.80,"prediction":"Detachment from material gains brings spiritual richness. Income fluctuates; inner clarity increases."},

    # ── Dasha activations for 6H/8H/12H (finance-aware) ────────────
    ("Saturn", 6): {"domain":"finance","confidence":0.82,"prediction":"Saturn dasha activating loan zone — a multi-year window for building institutional credit and borrowing capacity. Patience in this dasha converts directly into fundable track record. Loan applications made toward the end of this period carry the strongest approval signals.","funding_signal":"institutional_credit_building"},
    ("Jupiter", 6):{"domain":"finance","confidence":0.80,"prediction":"Jupiter dasha activating loan zone — generous borrowing window. Institutional lenders, banks, and government grant programs are favorable. Legal matters move in favor. Service and advisory roles also open.","funding_signal":"institutional_loan_window"},
    ("Rahu", 6):   {"domain":"finance","confidence":0.78,"prediction":"Rahu dasha activating loan zone — unconventional funding sources, foreign credit, and alternative capital channels are the primary path. Hidden workplace complications may surface simultaneously.","warning":"Read all loan fine print during Rahu dasha. Unconventional lenders carry hidden terms.","funding_signal":"foreign_unconventional_loan"},
    ("Jupiter", 8):{"domain":"finance","confidence":0.88,"prediction":"Jupiter dasha activating OPM zone — one of the most powerful dasha configurations for external capital. Investor funding, angel capital, inheritance, and joint venture money flows toward wisdom and credibility. This dasha window should be maximally utilized for funding outreach.","funding_signal":"investor_windfall"},
    ("Venus", 8):  {"domain":"finance","confidence":0.85,"prediction":"Venus dasha activating OPM zone — partner-driven funding, co-founder capital, inheritance from female connections, and real estate joint ventures are the primary external capital channels.","funding_signal":"partner_cofounder_funding"},
    ("Rahu", 8):   {"domain":"finance","confidence":0.82,"prediction":"Rahu dasha activating OPM zone — sudden, unexpected external capital. Foreign investors and unconventional equity structures are the channels. The funding can arrive quickly and in unusual ways.","warning":"Vet all investors during Rahu dasha. Both genuine windfalls and sophisticated fraud are activated.","funding_signal":"sudden_foreign_capital"},
    ("Saturn", 8): {"domain":"finance","confidence":0.80,"prediction":"Saturn dasha activating OPM zone — patient institutional capital is available but requires extensive due diligence. Long-horizon investors are the match. Funding comes only after demonstrated longevity.","funding_signal":"patient_institutional_capital"},
    ("Moon", 6):   {"domain":"finance","confidence":0.72,"prediction":"Moon dasha activating loan zone — community-based funding, emotionally-driven credit, and women-led investment are the channels. Emotional stability directly correlates with financial stability throughout this dasha.","funding_signal":"community_crowdfunding"},
    ("Moon", 8):   {"domain":"finance","confidence":0.75,"prediction":"Moon dasha activating OPM zone — consumer trust and emotional connection drive investor relationships. Community crowdfunding and consumer-facing brand investment are the aligned external capital channels.","funding_signal":"community_consumer_funding"},
    ("Mercury", 6):{"domain":"finance","confidence":0.75,"prediction":"Mercury dasha activating loan zone — grant applications, written loan documentation, and technology sector credit are the strongest channels. Contracts and written agreements with lenders carry unusual traction.","funding_signal":"grant_documentation"},
    ("Mercury", 8):{"domain":"finance","confidence":0.80,"prediction":"Mercury dasha activating OPM zone — IP deals, tech funding, and analytically-driven investor pitches carry strong momentum. Data-driven businesses and communication infrastructure attract capital.","funding_signal":"tech_ip_funding"},
    ("Mercury", 12):{"domain":"finance","confidence":0.75,"prediction":"Mercury dasha activating expenditure zone — foreign tech contracts, cross-border media, and intellectual property work abroad are activated. Communication-related expenditures are elevated.","investment_signal":"foreign_tech_media"},
    ("Venus", 6):  {"domain":"finance","confidence":0.78,"prediction":"Venus dasha activating loan zone — partnership-backed credit, co-founder funding discussions, and relationship-driven borrowing are the aligned channels.","funding_signal":"relationship_partner_funding"},
    ("Venus", 12): {"domain":"finance","confidence":0.78,"prediction":"Venus dasha activating expenditure zone — luxury spending is natural and recurring. Foreign partnerships, hospitality abroad, and consumer-brand investments are the financial channels.","investment_signal":"luxury_hospitality_foreign"},

    # ── Dasha activations: Love / Romance ────────────────────────────────
    ("Venus", 1):  {"domain":"love","confidence":0.90,"prediction":"Venus dasha activating the ascendant — beauty, love, and romantic energy are fully embodied. This is one of the most powerful dashas for romantic connection, marriage proposals, and creative partnerships. The magnetism is high.","love_signal":"peak_romance_dasha"},
    ("Venus", 5):  {"domain":"love","confidence":0.90,"prediction":"Venus dasha activating the romance zone — the most auspicious dasha for love affairs, romantic fulfillment, and creative expression. If seeking love, this dasha is the window. If in a relationship, this deepens it significantly.","love_signal":"romance_fulfillment_dasha"},
    ("Venus", 7):  {"domain":"love","confidence":0.92,"prediction":"Venus dasha activating the partnership zone — peak dasha for marriage and committed partnership formation. The most consistently reliable indicator for marriage in Vedic timing. Deeply favorable for both romantic and business partnerships.","love_signal":"marriage_prime_dasha"},
    ("Moon", 5):   {"domain":"love","confidence":0.82,"prediction":"Moon dasha activating the romance zone — emotionally rich love experiences, deep romantic connections, and heightened creative sensitivity. Relationships formed in this dasha carry strong emotional depth and family orientation.","love_signal":"emotional_romance_dasha"},
    ("Jupiter", 7):{"domain":"love","confidence":0.88,"prediction":"Jupiter dasha activating the partnership zone — blessed, wisdom-driven partnerships. Marriage in this dasha carries philosophical depth and genuine growth. Jupiter expands and protects committed relationships.","love_signal":"blessed_partnership_dasha"},
    ("Jupiter", 5):{"domain":"love","confidence":0.85,"prediction":"Jupiter dasha activating the romance zone — expansive, joyful romantic experiences. Luck in love, creative ventures, and children. Relationships formed here are often karmic and growth-oriented.","love_signal":"expansive_romance_dasha"},
    ("Mars", 5):   {"domain":"love","confidence":0.80,"prediction":"Mars dasha activating the romance zone — intense, passionate, physically driven romantic energy. Bold pursuit of love interests. Simultaneously: speculative impulses are elevated. Pursue love boldly; pursue speculation cautiously.","love_signal":"passionate_love_dasha","speculation_signal":"impulsive_risk_dasha"},
    ("Rahu", 7):   {"domain":"love","confidence":0.78,"prediction":"Rahu dasha activating the partnership zone — sudden, karmic, or cross-cultural romantic connections. Unexpected relationship developments. Attractions are intense and often transformative. Cross-cultural or inter-faith relationships are common.","love_signal":"karmic_attraction_dasha"},

    # ── Dasha activations: Divorce / Separation ──────────────────────────
    ("Mars", 7):   {"domain":"divorce","confidence":0.82,"prediction":"Mars dasha activating the partnership zone (Mangal Dosh activated) — intensity and conflict in relationships are at maximum. The partnership is being tested. What survives this dasha is genuinely resilient. Couples counseling is strongly protective.","warning":"Do not make permanent relationship decisions during the heat of Mars dasha conflict. The energy is temporary; decisions are permanent.","divorce_signal":"mangal_test_dasha","is_pain_signal":True},
    ("Saturn", 7): {"domain":"divorce","confidence":0.85,"prediction":"Saturn dasha activating the partnership zone — karmic relationship evaluation. Inauthentic partnerships face serious strain or ending. Authentic partnerships are deepened through shared difficulty. This dasha separates what was duty-based from what was love-based.","warning":"Do not rush separation decisions in Saturn dasha. Let the full cycle complete before concluding. What feels like ending may be restructuring.","divorce_signal":"karmic_evaluation_dasha"},
    ("Ketu", 7):   {"domain":"divorce","confidence":0.78,"prediction":"Ketu dasha activating the partnership zone — spiritual detachment from conventional relationship structures. Some relationships reach karmic completion during this dasha. A desire for solitude or non-conventional partnership arrangements is natural.","divorce_signal":"spiritual_detachment_dasha"},
    ("Rahu", 1):   {"domain":"divorce","confidence":0.72,"prediction":"Rahu dasha activating the ascendant — identity disruption can spill into partnerships. Unconventional life choices may create friction in conventional relationships. Not a separation indicator alone, but a signal to consciously tend to relationship foundations.","divorce_signal":"identity_disruption_risk"},

    # ── Dasha activations: Foreign Travel / Abroad ───────────────────────
    ("Jupiter", 9):{"domain":"foreign","confidence":0.90,"prediction":"Jupiter dasha activating the fortune/foreign zone — the most powerful dasha period for foreign education, spiritual pilgrimage, international opportunity, and dharmic work abroad. Immigration decisions made in this dasha carry long-term positive outcomes.","foreign_signal":"dharma_fortune_dasha"},
    ("Rahu", 9):   {"domain":"foreign","confidence":0.82,"prediction":"Rahu dasha activating the fortune/foreign zone — strong foreign pull throughout this dasha period. Cross-border work, immigration, and unconventional international paths are activated. Material fortune through foreign connections is strong.","warning":"Foreign commitments carry hidden complications in Rahu dasha. Vet all international agreements thoroughly.","foreign_signal":"unconventional_foreign_dasha"},
    ("Rahu", 12):  {"domain":"foreign","confidence":0.80,"prediction":"Rahu dasha activating the foreign/loss zone — a sustained period of foreign financial connections and cross-border activity. Immigration, foreign work, and cross-border investments are activated throughout this dasha.","foreign_signal":"cross_border_dasha"},
    ("Venus", 9):  {"domain":"foreign","confidence":0.85,"prediction":"Venus dasha activating the fortune/foreign zone — beauty, arts, luxury, and diplomacy in international contexts. A foreign partner is possible. Creative work and travel abroad yield genuine rewards.","foreign_signal":"creative_foreign_dasha"},
    ("Saturn", 9): {"domain":"foreign","confidence":0.82,"prediction":"Saturn dasha activating the fortune/foreign zone — slow, serious, structured foreign work. Law, infrastructure, and institutional roles abroad. Fortune arrives in the second half of this dasha period through patient foreign engagement.","foreign_signal":"structured_foreign_dasha"},
    ("Mercury", 9):{"domain":"foreign","confidence":0.80,"prediction":"Mercury dasha activating the fortune/foreign zone — foreign communication, publishing, education, and international intellectual work. Multiple foreign connections and language-related opportunities.","foreign_signal":"intellectual_foreign_dasha"},
    ("Moon", 9):   {"domain":"foreign","confidence":0.78,"prediction":"Moon dasha activating the fortune/foreign zone — emotional connection to foreign cultures and places. Frequent travel, especially to water-adjacent locations. International business in hospitality, food, and care sectors.","foreign_signal":"emotional_travel_dasha"},

    # ── Dasha activations: Speculation ───────────────────────────────────
    ("Rahu", 5):   {"domain":"speculation","confidence":0.80,"prediction":"Rahu dasha activating the speculation zone — amplified speculative instincts and sudden financial events throughout this dasha period. Variance is maximum — wins can be spectacular but losses equally so.","warning":"Set hard position limits on ALL speculative activity during Rahu dasha in 5H. The intelligence that makes you think you can beat the system is itself the Rahu illusion.","speculation_signal":"maximum_variance_dasha"},
    ("Saturn", 5): {"domain":"speculation","confidence":0.88,"prediction":"Saturn dasha activating the speculation zone — the clearest sustained prohibition on speculative activity in Vedic timing. Any gambling, lottery, or high-risk trading during Saturn dasha in 5H consistently produces financial loss.","warning":"AVOID ALL SPECULATION THROUGHOUT SATURN DASHA. This is non-negotiable. The protection here is the rule itself — every deviation from it will be financially costly.","speculation_signal":"avoid_entire_dasha"},

    # ── Dasha activations: Loss / Financial Drain ────────────────────────
    ("Saturn", 12):{"domain":"loss","confidence":0.82,"prediction":"Saturn dasha activating the loss/liberation zone — sustained period of elevated expenses, hidden costs, and financial discipline requirements. Service-based foreign ventures and long-horizon investments begun now convert loss-energy into future structural gain.","loss_signal":"sustained_expense_dasha"},
    ("Mars", 12):  {"domain":"loss","confidence":0.78,"prediction":"Mars dasha activating the loss zone — hidden expenditures are large, sudden, and often related to foreign or behind-the-scenes activity. Control all financial outflows actively. Never lend money during this dasha.","warning":"Do NOT lend money during Mars dasha in 12H. The loss is near-certain.","loss_signal":"sudden_loss_dasha"},
    ("Moon", 12):  {"domain":"loss","confidence":0.72,"prediction":"Moon dasha activating the loss zone — emotional financial decisions are the primary loss pattern. Unconscious spending, emotionally-driven commitments, and nurturing others at financial cost to yourself are recurring themes.","warning":"Build systematic spending controls before this dasha begins. The protection is systems, not willpower.","loss_signal":"emotional_loss_dasha"},
    ("Ketu", 12):  {"domain":"loss","confidence":0.75,"prediction":"Ketu dasha activating the liberation/loss zone — karmic expenditures complete their cycle. Apparent losses are karmic releases. Spiritual and non-material investments are the highest use of this dasha energy.","loss_signal":"karmic_release_dasha"},
}


# ═══════════════════════════════════════════════════════════════
# TRANSIT TRIGGER RULES — Standard transits
# ═══════════════════════════════════════════════════════════════

TRANSIT_TRIGGER_RULES = {
    ("Jupiter", 1): {"domain":"general","confidence":0.90,"prediction":"Jupiter transiting your rising — expansion, protection, and new beginnings. Health improves. Opportunities multiply.","timeframe":"~12 months"},
    ("Jupiter", 2): {"domain":"wealth","confidence":0.85,"prediction":"Jupiter transiting wealth zone — income expands, family relationships improve, speech carries more influence.","timeframe":"~12 months"},
    ("Jupiter", 5): {"domain":"career","confidence":0.85,"prediction":"Jupiter transiting creativity zone — ideas flow, recognition of intellect peaks, speculative ventures favored.","timeframe":"~12 months"},
    ("Jupiter", 7): {"domain":"marriage","confidence":0.88,"prediction":"Jupiter transiting partnership zone — marriage and business partnerships receive grace. Existing relationships deepen.","timeframe":"~12 months"},
    ("Jupiter", 9): {"domain":"spiritual","confidence":0.88,"prediction":"Jupiter transiting dharma zone — a spiritually rich year. Higher education, foreign travel, mentors available.","timeframe":"~12 months"},
    ("Jupiter", 10):{"domain":"career","confidence":0.92,"prediction":"Jupiter transiting career zone — one of the strongest annual indicators for professional advancement and recognition.","timeframe":"~12 months"},
    ("Jupiter", 11):{"domain":"wealth","confidence":0.90,"prediction":"Jupiter transiting gains zone — significant income increase, fulfilment of desires, network expansion.","timeframe":"~12 months"},
    ("Saturn", 1):  {"domain":"health","confidence":0.85,"prediction":"Saturn transiting rising sign — identity restructuring and life reassessment. Hard disciplined work now builds unshakeable foundation.","warning":"Prioritize health and avoid overexertion.","timeframe":"~2.5 years"},
    ("Saturn", 4):  {"domain":"family","confidence":0.82,"prediction":"Saturn transiting home zone — property decisions, family restructuring, or change of residence likely.","timeframe":"~2.5 years"},
    ("Saturn", 8):  {"domain":"health","confidence":0.80,"prediction":"Saturn transiting transformation zone — deep psychological and physical changes. Investigations and legal matters may surface. This is a restructuring period, not a crisis.","warning":"Proactive health management and legal documentation are protective during this transit.","timeframe":"~2.5 years"},
    ("Saturn", 10): {"domain":"career","confidence":0.88,"prediction":"Saturn transiting career zone — serious, productive career period. Responsibilities increase. Hard honest work is directly rewarded.","timeframe":"~2.5 years"},
    ("Saturn", 12): {"domain":"spiritual","confidence":0.80,"prediction":"Saturn transiting liberation zone — preparation for Sade Sati. Expenses increase. Spiritual practice brings the most value now.","timeframe":"~2.5 years"},
    ("Rahu", 1):    {"domain":"general","confidence":0.82,"prediction":"Rahu transiting rising sign — identity disruption and transformation. Unconventional choices define this period.","timeframe":"~18 months"},
    ("Rahu", 7):    {"domain":"marriage","confidence":0.82,"prediction":"Rahu transiting partnership zone — unusual, karmic, or sudden relationship developments. Be discerning about new partnerships.","timeframe":"~18 months"},
    ("Rahu", 10):   {"domain":"career","confidence":0.85,"prediction":"Rahu transiting career zone — sudden rise or unexpected career changes. Foreign and unconventional paths to success highlighted.","timeframe":"~18 months"},
    ("Ketu", 1):    {"domain":"spiritual","confidence":0.80,"prediction":"Ketu transiting rising sign — spiritual awakening and identity detachment. Who you thought you were is being refined.","timeframe":"~18 months"},
    ("Ketu", 4):    {"domain":"family","confidence":0.78,"prediction":"Ketu transiting home zone — detachment from home and roots. Relocation possible.","timeframe":"~18 months"},
    ("Ketu", 7):    {"domain":"marriage","confidence":0.80,"prediction":"Ketu transiting partnership zone — karmic completions in relationships. Some connections release; those that remain are purified.","timeframe":"~18 months"},
}

# ═══════════════════════════════════════════════════════════════
# 6H / 8H / 12H TRANSIT RULES — Dushtana houses (v4 — finance-aware)
# Each planet transiting 6H/8H/12H fires multi-domain signals:
#   6H = loan capacity window / health / conflict
#   8H = OPM/investor window / transformation / inheritance
#   12H = investment/expense surge / foreign gains / liberation
# ═══════════════════════════════════════════════════════════════

DUSHTANA_TRANSIT_RULES = {
    # ── 6H TRANSITS — Loan window + health/conflict ──────────────────
    ("Sun", 6):     {"domain":"finance","confidence":0.75,
                     "prediction":"Sun transiting the loan/service zone — a window for government-backed funding, institutional grants, and authority-linked credit. Simultaneously: workplace tensions and health fluctuations are elevated. Use the authority signal to advance funding applications; manage health and conflict proactively.",
                     "warning":"Ego conflicts with lenders or bureaucracy delay approvals during this window.",
                     "funding_signal":"government_institutional_window",
                     "timeframe":"~1 month","rarity":"common"},
    ("Moon", 6):    {"domain":"finance","confidence":0.72,
                     "prediction":"Moon transiting the loan zone — a brief window where community-based funding, women-led investment, and relationship-driven credit are accessible. Emotionally stable days within this transit are the best days to initiate funding conversations.",
                     "warning":"Avoid signing loan documents on emotionally volatile days during this transit.",
                     "funding_signal":"community_funding_window",
                     "timeframe":"~2.5 days","rarity":"common"},
    ("Mars", 6):    {"domain":"finance","confidence":0.78,
                     "prediction":"Mars transiting the conflict/loan zone — aggressive borrowing capacity is activated. Asset-backed loans and real estate debt move quickly in this window. Simultaneously: accident risk and workplace disputes are elevated.",
                     "warning":"Avoid impulsive confrontations. Extra care with fire, sharp objects, vehicles.",
                     "funding_signal":"asset_loan_window",
                     "timeframe":"~6 weeks","rarity":"common"},
    ("Mercury", 6): {"domain":"finance","confidence":0.75,
                     "prediction":"Mercury transiting the loan zone — excellent window for finalizing loan documentation, grant applications, and financial contracts. Written communication with lenders and financial institutions carries unusual traction now.",
                     "warning":"Read every document carefully — Mercury in 6H transit accelerates both signings and errors.",
                     "funding_signal":"documentation_grant_window",
                     "timeframe":"~3 weeks","rarity":"common"},
    ("Jupiter", 6): {"domain":"finance","confidence":0.80,
                     "prediction":"Jupiter transiting the loan/service zone — one of the strongest annual windows for institutional borrowing. Banks and established lenders are more receptive. Legal matters move in your favor. Service and advisory opportunities open simultaneously.",
                     "warning":"Do not over-borrow during Jupiter's generosity window — what Jupiter gives easily, Saturn later asks to repay.",
                     "funding_signal":"institutional_loan_window",
                     "timeframe":"~12 months","rarity":"notable"},
    ("Venus", 6):   {"domain":"finance","confidence":0.75,
                     "prediction":"Venus transiting the loan zone — funding through partnerships, creative ventures, and relationship-based channels is activated. Co-founder discussions and partnership-backed credit work well in this window.",
                     "funding_signal":"partner_relationship_loan_window",
                     "timeframe":"~4 weeks","rarity":"common"},
    ("Saturn", 6):  {"domain":"finance","confidence":0.82,
                     "prediction":"Saturn transiting the loan/service zone (2.5 years) — a sustained window for building institutional credit and demonstrating the track record required for bank financing. Chronic obligations and service commitments surface for resolution. Patience in this window converts into fundable credibility.",
                     "warning":"Chronic health issues may surface — proactive medical management is protective.",
                     "funding_signal":"institutional_credit_building",
                     "timeframe":"~2.5 years","rarity":"notable"},
    ("Rahu", 6):    {"domain":"finance","confidence":0.80,
                     "prediction":"Rahu transiting the loan zone (18 months) — unconventional funding channels are wide open. Foreign investors, fintech lenders, alternative credit, and non-traditional capital sources are highly accessible. Hidden enemies or workplace complications may surface simultaneously.",
                     "warning":"Be discerning about who you trust in professional settings during this period.",
                     "funding_signal":"unconventional_foreign_loan_window",
                     "timeframe":"~18 months","rarity":"notable"},
    ("Ketu", 6):    {"domain":"finance","confidence":0.72,
                     "prediction":"Ketu transiting the loan zone (18 months) — karmic release of old financial conflicts and debt patterns. Complex loan structures are inadvisable during this transit. Prefer simpler, self-directed financing. Old enemies and health patterns from the past surface for completion.",
                     "funding_signal":"debt_simplification_window",
                     "timeframe":"~18 months","rarity":"notable"},

    # ── 8H TRANSITS — OPM/Investor window + transformation ───────────
    ("Sun", 8):     {"domain":"finance","confidence":0.75,
                     "prediction":"Sun transiting the OPM/transformation zone — a window for approaching government-backed investors, public sector co-funders, and authority-figure backers. Simultaneously: ego-related authority challenges surface. Hidden matters in finances or career may be exposed.",
                     "warning":"Avoid overexerting authority. What gets exposed now is ultimately liberating.",
                     "funding_signal":"authority_investor_window",
                     "timeframe":"~1 month","rarity":"common"},
    ("Moon", 8):    {"domain":"finance","confidence":0.75,
                     "prediction":"Moon transiting the OPM zone — fluctuating access to external capital. Investor and co-funder conversations begun during emotionally stable days in this transit carry unusual momentum. Consumer-facing brand investment and community crowdfunding are activated.",
                     "funding_signal":"community_investor_window",
                     "timeframe":"~2.5 days","rarity":"common"},
    ("Mars", 8):    {"domain":"finance","confidence":0.82,
                     "prediction":"Mars transiting the OPM/transformation zone — ACUTE CHANGE SIGNAL. Sudden financial shocks or windfalls are both possible. Asset-backed external capital and inheritance-related matters activate suddenly. High-energy window for bold investor pitches and joint venture negotiations.",
                     "warning":"Extra vigilance with physical safety. Document all financial agreements made in this window.",
                     "funding_signal":"sudden_external_capital_window",
                     "timeframe":"~6 weeks","rarity":"notable"},
    ("Mercury", 8): {"domain":"finance","confidence":0.80,
                     "prediction":"Mercury transiting the OPM zone — investor pitch documentation, IP agreements, and tech-sector funding conversations carry strong momentum. Written investor communications and term sheets finalized in this window have favorable outcomes.",
                     "warning":"Protect IP legally before initiating any pitch during this transit.",
                     "funding_signal":"ip_investor_pitch_window",
                     "timeframe":"~3 weeks","rarity":"common"},
    ("Jupiter", 8): {"domain":"finance","confidence":0.85,
                     "prediction":"Jupiter transiting the OPM/investor zone — THE most powerful annual transit for attracting external capital. Angel investors, VCs, inheritance matters, and joint venture capital are all highly activated. Wisdom and credibility are the magnets. This window is rare and should be fully utilized for funding outreach.",
                     "warning":"Never misuse investor trust activated during this window. Jupiter's grace here is lent, not given.",
                     "funding_signal":"peak_investor_window",
                     "timeframe":"~12 months","rarity":"significant"},
    ("Venus", 8):   {"domain":"finance","confidence":0.82,
                     "prediction":"Venus transiting the OPM zone — partnership funding, co-founder capital, and joint venture investment are strongly activated. Business relationships formed or deepened in this window frequently carry financial upside. Good window for joint real estate deals.",
                     "funding_signal":"partner_cofounder_window",
                     "timeframe":"~4 weeks","rarity":"common"},
    ("Saturn", 8):  {"domain":"finance","confidence":0.82,
                     "prediction":"Saturn transiting the OPM/transformation zone (2.5 years) — patient, long-term institutional capital is available but requires extensive due diligence. Family offices, pension-adjacent funds, and 5-10 year horizon investors are evaluating track records now. Deep life restructuring runs simultaneously — legal documentation is essential.",
                     "warning":"Proactive health management and legal documentation are essential throughout this transit.",
                     "funding_signal":"patient_capital_due_diligence",
                     "timeframe":"~2.5 years","rarity":"significant"},
    ("Rahu", 8):    {"domain":"finance","confidence":0.85,
                     "prediction":"Rahu transiting the OPM/transformation zone — MAJOR CHANGE SIGNAL for external capital. Sudden, unexpected access to large funding from foreign investors, unconventional equity sources, or cross-border capital. The change is disruptive AND opens a fundamentally new financial chapter. Vet all sources carefully.",
                     "warning":"Ensure all insurances and legal documents are current. Avoid high-risk investment decisions during this window.",
                     "funding_signal":"sudden_foreign_capital_window",
                     "timeframe":"~18 months","rarity":"significant"},
    ("Ketu", 8):    {"domain":"finance","confidence":0.80,
                     "prediction":"Ketu transiting the OPM zone — karmic completions around shared resources, inheritance, and external capital. What was borrowed or owed reaches resolution. Impact-driven and mission-aligned investors are the right fit for any new capital conversations during this transit.",
                     "funding_signal":"karmic_capital_completion",
                     "timeframe":"~18 months","rarity":"notable"},

    # ── 12H TRANSITS — Investment/expense surge + foreign + liberation ──
    ("Sun", 12):    {"domain":"finance","confidence":0.72,
                     "prediction":"Sun transiting the investment/expenditure zone — energy and spending turn toward behind-the-scenes work, foreign-facing activity, and institutional causes. Public visibility is lower but private financial groundwork done now yields returns later. Foreign government-adjacent investments are activated.",
                     "timeframe":"~1 month","rarity":"common",
                     "investment_signal":"foreign_institutional_window"},
    ("Moon", 12):   {"domain":"finance","confidence":0.72,
                     "prediction":"Moon transiting the expenditure zone — emotional spending patterns are elevated. Watch for impulse expenditures tied to comfort, home, and nurturing. Foreign real estate and care-sector opportunities briefly activate.",
                     "warning":"Avoid large financial commitments made during emotional vulnerability in this transit.",
                     "timeframe":"~2.5 days","rarity":"common",
                     "investment_signal":"emotional_expenditure_watch"},
    ("Mars", 12):   {"domain":"finance","confidence":0.78,
                     "prediction":"Mars transiting the investment/expenditure zone — hidden expenditures, foreign-related expenses, and behind-the-scenes financial battles are activated. Import/export, foreign infrastructure, and real estate abroad are the investment signals here. Control outflows proactively.",
                     "warning":"Do NOT lend money during this transit — it rarely returns.",
                     "timeframe":"~6 weeks","rarity":"common",
                     "investment_signal":"foreign_infrastructure_window"},
    ("Mercury", 12):{"domain":"finance","confidence":0.75,
                     "prediction":"Mercury transiting the expenditure zone — spending on information, communication systems, and foreign intellectual work is elevated. Foreign tech contracts, media deals, and cross-border written agreements are briefly activated.",
                     "warning":"Foreign contracts need extra legal scrutiny during this transit.",
                     "timeframe":"~3 weeks","rarity":"common",
                     "investment_signal":"foreign_tech_contract_window"},
    ("Jupiter", 12):{"domain":"finance","confidence":0.78,
                     "prediction":"Jupiter transiting the investment/liberation zone — generous outflows toward spiritual, educational, and foreign causes. Returns on dharmic and educational investments begin to materialize. Foreign wisdom partnerships and spiritual ventures yield unexpected value.",
                     "warning":"Monitor overall expenditure levels — Jupiter in 12H expands outflows generously.",
                     "timeframe":"~12 months","rarity":"common",
                     "investment_signal":"educational_spiritual_foreign_window"},
    ("Venus", 12):  {"domain":"finance","confidence":0.78,
                     "prediction":"Venus transiting the expenditure zone — spending on luxury, comfort, and relationship-driven foreign activity is elevated. Foreign hospitality ventures, beauty and arts investments, and cross-border partnership financial activity are briefly activated.",
                     "warning":"Luxury expenditure tracking is important during this transit.",
                     "timeframe":"~4 weeks","rarity":"common",
                     "investment_signal":"luxury_foreign_partnership_window"},
    ("Saturn", 12): {"domain":"finance","confidence":0.82,
                     "prediction":"Saturn transiting the investment/liberation zone (2.5 years) — a sustained period of elevated expenses and financial discipline requirements. Service-based foreign investments, institutional ventures abroad, and long-horizon positions begun now carry reliable long-term returns. Spiritual practice reduces the weight of this transit significantly.",
                     "timeframe":"~2.5 years","rarity":"notable",
                     "investment_signal":"long_horizon_foreign_service"},
    ("Rahu", 12):   {"domain":"finance","confidence":0.80,
                     "prediction":"Rahu transiting the investment/liberation zone (18 months) — strong activation of foreign financial connections and unconventional investment channels. Cross-border capital, foreign currency positions, and hidden financial structures become active. What is being built in secret or in foreign markets is the actual financial story.",
                     "warning":"Hidden financial activity carries hidden legal risk. Ensure full regulatory compliance in all foreign structures.",
                     "timeframe":"~18 months","rarity":"notable",
                     "investment_signal":"foreign_unconventional_hidden_window"},
    ("Ketu", 12):   {"domain":"spiritual","confidence":0.82,
                     "prediction":"Ketu transiting the liberation zone — deep spiritual activation. Karmic expenditures complete their cycle. Investment return here is non-material — retreat, service, and liberation practices yield incalculable inner returns. Material financial expectations are misaligned with this transit's purpose.",
                     "timeframe":"~18 months","rarity":"notable"},
}

# ═══════════════════════════════════════════════════════════════
# TRANSIT RULES — Love, Romance, Divorce, Foreign, Speculation, Loss
# Fired by apply_transit_rules() when concern matches
# ═══════════════════════════════════════════════════════════════

TRANSIT_LOVE_RULES = {
    ("Venus", 5):   {"domain":"love","confidence":0.85,"prediction":"Venus transiting the romance zone — a peak love activation window. Romantic meetings, deepening connections, and creative expression are heightened. For those seeking love, initiate during this window.","timeframe":"~4 weeks","rarity":"notable","love_signal":"peak_romance_window"},
    ("Jupiter", 5): {"domain":"love","confidence":0.85,"prediction":"Jupiter transiting the romance zone — an expanded, blessed period for romance and creativity. Relationships formed in this window carry genuine growth and philosophical depth.","timeframe":"~12 months","rarity":"notable","love_signal":"blessed_romance_window"},
    ("Venus", 7):   {"domain":"love","confidence":0.88,"prediction":"Venus transiting the partnership zone — the strongest annual transit for relationship deepening, proposal, and romantic milestones. Existing relationships receive grace. New relationships initiated here carry strong longevity signals.","timeframe":"~4 weeks","rarity":"notable","love_signal":"partnership_milestone_window"},
    ("Jupiter", 7): {"domain":"love","confidence":0.90,"prediction":"Jupiter transiting the partnership zone — the most powerful annual signal for marriage and partnership formation. Relationships and business partnerships receive Jupiter's full grace.","timeframe":"~12 months","rarity":"significant","love_signal":"marriage_formation_window"},
    ("Mars", 7):    {"domain":"divorce","confidence":0.78,"prediction":"Mars transiting the partnership zone — increased friction and conflict in relationships. Existing issues surface for resolution. What is suppressed erupts. What is addressed grows stronger.","warning":"Avoid ultimatums and major relationship decisions during this transit. The friction is temporary.","timeframe":"~6 weeks","rarity":"common","divorce_signal":"conflict_window"},
    ("Saturn", 7):  {"domain":"divorce","confidence":0.85,"prediction":"Saturn transiting the partnership zone — karmic relationship audit. All partnerships are tested for authenticity. Inauthentic relationships face real strain. Authentic ones are strengthened.","warning":"Do NOT make hasty relationship decisions. Let Saturn's review complete. What survives this transit is built for decades.","timeframe":"~2.5 years","rarity":"significant","divorce_signal":"karmic_audit_window"},
    ("Rahu", 7):    {"domain":"divorce","confidence":0.80,"prediction":"Rahu transiting the partnership zone — sudden, disruptive, or karmic relationship events. Unexpected partner changes, unusual attractions, or hidden partnership issues surface.","warning":"Wait 6 months before finalizing any major relationship decision made under this transit.","timeframe":"~18 months","rarity":"notable","divorce_signal":"sudden_disruption_window"},
    ("Ketu", 7):    {"domain":"divorce","confidence":0.75,"prediction":"Ketu transiting the partnership zone — karmic completions in relationships. Connections that have run their course reach natural endings. Those that remain are purified and deepened.","timeframe":"~18 months","rarity":"notable","divorce_signal":"karmic_completion_window"},
}

TRANSIT_FOREIGN_RULES = {
    ("Jupiter", 9): {"domain":"foreign","confidence":0.90,"prediction":"Jupiter transiting the fortune/foreign zone — the most powerful annual signal for foreign travel, higher education abroad, and international opportunity. Visa applications, relocation, and foreign business initiated now carry strong success signals.","timeframe":"~12 months","rarity":"significant","foreign_signal":"peak_foreign_opportunity"},
    ("Venus", 9):   {"domain":"foreign","confidence":0.82,"prediction":"Venus transiting the fortune zone — a window for foreign travel with romantic or creative purpose. International arts, luxury, and beauty-sector opportunities activate briefly.","timeframe":"~4 weeks","rarity":"common","foreign_signal":"creative_travel_window"},
    ("Rahu", 9):    {"domain":"foreign","confidence":0.82,"prediction":"Rahu transiting the fortune/foreign zone — strong activation of foreign connections, cross-border opportunities, and unconventional international paths. Immigration decisions now carry both strong potential and hidden complications.","warning":"Read all foreign contracts and immigration commitments carefully.","timeframe":"~18 months","rarity":"notable","foreign_signal":"unconventional_foreign_window"},
    ("Mercury", 9): {"domain":"foreign","confidence":0.78,"prediction":"Mercury transiting the fortune zone — foreign communication, publishing, education, and language-related travel are briefly activated.","timeframe":"~3 weeks","rarity":"common","foreign_signal":"communication_travel_window"},
    ("Saturn", 12): {"domain":"foreign","confidence":0.75,"prediction":"Saturn transiting the loss/foreign zone — work-related foreign commitments, service in foreign lands, and institutional foreign investments are the aligned expressions. Liberation through disciplined foreign work.","timeframe":"~2.5 years","rarity":"notable","foreign_signal":"foreign_service_window"},
    ("Rahu", 12):   {"domain":"foreign","confidence":0.78,"prediction":"Rahu transiting the foreign/loss zone — strong activation of cross-border connections, foreign financial structures, and hidden foreign activity. What is built in foreign markets now carries outsized long-term value.","timeframe":"~18 months","rarity":"notable","foreign_signal":"hidden_foreign_activity"},
}

TRANSIT_SPECULATION_RULES = {
    ("Jupiter", 5): {"domain":"speculation","confidence":0.82,"prediction":"Jupiter transiting the speculation zone — a window where moderate, calculated investment risk carries elevated success probability. This is NOT a signal to gamble recklessly — it is a signal that researched investments have improved odds.","warning":"This window does NOT override a natal Saturn or Ketu in 5H warning. Natal signals override all transit windows.","timeframe":"~12 months","rarity":"notable","speculation_signal":"calculated_risk_window"},
    ("Mars", 5):    {"domain":"speculation","confidence":0.72,"prediction":"Mars transiting the speculation zone — speculative impulses are elevated. For charts with natal Jupiter or Venus in 5H, this can activate short-term gains. For charts with natal Saturn or Ketu in 5H, this transit amplifies the loss pattern.","warning":"Know your natal 5H placement before acting on Mars transit speculation impulses.","timeframe":"~6 weeks","rarity":"common","speculation_signal":"impulsive_risk_window"},
    ("Rahu", 5):    {"domain":"speculation","confidence":0.80,"prediction":"Rahu transiting the speculation zone — amplified speculative instincts, sudden lottery-type events, and unusual financial opportunities. Highest variance transit — wins are bigger and losses are bigger.","warning":"Set a hard loss limit before entering ANY speculative position during this transit. Rahu in 5H removes rational judgment at the peak.","timeframe":"~18 months","rarity":"notable","speculation_signal":"high_variance_window"},
    ("Saturn", 5):  {"domain":"speculation","confidence":0.88,"prediction":"Saturn transiting the speculation zone — speculative activity during this period consistently produces loss or disappointment. Lottery, gambling, and high-risk trading are strongly inadvisable for the entire duration.","warning":"AVOID ALL SPECULATION, GAMBLING, AND LOTTERY during Saturn's transit through your 5th house. This is the clearest 'avoid' signal in Vedic timing.","timeframe":"~2.5 years","rarity":"significant","speculation_signal":"avoid_all_speculation"},
    ("Venus", 5):   {"domain":"speculation","confidence":0.75,"prediction":"Venus transiting the speculation zone — creative financial ventures, arts investments, and aesthetically-driven speculative plays have elevated positive signals.","timeframe":"~4 weeks","rarity":"common","speculation_signal":"creative_speculation_window"},
}

TRANSIT_LOSS_RULES = {
    ("Mars", 12):   {"domain":"loss","confidence":0.80,"prediction":"Mars transiting the loss zone — sudden, large hidden expenditures and financial energy drain from behind-the-scenes battles. Control all outflows actively.","warning":"Do NOT lend money during this transit. It rarely returns.","timeframe":"~6 weeks","rarity":"common","loss_signal":"sudden_expenditure_window"},
    ("Saturn", 12): {"domain":"loss","confidence":0.82,"prediction":"Saturn transiting the loss zone — sustained elevated expenses and systematic financial discipline requirements. Losses are teachers. Service-based foreign investments begun now convert loss-energy into future gain.","timeframe":"~2.5 years","rarity":"notable","loss_signal":"sustained_loss_discipline"},
    ("Rahu", 12):   {"domain":"loss","confidence":0.78,"prediction":"Rahu transiting the loss zone — hidden financial activity, cross-border capital, and unconventional investment structures are active. What is built in secret now carries outsized returns but hidden legal risk.","warning":"Ensure full regulatory compliance in all foreign financial structures.","timeframe":"~18 months","rarity":"notable","loss_signal":"hidden_loss_or_gain"},
    ("Ketu", 12):   {"domain":"loss","confidence":0.80,"prediction":"Ketu transiting the loss zone — karmic expenditures complete their cycle. Unexpected financial outflows often related to past obligations or foreign commitments.","timeframe":"~18 months","rarity":"notable","loss_signal":"karmic_expenditure"},
    ("Jupiter", 8): {"domain":"loss","confidence":0.72,"prediction":"Jupiter transiting the transformation zone — research, investigation, and understanding hidden matters are the primary gifts. Financial transformation is possible — what appears as loss is often restructuring toward greater alignment.","timeframe":"~12 months","rarity":"common","loss_signal":"transformative_restructuring"},
}



# ═══════════════════════════════════════════════════════════════
# RAHU/KETU OVER NATAL PLANETS — Change markers (NEW v2)
# When transiting Rahu or Ketu conjuncts a natal planet
# ═══════════════════════════════════════════════════════════════

RAHU_KETU_NATAL_RULES = {
    # Rahu conjunct natal planet
    ("Rahu", "Sun"):    {"domain":"career","confidence":0.85,"prediction":"Rahu moving over your natal Sun — a rare identity and authority transformation. Career reinvention, sudden visibility, or disruption of your established role. Who you are publicly is being rewritten.","warning":"Ego inflation is possible. Stay grounded — the change is real but must be navigated consciously.","rarity":"significant"},
    ("Rahu", "Moon"):   {"domain":"health","confidence":0.82,"prediction":"Rahu moving over your natal Moon — emotional disruption and mental turbulence. Unusual fears, obsessive thinking, or psychosomatic health issues may surface. This is a psychological transformation period.","warning":"Prioritize mental health practices. Avoid major emotional decisions for 6 months.","rarity":"significant"},
    ("Rahu", "Mars"):   {"domain":"health","confidence":0.82,"prediction":"Rahu moving over your natal Mars — sudden aggression, accidents, or unexpected career battles. Physical energy is volatile and powerful.","warning":"Extra caution with physical safety, fire, and impulsive decisions.","rarity":"notable"},
    ("Rahu", "Mercury"):{"domain":"career","confidence":0.78,"prediction":"Rahu moving over your natal Mercury — communication and business disruptions. Contracts, deals, and negotiations are unpredictable. New, unconventional ideas break through.","warning":"Double-check all agreements. Avoid rushing communication decisions.","rarity":"notable"},
    ("Rahu", "Jupiter"):{"domain":"spiritual","confidence":0.82,"prediction":"Rahu moving over your natal Jupiter — a teacher, belief system, or philosophical worldview is being challenged or expanded. Unconventional wisdom enters your life.","warning":"Be discerning about new teachers or spiritual influences during this period.","rarity":"significant"},
    ("Rahu", "Venus"):  {"domain":"marriage","confidence":0.85,"prediction":"Rahu moving over your natal Venus — MAJOR RELATIONSHIP CHANGE SIGNAL. Unusual, karmic, or sudden romantic or partnership developments. An encounter now can be life-altering.","warning":"Ensure new relationships are based on substance. Rahu over Venus creates powerful attraction that may not last without strong foundations.","rarity":"significant"},
    ("Rahu", "Saturn"): {"domain":"career","confidence":0.82,"prediction":"Rahu moving over your natal Saturn — karmic acceleration. Structures you built over years are being tested. Career and discipline are under intense pressure — what is solid remains, what was built on shortcuts collapses.","warning":"No shortcuts. This period ruthlessly exposes any lack of integrity in career and commitments.","rarity":"significant"},
    # Ketu conjunct natal planet
    ("Ketu", "Sun"):    {"domain":"career","confidence":0.80,"prediction":"Ketu moving over your natal Sun — identity dissolution and ego detachment. A past-life completion around authority and recognition. Career matters feel less important; spiritual truth feels more important.","rarity":"significant"},
    ("Ketu", "Moon"):   {"domain":"health","confidence":0.78,"prediction":"Ketu moving over your natal Moon — emotional detachment and past-life karmic release. Old emotional patterns, particularly around mother or home, complete their cycle.","rarity":"notable"},
    ("Ketu", "Mars"):   {"domain":"career","confidence":0.75,"prediction":"Ketu moving over natal Mars — past ambitions and battles are being released. Energy turns inward and spiritual. A good period for research, investigation, and behind-the-scenes work.","rarity":"notable"},
    ("Ketu", "Jupiter"):{"domain":"spiritual","confidence":0.82,"prediction":"Ketu moving over natal Jupiter — past-life wisdom resurfaces. Deep spiritual insights, past teacher connections, or philosophical completions. Inner knowing strengthens.","rarity":"significant"},
    ("Ketu", "Venus"):  {"domain":"marriage","confidence":0.80,"prediction":"Ketu moving over natal Venus — past relationship karma is completing. A significant relationship may end, transform, or reveal its true spiritual depth. Beauty and art become more spiritually meaningful.","rarity":"significant"},
    ("Ketu", "Saturn"): {"domain":"career","confidence":0.78,"prediction":"Ketu moving over natal Saturn — past-life karmic debts around discipline and responsibility are releasing. Old structures dissolve. A new, more spiritually aligned career direction may emerge.","rarity":"notable"},
}


# ═══════════════════════════════════════════════════════════════
# RAHU/KETU AXIS TRANSIT — Major life shift marker (NEW v2)
# When Rahu and Ketu change signs (every ~18 months)
# This creates a new karmic axis for everyone
# ═══════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════
# DETECT CONCERN — Full keyword router
# Maps user question → canonical concern string
# Used by: main.py → predict endpoint → all rule appliers
# ═══════════════════════════════════════════════════════════════

def detect_concern(question: str) -> str:
    """
    Map a user question to a canonical concern domain.
    Returns one of: career, finance, marriage, love, divorce, health,
                    foreign, speculation, loss, wealth, spiritual, general
    Order matters — more specific matches before general ones.
    """
    q = question.lower()

    # ── Speculation / Gambling / Lottery ──────────────────────
    specul_words = ["specul","gambl","lotter","casino","bet ","betting","poker",
                    "stock market","stocks","trading","crypto","invest in","should i buy",
                    "should i sell","day trad","options trad","forex","penny stock"]
    if any(w in q for w in specul_words):
        return "speculation"

    # ── Divorce / Separation ───────────────────────────────────
    divorce_words = ["divorce","separate","separation","break up","breakup","split","failing","not working","struggling with my","problems with my",
                     "end my marriage","leaving my wife","leaving my husband",
                     "my partner left","spouse left","marriage failing","marriage over",
                     "should i leave","leave my partner","leave my spouse"]
    if any(w in q for w in divorce_words):
        return "divorce"

    # ── Love / Romance ─────────────────────────────────────────
    love_words = ["love","romance","romantic","crush","dating","date","relationship",
                  "boyfriend","girlfriend","partner","soulmate","when will i meet",
                  "when will i find love","find someone","marriage prospects",
                  "will i get married","arranged marriage","love marriage","ex ",
                  "ex-","heartbreak","fall in love","in love"]
    if any(w in q for w in love_words):
        return "love"

    # ── Marriage (distinct from love — existing partnership) ──
    marriage_words = ["marriage","married","wedding","husband","wife","spouse",
                      "my relationship","my marriage","my partner"]
    if any(w in q for w in marriage_words):
        return "marriage"

    # ── Foreign / Travel ───────────────────────────────────────
    foreign_words = ["foreign","abroad","overseas","travel","immigrat","visa",
                     "move to","relocat","settle in","work in","study in",
                     "move abroad","move overseas","international","other country",
                     "another country","go to","going to","leave india","leave country"]
    if any(w in q for w in foreign_words):
        return "foreign"

    # ── Loss / Financial ruin ──────────────────────────────────
    loss_words = ["loss","losing money","lost money","financial loss","debt trap",
                  "bankruptcy","ruined","drained","money gone","savings gone",
                  "why am i losing","why do i lose","bad luck with money",
                  "expenses","expenditure","spending too much","losing everything"]
    if any(w in q for w in loss_words):
        return "loss"

    # ── Funding / OPM / Investment ─────────────────────────────
    funding_words = ["funding","investor","investors","capital","raise money","cashflow","cash flow","cash-flow",
                     "raise funds","vc","venture","angel invest","grant","loan",
                     "borrow","bank loan","credit","debt","opm","seed round",
                     "series a","series b","crowdfund","get funded","get investment"]
    if any(w in q for w in funding_words):
        return "finance"

    # ── Wealth / Money accumulation ────────────────────────────
    wealth_words = ["wealth","rich","wealthy","make money","earn money","income",
                    "salary","savings","property","real estate","assets","net worth",
                    "financial freedom","passive income","when will i be rich",
                    "money problem","money situation","financial situation",
                    "profit"]
    if any(w in q for w in wealth_words):
        return "wealth"

    # ── Finance (general money questions) ─────────────────────
    finance_words = ["financ","money","business","revenue","budget","payment","cashflow","cash flow","earning","afford","economic",
                     "afford","economic"]
    if any(w in q for w in finance_words):
        return "finance"

    # ── Health ─────────────────────────────────────────────────
    health_words = ["health","sick","illness","disease","hospital","surgery",
                    "recover","pain","body","energy level","fatigue","tired",
                    "stress","anxiety","mental health","depression","healing"]
    if any(w in q for w in health_words):
        return "health"

    # ── Career / Work ──────────────────────────────────────────
    career_words = ["career","job","work","profession","business","promotion",
                    "promotion","startup","company","office","boss","colleague",
                    "fired","resign","quit","new job","better job","professional",
                    "interview","opportunity","recognition","success","achieve",
                    "entrepreneur"]
    if any(w in q for w in career_words):
        return "career"

    # ── Spiritual ──────────────────────────────────────────────
    spiritual_words = ["spiritual","meditation","dharma","karma","moksha","purpose",
                       "meaning","soul","life purpose","why am i here","destiny",
                       "higher self","awakening","consciousness"]
    if any(w in q for w in spiritual_words):
        return "spiritual"

    return "general"

def check_rahu_ketu_axis_shift(current_transits: list) -> Optional[dict]:
    """
    Check if Rahu/Ketu are in a notable axis combination.
    Key axes and what they mean for different lagna signs.
    """
    rahu_house = None
    ketu_house = None
    for t in current_transits:
        if t.get("planet") == "Rahu":
            rahu_house = t.get("transit_house")
        elif t.get("planet") == "Ketu":
            ketu_house = t.get("transit_house")

    if not rahu_house or not ketu_house:
        return None

    # Notable axis combinations
    axis_meanings = {
        (5, 11): {"domain":"career","prediction":"The creative-gains axis is activated. Rahu in your intelligence zone and Ketu in your network zone creates a powerful cycle: innovate and create (Rahu) to manifest income (Ketu releases attachment to gains, making room for more).","confidence":0.82},
        (11, 5): {"domain":"wealth","prediction":"The gains-creativity axis is activated. Rahu's ambition is focused on networks and income. Ketu in creativity zone asks you to detach from recognition and create for pure purpose — which paradoxically brings the most recognition.","confidence":0.82},
        (1, 7):  {"domain":"marriage","prediction":"The identity-partnership axis is activated. Rahu is pushing your sense of self forward; Ketu is releasing old partnership karma. A major identity shift is underway, and relationship patterns from the past are completing their cycle.","confidence":0.85},
        (7, 1):  {"domain":"marriage","prediction":"The partnership-identity axis is activated. Rahu is seeking deep partnership; Ketu is releasing old ego constructs. A new, more authentic version of yourself emerges through relationship.","confidence":0.85},
        (10, 4): {"domain":"career","prediction":"The career-home axis is activated. Rahu is pushing career ambition to the maximum; Ketu is releasing attachment to domestic security. A major career chapter opens, requiring you to prioritize professional destiny over comfort.","confidence":0.85},
        (4, 10): {"domain":"family","prediction":"The home-career axis is activated. Rahu is seeking home and roots; Ketu is releasing old career identities. A homecoming or relocation, combined with a career transition, defines this period.","confidence":0.82},
        (2, 8):  {"domain":"wealth","prediction":"The wealth-transformation axis is activated. Rahu in wealth zone is accumulating; Ketu in transformation zone is releasing old debts and hidden patterns. A significant financial restructuring cycle.","confidence":0.82,"warning":"Ensure all financial and legal documents are in order during this axis."},
        (8, 2):  {"domain":"wealth","prediction":"The transformation-wealth axis is activated. Rahu is pursuing hidden knowledge and inheritance; Ketu is releasing attachment to accumulated wealth. A profound period of financial restructuring and inner wealth.","confidence":0.82},
        (3, 9):  {"domain":"spiritual","prediction":"The communication-dharma axis is activated. Rahu is amplifying your voice and courage; Ketu is releasing old belief systems. What you say and teach now has unusual reach and impact.","confidence":0.80},
        (9, 3):  {"domain":"spiritual","prediction":"The dharma-communication axis is activated. Rahu is seeking higher wisdom and foreign connection; Ketu is releasing old sibling or neighborhood patterns. Philosophy, travel, and higher education define this period.","confidence":0.80},
        (6, 12): {"domain":"health","prediction":"The health-liberation axis is activated. Rahu in conflict zone can intensify health challenges or workplace disputes; Ketu in liberation zone is releasing old karmic patterns. Service, healing, and spiritual practice are the highest use of this axis.","confidence":0.80,"warning":"Proactive health management is especially important during this nodal axis."},
        (12, 6): {"domain":"spiritual","prediction":"The liberation-conflict axis is activated. Rahu is seeking foreign or spiritual experiences; Ketu is releasing old enemies and health patterns. A deeply spiritual and physically transformative period.","confidence":0.80},
    }

    key = (rahu_house, ketu_house)
    meaning = axis_meanings.get(key)
    if meaning:
        return {
            "system": "rahu_ketu_axis",
            "rule_id": f"RK_AXIS_{rahu_house}_{ketu_house}",
            "planet": "Rahu/Ketu",
            "domain": meaning["domain"],
            "confidence": meaning["confidence"],
            "prediction": meaning["prediction"],
            "warning": meaning.get("warning", ""),
            "timeframe": "~18 months (until next nodal shift)",
            "rahu_house": rahu_house,
            "ketu_house": ketu_house,
            "concern_relevance": 0.85,
            "is_axis_signal": True,
        }
    return None


# ═══════════════════════════════════════════════════════════════
# KARAKA COMPUTATION
# ═══════════════════════════════════════════════════════════════

def compute_karakas(chart_data: dict) -> dict:
    planets_to_use = ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn"]
    degrees = {}
    for p in planets_to_use:
        lon = chart_data.get("planets",{}).get(p,{}).get("longitude", 0)
        degrees[p] = lon % 30
    sorted_p = sorted(degrees.items(), key=lambda x: x[1], reverse=True)
    roles = ["AK","AmK","BK","MK","PK","GK","DK"]
    return {roles[i]: sorted_p[i][0] for i in range(min(len(roles), len(sorted_p)))}


# ═══════════════════════════════════════════════════════════════
# RULE APPLICATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════

# Concern alias map — maps all concern keywords to canonical domain names
CONCERN_DOMAIN_ALIASES = {
    "love":        {"love", "marriage"},
    "romance":     {"love", "marriage"},
    "marriage":    {"marriage", "love"},
    "divorce":     {"divorce", "marriage", "love"},
    "separation":  {"divorce", "marriage"},
    "relationship":{"love", "marriage", "divorce"},
    "career":      {"career", "wealth"},
    "job":         {"career"},
    "business":    {"career", "wealth", "finance"},
    "finance":     {"finance", "wealth", "loss"},
    "funding":     {"finance", "wealth"},
    "money":       {"wealth", "finance"},
    "wealth":      {"wealth", "finance"},
    "investment":  {"wealth", "finance", "speculation"},
    "speculation": {"speculation", "wealth"},
    "gambling":    {"speculation"},
    "lottery":     {"speculation"},
    "loss":        {"loss", "finance"},
    "foreign":     {"foreign"},
    "travel":      {"foreign"},
    "abroad":      {"foreign"},
    "health":      {"health"},
    "spiritual":   {"spiritual"},
    "family":      {"family"},
    "general":     set(),  # general matches everything equally
}

def _concern_relevance(rule_domain: str, concern: str) -> float:
    """Score how relevant a rule domain is to the user's concern."""
    if concern == "general":
        return 0.70  # everything equally relevant for general
    aliases = CONCERN_DOMAIN_ALIASES.get(concern, {concern})
    if rule_domain == concern:
        return 0.95
    if rule_domain in aliases:
        return 0.88
    # Cross-domain boosts
    if concern in ("finance", "funding", "money") and rule_domain in ("wealth", "loss", "speculation"):
        return 0.82
    if concern in ("love", "romance", "marriage") and rule_domain == "divorce":
        return 0.75
    if concern == "divorce" and rule_domain in ("love", "marriage"):
        return 0.75
    return 0.45  # low relevance but never zero — context matters


def apply_lal_kitab_rules(chart_data: dict, concern: str) -> list:
    signals = []
    for planet, pdata in chart_data.get("planets",{}).items():
        house = pdata.get("house", 0)
        rule  = LAL_KITAB_RULES.get((planet, house))
        if rule:
            rel = _concern_relevance(rule["domain"], concern)
            sig = {
                "system":          "lal_kitab",
                "planet":          planet,
                "house":           house,
                "rule_id":         f"LK_{planet}_H{house}",
                "domain":          rule["domain"],
                "confidence":      rule["confidence"],
                "prediction":      rule["prediction"],
                "warning":         rule.get("warning", ""),
                "remedy_planet":   rule.get("remedy_planet", planet),
                "concern_relevance": rel,
            }
            # Pass through all signal tags
            for tag in ("funding_signal","investment_signal","love_signal","divorce_signal",
                        "foreign_signal","speculation_signal","wealth_signal","loss_signal"):
                if tag in rule:
                    sig[tag] = rule[tag]
            if rule.get("is_pain_signal"):
                sig["is_pain_signal"] = True
            signals.append(sig)
    return signals


def apply_jaimini_rules(chart_data: dict, concern: str) -> list:
    signals = []
    karakas = compute_karakas(chart_data)
    gk_planet = karakas.get("GK", "")

    for role, planet in karakas.items():
        house = chart_data.get("planets",{}).get(planet,{}).get("house", 0)
        rule  = JAIMINI_KARAKA_RULES.get((role, house))
        if rule:
            is_pain = rule.get("is_pain_signal", False) or (role == "GK")
            # GK always gets a rarity boost — it's the pain giver
            rarity_boost = 1.3 if is_pain else 1.0
            signals.append({
                "system": "jaimini", "planet": planet, "house": house,
                "karaka_role": role,
                "rule_id": f"JAI_{role}_{planet}_H{house}",
                "domain": rule["domain"],
                "confidence": min(rule["confidence"] * rarity_boost, 0.97),
                "prediction": rule["prediction"],
                "warning": rule.get("warning",""),
                "remedy_planet": planet,
                "concern_relevance": _concern_relevance(rule["domain"], concern),
                "is_pain_signal": is_pain,
            })
    return signals


def apply_dasha_rules(chart_data: dict, dashas: dict, concern: str) -> list:
    signals = []
    vimsottari = dashas.get("vimsottari", [])
    for entry in vimsottari[:3]:  # MD + AD + PD
        lord  = entry.get("lord_or_sign","")
        house = chart_data.get("planets",{}).get(lord,{}).get("house", 0)
        rule  = DASHA_ACTIVATION_RULES.get((lord, house))
        if rule:
            level = entry.get("level","MD")
            mult  = 1.0 if level=="MD" else 0.85 if level=="AD" else 0.70
            signals.append({
                "system": "dasha", "dasha_lord": lord, "house": house,
                "dasha_level": level,
                "rule_id": f"DASHA_{lord}_H{house}_{level}",
                "domain": rule["domain"],
                "confidence": rule["confidence"] * mult,
                "prediction": rule["prediction"],
                "warning": rule.get("warning",""),
                "remedy_planet": lord,
                "concern_relevance": _concern_relevance(rule["domain"], concern),
                "timeframe": entry.get("end",""),
            })
    return signals


def apply_transit_rules(chart_data: dict, current_transits: list, concern: str) -> list:
    """Apply standard + dushtana + love/foreign/speculation/loss transit rules."""
    signals = []
    lagna_si = chart_data.get("lagna",{}).get("sign_index", 0)
    natal_positions = {}
    for planet, pdata in chart_data.get("planets",{}).items():
        natal_positions[planet] = pdata.get("sign_index", 0)

    for t in current_transits:
        planet = t.get("planet","")
        house  = t.get("transit_house", 0)
        t_sign = t.get("transit_sign_index", t.get("sign_index", 0))

        if not planet or not house:
            continue

        # 1. Standard transit rules
        rule = TRANSIT_TRIGGER_RULES.get((planet, house))
        if rule:
            signals.append({
                "system": "transit", "transit_planet": planet, "house": house,
                "rule_id": f"TR_{planet}_H{house}",
                "domain": rule["domain"],
                "confidence": rule["confidence"],
                "prediction": rule["prediction"],
                "warning": rule.get("warning",""),
                "timeframe": rule.get("timeframe",""),
                "remedy_planet": planet,
                "concern_relevance": 0.88 if rule["domain"]==concern else 0.50,
            })

        # 2. Dushtana (6/8/12) transit rules — NEW
        if house in (6, 8, 12):
            drule = DUSHTANA_TRANSIT_RULES.get((planet, house))
            if drule:
                rarity = drule.get("rarity","common")
                rarity_boost = {"common":1.0, "notable":1.1, "significant":1.2}.get(rarity, 1.0)
                signals.append({
                    "system": "transit_dushtana", "transit_planet": planet, "house": house,
                    "rule_id": f"TR_DUST_{planet}_H{house}",
                    "domain": drule["domain"],
                    "confidence": drule["confidence"] * rarity_boost,
                    "prediction": drule["prediction"],
                    "warning": drule.get("warning",""),
                    "timeframe": drule.get("timeframe",""),
                    "remedy_planet": planet,
                    "concern_relevance": 0.85 if drule["domain"]==concern else 0.50,
                    "is_dushtana": True,
                    "rarity": rarity,
                })

        # 3. Rahu/Ketu transiting over natal planets — NEW
        if planet in ("Rahu", "Ketu"):
            for natal_planet, natal_sign_i in natal_positions.items():
                # Conjunct = within same sign (sign-based, not degree)
                if t_sign == natal_sign_i and natal_planet not in ("Rahu","Ketu","Ascendant"):
                    rk_rule = RAHU_KETU_NATAL_RULES.get((planet, natal_planet))
                    if rk_rule:
                        rarity = rk_rule.get("rarity","notable")
                        rarity_boost = {"notable":1.15, "significant":1.25}.get(rarity, 1.0)
                        signals.append({
                            "system": "rahu_ketu_over_natal",
                            "transit_planet": planet,
                            "natal_planet": natal_planet,
                            "house": house,
                            "rule_id": f"RK_OVER_{planet}_{natal_planet}",
                            "domain": rk_rule["domain"],
                            "confidence": rk_rule["confidence"] * rarity_boost,
                            "prediction": rk_rule["prediction"],
                            "warning": rk_rule.get("warning",""),
                            "timeframe": "~6-12 months (nodal conjunction)",
                            "remedy_planet": natal_planet,
                            "concern_relevance": 0.90 if rk_rule["domain"]==concern else 0.65,
                            "is_rk_over_natal": True,
                            "rarity": rarity,
                        })

    # 4. Rahu/Ketu axis signal — NEW
    axis_signal = check_rahu_ketu_axis_shift(current_transits)
    if axis_signal:
        axis_signal["concern_relevance"] = 0.88 if axis_signal["domain"]==concern else 0.60
        signals.append(axis_signal)


    # ── 5. New concern-specific transit rule dicts ────────────────────────
    CONCERN_TRANSIT_MAP = {
        "love":        TRANSIT_LOVE_RULES,
        "marriage":    TRANSIT_LOVE_RULES,
        "divorce":     TRANSIT_LOVE_RULES,
        "foreign":     TRANSIT_FOREIGN_RULES,
        "travel":      TRANSIT_FOREIGN_RULES,
        "speculation": TRANSIT_SPECULATION_RULES,
        "gambling":    TRANSIT_SPECULATION_RULES,
        "lottery":     TRANSIT_SPECULATION_RULES,
        "loss":        TRANSIT_LOSS_RULES,
        "wealth":      TRANSIT_SPECULATION_RULES,
        "finance":     TRANSIT_LOSS_RULES,
    }
    extra_rules = CONCERN_TRANSIT_MAP.get(concern, {})
    if extra_rules:
        _tlist = (
            list(current_transits.values()) if isinstance(current_transits, dict)
            else (current_transits if isinstance(current_transits, list) else [])
        )
        for t in _tlist:
            if not isinstance(t, dict):
                continue
            t_planet = t.get("planet", "")
            t_house  = t.get("house", 0)
            rule = extra_rules.get((t_planet, t_house))
            if rule:
                signals.append({
                    "system":            "transit_concern",
                    "planet":            t_planet,
                    "house":             t_house,
                    "domain":            rule["domain"],
                    "confidence":        rule["confidence"],
                    "prediction":        rule["prediction"],
                    "warning":           rule.get("warning", ""),
                    "timeframe":         rule.get("timeframe", ""),
                    "rarity":            rule.get("rarity", "common"),
                    "concern_relevance": 0.95,
                    "rule_id":           f"TRANSIT_{concern.upper()}_{t_planet}_H{t_house}",
                    "love_signal":       rule.get("love_signal", ""),
                    "divorce_signal":    rule.get("divorce_signal", ""),
                    "foreign_signal":    rule.get("foreign_signal", ""),
                    "speculation_signal":rule.get("speculation_signal", ""),
                    "loss_signal":       rule.get("loss_signal", ""),
                    "wealth_signal":     rule.get("wealth_signal", ""),
                })

    return signals


# ═══════════════════════════════════════════════════════════════
# SMART SIGNAL FILTER + RANKER
# This is the jyotishi's judgment — which 5 rules matter most?
# ═══════════════════════════════════════════════════════════════

def rank_signals(all_signals: list, concern: str, karakas: dict) -> list:
    """
    Rank signals using jyotishi judgment:
    1. Concern relevance × base confidence
    2. Rarity boost (GK, 8H, Rahu/Ketu over natal = higher priority)
    3. Pain signals always surfaced if active
    4. Karaka signals (AK, AmK, GK) always in top 5
    5. Max 1 dushtana per type to avoid doom-loop
    """
    ranked = []
    for s in all_signals:
        base   = s["confidence"] * s.get("concern_relevance", 0.5)
        # Rarity boosts
        if s.get("is_pain_signal"):       base *= 1.3
        if s.get("is_rk_over_natal"):     base *= 1.2
        if s.get("is_dushtana") and s.get("rarity") == "significant": base *= 1.15
        if s.get("is_axis_signal"):       base *= 1.1
        # Karaka roles boost
        role = s.get("karaka_role","")
        if role in ("AK","AmK","GK"):     base *= 1.25
        if role == "DK" and concern in ("marriage","general"): base *= 1.15
        s["_rank_score"] = base
        ranked.append(s)

    ranked.sort(key=lambda x: x["_rank_score"], reverse=True)

    # Ensure we always include:
    # - At least 1 karaka signal (AK or AmK)
    # - GK signal if it fired (pain giver)
    # - Best confluence
    final = []
    seen_systems = set()
    pain_included = False
    karaka_included = False

    # First pass: required signals
    for s in ranked:
        if s.get("karaka_role") in ("AK","AmK") and not karaka_included:
            final.append(s); karaka_included = True
        if s.get("is_pain_signal") and not pain_included:
            final.append(s); pain_included = True

    # Second pass: fill top 5 with highest ranked, avoid duplication
    for s in ranked:
        if len(final) >= 6: break
        if s in final: continue
        # Limit to 1 dushtana signal total to avoid doom-loop
        if s.get("is_dushtana"):
            if any(f.get("is_dushtana") for f in final): continue
        final.append(s)

    return final[:6]


# ═══════════════════════════════════════════════════════════════
# TRIPLE CONFLUENCE DETECTION
# ═══════════════════════════════════════════════════════════════

def detect_triple_confluence(lk_signals, dasha_signals, transit_signals) -> list:
    confluences = []
    lk_by_planet     = {s.get("planet",""):     s for s in lk_signals}
    dasha_by_lord    = {s.get("dasha_lord",""): s for s in dasha_signals}
    transit_by_planet= {s.get("transit_planet",""):s for s in transit_signals}

    all_planets = set(lk_by_planet) | set(dasha_by_lord) | set(transit_by_planet)
    for planet in all_planets:
        hits = []
        if planet in lk_by_planet:     hits.append(("natal",   lk_by_planet[planet]))
        if planet in dasha_by_lord:    hits.append(("dasha",   dasha_by_lord[planet]))
        if planet in transit_by_planet:hits.append(("transit", transit_by_planet[planet]))
        if len(hits) >= 2:
            domains = [h[1]["domain"] for h in hits]
            primary = Counter(domains).most_common(1)[0][0]
            avg_conf= sum(h[1]["confidence"] for h in hits) / len(hits)
            triple  = len(hits) == 3
            confluences.append({
                "type": "TRIPLE CONFLUENCE" if triple else "DOUBLE CONFLUENCE",
                "planet": planet, "domain": primary,
                "layers": [h[0] for h in hits],
                "confidence": min(avg_conf + (0.08 if triple else 0.04), 0.97),
                "supporting_predictions": [h[1]["prediction"] for h in hits],
                "warnings": [h[1].get("warning","") for h in hits if h[1].get("warning")][:2],
                "remedy_planet": planet,
                "message": (
                    f"{'RARE TRIPLE' if triple else 'DOUBLE'} CONFLUENCE on {planet}: "
                    f"natal pattern, current life chapter, and live transit all pointing to {primary}. "
                    f"This is the highest-confidence signal window."
                ),
            })

    # Domain-level confluence across different planets
    all_signals = lk_signals + dasha_signals + transit_signals
    domain_groups = defaultdict(list)
    for s in all_signals:
        domain_groups[s["domain"]].append(s)
    for domain, sigs in domain_groups.items():
        systems = list({s.get("system","?") for s in sigs})
        if len(systems) >= 2 and not any(c["domain"]==domain for c in confluences):
            avg_conf = sum(s["confidence"] for s in sigs) / len(sigs)
            confluences.append({
                "type": "DOMAIN CONFLUENCE",
                "planet": None, "domain": domain,
                "layers": systems,
                "confidence": min(avg_conf + 0.03, 0.93),
                "supporting_predictions": [s["prediction"] for s in sigs[:3]],
                "warnings": [s.get("warning","") for s in sigs if s.get("warning")][:2],
                "remedy_planet": sigs[0].get("planet") or sigs[0].get("dasha_lord",""),
                "message": f"Multiple pattern systems ({', '.join(systems)}) all point to {domain} as the dominant active theme.",
            })

    return sorted(confluences, key=lambda x: x["confidence"], reverse=True)


# ═══════════════════════════════════════════════════════════════
# LOCATION-AWARE REMEDY FORMATTER
# ═══════════════════════════════════════════════════════════════

def format_remedy_for_location(remedy_planet: str, country_code: str = "IN") -> dict:
    remedy = REMEDIES.get(remedy_planet, {})
    if not remedy: return {}
    in_india = country_code.upper() in ("IN","NP","BD","LK","PK")
    return {
        "mantra": remedy["mantra"],
        "mantra_count": remedy["mantra_count"],
        "mantra_timing": remedy["mantra_timing"],
        "action": remedy["india_action"] if in_india else remedy["global_action"],
        "solves": remedy["solves"],
    }


# ═══════════════════════════════════════════════════════════════
# MASTER FUNCTION — run_all_rules
# ═══════════════════════════════════════════════════════════════

def run_all_rules(chart_data: dict, dashas: dict, current_transits,
                  concern: str = "general", country_code: str = "IN") -> dict:
    """
    The jyotishi's judgment pipeline:
    1. Fire all applicable rules
    2. Detect confluence
    3. Smart-rank by concern + strength + rarity
    4. Return top 5-6 signals only (not 50)
    """
    karakas  = compute_karakas(chart_data)
    lk       = apply_lal_kitab_rules(chart_data, concern)
    jai      = apply_jaimini_rules(chart_data, concern)
    dasha    = apply_dasha_rules(chart_data, dashas, concern)
    transit  = apply_transit_rules(chart_data, current_transits, concern)

    confluence = detect_triple_confluence(lk, dasha, transit)

    all_signals = lk + jai + dasha + transit
    top_signals = rank_signals(all_signals, concern, karakas)

    domain_votes  = Counter(s["domain"] for s in all_signals)
    dominant_domain = domain_votes.most_common(1)[0][0] if domain_votes else "general"

    # Location-aware remedies for top signals
    seen_planets = set()
    remedies = []
    for s in top_signals:
        rp = s.get("remedy_planet","")
        if rp and rp not in seen_planets:
            rem = format_remedy_for_location(rp, country_code)
            if rem:
                rem["for_domain"] = s["domain"]
                remedies.append(rem)
                seen_planets.add(rp)
        if len(remedies) >= 3:
            break

    # Flag special signal types for context block
    has_pain_signal    = any(s.get("is_pain_signal") for s in top_signals)
    has_rk_over_natal  = any(s.get("is_rk_over_natal") for s in top_signals)
    has_dushtana       = any(s.get("is_dushtana") for s in top_signals)

    return {
        "lal_kitab": lk, "jaimini": jai, "dasha": dasha, "transit": transit,
        "confluence": confluence,
        "karakas": karakas,
        "top_signals": top_signals,
        "dominant_domain": dominant_domain,
        "has_confluence": len(confluence) > 0,
        "has_triple_confluence": any(c["type"]=="TRIPLE CONFLUENCE" for c in confluence),
        "has_pain_signal": has_pain_signal,
        "has_rk_over_natal": has_rk_over_natal,
        "has_dushtana": has_dushtana,
        "total_rules_fired": len(all_signals),
        "total_rules_passed_filter": len(top_signals),
        "remedies": remedies,
    }


# ═══════════════════════════════════════════════════════════════
# CONTEXT BLOCK — what the LLM actually sees
# Only top signals, smartly formatted
# ═══════════════════════════════════════════════════════════════

def rules_to_context_block(rules_result: dict, concern: str = "general") -> str:
    if not rules_result:
        return ""

    karakas = rules_result.get("karakas", {})
    lines   = ["═══ ASTROLOGICAL RULE ENGINE — TOP SIGNALS ONLY ═══\n"]
    lines.append("INSTRUCTION: These are the TOP signals filtered for this specific person")
    lines.append("and their concern. Reference them by name. Don't invent signals.\n")

    # Karakas summary
    if karakas:
        karaka_labels = {
            "AK":  "Soul's core signal (Atmakaraka)",
            "AmK": "Career/path energy signal (Amatyakaraka)",
            "DK":  "Partnership significator (Darakaraka)",
            "GK":  "⚠ Obstacle/pain signal (Gnatikaraka)",
            "PK":  "Legacy/children signal (Putrakaraka)",
            "BK":  "Courage/sibling signal (Bhratrukaraka)",
            "MK":  "Mother/home signal (Matrukaraka)",
        }
        lines.append("SOUL INDICATORS (always name these in response):")
        for role, planet in karakas.items():
            label = karaka_labels.get(role, role)
            is_gk = (role == "GK")
            lines.append(f"  {'⚠ ' if is_gk else ''}{label}: {planet}")
        lines.append("")

    # Confluence first — highest impact
    for c in rules_result.get("confluence", [])[:2]:
        ctype = c["type"]
        lines.append(f"{'⚡⚡⚡' if 'TRIPLE' in ctype else '⚡⚡'} {ctype} — {c['domain'].upper()}")
        lines.append(f"  {c['message']}")
        for pred in c.get("supporting_predictions", [])[:2]:
            lines.append(f"  → {pred}")
        for warn in c.get("warnings", [])[:1]:
            lines.append(f"  ⚠ ALERT: {warn}")
        lines.append("")

    # Top filtered signals
    lines.append(f"TOP {len(rules_result.get('top_signals',[]))} SIGNALS (filtered from {rules_result.get('total_rules_fired',0)} total rules):")
    for i, s in enumerate(rules_result.get("top_signals", []), 1):
        system = s.get("system","").replace("_"," ").title()

        # Build label
        if s.get("karaka_role"):
            role_label = f"[{s['karaka_role']}: {s.get('planet','')}]"
            if s["karaka_role"] == "GK":
                role_label = f"⚠ PAIN GIVER [{s['karaka_role']}: {s.get('planet','')}]"
        elif s.get("is_rk_over_natal"):
            role_label = f"[{s.get('transit_planet','')} over natal {s.get('natal_planet','')}]"
        elif s.get("is_dushtana"):
            role_label = f"[{s.get('transit_planet','')} in H{s.get('house','')} — DUSHTANA]"
        elif s.get("is_axis_signal"):
            role_label = f"[Rahu H{s.get('rahu_house','')} / Ketu H{s.get('ketu_house','')}]"
        else:
            role_label = f"[{s.get('planet',s.get('dasha_lord',''))} H{s.get('house','')}]"

        lines.append(f"\n{i}. {system} {role_label} — {s['confidence']:.0%} confidence | domain: {s['domain']}")
        lines.append(f"   SIGNAL: {s['prediction']}")
        if s.get("warning"):
            lines.append(f"   ⚠ ALERT: {s['warning']}")
        if s.get("timeframe"):
            lines.append(f"   ⏱ WINDOW: {s['timeframe']}")
        # New concern-specific signal tags — surface to LLM
        if s.get("love_signal"):
            lines.append(f"   💛 LOVE SIGNAL: {s['love_signal']}")
        if s.get("divorce_signal"):
            lines.append(f"   ⚡ RELATIONSHIP STRESS: {s['divorce_signal']}")
        if s.get("foreign_signal"):
            lines.append(f"   ✈ FOREIGN SIGNAL: {s['foreign_signal']}")
        if s.get("speculation_signal"):
            lines.append(f"   🎯 SPECULATION SIGNAL: {s['speculation_signal']}")
        if s.get("loss_signal"):
            lines.append(f"   📉 LOSS SIGNAL: {s['loss_signal']}")
        if s.get("wealth_signal"):
            lines.append(f"   💰 WEALTH SIGNAL: {s['wealth_signal']}")
        if s.get("funding_signal"):
            lines.append(f"   🏦 FUNDING SIGNAL: {s['funding_signal']}")
        if s.get("investment_signal"):
            lines.append(f"   📈 INVESTMENT SIGNAL: {s['investment_signal']}")

    # Remedies
    remedies = rules_result.get("remedies", [])
    if remedies:
        lines.append("\n\nRECALIBRATION PRACTICES (use 2-3 of these):")
        for r in remedies[:3]:
            lines.append(f"\n✦ {r.get('mantra','')} — {r.get('mantra_count','')} {r.get('mantra_timing','')}")
            lines.append(f"  ACTION: {r.get('action','')}")
            lines.append(f"  THIS RECALIBRATES: {r.get('solves','')}")

    lines.append(f"\n\nActive concern: {concern.upper()} | Dominant domain: {rules_result.get('dominant_domain','?').upper()}")
    lines.append(f"Rules fired: {rules_result.get('total_rules_fired',0)} → filtered to: {rules_result.get('total_rules_passed_filter',0)}")
    lines.append(f"Confluence: {rules_result.get('has_confluence',False)} | Pain signal active: {rules_result.get('has_pain_signal',False)}")
    lines.append(f"Rahu/Ketu over natal: {rules_result.get('has_rk_over_natal',False)} | Dushtana transit: {rules_result.get('has_dushtana',False)}")

    # Surface active concern-specific signal summary
    top = rules_result.get("top_signals", [])
    love_sigs    = [s["love_signal"]       for s in top if s.get("love_signal")]
    divorce_sigs = [s["divorce_signal"]    for s in top if s.get("divorce_signal")]
    foreign_sigs = [s["foreign_signal"]    for s in top if s.get("foreign_signal")]
    spec_sigs    = [s["speculation_signal"] for s in top if s.get("speculation_signal")]
    loss_sigs    = [s["loss_signal"]       for s in top if s.get("loss_signal")]
    wealth_sigs  = [s["wealth_signal"]     for s in top if s.get("wealth_signal")]

    if love_sigs:    lines.append(f"LOVE PATTERNS ACTIVE: {', '.join(love_sigs)}")
    if divorce_sigs: lines.append(f"RELATIONSHIP STRESS ACTIVE: {', '.join(divorce_sigs)}")
    if foreign_sigs: lines.append(f"FOREIGN SIGNALS ACTIVE: {', '.join(foreign_sigs)}")
    if spec_sigs:
        avoid = [s for s in spec_sigs if "avoid" in s]
        active = [s for s in spec_sigs if "avoid" not in s]
        if avoid:    lines.append(f"⚠ SPECULATION PROHIBITED: {', '.join(avoid)}")
        if active:   lines.append(f"SPECULATION WINDOW: {', '.join(active)}")
    if loss_sigs:    lines.append(f"LOSS PATTERNS ACTIVE: {', '.join(loss_sigs)}")
    if wealth_sigs:  lines.append(f"WEALTH SIGNALS ACTIVE: {', '.join(wealth_sigs)}")

    lines.append("\n═══ END RULE ENGINE ═══")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# D-9 NAVAMSA COMPUTATION
# Navamsa = each sign divided into 9 parts of 3°20' each
# D9 sign = tells soul-level strength of planet
# D9 house = from D9 lagna (first planet to determine lagna)
#
# Formula:
#   navamsa_index = floor(longitude_in_sign / (30/9))
#   fire signs (0,4,8)  → start from Aries  (0)
#   earth signs(1,5,9)  → start from Capricorn (9)
#   air signs (2,6,10)  → start from Libra (6)
#   water signs(3,7,11) → start from Cancer (3)
# ═══════════════════════════════════════════════════════════════

SIGN_NAMES = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
              "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]

def compute_d9(chart_data: dict) -> dict:
    """
    Returns D9 chart: {planet: {sign_index, sign, longitude_in_d9_sign}}
    Also computes D9 lagna from the Ascendant longitude.
    """
    d9 = {}
    for planet, pdata in chart_data.get("planets", {}).items():
        lon = pdata.get("longitude", 0)
        d9_sign_index = _lon_to_d9_sign(lon)
        d9[planet] = {
            "sign_index": d9_sign_index,
            "sign": SIGN_NAMES[d9_sign_index],
        }

    # D9 lagna from ascendant longitude
    lagna_lon = chart_data.get("lagna", {}).get("longitude", 0)
    if not lagna_lon:
        # fallback: reconstruct from sign_index + degree
        si = chart_data.get("lagna", {}).get("sign_index", 0)
        deg = chart_data.get("lagna", {}).get("degree", 0)
        lagna_lon = si * 30 + deg
    d9_lagna_sign = _lon_to_d9_sign(lagna_lon)
    d9["_lagna"] = {"sign_index": d9_lagna_sign, "sign": SIGN_NAMES[d9_lagna_sign]}

    # Compute D9 house for each planet (from D9 lagna)
    for planet, pdata in d9.items():
        if planet == "_lagna":
            continue
        d9_house = ((pdata["sign_index"] - d9_lagna_sign) % 12) + 1
        pdata["house"] = d9_house

    return d9


def _lon_to_d9_sign(longitude: float) -> int:
    """Convert absolute longitude (0-360) to D9 sign index (0-11)."""
    sign_index = int(longitude / 30) % 12
    deg_in_sign = longitude % 30
    navamsa_index = int(deg_in_sign / (30 / 9))  # 0-8

    # Starting sign for each element group
    start_map = {
        0: 0,   # Aries   → fire → start Aries
        1: 9,   # Taurus  → earth → start Capricorn
        2: 6,   # Gemini  → air → start Libra
        3: 3,   # Cancer  → water → start Cancer
        4: 0,   # Leo     → fire
        5: 9,   # Virgo   → earth
        6: 6,   # Libra   → air
        7: 3,   # Scorpio → water
        8: 0,   # Sagittarius → fire
        9: 9,   # Capricorn → earth
        10: 6,  # Aquarius → air
        11: 3,  # Pisces → water
    }
    start = start_map[sign_index]
    return (start + navamsa_index) % 12


# ═══════════════════════════════════════════════════════════════
# D-9 NAVAMSA RULES
# What planet placement in D9 means for soul-level predictions
#
# Key principle:
#   D1 = what happens in life (events)
#   D9 = why it happens + soul-level strength/weakness
#   When D1 and D9 agree → VARGOTTAMA (same sign) = maximum strength
# ═══════════════════════════════════════════════════════════════

D9_PLANET_SIGN_RULES = {
    # Venus in D9 — marriage, relationships
    ("Venus", "Taurus"):    {"domain":"marriage","confidence":0.88,"prediction":"Venus in its own sign in Navamsa — marriage is a source of deep joy, beauty, and stability. The soul is oriented toward genuine love. Long-term partnership is strongly blessed at the soul level.","warning":"Don't take this blessing for granted. Venus in own D9 sign asks for active appreciation and creative investment in the relationship."},
    ("Venus", "Libra"):     {"domain":"marriage","confidence":0.88,"prediction":"Venus in Libra in Navamsa — the soul's deepest orientation is toward harmony and partnership. Marriage is a dharmic path, not just a social institution. Balance and equity in relationships are soul-level requirements.","warning":"Avoid people-pleasing in relationships. Soul-level balance means both partners flourish."},
    ("Venus", "Pisces"):    {"domain":"marriage","confidence":0.92,"prediction":"Venus exalted in Navamsa (Pisces D9) — the highest spiritual marriage placement. Soul-level love is unconditional, transcendent, and deeply compassionate. This is the placement of a truly beautiful marriage — when the right person arrives.","warning":"The exaltation can also create idealization. Ensure your partner is real, not a projection of your ideal."},
    ("Venus", "Virgo"):     {"domain":"marriage","confidence":0.72,"prediction":"Venus debilitated in Navamsa — the soul carries a pattern of perfectionism, criticism, or unworthiness in love. Past-life relationship wounds may surface in marriage.","warning":"IMPORTANT: This is not a life sentence — it is a pattern to heal. Therapy, self-compassion, and conscious communication transform this placement completely.","is_pain_signal":True},
    ("Venus", "Scorpio"):   {"domain":"marriage","confidence":0.80,"prediction":"Venus in Scorpio Navamsa — deep, intense, transformative relationships. The soul seeks profound union, not surface partnership. Marriage will go through powerful transformations and emerge stronger.","warning":"Jealousy and control patterns can emerge. Conscious work on trust and vulnerability is essential."},
    ("Venus", "Capricorn"): {"domain":"marriage","confidence":0.80,"prediction":"Venus in Capricorn Navamsa — the soul values commitment, longevity, and practical love. Marriage may come later but lasts. Status and stability in partnership are soul-level values."},

    # Jupiter in D9 — wisdom, dharma, prosperity
    ("Jupiter", "Cancer"):  {"domain":"spiritual","confidence":0.92,"prediction":"Jupiter exalted in Navamsa — the soul carries enormous wisdom, dharmic clarity, and philosophical depth. Teaching, guidance, and spiritual work are soul-level callings. This is one of the most blessed D9 placements."},
    ("Jupiter", "Sagittarius"):{"domain":"spiritual","confidence":0.88,"prediction":"Jupiter in own sign in Navamsa — the soul is a natural teacher, philosopher, and guide. Higher wisdom is not just intellectual — it's lived experience translated into guidance for others."},
    ("Jupiter", "Pisces"):  {"domain":"spiritual","confidence":0.88,"prediction":"Jupiter in own sign in Navamsa (Pisces) — the soul seeks liberation, spiritual surrender, and compassionate wisdom. Spiritual work and service are the deepest sources of meaning."},
    ("Jupiter", "Capricorn"):{"domain":"career","confidence":0.72,"prediction":"Jupiter debilitated in Navamsa — the soul may struggle with overconfidence, misjudging advice, or following false teachers. Wisdom comes through hard experience, not shortcut.","warning":"Be especially careful about who you take advice from. Verify before trusting.","is_pain_signal":True},

    # Saturn in D9 — discipline, karma, longevity
    ("Saturn", "Libra"):    {"domain":"career","confidence":0.90,"prediction":"Saturn exalted in Navamsa — the soul is built for leadership through service, justice, and enduring integrity. Career success is written at the soul level — slow, structural, and permanent. This is a profound long-term career blessing."},
    ("Saturn", "Capricorn"):{"domain":"career","confidence":0.88,"prediction":"Saturn in own sign in Navamsa — the soul's path is through discipline, mastery, and methodical achievement. What you build in this lifetime is meant to outlast you. Legacy is a soul-level mission."},
    ("Saturn", "Aquarius"): {"domain":"career","confidence":0.85,"prediction":"Saturn in own sign in Navamsa — social reform, community leadership, and systemic thinking are soul-level gifts. Your career impact is meant to be collective, not just personal."},
    ("Saturn", "Aries"):    {"domain":"career","confidence":0.70,"prediction":"Saturn debilitated in Navamsa — the soul carries impatience with structure, or past-life wounds around authority. Discipline must be consciously cultivated.","warning":"Don't abandon plans at the first obstacle. The debilitation means persistence is the exact lesson.","is_pain_signal":True},

    # Mars in D9 — energy, action, courage
    ("Mars", "Capricorn"):  {"domain":"career","confidence":0.90,"prediction":"Mars exalted in Navamsa — the soul is built for decisive action, fearless leadership, and executive power. Career and ambition are soul-level strengths. When you act from conviction, obstacles dissolve."},
    ("Mars", "Aries"):      {"domain":"career","confidence":0.85,"prediction":"Mars in own sign Navamsa — the soul is a natural pioneer, warrior, and initiator. Independent work and courageous action are soul-level orientations. You are built to start things."},
    ("Mars", "Scorpio"):    {"domain":"career","confidence":0.85,"prediction":"Mars in own sign Navamsa — the soul has enormous research, investigative, and transformative power. What others avoid, you master. Hidden matters and deep work are your soul's domain."},
    ("Mars", "Cancer"):     {"domain":"health","confidence":0.72,"prediction":"Mars debilitated in Navamsa — the soul may carry patterns of suppressed aggression or misdirected energy. Physical health needs conscious attention, especially related to gut and blood.","warning":"Regular vigorous exercise and healthy anger expression are protective.","is_pain_signal":True},

    # Sun in D9 — authority, father, soul identity
    ("Sun", "Aries"):       {"domain":"career","confidence":0.90,"prediction":"Sun exalted in Navamsa — the soul is built for authority, leadership, and pioneering identity. Confidence and self-expression are soul-level strengths. Public recognition is part of the soul's mission."},
    ("Sun", "Leo"):         {"domain":"career","confidence":0.88,"prediction":"Sun in own sign Navamsa — the soul radiates authority and creative self-expression. Leadership is not a role — it is your natural state of being. Career in public, creative, or executive roles is soul-aligned."},
    ("Sun", "Libra"):       {"domain":"career","confidence":0.68,"prediction":"Sun debilitated in Navamsa — the soul may struggle with authority, father wounds, or lack of confidence in its own identity. Self-doubt can undermine otherwise strong natal placements.","warning":"Self-worth work and leadership mentoring are specifically protective for this placement.","is_pain_signal":True},

    # Moon in D9 — mind, mother, emotional intelligence
    ("Moon", "Taurus"):     {"domain":"health","confidence":0.90,"prediction":"Moon exalted in Navamsa — the soul's emotional intelligence is profound and deeply stable. Mental peace, intuition, and nurturing capacity are soul-level gifts. This is one of the best placements for emotional resilience."},
    ("Moon", "Cancer"):     {"domain":"family","confidence":0.88,"prediction":"Moon in own sign Navamsa — the soul is deeply intuitive, nurturing, and emotionally connected. Home, mother, and family are soul-level anchors. Emotional intelligence is your greatest leadership tool."},
    ("Moon", "Scorpio"):    {"domain":"health","confidence":0.72,"prediction":"Moon debilitated in Navamsa — the soul carries emotional intensity, deep feeling, and possibly past-life trauma around security or mother. Emotional healing is a soul-level mission.","warning":"Therapy, journaling, and consistent emotional hygiene practices are specifically strengthening for this placement.","is_pain_signal":True},

    # Mercury in D9 — intellect, communication
    ("Mercury", "Gemini"):  {"domain":"career","confidence":0.85,"prediction":"Mercury in own sign Navamsa — the soul is a natural communicator, teacher, and networker. Intelligence is a soul-level gift meant to be shared generously."},
    ("Mercury", "Virgo"):   {"domain":"career","confidence":0.85,"prediction":"Mercury in own sign Navamsa — the soul's analytical precision and attention to detail are gifts. Research, systems thinking, and mastery of craft are soul-level orientations."},
}

# D9 HOUSE RULES — what house the planet occupies in Navamsa
D9_HOUSE_RULES = {
    ("Venus", 1):  {"domain":"marriage","confidence":0.85,"prediction":"Venus in D9 ascendant — marriage is central to your soul's identity. The spouse will be a defining presence. Partnership is not optional for your wellbeing — it is part of your dharma."},
    ("Venus", 7):  {"domain":"marriage","confidence":0.90,"prediction":"Venus in D9 7th — the strongest marriage placement in Navamsa. The soul's purpose includes deep, lasting partnership. Marriage brings out your highest self. What you build together is greater than either alone."},
    ("Venus", 4):  {"domain":"marriage","confidence":0.82,"prediction":"Venus in D9 4th — the soul finds home through partnership. Marriage and domestic happiness are deeply intertwined. A loving, beautiful home environment is a soul-level need."},
    ("Venus", 12): {"domain":"marriage","confidence":0.78,"prediction":"Venus in D9 12th — spiritual love, foreign partner, or deeply private relationship is soul-aligned. The marriage has an otherworldly, sacred quality. Bedroom happiness is a soul-level gift."},
    ("Jupiter", 1):{"domain":"spiritual","confidence":0.88,"prediction":"Jupiter in D9 ascendant — wisdom and dharma are core to the soul's identity. Teaching, guiding, and expanding others' consciousness is part of your soul's mission this lifetime."},
    ("Jupiter", 9):{"domain":"spiritual","confidence":0.90,"prediction":"Jupiter in D9 9th — the strongest dharmic placement in Navamsa. Higher wisdom, spiritual teaching, and philosophical mastery are the soul's deepest calling. You are meant to be a guide."},
    ("Saturn", 10):{"domain":"career","confidence":0.90,"prediction":"Saturn in D9 10th — the soul's mission is built through career and public contribution. Professional legacy is not ambition — it is soul-level dharma. What you build professionally outlasts your lifetime."},
    ("Mars", 10):  {"domain":"career","confidence":0.85,"prediction":"Mars in D9 10th — the soul is a natural executive, warrior, and achiever. Decisive action in career is a soul-level calling. Leadership roles are not a destination — they are your natural habitat."},
    ("Sun", 10):   {"domain":"career","confidence":0.88,"prediction":"Sun in D9 10th — public authority and recognition are soul-level themes. Leadership, government, and institutional roles are soul-aligned. Your name in the public sphere is part of your dharmic path."},
    ("Moon", 4):   {"domain":"family","confidence":0.85,"prediction":"Moon in D9 4th — home and emotional security are the soul's foundation. Creating a nurturing, beautiful home environment is one of your deepest soul-level needs and gifts."},
    ("Rahu", 7):   {"domain":"marriage","confidence":0.80,"prediction":"Rahu in D9 7th — karmic, unusual, or cross-cultural partnership is soul-level destiny. The relationship will be transformative and may break family expectations. This is intentional at the soul level.","warning":"Ensure the partner is grounded — Rahu in D9 7th can create intense attraction without lasting substance."},
    ("Ketu", 7):   {"domain":"marriage","confidence":0.78,"prediction":"Ketu in D9 7th — past-life partnership karma. The soul is completing a deep relationship cycle. Marriage may feel like a recognition rather than a new meeting. Spiritual partnership is more fulfilling than conventional marriage for this placement."},
}

# VARGOTTAMA CHECK — same sign in D1 and D9 = maximum strength
def check_vargottama(chart_data: dict, d9: dict) -> list:
    """
    Vargottama = planet occupies same sign in D1 and D9.
    This is the highest strength indicator — the planet expresses
    its fullest potential across both the physical and soul levels.
    """
    vargottama = []
    for planet, pdata in chart_data.get("planets", {}).items():
        d1_sign = pdata.get("sign_index", -1)
        d9_sign = d9.get(planet, {}).get("sign_index", -2)
        if d1_sign == d9_sign and d1_sign >= 0:
            domain_map = {
                "Sun":"career","Moon":"health","Mars":"career","Mercury":"career",
                "Jupiter":"spiritual","Venus":"marriage","Saturn":"career",
                "Rahu":"career","Ketu":"spiritual"
            }
            vargottama.append({
                "system": "d9_vargottama",
                "planet": planet,
                "sign": SIGN_NAMES[d1_sign],
                "rule_id": f"VARG_{planet}",
                "domain": domain_map.get(planet,"general"),
                "confidence": 0.92,
                "prediction": (
                    f"{planet} is Vargottama — same sign in both your birth chart and soul chart ({SIGN_NAMES[d1_sign]}). "
                    f"This is the highest strength indicator in Vedic astrology. "
                    f"{planet}'s qualities are expressed at maximum power across both your material life and soul path. "
                    f"What {planet} represents in your chart is not just circumstantial — it is your deepest nature."
                ),
                "warning": "",
                "remedy_planet": planet,
                "concern_relevance": 0.85,
                "is_vargottama": True,
            })
    return vargottama


# ═══════════════════════════════════════════════════════════════
# YOGA DETECTION ENGINE
# Yogas = planetary combinations that create specific life outcomes
#
# Priority yogas (highest user impact):
#   Raj Yoga       — authority and power combinations
#   Dhana Yoga     — wealth combinations
#   Viparita Raj   — reversals that ultimately create power
#   Gajakesari     — Jupiter-Moon combination (wisdom + wealth)
#   Budhaditya     — Sun-Mercury (intelligence in career)
#   Panch Mahapurusha — planet in own/exalted sign in kendra
#   Hamsa          — Jupiter in kendra in own/exalt
#   Malavya        — Venus in kendra in own/exalt
#   Sasa           — Saturn in kendra in own/exalt
#   Ruchaka        — Mars in kendra in own/exalt
#   Bhadra         — Mercury in kendra in own/exalt
# ═══════════════════════════════════════════════════════════════

# Own signs and exaltation signs per planet
OWN_SIGNS = {
    "Sun": [4],           # Leo
    "Moon": [3],          # Cancer
    "Mars": [0, 7],       # Aries, Scorpio
    "Mercury": [2, 5],    # Gemini, Virgo
    "Jupiter": [8, 11],   # Sagittarius, Pisces
    "Venus": [1, 6],      # Taurus, Libra
    "Saturn": [9, 10],    # Capricorn, Aquarius
}
EXALT_SIGNS = {
    "Sun": 0,      # Aries
    "Moon": 1,     # Taurus
    "Mars": 9,     # Capricorn
    "Mercury": 5,  # Virgo
    "Jupiter": 3,  # Cancer
    "Venus": 11,   # Pisces
    "Saturn": 6,   # Libra
}
DEBIT_SIGNS = {
    "Sun": 6,      # Libra
    "Moon": 7,     # Scorpio
    "Mars": 3,     # Cancer
    "Mercury": 11, # Pisces
    "Jupiter": 9,  # Capricorn
    "Venus": 5,    # Virgo
    "Saturn": 0,   # Aries
}
KENDRA_HOUSES = {1, 4, 7, 10}
TRIKONA_HOUSES = {1, 5, 9}
DUSHTANA_HOUSES = {6, 8, 12}


def _planet_sign(chart_data: dict, planet: str) -> int:
    return chart_data.get("planets", {}).get(planet, {}).get("sign_index", -1)

def _planet_house(chart_data: dict, planet: str) -> int:
    return chart_data.get("planets", {}).get(planet, {}).get("house", -1)

def _is_own_or_exalt(planet: str, sign_index: int) -> bool:
    return (sign_index in OWN_SIGNS.get(planet, []) or
            sign_index == EXALT_SIGNS.get(planet, -1))

def _is_in_house(chart_data: dict, planet: str, houses: set) -> bool:
    return _planet_house(chart_data, planet) in houses


def detect_yogas(chart_data: dict, concern: str = "general") -> list:
    """
    Detect all active yogas from D1 chart.
    Returns list of yoga dicts with domain, confidence, prediction, warning.
    """
    yogas = []
    planets = chart_data.get("planets", {})
    lagna_si = chart_data.get("lagna", {}).get("sign_index", 0)

    # ── PANCH MAHAPURUSHA YOGAS ────────────────────────────────
    # Planet in kendra (1/4/7/10) in own or exalted sign
    pancha_map = {
        "Mars":    ("Ruchaka",    "career",   0.88,
                    "Ruchaka Yoga (Mars in kendra, own/exalt) — a warrior's chart. You are built for decisive action, fearless leadership, and physical and professional courage. Success comes through boldness and direct execution."),
        "Mercury": ("Bhadra",     "career",   0.85,
                    "Bhadra Yoga (Mercury in kendra, own/exalt) — an intellectual's chart. Business, communication, writing, and analytical excellence are your natural power zones. Intelligence is your career superpower."),
        "Jupiter": ("Hamsa",      "spiritual",0.90,
                    "Hamsa Yoga (Jupiter in kendra, own/exalt) — a teacher's chart. Wisdom, dharma, and expansion are written into your professional destiny. You are meant to guide, teach, and elevate others. This is one of the most auspicious yogas in Vedic astrology."),
        "Venus":   ("Malavya",    "marriage", 0.88,
                    "Malavya Yoga (Venus in kendra, own/exalt) — a chart of beauty, love, and abundance. Relationships, creativity, and luxury are your natural domain. Marriage and partnerships are particularly blessed. Artistic and aesthetic work is soul-aligned."),
        "Saturn":  ("Sasa",       "career",   0.87,
                    "Sasa Yoga (Saturn in kendra, own/exalt) — a builder's chart. Mastery through discipline, structural thinking, and long-term vision are your gifts. Career success may come after 35 but is exceptionally durable. You build things that outlast you."),
    }
    for planet, (name, domain, conf, pred) in pancha_map.items():
        house = _planet_house(chart_data, planet)
        sign  = _planet_sign(chart_data, planet)
        if house in KENDRA_HOUSES and _is_own_or_exalt(planet, sign):
            yogas.append({
                "system": "yoga", "yoga_name": name, "planet": planet,
                "rule_id": f"YOGA_{name.upper()}",
                "domain": domain, "confidence": conf,
                "prediction": pred, "warning": "",
                "remedy_planet": planet,
                "concern_relevance": 0.92 if domain == concern else 0.65,
            })

    # ── GAJAKESARI YOGA ────────────────────────────────────────
    # Jupiter in kendra from Moon (1/4/7/10 houses from Moon's position)
    moon_house  = _planet_house(chart_data, "Moon")
    jup_house   = _planet_house(chart_data, "Jupiter")
    if moon_house > 0 and jup_house > 0:
        diff = ((jup_house - moon_house) % 12) + 1
        # kendra from Moon = 1, 4, 7, 10 houses away
        if diff in (1, 4, 7, 10):
            yogas.append({
                "system": "yoga", "yoga_name": "Gajakesari",
                "planet": "Jupiter/Moon",
                "rule_id": "YOGA_GAJAKESARI",
                "domain": "general", "confidence": 0.88,
                "prediction": (
                    "Gajakesari Yoga (Jupiter in kendra from Moon) — one of the most celebrated yogas. "
                    "Wisdom meets emotional intelligence. You are naturally magnetic, respected, and trusted. "
                    "Success comes through reputation and the genuine desire to help others. "
                    "This yoga produces people who are remembered long after they are gone."
                ),
                "warning": "",
                "remedy_planet": "Jupiter",
                "concern_relevance": 0.88,
            })

    # ── BUDHADITYA YOGA ────────────────────────────────────────
    # Sun and Mercury in same house
    sun_house = _planet_house(chart_data, "Sun")
    mer_house = _planet_house(chart_data, "Mercury")
    if sun_house > 0 and sun_house == mer_house:
        yogas.append({
            "system": "yoga", "yoga_name": "Budhaditya",
            "planet": "Sun/Mercury",
            "rule_id": "YOGA_BUDHADITYA",
            "domain": "career", "confidence": 0.85,
            "prediction": (
                "Budhaditya Yoga (Sun + Mercury in same house) — the yoga of brilliant intelligence. "
                "Your mind and your identity are fused — intellect, communication, and authority work as one unit. "
                "Writing, speaking, teaching, consulting, and analytical work carry unusual power. "
                "People remember what you say."
            ),
            "warning": "Can create Mercury combustion if degrees are close — double-check before launching major communication projects.",
            "remedy_planet": "Mercury",
            "concern_relevance": 0.90 if concern == "career" else 0.65,
        })

    # ── RAJ YOGA ───────────────────────────────────────────────
    # Lord of kendra (1/4/7/10) conjunct or aspects lord of trikona (1/5/9)
    # Simplified: planets ruling kendra and trikona houses in same house
    def house_lord(house_num: int, lagna: int) -> str:
        """Returns the lord of a house based on lagna sign."""
        sign_of_house = (lagna + house_num - 1) % 12
        lords = {
            0:"Sun",1:"Moon",2:"Mars",3:"Mars",4:"Jupiter",5:"Jupiter",
            6:"Saturn",7:"Saturn",8:"Saturn",9:"Jupiter",10:"Venus",11:"Venus",
            # Note: more accurate with proper lordship table but this covers core cases
        }
        # Standard sign lords (Aries=Mars, Taurus=Venus, etc.)
        sign_lords = [
            "Mars","Venus","Mercury","Moon","Sun","Mercury",
            "Venus","Mars","Jupiter","Saturn","Saturn","Jupiter"
        ]
        return sign_lords[sign_of_house]

    kendra_lords = {house_lord(h, lagna_si) for h in [1, 4, 7, 10]}
    trikona_lords = {house_lord(h, lagna_si) for h in [1, 5, 9]}
    raj_yoga_planets = kendra_lords & trikona_lords

    for planet in raj_yoga_planets:
        if planet in ("Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn"):
            house = _planet_house(chart_data, planet)
            if house in KENDRA_HOUSES or house in TRIKONA_HOUSES:
                yogas.append({
                    "system": "yoga", "yoga_name": "Raj Yoga",
                    "planet": planet,
                    "rule_id": f"YOGA_RAJ_{planet}",
                    "domain": "career", "confidence": 0.87,
                    "prediction": (
                        f"Raj Yoga through {planet} — a chart with genuine authority potential. "
                        f"{planet} rules both a power house and a dharma house simultaneously, creating a direct channel "
                        f"from effort to recognition. This yoga matures after the age of 35 and peaks in Saturn dasha "
                        f"or during the dasha of the yoga-forming planet."
                    ),
                    "warning": f"Raj Yoga requires activation — it is potential, not guarantee. The dasha of {planet} is when this fully opens.",
                    "remedy_planet": planet,
                    "concern_relevance": 0.90 if concern == "career" else 0.65,
                })

    # ── DHANA YOGA ─────────────────────────────────────────────
    # Lord of 2H or 11H with lord of 1H, 5H, or 9H
    lord_2  = house_lord(2,  lagna_si)
    lord_11 = house_lord(11, lagna_si)
    lord_1  = house_lord(1,  lagna_si)
    lord_5  = house_lord(5,  lagna_si)
    lord_9  = house_lord(9,  lagna_si)

    wealth_lords   = {lord_2, lord_11}
    trikona_lords2 = {lord_1, lord_5, lord_9}

    for wp in wealth_lords:
        for tp in trikona_lords2:
            if wp == tp:
                continue
            wp_house = _planet_house(chart_data, wp)
            tp_house = _planet_house(chart_data, tp)
            if wp_house > 0 and wp_house == tp_house:
                yogas.append({
                    "system": "yoga", "yoga_name": "Dhana Yoga",
                    "planet": f"{wp}/{tp}",
                    "rule_id": f"YOGA_DHANA_{wp}_{tp}",
                    "domain": "wealth", "confidence": 0.85,
                    "prediction": (
                        f"Dhana Yoga ({wp} + {tp} conjunct) — a wealth yoga. "
                        f"The wealth house lord and dharma house lord are combined, creating a direct pipeline "
                        f"from your purpose to your prosperity. Financial growth is not accidental — "
                        f"it comes when you work in full alignment with your core strengths."
                    ),
                    "warning": "Dhana Yoga requires effort — it multiplies directed work, not passive waiting.",
                    "remedy_planet": wp,
                    "concern_relevance": 0.90 if concern == "wealth" else 0.60,
                })

    # ── VIPARITA RAJ YOGA ──────────────────────────────────────
    # Lord of dushtana (6/8/12) placed in another dushtana house
    # Reversal yoga — destruction of obstacles becomes power
    for house_num in [6, 8, 12]:
        lord = house_lord(house_num, lagna_si)
        lord_placed_in = _planet_house(chart_data, lord)
        if lord_placed_in in DUSHTANA_HOUSES and lord_placed_in != house_num:
            yogas.append({
                "system": "yoga", "yoga_name": "Viparita Raj Yoga",
                "planet": lord,
                "rule_id": f"YOGA_VIPARITA_H{house_num}",
                "domain": "career", "confidence": 0.83,
                "prediction": (
                    f"Viparita Raj Yoga — the reversal yoga. The lord of your {house_num}th house "
                    f"(obstacles, transformation) is placed in a house of dissolution, causing your obstacles "
                    f"to dissolve each other. What appears to be setbacks in life have a pattern of reversing "
                    f"into unexpected victories. Your greatest career breakthroughs often come after apparent defeats."
                ),
                "warning": "This yoga activates most powerfully during the dasha of the involved planet. The reversal is real but not instant.",
                "remedy_planet": lord,
                "concern_relevance": 0.85 if concern == "career" else 0.60,
            })

    # ── KEMADRUMA YOGA (pain yoga — moon without support) ──────
    # Moon with no planets in adjacent houses (2H and 12H from Moon)
    moon_house = _planet_house(chart_data, "Moon")
    if moon_house > 0:
        adjacent_houses = {((moon_house - 2) % 12) + 1, (moon_house % 12) + 1}
        planets_in_adjacent = {
            _planet_house(chart_data, p) for p in planets
            if p not in ("Moon", "Rahu", "Ketu")
        }
        if not adjacent_houses & planets_in_adjacent:
            yogas.append({
                "system": "yoga", "yoga_name": "Kemadruma",
                "planet": "Moon",
                "rule_id": "YOGA_KEMADRUMA",
                "domain": "health", "confidence": 0.72,
                "prediction": (
                    "Kemadruma Yoga — Moon without adjacent planetary support. "
                    "The mind can feel isolated, misunderstood, or emotionally unsupported at times. "
                    "Financial fluctuations tied to emotional cycles are possible. "
                    "This is a pattern to work with consciously, not a sentence."
                ),
                "warning": "Strong Jupiter aspect on Moon cancels this yoga. Check if Jupiter aspects Moon — if yes, Kemadruma is nullified.",
                "remedy_planet": "Moon",
                "concern_relevance": 0.80 if concern == "health" else 0.55,
                "is_pain_signal": True,
            })

    return yogas


# ═══════════════════════════════════════════════════════════════
# UPDATED apply_d9_rules and apply_yoga_rules
# ═══════════════════════════════════════════════════════════════

def apply_d9_rules(chart_data: dict, concern: str) -> list:
    """Apply D9 Navamsa rules — planet in sign + planet in house + vargottama."""
    d9 = compute_d9(chart_data)
    signals = []

    # Planet-sign rules
    for planet, pdata in d9.items():
        if planet == "_lagna":
            continue
        sign = pdata.get("sign", "")
        rule = D9_PLANET_SIGN_RULES.get((planet, sign))
        if rule:
            signals.append({
                "system": "d9_navamsa",
                "planet": planet,
                "house": pdata.get("house", 0),
                "d9_sign": sign,
                "rule_id": f"D9_{planet}_{sign.replace(' ','_')}",
                "domain": rule["domain"],
                "confidence": rule["confidence"],
                "prediction": rule["prediction"],
                "warning": rule.get("warning", ""),
                "remedy_planet": planet,
                "concern_relevance": 0.90 if rule["domain"] == concern else 0.58,
                "is_pain_signal": rule.get("is_pain_signal", False),
            })

    # Planet-house rules in D9
    for planet, pdata in d9.items():
        if planet == "_lagna":
            continue
        house = pdata.get("house", 0)
        rule  = D9_HOUSE_RULES.get((planet, house))
        if rule:
            signals.append({
                "system": "d9_navamsa_house",
                "planet": planet,
                "house": house,
                "rule_id": f"D9H_{planet}_H{house}",
                "domain": rule["domain"],
                "confidence": rule["confidence"],
                "prediction": rule["prediction"],
                "warning": rule.get("warning", ""),
                "remedy_planet": planet,
                "concern_relevance": 0.90 if rule["domain"] == concern else 0.58,
            })

    # Vargottama
    vargottama = check_vargottama(chart_data, d9)
    signals.extend(vargottama)

    return signals


def apply_yoga_rules(chart_data: dict, concern: str) -> list:
    """Detect all classical yogas from D1 chart."""
    return detect_yogas(chart_data, concern)


# ═══════════════════════════════════════════════════════════════
# PATCH run_all_rules to include D9 + Yogas
# ═══════════════════════════════════════════════════════════════

# Save reference to original function
_run_all_rules_v1 = run_all_rules

def run_all_rules(chart_data: dict, dashas: dict, current_transits,
                  concern: str = "general", country_code: str = "IN") -> dict:
    """
    Extended run_all_rules with D9 Navamsa + Yoga detection.
    Drops cleanly on top of v1 — same return shape, more signals.
    """
    # Run base rules
    result = _run_all_rules_v1(chart_data, dashas, current_transits, concern, country_code)

    # Add D9 and Yoga signals
    d9_signals    = apply_d9_rules(chart_data, concern)
    yoga_signals  = apply_yoga_rules(chart_data, concern)

    # Add to lal_kitab/jaimini pools for confluence detection
    all_new = d9_signals + yoga_signals

    # Re-run confluence with new signals included
    from collections import Counter as _Counter
    new_confluence = detect_triple_confluence(
        result["lal_kitab"] + d9_signals,
        result["dasha"],
        result["transit"],
    )

    # Re-rank including new signals
    all_signals_extended = (
        result["lal_kitab"] + result["jaimini"] +
        result["dasha"] + result["transit"] +
        d9_signals + yoga_signals
    )
    karakas = result["karakas"]
    top_signals = rank_signals(all_signals_extended, concern, karakas)

    # Rebuild remedies from new top signals
    seen_planets = set()
    remedies = []
    for s in top_signals:
        rp = s.get("remedy_planet", "")
        if rp and rp not in seen_planets:
            rem = format_remedy_for_location(rp, country_code)
            if rem:
                rem["for_domain"] = s["domain"]
                remedies.append(rem)
                seen_planets.add(rp)
        if len(remedies) >= 3:
            break

    # Detect special signal types
    has_yoga        = any(s.get("system") == "yoga" for s in top_signals)
    has_vargottama  = any(s.get("is_vargottama") for s in top_signals)
    has_d9          = any(s.get("system","").startswith("d9") for s in top_signals)

    domain_votes = _Counter(s["domain"] for s in all_signals_extended)
    dominant_domain = domain_votes.most_common(1)[0][0] if domain_votes else "general"

    return {
        **result,   # all original fields preserved
        "d9":               d9_signals,
        "yogas":            yoga_signals,
        "confluence":       new_confluence,
        "top_signals":      top_signals,
        "dominant_domain":  dominant_domain,
        "has_yoga":         has_yoga,
        "has_vargottama":   has_vargottama,
        "has_d9_signal":    has_d9,
        "total_rules_fired": len(all_signals_extended),
        "total_rules_passed_filter": len(top_signals),
        "remedies":         remedies,
        "yoga_names":       [y.get("yoga_name","") for y in yoga_signals],
    }


# ═══════════════════════════════════════════════════════════════
# V3 INTEGRATION — patch run_all_rules to include all extended rules
# ═══════════════════════════════════════════════════════════════

# Save v2 reference
_run_all_rules_v2 = run_all_rules

def run_all_rules(chart_data: dict, dashas: dict, current_transits,
                  concern: str = "general", country_code: str = "IN",
                  user_age: int = 40) -> dict:
    """
    FINAL run_all_rules — v1 (base) + v2 (D9+yogas) + v3 (full engine).
    All 15 missing categories now wired.
    """
    # Run v2 base
    result = _run_all_rules_v2(chart_data, dashas, current_transits, concern, country_code)

    # Run v3 extended
    try:
        from antar_engine.astrological_rules_v3_addon import apply_all_extended_rules
        v3 = apply_all_extended_rules(
            chart_data=chart_data, dashas=dashas,
            current_transits=current_transits, concern=concern,
            country_code=country_code, user_age=user_age,
        )
    except ImportError:
        # Fallback: try loading from same dir (for testing)
        try:
            import sys, os
            sys.path.insert(0, os.path.dirname(__file__))
            from astrological_rules_v3_addon import apply_all_extended_rules
            v3 = apply_all_extended_rules(
                chart_data=chart_data, dashas=dashas,
                current_transits=current_transits, concern=concern,
                country_code=country_code, user_age=user_age,
            )
        except Exception as e:
            print(f"  [v3 addon] not available: {e}")
            v3 = {"all_new": [], "has_sade_sati": False,
                  "has_antardasha_signal": False, "total_new_signals": 0,
                  "yoga_names_full": [], "d_charts": {}}

    # Apply Ashtakavarga boost to existing transit signals
    try:
        from antar_engine.astrological_rules_v3_addon import apply_ashtakavarga_transit_boost
        boosted_transit = apply_ashtakavarga_transit_boost(result["transit"], current_transits)
        result["transit"] = boosted_transit
    except Exception:
        pass

    # Merge all signals
    all_new = v3.get("all_new", [])
    all_signals_full = (
        result["lal_kitab"] + result["jaimini"] +
        result["dasha"] + result["transit"] +
        result.get("d9", []) + result.get("yogas", []) +
        all_new
    )

    # Re-rank with full signal set
    karakas = result["karakas"]
    top_signals = rank_signals(all_signals_full, concern, karakas)

    # Rebuild confluence with full signal set
    new_confluence = detect_triple_confluence(
        result["lal_kitab"] + result.get("d9",[]) + v3.get("divisional",[]),
        result["dasha"] + v3.get("antardasha",[]),
        result["transit"] + v3.get("nakshatra",[]),
    )

    # Rebuild remedies
    from antar_engine.astrological_rules_v2 import format_remedy_for_location
    seen_planets = set()
    remedies = []
    for s in top_signals:
        rp = s.get("remedy_planet","")
        if rp and rp not in seen_planets:
            rem = format_remedy_for_location(rp, country_code)
            if rem:
                rem["for_domain"] = s["domain"]
                remedies.append(rem)
                seen_planets.add(rp)
        if len(remedies) >= 3:
            break

    from collections import Counter as _C
    domain_votes = _C(s["domain"] for s in all_signals_full)
    dominant_domain = domain_votes.most_common(1)[0][0] if domain_votes else "general"

    return {
        **result,
        # New signal categories
        "yoga_engine":          v3.get("yoga_engine",[]),
        "divisional":           v3.get("divisional",[]),
        "antardasha":           v3.get("antardasha",[]),
        "sade_sati":            v3.get("sade_sati"),
        "nakshatra":            v3.get("nakshatra",[]),
        "lk_aspects":           v3.get("lk_aspects",[]),
        "lk_rin":               v3.get("lk_rin",[]),
        "varshphal":            v3.get("varshphal",[]),
        "d_charts":             v3.get("d_charts",{}),
        # Updated aggregates
        "confluence":           new_confluence,
        "top_signals":          top_signals,
        "dominant_domain":      dominant_domain,
        "remedies":             remedies,
        "total_rules_fired":    len(all_signals_full),
        "total_rules_passed_filter": len(top_signals),
        # Metadata flags
        "has_sade_sati":        v3.get("has_sade_sati", False),
        "has_antardasha_signal":v3.get("has_antardasha_signal", False),
        "yoga_names_full":      list({*result.get("yoga_names",[]), *v3.get("yoga_names_full",[])}),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION LAYER v3
# Wires yoga_engine, d_charts_calculator, vimsottari antardasha,
# lal_kitab Varshphal, Sade Sati, and Nakshatra transit rules
# into the signal pipeline.
#
# DESIGN PRINCIPLE:
#   Each existing engine already computes the right math.
#   This layer TRANSLATES their outputs into ranked signals
#   in the same format as all other rules:
#   { system, rule_id, domain, confidence, prediction, warning,
#     remedy_planet, concern_relevance }
# ═══════════════════════════════════════════════════════════════════════════════

from datetime import datetime, timezone as _tz

# ── NAKSHATRA DATA ─────────────────────────────────────────────────────────────
# 27 Nakshatras with their lords and key properties
NAKSHATRA_DATA = [
    {"name":"Ashwini",     "lord":"Ketu",    "index":0},
    {"name":"Bharani",     "lord":"Venus",   "index":1},
    {"name":"Krittika",    "lord":"Sun",     "index":2},
    {"name":"Rohini",      "lord":"Moon",    "index":3},
    {"name":"Mrigashira",  "lord":"Mars",    "index":4},
    {"name":"Ardra",       "lord":"Rahu",    "index":5},
    {"name":"Punarvasu",   "lord":"Jupiter", "index":6},
    {"name":"Pushya",      "lord":"Saturn",  "index":7},
    {"name":"Ashlesha",    "lord":"Mercury", "index":8},
    {"name":"Magha",       "lord":"Ketu",    "index":9},
    {"name":"Purva Phalguni","lord":"Venus", "index":10},
    {"name":"Uttara Phalguni","lord":"Sun",  "index":11},
    {"name":"Hasta",       "lord":"Moon",    "index":12},
    {"name":"Chitra",      "lord":"Mars",    "index":13},
    {"name":"Swati",       "lord":"Rahu",    "index":14},
    {"name":"Vishakha",    "lord":"Jupiter", "index":15},
    {"name":"Anuradha",    "lord":"Saturn",  "index":16},
    {"name":"Jyeshtha",    "lord":"Mercury", "index":17},
    {"name":"Mula",        "lord":"Ketu",    "index":18},
    {"name":"Purva Ashadha","lord":"Venus",  "index":19},
    {"name":"Uttara Ashadha","lord":"Sun",   "index":20},
    {"name":"Shravana",    "lord":"Moon",    "index":21},
    {"name":"Dhanishtha",  "lord":"Mars",    "index":22},
    {"name":"Shatabhisha", "lord":"Rahu",    "index":23},
    {"name":"Purva Bhadra","lord":"Jupiter", "index":24},
    {"name":"Uttara Bhadra","lord":"Saturn", "index":25},
    {"name":"Revati",      "lord":"Mercury", "index":26},
]

# Tara (transit nakshatra relationship to natal Moon nakshatra)
# Position from birth nakshatra → meaning
TARA_MEANINGS = {
    1:  ("Janma",     "health",   0.78, "Transit nakshatra is your birth star — physical and mental stress, identity challenges. Keep health routines strict.", True),
    2:  ("Sampat",    "wealth",   0.82, "Transit nakshatra is your wealth star — excellent for financial decisions, investments, and new income sources.", False),
    3:  ("Vipat",     "health",   0.80, "Transit nakshatra is your danger star — increased risk of accidents, conflicts, or sudden reversals. Move carefully.", True),
    4:  ("Kshema",    "general",  0.80, "Transit nakshatra is your prosperity star — overall wellbeing is supported. Good for starting new ventures.", False),
    5:  ("Pratyak",   "health",   0.75, "Transit nakshatra is your obstacle star — delays and frustrations are more likely. Patience is protective.", True),
    6:  ("Sadhana",   "career",   0.82, "Transit nakshatra is your achievement star — efforts are rewarded. Hard work in this window gets recognized.", False),
    7:  ("Naidhana",  "health",   0.85, "Transit nakshatra is your death star — the most challenging tara. Major caution in decisions, especially travel and legal matters.", True),
    8:  ("Mitra",     "marriage", 0.80, "Transit nakshatra is your friend star — relationships, partnerships, and collaborations are strongly supported.", False),
    9:  ("Parama Mitra","general",0.85, "Transit nakshatra is your best friend star — the most auspicious tara. Major decisions, launches, and commitments made now carry strong divine support.", False),
}


def _get_nakshatra_index(longitude: float) -> int:
    """Convert longitude to nakshatra index (0-26)."""
    return int((longitude % 360) / (360 / 27))


def apply_nakshatra_transit_rules(chart_data: dict, current_transits: list, concern: str) -> list:
    """
    Tara system: relationship between transiting planet's nakshatra
    and the natal Moon's nakshatra.
    Especially powerful for Sun, Moon, Mars, Jupiter, Saturn transits.
    """
    signals = []
    moon_lon = chart_data.get("planets", {}).get("Moon", {}).get("longitude", 0)
    birth_nak_idx = _get_nakshatra_index(moon_lon)

    key_planets = {"Sun", "Moon", "Mars", "Jupiter", "Saturn"}

    for t in current_transits:
        planet = t.get("planet", "")
        if planet not in key_planets:
            continue
        tr_lon = t.get("longitude", t.get("transit_longitude", 0))
        if not tr_lon:
            continue
        tr_nak_idx = _get_nakshatra_index(tr_lon)
        tr_nak = NAKSHATRA_DATA[tr_nak_idx]

        # Tara position = how many nakshatras from birth nak (1-9, cycling)
        tara_pos = ((tr_nak_idx - birth_nak_idx) % 27) % 9
        if tara_pos == 0:
            tara_pos = 9  # same nakshatra = Parama Mitra

        tara = TARA_MEANINGS.get(tara_pos)
        if not tara:
            continue

        tara_name, domain, conf, pred, is_pain = tara

        # Only surface Vipat (3), Naidhana (7), Janma (1) as pain signals
        # and Sampat (2), Sadhana (6), Parama Mitra (9) as opportunity signals
        if tara_pos not in (1, 2, 3, 6, 7, 9):
            continue

        signals.append({
            "system": "nakshatra_tara",
            "transit_planet": planet,
            "nakshatra": tr_nak["name"],
            "tara": tara_name,
            "tara_position": tara_pos,
            "rule_id": f"TARA_{planet}_{tara_name}",
            "domain": domain,
            "confidence": conf,
            "prediction": f"{planet} transiting {tr_nak['name']} ({tara_name} tara for you) — {pred}",
            "warning": pred if is_pain else "",
            "remedy_planet": planet,
            "concern_relevance": 0.88 if domain == concern else 0.55,
            "is_pain_signal": is_pain,
            "timeframe": "~days to weeks (nakshatra transit)",
        })

    return signals


# ── SADE SATI — Full 3-Phase ───────────────────────────────────────────────────

def check_sade_sati(chart_data: dict, current_transits: list) -> list:
    """
    Sade Sati = Saturn transiting 12H, 1H, 2H FROM natal Moon sign.
    Three phases, each ~2.5 years. Total = 7.5 years.
    Phase 1 (12H from Moon): preparation, mental pressure, sleep issues
    Phase 2 (1H = Moon sign): identity crisis, peak pressure, transformation
    Phase 3 (2H from Moon): financial restructuring, family stress, release
    """
    signals = []
    moon_sign_idx = chart_data.get("planets", {}).get("Moon", {}).get("sign_index", -1)
    if moon_sign_idx < 0:
        return signals

    saturn_transit = next((t for t in current_transits if t.get("planet") == "Saturn"), None)
    if not saturn_transit:
        return signals

    sat_sign_idx = saturn_transit.get("sign_index", saturn_transit.get("transit_sign_index", -1))
    if sat_sign_idx < 0:
        return signals

    # Phase detection
    diff = (sat_sign_idx - moon_sign_idx) % 12

    phase_data = {
        11: (1, "PREPARATION PHASE",
             "Saturn has entered the 12th sign from your Moon — Sade Sati Phase 1 has begun. "
             "This is the preparation phase: sleep may be disrupted, spiritual questions surface, "
             "and hidden matters come to light. Expenditures rise. Spiritual practice is the highest "
             "use of this energy.",
             "health", 0.85,
             "Do NOT make major financial commitments in Phase 1. Let Saturn's review complete first.",
             "~2.5 years"),
        0:  (2, "PEAK PHASE — TRANSFORMATION",
             "Saturn is transiting YOUR Moon sign — Sade Sati Phase 2, the peak. "
             "This is the most intense phase: identity is restructured, career may shift, "
             "and relationships are tested for authenticity. What emerges from this phase "
             "is the most authentic version of you. This is not punishment — it is precision editing.",
             "health", 0.90,
             "CRITICAL: Do NOT make impulsive major decisions. Saturn Phase 2 is a restructuring, "
             "not a crisis — but decisions made impulsively now can be very difficult to reverse.",
             "~2.5 years"),
        1:  (3, "RELEASE PHASE",
             "Saturn has moved to the 2nd sign from your Moon — Sade Sati Phase 3. "
             "Financial restructuring and family matters come to resolution. "
             "The worst is behind you. This phase completes the 7.5-year cycle. "
             "What you built during Sade Sati now shows its true strength.",
             "wealth", 0.82,
             "Family and financial decisions need care in Phase 3. Don't rush to 'make up for lost time.'",
             "~2.5 years"),
    }

    if diff in phase_data:
        phase_num, phase_name, pred, domain, conf, warning, timeframe = phase_data[diff]
        signals.append({
            "system": "sade_sati",
            "planet": "Saturn",
            "rule_id": f"SADE_SATI_P{phase_num}",
            "domain": domain,
            "confidence": conf,
            "prediction": f"SADE SATI {phase_name} (Phase {phase_num}/3): {pred}",
            "warning": warning,
            "remedy_planet": "Saturn",
            "concern_relevance": 0.92,
            "is_pain_signal": True,
            "sade_sati_phase": phase_num,
            "timeframe": timeframe,
        })

    return signals


# ── ANTARDASHA RULES ──────────────────────────────────────────────────────────

# What each MD+AD combination produces
# Format: (MD_lord, AD_lord) → {domain, confidence, prediction, warning}
ANTARDASHA_RULES = {
    # Saturn MD combinations — the most common "why is life hard right now"
    ("Saturn","Venus"):  {"domain":"marriage","confidence":0.87,
        "prediction":"Saturn MD / Venus AD — the most auspicious sub-period of Saturn dasha. "
        "Career meets creativity and partnership. Marriage and significant relationships reach a milestone. "
        "Financial gains through creative or partnership work. This is Saturn's grace period.",
        "warning":"Don't let career ambition crowd out relationship investment during this window."},
    ("Saturn","Jupiter"):{"domain":"spiritual","confidence":0.85,
        "prediction":"Saturn MD / Jupiter AD — wisdom and discipline combine. Teaching, advisory, and "
        "institutional roles peak. This is the sub-period of earned recognition and spiritual depth.",
        "warning":""},
    ("Saturn","Mercury"):{"domain":"career","confidence":0.83,
        "prediction":"Saturn MD / Mercury AD — business, communication, and intellectual work are highlighted. "
        "Contracts, negotiations, and written agreements carry long-term weight. Sign nothing carelessly.",
        "warning":"Read all contracts with extreme care. Mercury under Saturn means errors in agreements are costly."},
    ("Saturn","Moon"):   {"domain":"health","confidence":0.78,
        "prediction":"Saturn MD / Moon AD — emotional depth meets structural pressure. "
        "A period of introspection, potential health focus, and deep inner work. Mother or home may require attention.",
        "warning":"Prioritize mental health practices. Emotional decisions need extra time to process."},
    ("Saturn","Sun"):    {"domain":"career","confidence":0.80,
        "prediction":"Saturn MD / Sun AD — authority and discipline combine. "
        "Government, leadership, and recognition of long-term work are highlighted. Father figure or authority relationship is significant.",
        "warning":"Ego conflicts with authority figures can flare. Choose integrity over pride."},
    ("Saturn","Mars"):   {"domain":"health","confidence":0.75,
        "prediction":"Saturn MD / Mars AD — the most challenging Saturn sub-period. "
        "Physical energy is constrained, frustrations run high, and accidents are more possible. "
        "Channel energy into disciplined physical work, not confrontation.",
        "warning":"CAUTION: Avoid risky physical activities and aggressive confrontations. Health monitoring is essential."},
    ("Saturn","Rahu"):   {"domain":"career","confidence":0.78,
        "prediction":"Saturn MD / Rahu AD — sudden, unconventional career shifts within the Saturn structure. "
        "Foreign elements, technology, or disruptive change enters the professional picture. "
        "Can be powerful if navigated consciously.",
        "warning":"Beware of shortcuts and overconfidence. Rahu in Saturn dasha accelerates but can also destabilize."},
    ("Saturn","Ketu"):   {"domain":"spiritual","confidence":0.75,
        "prediction":"Saturn MD / Ketu AD — deep spiritual introspection, karmic release, and past-life completions. "
        "Material ambitions feel less important. Meditation and service are most productive.",
        "warning":"Don't abandon career completely. This is a spiritual deepening, not a career ending."},

    # Venus MD combinations
    ("Venus","Saturn"):  {"domain":"career","confidence":0.83,
        "prediction":"Venus MD / Saturn AD — creative or relationship work gets structured and serious. "
        "Long-term commitments in career and love are made. What is built now endures.",
        "warning":"Avoid pessimism about love or career during this sub-period — Saturn slows but doesn't deny."},
    ("Venus","Jupiter"): {"domain":"wealth","confidence":0.88,
        "prediction":"Venus MD / Jupiter AD — the most auspicious sub-period of Venus dasha. "
        "Wealth, wisdom, love, and expansion align simultaneously. Major financial and relationship milestones. "
        "A genuinely blessed window.",
        "warning":""},
    ("Venus","Rahu"):    {"domain":"marriage","confidence":0.78,
        "prediction":"Venus MD / Rahu AD — intense, karmic, or unconventional relationship developments. "
        "Powerful attraction. Foreign or cross-cultural connections. Creative disruption.",
        "warning":"Ensure new relationships are grounded — Venus/Rahu creates powerful magnetism that can lack substance."},
    ("Venus","Moon"):    {"domain":"marriage","confidence":0.85,
        "prediction":"Venus MD / Moon AD — emotional and romantic fulfillment peak. "
        "Marriage, creative work, and domestic happiness are all highlighted. "
        "A tender, beautiful sub-period.",
        "warning":""},
    ("Venus","Mars"):    {"domain":"marriage","confidence":0.82,
        "prediction":"Venus MD / Mars AD — passionate, energetic relationship and creative period. "
        "Physical vitality is high. Bold creative and romantic moves succeed.",
        "warning":"Manage impulsiveness in relationships. Passion is high — channel it constructively."},
    ("Venus","Mercury"): {"domain":"career","confidence":0.83,
        "prediction":"Venus MD / Mercury AD — creative, business, and communication work peak. "
        "Artistic and intellectual career moves succeed. Writing, speaking, and advisory work are prominent.",
        "warning":""},

    # Jupiter MD combinations
    ("Jupiter","Venus"): {"domain":"wealth","confidence":0.90,
        "prediction":"Jupiter MD / Venus AD — the pinnacle sub-period of Jupiter dasha. "
        "Wealth, love, and wisdom align. Marriage, significant financial gains, and creative recognition "
        "are all possible in this window. One of the best periods in any chart.",
        "warning":""},
    ("Jupiter","Saturn"):{"domain":"career","confidence":0.85,
        "prediction":"Jupiter MD / Saturn AD — wisdom meets discipline. Institutional, teaching, "
        "and leadership roles peak. Long-term career structures are built with Jupiter's blessing.",
        "warning":"Don't rush what Saturn is building patiently."},
    ("Jupiter","Mercury"):{"domain":"career","confidence":0.85,
        "prediction":"Jupiter MD / Mercury AD — intellectual, business, and teaching work peak. "
        "Writing, publishing, and advisory work carry significant impact. Your words have unusual reach.",
        "warning":""},
    ("Jupiter","Moon"):  {"domain":"family","confidence":0.85,
        "prediction":"Jupiter MD / Moon AD — emotional wisdom and family expansion peak. "
        "Children, home, and domestic happiness are highlighted. Intuition is strong.",
        "warning":""},
    ("Jupiter","Rahu"):  {"domain":"career","confidence":0.80,
        "prediction":"Jupiter MD / Rahu AD — unconventional wisdom and foreign expansion. "
        "Technology, cross-cultural work, and innovative approaches to traditional fields are highlighted.",
        "warning":"Discern carefully between genuine wisdom and attractive illusions during this sub-period."},

    # Rahu MD combinations
    ("Rahu","Jupiter"):  {"domain":"spiritual","confidence":0.78,
        "prediction":"Rahu MD / Jupiter AD — the most stable and potentially beneficial sub-period of Rahu dasha. "
        "Wisdom tempers ambition. Teaching, foreign wisdom traditions, and philosophical depth emerge.",
        "warning":""},
    ("Rahu","Saturn"):   {"domain":"career","confidence":0.75,
        "prediction":"Rahu MD / Saturn AD — karmic acceleration meets structural discipline. "
        "Foreign, technology, or unconventional career moves get serious and structured.",
        "warning":"Legal and contractual vigilance is essential. Rahu+Saturn can create sudden legal complications."},
    ("Rahu","Venus"):    {"domain":"marriage","confidence":0.78,
        "prediction":"Rahu MD / Venus AD — intense karmic relationship developments. "
        "Attraction is powerful. Foreign or unconventional romantic connections are highlighted.",
        "warning":"Ensure relationships are built on substance. Rahu/Venus creates magnetism that can be illusory."},
    ("Rahu","Mercury"):  {"domain":"career","confidence":0.75,
        "prediction":"Rahu MD / Mercury AD — fast-moving communication and business activity. "
        "Technology, media, and unconventional business models are highlighted.",
        "warning":"Double-check all agreements and communications. Rahu/Mercury speeds up but can create miscommunication."},
    ("Rahu","Moon"):     {"domain":"health","confidence":0.78,
        "prediction":"Rahu MD / Moon AD — emotional turbulence and mental intensity peak. "
        "Unusual psychological experiences, vivid dreams, or anxiety patterns may surface.",
        "warning":"Prioritize mental health support. Avoid major emotional decisions during peak Rahu/Moon windows."},

    # Ketu MD
    ("Ketu","Jupiter"):  {"domain":"spiritual","confidence":0.82,
        "prediction":"Ketu MD / Jupiter AD — the deepest spiritual sub-period. "
        "Past-life wisdom resurfaces. Moksha, liberation, and genuine spiritual insight peak.",
        "warning":""},
    ("Ketu","Venus"):    {"domain":"marriage","confidence":0.75,
        "prediction":"Ketu MD / Venus AD — past relationship karma completes. "
        "A significant relationship may transform, end, or reveal its true spiritual nature.",
        "warning":"Don't cling to relationships that are completing their karmic cycle."},
    ("Ketu","Moon"):     {"domain":"health","confidence":0.75,
        "prediction":"Ketu MD / Moon AD — emotional detachment and past-life memories may surface. "
        "Meditation and spiritual practice are unusually powerful now.",
        "warning":"Avoid emotional isolation. Stay connected to trusted relationships."},
}


def apply_antardasha_rules(chart_data: dict, dashas: dict, concern: str) -> list:
    """
    Wire vimsottari antardasha data into the rules pipeline.
    Finds the CURRENT antardasha (today's date) and fires the right rule.
    Gives 6-month precision vs 20-year mahadasha windows.
    """
    signals = []
    today = datetime.now(_tz.utc)
    vimsottari = dashas.get("vimsottari", [])

    # Find current MD
    current_md = None
    current_ad = None

    for entry in vimsottari:
        if entry.get("level") in ("MD", "mahadasha", None):
            start = entry.get("start", "")
            end   = entry.get("end", "")
            try:
                s = datetime.fromisoformat(start.replace("Z","+00:00")) if start else None
                e = datetime.fromisoformat(end.replace("Z","+00:00")) if end else None
                if s and e and s <= today <= e:
                    current_md = entry
                    break
            except Exception:
                pass

    # Find current AD within current MD
    if current_md:
        md_lord = current_md.get("lord_or_sign", current_md.get("lord", ""))
        for entry in vimsottari:
            if entry.get("level") in ("AD", "antardasha"):
                start = entry.get("start", "")
                end   = entry.get("end", "")
                parent = entry.get("parent_lord", "")
                try:
                    s = datetime.fromisoformat(start.replace("Z","+00:00")) if start else None
                    e = datetime.fromisoformat(end.replace("Z","+00:00")) if end else None
                    if s and e and s <= today <= e:
                        current_ad = entry
                        break
                except Exception:
                    pass

    # Fire antardasha rule
    if current_md and current_ad:
        md_lord = current_md.get("lord_or_sign", current_md.get("lord", ""))
        ad_lord = current_ad.get("lord_or_sign", current_ad.get("lord", ""))
        ad_end  = current_ad.get("end", "")

        rule = ANTARDASHA_RULES.get((md_lord, ad_lord))
        if rule:
            signals.append({
                "system":           "antardasha",
                "planet":           f"{md_lord}/{ad_lord}",
                "md_lord":          md_lord,
                "ad_lord":          ad_lord,
                "rule_id":          f"AD_{md_lord}_{ad_lord}",
                "domain":           rule["domain"],
                "confidence":       rule["confidence"],
                "prediction":       rule["prediction"],
                "warning":          rule.get("warning", ""),
                "remedy_planet":    ad_lord,
                "concern_relevance":0.92 if rule["domain"] == concern else 0.65,
                "timeframe":        f"Until {ad_end[:10] if ad_end else 'end of sub-period'}",
                "is_antardasha":    True,
            })

    return signals


# ── YOGA ENGINE WIRING ──────────────────────────────────────────────────────

def apply_yoga_engine_signals(chart_data: dict, concern: str) -> list:
    """
    Wire yoga_engine.py into the rules pipeline.
    Maps yoga results → ranked signals with prediction text.

    yoga_engine already computes the hard math.
    This layer translates {present, strength, implication} → signal format.
    """
    signals = []

    try:
        # Import here to avoid circular import at module load
        from antar_engine.d_charts_calculator import get_all_d_charts
        from antar_engine.yoga_engine import detect_yogas_for_question

        # Determine which D-charts to compute based on concern
        concern_charts = {
            "wealth":   [2, 9],
            "marriage": [9],
            "health":   [6],
            "legal":    [6],
            "children": [7, 9],
            "career":   [10, 9],
            "general":  [9, 10],
            "spiritual":[9, 20],
        }
        divisions = concern_charts.get(concern, [9, 10])
        d_charts = get_all_d_charts(chart_data, divisions)

        yogas = detect_yogas_for_question(concern, chart_data, d_charts)

        strength_confidence = {
            "very strong": 0.92, "strong": 0.87,
            "moderate": 0.80,   "partial": 0.72,
            "weak": 0.65,        "limited": 0.60,
            "absent": 0.0,
        }

        for yoga in yogas:
            if not yoga.get("present"):
                continue
            strength = yoga.get("strength", "moderate")
            conf = strength_confidence.get(strength, 0.75)
            if conf < 0.65:
                continue  # skip weak/absent

            name = yoga.get("name", "")
            impl = yoga.get("implication", "")
            timing = yoga.get("timing_note", "")
            desc = yoga.get("description", "")

            signals.append({
                "system":           "yoga_engine",
                "yoga_name":        name,
                "planet":           yoga.get("description", "")[:30],
                "rule_id":          f"YOGA_{name.replace(' ','_').replace('—','').strip()[:30]}",
                "domain":           concern if concern != "general" else "career",
                "confidence":       conf,
                "prediction":       f"{name}: {impl}" + (f" Timing: {timing}" if timing else ""),
                "warning":          "",
                "remedy_planet":    "Jupiter",  # default — yogas are generally positive
                "concern_relevance":0.92,
                "is_yoga":          True,
                "yoga_strength":    strength,
                "yoga_timing":      timing,
            })

    except ImportError as e:
        print(f"  [yoga_engine] import error: {e}")
    except Exception as e:
        print(f"  [yoga_engine] error: {e}")

    return signals


# ── D-CHART SPECIFIC SIGNALS ─────────────────────────────────────────────────

def apply_d10_dashamsa_signals(chart_data: dict, concern: str) -> list:
    """
    D-10 Dashamsa — the career destiny chart.
    Key signals: lagna lord strength, Sun strength, Saturn strength,
    and planets in 10H of D-10.
    """
    if concern not in ("career", "general"):
        return []

    signals = []
    try:
        from antar_engine.d_charts_calculator import get_d_chart, is_planet_strong, is_planet_weak, get_planets_in_house
        d10 = get_d_chart(chart_data, 10)
        lagna_sign = d10.get("Lagna", {}).get("sign", "")

        # Sun in D-10 — career authority
        sun_d10 = d10.get("Sun", {})
        if sun_d10.get("strength") in ("exalted", "own"):
            signals.append({
                "system": "d10_dashamsa", "planet": "Sun",
                "rule_id": "D10_SUN_STRONG",
                "domain": "career", "confidence": 0.88,
                "prediction": f"Sun is {sun_d10['strength']} in your career destiny chart (D-10). "
                              f"Public authority, government roles, and recognition are written into your professional DNA. "
                              f"Leadership positions come naturally when you claim them.",
                "warning": "", "remedy_planet": "Sun",
                "concern_relevance": 0.92,
            })
        elif sun_d10.get("strength") == "debilitated":
            signals.append({
                "system": "d10_dashamsa", "planet": "Sun",
                "rule_id": "D10_SUN_WEAK",
                "domain": "career", "confidence": 0.75,
                "prediction": "Sun is debilitated in your career destiny chart (D-10). "
                              "Self-confidence and authority in career require conscious cultivation. "
                              "Finding a mentor or senior advisor is specifically protective.",
                "warning": "Avoid ego conflicts with superiors — D-10 debilitated Sun needs allies, not adversaries.",
                "remedy_planet": "Sun",
                "concern_relevance": 0.88,
                "is_pain_signal": True,
            })

        # Saturn in D-10 — career discipline and longevity
        sat_d10 = d10.get("Saturn", {})
        if sat_d10.get("strength") in ("exalted", "own"):
            signals.append({
                "system": "d10_dashamsa", "planet": "Saturn",
                "rule_id": "D10_SATURN_STRONG",
                "domain": "career", "confidence": 0.90,
                "prediction": f"Saturn is {sat_d10['strength']} in your career destiny chart (D-10). "
                              f"This is the highest indicator of career longevity and enduring professional legacy. "
                              f"What you build professionally is meant to outlast you. "
                              f"Slow rise, unshakeable foundation.",
                "warning": "", "remedy_planet": "Saturn",
                "concern_relevance": 0.92,
            })

        # Jupiter in D-10 — career wisdom and expansion
        jup_d10 = d10.get("Jupiter", {})
        if jup_d10.get("strength") in ("exalted", "own"):
            signals.append({
                "system": "d10_dashamsa", "planet": "Jupiter",
                "rule_id": "D10_JUPITER_STRONG",
                "domain": "career", "confidence": 0.88,
                "prediction": f"Jupiter is {jup_d10['strength']} in your career destiny chart (D-10). "
                              f"Teaching, advisory, wisdom-based, and institutional careers are soul-aligned. "
                              f"Career expansion comes through sharing knowledge, not just executing tasks.",
                "warning": "", "remedy_planet": "Jupiter",
                "concern_relevance": 0.88,
            })

        # D-10 lagna lord strength
        from antar_engine.d_charts_calculator import SIGN_LORDS, SIGN_INDEX
        d10_ll = SIGN_LORDS.get(lagna_sign, "")
        if d10_ll and is_planet_strong(d10_ll, d10):
            signals.append({
                "system": "d10_dashamsa", "planet": d10_ll,
                "rule_id": f"D10_LAGNA_LORD_{d10_ll}",
                "domain": "career", "confidence": 0.85,
                "prediction": f"Your career destiny chart lagna lord ({d10_ll}) is strong in D-10. "
                              f"Professional success is supported at the soul destiny level — "
                              f"not just circumstantial luck but actual dharmic alignment with career.",
                "warning": "", "remedy_planet": d10_ll,
                "concern_relevance": 0.90,
            })

    except Exception as e:
        print(f"  [d10] error: {e}")

    return signals


def apply_d3_drekkana_signals(chart_data: dict, concern: str) -> list:
    """
    D-3 Drekkana — siblings, self-effort, courage, short journeys.
    Mars strength in D-3 = courage and self-effort.
    """
    if concern not in ("general", "career", "health"):
        return []
    signals = []
    try:
        from antar_engine.d_charts_calculator import get_d_chart, is_planet_strong, is_planet_weak
        d3 = get_d_chart(chart_data, 3)
        mars_d3 = d3.get("Mars", {})
        if mars_d3.get("strength") in ("exalted", "own"):
            signals.append({
                "system": "d3_drekkana", "planet": "Mars",
                "rule_id": "D3_MARS_STRONG",
                "domain": "career", "confidence": 0.82,
                "prediction": "Mars is strong in your courage and self-effort chart (D-3). "
                              "Your own initiative and courage are your primary career assets. "
                              "Self-directed work, entrepreneurship, and independent roles suit your destiny.",
                "warning": "", "remedy_planet": "Mars",
                "concern_relevance": 0.80,
            })
        elif mars_d3.get("strength") == "debilitated":
            signals.append({
                "system": "d3_drekkana", "planet": "Mars",
                "rule_id": "D3_MARS_WEAK",
                "domain": "health", "confidence": 0.72,
                "prediction": "Mars is debilitated in your courage chart (D-3). "
                              "Self-motivation and initiative need conscious cultivation. "
                              "Working with partners or teams provides more momentum than solo effort.",
                "warning": "Avoid risky solo ventures without strong partner support.",
                "remedy_planet": "Mars",
                "concern_relevance": 0.70,
                "is_pain_signal": True,
            })
    except Exception as e:
        print(f"  [d3] error: {e}")
    return signals


def apply_d60_shashtiamsha_signals(chart_data: dict, concern: str) -> list:
    """
    D-60 Shashtiamsha — past-life karma. Most precise timing chart.
    Lagna lord and Moon strength in D-60 reveal karmic debt or credit.
    """
    signals = []
    try:
        from antar_engine.d_charts_calculator import get_d_chart, is_planet_strong, is_planet_weak, SIGN_LORDS
        d60 = get_d_chart(chart_data, 60)
        lagna_sign = d60.get("Lagna", {}).get("sign", "")
        d60_ll = SIGN_LORDS.get(lagna_sign, "")

        if d60_ll and is_planet_strong(d60_ll, d60):
            signals.append({
                "system": "d60_shashtiamsha", "planet": d60_ll,
                "rule_id": "D60_LL_STRONG",
                "domain": "spiritual", "confidence": 0.85,
                "prediction": f"Your past-karma chart (D-60) shows strong karmic credit — "
                              f"the soul arrives in this life with significant positive karma from previous actions. "
                              f"Doors open that seem inexplicable by circumstance alone. "
                              f"This is not luck — it is earned from previous lives.",
                "warning": "", "remedy_planet": d60_ll,
                "concern_relevance": 0.80 if concern == "spiritual" else 0.60,
            })
        elif d60_ll and is_planet_weak(d60_ll, d60):
            signals.append({
                "system": "d60_shashtiamsha", "planet": d60_ll,
                "rule_id": "D60_LL_WEAK",
                "domain": "spiritual", "confidence": 0.78,
                "prediction": "Your past-karma chart (D-60) shows karmic debts from previous lives "
                              "that are being worked through in this lifetime. "
                              "Obstacles that seem disproportionate to effort are karmic balancing. "
                              "Service, integrity, and spiritual practice are the fastest paths through.",
                "warning": "This is not a permanent condition — karma is specifically workable through conscious action.",
                "remedy_planet": "Saturn",
                "concern_relevance": 0.80 if concern == "spiritual" else 0.58,
                "is_pain_signal": True,
            })

        # Moon in D-60
        moon_d60 = d60.get("Moon", {})
        if moon_d60.get("strength") in ("exalted", "own"):
            signals.append({
                "system": "d60_shashtiamsha", "planet": "Moon",
                "rule_id": "D60_MOON_STRONG",
                "domain": "health", "confidence": 0.82,
                "prediction": "Moon is strong in your past-karma chart — emotional intelligence "
                              "and intuitive gifts carry strong karmic support from previous lives. "
                              "Trust your gut instincts — they are karmically calibrated.",
                "warning": "", "remedy_planet": "Moon",
                "concern_relevance": 0.75,
            })

    except Exception as e:
        print(f"  [d60] error: {e}")
    return signals


def apply_lal_kitab_varshphal_signals(chart_data: dict, concern: str, user_age: int = 0) -> list:
    """
    Wire lal_kitab.py Varshphal into the rules pipeline.
    Annual chart gives year-specific signals on top of natal chart.
    """
    if not user_age:
        return []
    signals = []
    try:
        from antar_engine.lal_kitab import calculate_varshphal_chart, SPECIAL_CYCLES

        varshphal = calculate_varshphal_chart(chart_data, user_age)

        # Special cycle years = major signals
        if varshphal.is_special_cycle:
            signals.append({
                "system": "lal_kitab_varshphal", "planet": "Saturn",
                "rule_id": f"LK_VARSH_AGE{user_age}_SPECIAL",
                "domain": "spiritual", "confidence": 0.90,
                "prediction": f"Lal Kitab Varshphal — Age {user_age} is a SPECIAL CYCLE year: "
                              f"{varshphal.cycle_significance}. "
                              f"Annual chart signals carry extra weight this year — "
                              f"decisions made in this year have outsized long-term impact.",
                "warning": "Special cycle years require extra intentionality in major decisions.",
                "remedy_planet": "Saturn",
                "concern_relevance": 0.92,
                "is_special_year": True,
            })

        # Key annual placements — Saturn, Jupiter, Rahu in difficult houses
        pain_houses = {6, 8, 12}
        power_houses = {1, 5, 9, 10, 11}
        key_planets_annual = ["Saturn", "Jupiter", "Rahu", "Mars", "Venus", "Mercury", "Sun", "Moon", "Ketu"]

        # Finance-aware Varshphal predictions per planet per house
        VARSH_H6_PREDICTIONS = {
            "Saturn":  ("finance", 0.82, "Lal Kitab annual chart: Saturn in your loan zone this year — a year that tests financial patience. Bank approvals require documented track records. The delay in funding this year IS the preparation. Do the groundwork now; the door opens next cycle.", "Avoid rushed loan applications this year. Saturn in H6 annually rewards the prepared."),
            "Jupiter": ("finance", 0.80, "Lal Kitab annual chart: Jupiter in your loan zone this year — one of the strongest annual windows for institutional borrowing and grant applications. Banks are favorable. Apply for credit, institutional loans, and government grants actively this year.", "Do not over-borrow during Jupiter's generous annual window."),
            "Rahu":    ("finance", 0.78, "Lal Kitab annual chart: Rahu in your loan zone this year — unconventional funding channels, foreign credit, and fintech borrowing are activated this year. Simultaneously, hidden workplace complications or unusual legal disputes may surface.", "Read all loan fine print this year. Rahu's unconventional channels carry hidden terms."),
            "Mars":    ("finance", 0.78, "Lal Kitab annual chart: Mars in your loan/conflict zone this year — aggressive borrowing capacity is available. Asset-backed loans and real estate financing move quickly. Simultaneously, workplace conflicts and accident risks are elevated.", "Channel Mars energy into funding action, not confrontation."),
            "Venus":   ("finance", 0.75, "Lal Kitab annual chart: Venus in your loan zone this year — partnership-based funding, co-founder capital, and relationship-driven credit are the aligned channels this year.", "Keep financial and romantic relationships separate this year."),
            "Mercury": ("finance", 0.75, "Lal Kitab annual chart: Mercury in your loan zone this year — excellent year for completing loan documentation, grant applications, and financial contracts. Written communication with lenders carries unusual traction.", "Read every financial document carefully this year."),
            "Sun":     ("finance", 0.72, "Lal Kitab annual chart: Sun in your loan zone this year — government grants and authority-backed credit are available. Professional reputation is the key to borrowing capacity this year.", "Ego conflicts with lenders cause unnecessary delays this year."),
            "Moon":    ("finance", 0.72, "Lal Kitab annual chart: Moon in your loan zone this year — community-based funding and emotionally-driven financial decisions are elevated. Financial stability follows emotional stability closely this year.", "Avoid major financial decisions on emotionally turbulent days this year."),
            "Ketu":    ("finance", 0.68, "Lal Kitab annual chart: Ketu in your loan zone this year — a year to simplify debt, not add to it. Complex loan structures are inadvisable. Prefer self-funded or revenue-based financing this year.", "Avoid complex debt arrangements this year entirely."),
        }
        VARSH_H8_PREDICTIONS = {
            "Jupiter": ("finance", 0.85, "Lal Kitab annual chart: Jupiter in your OPM/investor zone this year — the single most powerful annual signal for attracting external capital. Angel investors, VCs, and inheritance matters are activated. Wisdom and credibility are the magnets. Prioritize investor outreach this year.", "Never misuse investor trust activated during this annual window."),
            "Rahu":    ("finance", 0.82, "Lal Kitab annual chart: Rahu in your OPM zone this year — sudden, unexpected access to large external capital. Foreign investors and unconventional equity sources are the channels. Vet all sources carefully. Hidden matters in finances or partnerships may surface unexpectedly.", "Verify ALL investors thoroughly this year. Rahu in H8 annually attracts both windfalls and sophisticated fraud."),
            "Saturn":  ("finance", 0.80, "Lal Kitab annual chart: Saturn in your OPM zone this year — patient institutional capital is available but requires extensive documentation and proof of longevity. This is a year to build the investor package, not close the round. The round closes next cycle after groundwork is complete.", "Proactive legal documentation and health management are protective this year."),
            "Mars":    ("finance", 0.78, "Lal Kitab annual chart: Mars in your OPM zone this year — bold external capital, asset-backed joint ventures, and inheritance-related matters activate suddenly. High-energy year for investor pitches.", "Document all joint financial arrangements made this year in writing."),
            "Venus":   ("finance", 0.78, "Lal Kitab annual chart: Venus in your OPM zone this year — partnership funding, co-founder investment, and joint ventures are favored. Real estate joint deals and consumer-brand co-investment carry unusual momentum this year.", None),
            "Mercury": ("finance", 0.78, "Lal Kitab annual chart: Mercury in your OPM zone this year — IP deals, tech funding, and analytically-driven investor pitches carry traction. Finalize investor documentation and term sheets this year.", "Protect IP before any pitch this year."),
            "Sun":     ("finance", 0.72, "Lal Kitab annual chart: Sun in your OPM zone this year — government-backed investors and authority-figure backers are accessible. Authority and track record are the pitch.", "Remain open to shared control in investor conversations this year."),
            "Moon":    ("finance", 0.72, "Lal Kitab annual chart: Moon in your OPM zone this year — community trust and emotional connection with investors are the key. Consumer-facing brand investment and crowdfunding are strongest this year.", "Wait for emotionally stable periods before major investor conversations this year."),
            "Ketu":    ("finance", 0.68, "Lal Kitab annual chart: Ketu in your OPM zone this year — karmic completions around shared resources and external capital. Mission-aligned and impact investors are the right match for any new capital conversations this year.", None),
        }
        VARSH_H12_PREDICTIONS = {
            "Saturn":  ("finance", 0.80, "Lal Kitab annual chart: Saturn in your investment/expenditure zone this year — a year of elevated expenses and disciplined spending requirements. Long-horizon investments begun this year yield reliable returns. Service-based foreign ventures are aligned. Control expenditures as the primary financial discipline.", None),
            "Jupiter": ("finance", 0.75, "Lal Kitab annual chart: Jupiter in your investment/expenditure zone this year — generous outflows toward spiritual, educational, and foreign causes. Monitor total expenditure levels — Jupiter expands outflows liberally. Foreign wisdom partnerships and educational investments yield unexpected value.", "Monitor overall spending levels this year."),
            "Rahu":    ("finance", 0.78, "Lal Kitab annual chart: Rahu in your investment/foreign zone this year — strong activation of foreign financial connections and unconventional investment channels. Cross-border capital and hidden financial structures are active. What is built in foreign markets this year carries outsized long-term returns.", "Ensure full regulatory compliance in all foreign financial structures this year."),
            "Mars":    ("finance", 0.75, "Lal Kitab annual chart: Mars in your expenditure zone this year — hidden expenditures, sudden large expenses, and foreign-related financial activity are elevated. Import/export and foreign infrastructure are the investment signals.", "Do NOT lend money this year — it rarely returns."),
            "Venus":   ("finance", 0.75, "Lal Kitab annual chart: Venus in your expenditure zone this year — luxury spending, foreign partnership investments, and hospitality-sector activity abroad are elevated. Track expenditures carefully.", "Luxury spending requires conscious limits this year."),
            "Mercury": ("finance", 0.72, "Lal Kitab annual chart: Mercury in your expenditure zone this year — foreign tech contracts, cross-border media deals, and intellectual property work abroad are activated. Communication expenditures are elevated.", "Foreign contracts require extra legal scrutiny this year."),
            "Sun":     ("finance", 0.70, "Lal Kitab annual chart: Sun in your expenditure zone this year — spending on status, authority-maintenance, and behind-the-scenes institutional work is elevated. Foreign government-adjacent investment is activated quietly.", None),
            "Moon":    ("finance", 0.70, "Lal Kitab annual chart: Moon in your expenditure zone this year — emotional spending and home-related expenditures are elevated. Foreign real estate and care-sector investments are briefly favorable.", "Avoid large financial commitments driven by emotional comfort this year."),
            "Ketu":    ("spiritual", 0.78, "Lal Kitab annual chart: Ketu in your liberation zone this year — karmic expenditures complete their cycle. Spiritual retreat, service, and inner work yield the deepest returns this year. Material financial expectations are misaligned with this annual placement.", None),
        }

        VARSH_LOOKUP = {6: VARSH_H6_PREDICTIONS, 8: VARSH_H8_PREDICTIONS, 12: VARSH_H12_PREDICTIONS}

        for planet in key_planets_annual:
            annual_house = varshphal.placements.get(planet)
            if not annual_house:
                continue
            if annual_house in pain_houses:
                lookup = VARSH_LOOKUP.get(annual_house, {})
                pred_data = lookup.get(planet)
                if pred_data:
                    domain, conf, prediction, warning = pred_data[0], pred_data[1], pred_data[2], pred_data[3] if len(pred_data) > 3 else None
                else:
                    # Fallback for planets not in lookup
                    domain = "health" if annual_house == 6 else "spiritual"
                    conf = 0.72
                    prediction = (f"Lal Kitab annual chart (Age {user_age}): {planet} in House {annual_house} "
                                  f"this year — {'loan and service zone activated.' if annual_house == 6 else 'OPM and transformation zone activated.' if annual_house == 8 else 'expenditure and foreign zone activated.'}")
                    warning = f"Annual {planet} in H{annual_house}: follow Lal Kitab remedy for {planet}."
                signals.append({
                    "system": "lal_kitab_varshphal", "planet": planet,
                    "rule_id": f"LK_VARSH_{planet}_H{annual_house}",
                    "domain": domain,
                    "confidence": conf,
                    "prediction": prediction,
                    "warning": warning or "",
                    "remedy_planet": planet,
                    "concern_relevance": 0.88 if concern in ("finance","career","wealth") and annual_house in (6,8) else 0.80,
                    "is_pain_signal": True,
                    "annual_house": annual_house,
                    "funding_signal": (VARSH_H6_PREDICTIONS.get(planet, (None,))[0] if annual_house == 6 else
                                       VARSH_H8_PREDICTIONS.get(planet, (None,))[0] if annual_house == 8 else None),
                })
            elif annual_house in power_houses and planet == "Jupiter":
                signals.append({
                    "system": "lal_kitab_varshphal", "planet": "Jupiter",
                    "rule_id": f"LK_VARSH_JUP_H{annual_house}",
                    "domain": "wealth" if annual_house in (9, 11) else "career",
                    "confidence": 0.82,
                    "prediction": f"Lal Kitab annual chart: Jupiter in House {annual_house} this year — "
                                  f"a powerful annual placement for {'fortune and gains' if annual_house in (9,11) else 'career and recognition'}. "
                                  f"Jupiter's annual transit through this house brings specific opportunities in {user_age}.",
                    "warning": "",
                    "remedy_planet": "Jupiter",
                    "concern_relevance": 0.82,
                })
    except Exception as e:
        print(f"  [varshphal] error: {e}")
    return signals


# ── UPDATED run_all_rules — COMPLETE INTEGRATION ─────────────────────────────

_run_all_rules_v3_base = _run_all_rules_v2  # snapshot before overwrite


def run_all_rules(chart_data: dict, dashas: dict, current_transits,
                  concern: str = "general", country_code: str = "IN",
                  user_age: int = 0) -> dict:
    """
    v3 — Full integration:
    Base rules (v1) + D9/Yogas (v2) + Antardasha + Nakshatra Tara +
    Sade Sati + Yoga Engine + D-10 + D-3 + D-60 + Lal Kitab Varshphal
    """
    result = _run_all_rules_v3_base(chart_data, dashas, current_transits, concern, country_code)

    # New signal sources
    antardasha_sigs  = apply_antardasha_rules(chart_data, dashas, concern)
    nakshatra_sigs   = apply_nakshatra_transit_rules(chart_data, current_transits, concern)
    sade_sati_sigs   = check_sade_sati(chart_data, current_transits)
    yoga_eng_sigs    = apply_yoga_engine_signals(chart_data, concern)
    d10_sigs         = apply_d10_dashamsa_signals(chart_data, concern)
    d3_sigs          = apply_d3_drekkana_signals(chart_data, concern)
    d60_sigs         = apply_d60_shashtiamsha_signals(chart_data, concern)
    varshphal_sigs   = apply_lal_kitab_varshphal_signals(chart_data, concern, user_age)

    all_new = (antardasha_sigs + nakshatra_sigs + sade_sati_sigs +
               yoga_eng_sigs + d10_sigs + d3_sigs + d60_sigs + varshphal_sigs)

    # Merge with existing signals and re-rank
    all_signals_extended = (
        result.get("lal_kitab", []) + result.get("jaimini", []) +
        result.get("dasha", []) + result.get("transit", []) +
        result.get("d9", []) + result.get("yogas", []) +
        all_new
    )

    karakas = result["karakas"]
    top_signals = rank_signals(all_signals_extended, concern, karakas)

    # Rebuild confluence with full signal set
    new_confluence = detect_triple_confluence(
        result.get("lal_kitab", []) + result.get("d9", []) + d10_sigs,
        result.get("dasha", []) + antardasha_sigs,
        result.get("transit", []) + nakshatra_sigs,
    )

    # Rebuild remedies
    seen_planets = set()
    remedies = []
    for s in top_signals:
        rp = s.get("remedy_planet", "")
        if rp and rp not in seen_planets:
            rem = format_remedy_for_location(rp, country_code)
            if rem:
                rem["for_domain"] = s["domain"]
                remedies.append(rem)
                seen_planets.add(rp)
        if len(remedies) >= 3:
            break

    # Signal type flags
    has_sade_sati    = bool(sade_sati_sigs)
    has_antardasha   = bool(antardasha_sigs)
    has_yoga_engine  = bool(yoga_eng_sigs)
    has_d10          = bool(d10_sigs)
    has_nakshatra    = bool(nakshatra_sigs)
    has_varshphal    = bool(varshphal_sigs)

    from collections import Counter as _C
    domain_votes = _C(s["domain"] for s in all_signals_extended)
    dominant_domain = domain_votes.most_common(1)[0][0] if domain_votes else "general"

    # Count active rule systems
    active_systems = set(s.get("system","") for s in all_signals_extended)

    return {
        **result,
        # New signal pools
        "antardasha":       antardasha_sigs,
        "nakshatra_tara":   nakshatra_sigs,
        "sade_sati":        sade_sati_sigs,
        "yoga_engine":      yoga_eng_sigs,
        "d10":              d10_sigs,
        "d3":               d3_sigs,
        "d60":              d60_sigs,
        "varshphal":        varshphal_sigs,
        # Updated aggregates
        "confluence":       new_confluence,
        "top_signals":      top_signals,
        "dominant_domain":  dominant_domain,
        "total_rules_fired":len(all_signals_extended),
        "total_rules_passed_filter": len(top_signals),
        "remedies":         remedies,
        # Flags
        "has_sade_sati":    has_sade_sati,
        "has_antardasha":   has_antardasha,
        "has_yoga_engine":  has_yoga_engine,
        "has_d10":          has_d10,
        "has_nakshatra_tara": has_nakshatra,
        "has_varshphal":    has_varshphal,
        "funding":          funding_sigs,
        "has_funding":      bool(funding_sigs),
        "funding_summary":  get_funding_summary(funding_sigs),
        "funding_types":    list({s.get("funding_signal") or s.get("investment_signal","") for s in funding_sigs if s.get("funding_signal") or s.get("investment_signal")}),
        "active_systems":   sorted(active_systems),
        "yoga_names":       result.get("yoga_names", []) + [s.get("yoga_name","") for s in yoga_eng_sigs if s.get("yoga_name")],
        "sade_sati_phase":  sade_sati_sigs[0].get("sade_sati_phase") if sade_sati_sigs else None,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION v4 — Ashtakavarga + Lal Kitab Aspects + Rin Rules
# ═══════════════════════════════════════════════════════════════════════════════

def apply_ashtakavarga_signals_local(chart_data: dict, current_transits: list,
                                     concern: str) -> list:
    """Wire ashtakavarga.py into the pipeline."""
    try:
        from antar_engine.ashtakavarga import (
            apply_ashtakavarga_signals, ashtakavarga_transit_boost
        )
        return apply_ashtakavarga_signals(chart_data, current_transits, concern)
    except ImportError:
        # Fallback: inline using the real math from ashtakavarga_real.py logic
        # This runs even without antar_engine on the path
        return _apply_ashtakavarga_inline(chart_data, current_transits, concern)


def _apply_ashtakavarga_inline(chart_data: dict, current_transits: list,
                                concern: str) -> list:
    """
    Self-contained Ashtakavarga signal generator.
    Uses the BPHS contribution tables directly — no external import needed.
    Runs inline so astrological_rules.py works standalone in tests.
    """
    # Inline BPHS tables (same as ashtakavarga.py)
    CONTRIBUTIONS_INLINE = {
        "Jupiter": {
            "Sun":     [1,2,3,4,7,8,9,10,11],
            "Moon":    [2,5,7,9,11],
            "Mars":    [1,2,4,7,8,10,11],
            "Mercury": [1,2,4,5,6,9,10,11],
            "Jupiter": [1,2,3,4,7,8,10,11],
            "Venus":   [2,5,6,9,10,11],
            "Saturn":  [3,5,6,12],
            "Lagna":   [1,2,4,5,6,7,9,10,11],
        },
        "Saturn": {
            "Sun":     [1,2,4,7,8,10,11],
            "Moon":    [3,6,11],
            "Mars":    [3,5,6,10,11,12],
            "Mercury": [6,8,9,10,11,12],
            "Jupiter": [5,6,11,12],
            "Venus":   [6,11,12],
            "Saturn":  [3,5,6,11],
            "Lagna":   [1,3,4,6,10,11],
        },
    }
    SIGNS_12 = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
                "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
    signals = []
    lagna_si = chart_data.get("lagna", {}).get("sign_index", 0)

    def _bhinna(planet, contrib_table):
        bindus = [0] * 12
        all_contrib = list(chart_data.get("planets", {}).keys()) + ["Lagna"]
        for contrib in all_contrib:
            positions = contrib_table.get(contrib, [])
            if contrib == "Lagna":
                c_si = lagna_si
            else:
                c_si = chart_data.get("planets", {}).get(contrib, {}).get("sign_index", 0)
            for pos in positions:
                bindus[(c_si + pos - 1) % 12] += 1
        return bindus

    for t in current_transits:
        planet = t.get("planet", "")
        if planet not in ("Jupiter", "Saturn"):
            continue
        house = t.get("transit_house", 0)
        if not house:
            continue
        sign_idx = (lagna_si + house - 1) % 12
        sign = SIGNS_12[sign_idx]

        if planet not in CONTRIBUTIONS_INLINE:
            continue

        bhinna  = _bhinna(planet, CONTRIBUTIONS_INLINE[planet])
        bindus  = bhinna[sign_idx]
        thresholds = {"Jupiter": {"weak":4,"strong":6}, "Saturn": {"weak":3,"strong":5}}
        th = thresholds[planet]

        if bindus >= th["strong"]:
            strength, label = "strong", "STRONG"
            conf = 0.88
            pred = (f"Ashtakavarga confirms: {planet} in House {house} ({sign}) "
                    f"has {bindus}/8 bindus — this transit is genuinely strong FOR YOUR CHART. "
                    f"Generic predictions are amplified here. Act decisively in this window.")
            is_pain = False
        elif bindus <= th["weak"] - 2:
            strength, label = "weak", "WEAK"
            conf = 0.78
            pred = (f"Ashtakavarga CAUTION: {planet} in House {house} ({sign}) "
                    f"has only {bindus}/8 bindus. Despite general predictions, "
                    f"this transit is low-power for your specific chart. "
                    f"Avoid over-committing to decisions timed to this window.")
            is_pain = True
        else:
            continue  # neutral — don't surface

        domain = "career" if house in (1,2,3,4,5,10,11) else "spiritual"
        signals.append({
            "system": "ashtakavarga",
            "planet": planet,
            "rule_id": f"AVG_{planet}_H{house}_{label}",
            "domain": domain,
            "confidence": conf,
            "prediction": pred,
            "warning": f"{planet} transit weak for your chart ({bindus}/8 bindus)" if is_pain else "",
            "remedy_planet": planet,
            "concern_relevance": 0.88 if domain == concern else 0.65,
            "ashtakavarga_bindus": bindus,
            "ashtakavarga_label": label,
            "is_pain_signal": is_pain,
        })
    return signals



# ═══════════════════════════════════════════════════════════════
# APPLY FUNDING RULES — 6H/8H/12H Finance Signal Detector
# Fires when concern is finance/career/wealth/general
# Checks: natal H6 (loan), natal H8 (OPM), 8th lord placement,
#         current transits through H6/H8/H12
# ═══════════════════════════════════════════════════════════════

SIGN_ORDER = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
              "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
SIGN_TO_LORD = {
    "Aries":"Mars","Taurus":"Venus","Gemini":"Mercury","Cancer":"Moon",
    "Leo":"Sun","Virgo":"Mercury","Libra":"Venus","Scorpio":"Mars",
    "Sagittarius":"Jupiter","Capricorn":"Saturn","Aquarius":"Saturn",
    "Pisces":"Jupiter"
}

def apply_funding_rules(chart_data: dict, concern: str, current_transits: list = None) -> list:
    """
    Dedicated funding/loan/OPM/investment signal detector.
    Uses 6H (loans), 8H (OPM), 12H (investments/expenses) natal + transit signals.
    Also checks 8th lord placement for OPM access quality.
    """
    signals = []
    if concern not in ("career", "finance", "wealth", "general"):
        return signals

    planets = chart_data.get("planets", {})
    lagna_sign = chart_data.get("lagna", {}).get("sign", "")

    # ── 1. Natal planets in H6, H8, H12 ──────────────────────────────
    for planet, pdata in planets.items():
        house = pdata.get("house", 0)
        if house in (6, 8, 12):
            rule = LAL_KITAB_RULES.get((planet, house))
            if rule and rule.get("domain") == "finance":
                sig = {
                    "system": "natal_funding",
                    "type": f"natal_h{house}_funding",
                    "planet": planet,
                    "house": house,
                    "domain": "finance",
                    "prediction": rule["prediction"],
                    "warning": rule.get("warning", ""),
                    "remedy_planet": rule.get("remedy_planet", planet),
                    "confidence": rule["confidence"],
                    "concern_relevance": 0.95 if concern in ("finance","career") else 0.80,
                    "source": f"natal_h{house}",
                    "rule_id": f"FUND_NATAL_{planet}_H{house}",
                }
                if "funding_signal" in rule:
                    sig["funding_signal"] = rule["funding_signal"]
                if "investment_signal" in rule:
                    sig["investment_signal"] = rule["investment_signal"]
                signals.append(sig)

    # ── 2. 8th lord placement — governs HOW external capital arrives ──
    if lagna_sign in SIGN_ORDER:
        lagna_idx = SIGN_ORDER.index(lagna_sign)
        sign_8 = SIGN_ORDER[(lagna_idx + 7) % 12]
        lord_8 = SIGN_TO_LORD.get(sign_8, "")
        if lord_8 and lord_8 in planets:
            h8_lord_house = planets[lord_8].get("house", 0)
            # H2/H5/H9/H11 = strong OPM access
            if h8_lord_house in (2, 5, 9, 11):
                signals.append({
                    "system": "natal_funding",
                    "type": "8th_lord_opm_strong",
                    "planet": lord_8,
                    "house": h8_lord_house,
                    "domain": "finance",
                    "prediction": (
                        f"Your 8th lord ({lord_8}) is in house {h8_lord_house} — "
                        f"a strong structural indicator that external capital (investor funding, "
                        f"joint ventures, or inheritance) is genuinely accessible. "
                        f"The channel: {'wealth accumulation' if h8_lord_house==2 else 'creative/speculative gains' if h8_lord_house==5 else 'dharma and fortune' if h8_lord_house==9 else 'networks and gains'}."
                    ),
                    "confidence": 0.85,
                    "concern_relevance": 0.90,
                    "funding_signal": "opm_lord_strong",
                    "source": "8th_lord_placement",
                    "rule_id": f"FUND_8TH_LORD_{lord_8}_H{h8_lord_house}",
                })
            # H6/H12 = debt/foreign path more accessible than equity
            elif h8_lord_house in (6, 12):
                signals.append({
                    "system": "natal_funding",
                    "type": "8th_lord_debt_path",
                    "planet": lord_8,
                    "house": h8_lord_house,
                    "domain": "finance",
                    "prediction": (
                        f"Your 8th lord ({lord_8}) in house {h8_lord_house} suggests "
                        f"{'institutional debt (6H = loan channel)' if h8_lord_house==6 else 'foreign investment and hidden capital (12H = foreign channel)'} "
                        f"is more accessible than standard equity investment. "
                        f"Bank financing and secured credit are your primary external capital path."
                    ),
                    "confidence": 0.78,
                    "concern_relevance": 0.85,
                    "funding_signal": "debt_over_equity",
                    "source": "8th_lord_placement",
                    "rule_id": f"FUND_8TH_LORD_{lord_8}_H{h8_lord_house}",
                })
            # H1 = investors back personal brand/authority
            elif h8_lord_house == 1:
                signals.append({
                    "system": "natal_funding",
                    "type": "8th_lord_personal_brand",
                    "planet": lord_8,
                    "house": 1,
                    "domain": "finance",
                    "prediction": (
                        f"Your 8th lord ({lord_8}) in the 1st house — investors and external capital "
                        f"back YOU specifically, not just the idea. Your personal brand, professional "
                        f"reputation, and visible authority are the primary funding magnets. "
                        f"Founder-led pitches significantly outperform team-led pitches for your chart."
                    ),
                    "confidence": 0.85,
                    "concern_relevance": 0.90,
                    "funding_signal": "personal_brand_capital",
                    "source": "8th_lord_placement",
                    "rule_id": f"FUND_8TH_LORD_{lord_8}_H1",
                })

    # ── 3. Current transits through H6/H8/H12 (if transits provided) ─
    if current_transits:
        # current_transits may be a dict {planet: data} or a list of dicts
        _transits_list = (
            list(current_transits.values())
            if isinstance(current_transits, dict)
            else current_transits
        )
        for transit in _transits_list:
            if not isinstance(transit, dict):
                continue
            t_planet = transit.get("planet", "")
            t_house = transit.get("house", 0)
            if t_house in (6, 8, 12):
                rule = DUSHTANA_TRANSIT_RULES.get((t_planet, t_house))
                if rule and rule.get("domain") == "finance":
                    sig = {
                        "system": "transit_funding",
                        "type": f"transit_h{t_house}_funding",
                        "planet": t_planet,
                        "house": t_house,
                        "domain": "finance",
                        "prediction": rule["prediction"],
                        "warning": rule.get("warning", ""),
                        "confidence": rule["confidence"],
                        "concern_relevance": 0.90 if t_house in (6, 8) else 0.80,
                        "timeframe": rule.get("timeframe", ""),
                        "rarity": rule.get("rarity", "common"),
                        "source": f"transit_h{t_house}",
                        "rule_id": f"FUND_TRANSIT_{t_planet}_H{t_house}",
                    }
                    if "funding_signal" in rule:
                        sig["funding_signal"] = rule["funding_signal"]
                    if "investment_signal" in rule:
                        sig["investment_signal"] = rule["investment_signal"]
                    signals.append(sig)

    return signals


def get_funding_summary(funding_signals: list) -> dict:
    """
    Summarize funding signals into a structured object for the prompt builder.
    Returns primary channel, timing, warnings, and investor type.
    """
    if not funding_signals:
        return {}

    CHANNEL_LABELS = {
        "government_institutional": "Government Grant / Institutional Funding",
        "institutional_loan": "Bank / Institutional Loan",
        "delayed_institutional": "Bank Funding (preparation required first)",
        "asset_backed_loan": "Asset-backed / Real Estate Debt",
        "grant_documentation": "Government Grant / Documented Credit",
        "relationship_partner_funding": "Partner / Co-founder Backed Credit",
        "community_crowdfunding": "Community / Crowdfunding",
        "foreign_unconventional_loan": "Foreign / Fintech / Alternative Credit",
        "avoid_complex_debt": "Simple Self-funding or Revenue-based (avoid complex debt)",
        "authority_government_grant": "Government Grant / Authority-backed Funding",
        "community_consumer_funding": "Community / Consumer Brand Investment",
        "competitive_asset_capital": "Asset-backed / Competitive External Capital",
        "tech_ip_funding": "Tech VC / IP-backed Investor Funding",
        "investor_windfall": "Angel / VC / Inheritance Capital",
        "partner_cofounder_funding": "Co-founder / Partner Capital",
        "patient_institutional_capital": "Long-term Institutional Capital (5-10yr)",
        "sudden_foreign_capital": "Foreign / Cross-border Investor Capital",
        "mission_impact_funding": "Impact / Mission-driven Investment",
        "opm_lord_strong": "External Capital (structurally accessible)",
        "personal_brand_capital": "Founder-led / Personal Brand Investment",
        "debt_over_equity": "Debt Financing (stronger than equity for this chart)",
        "peak_investor_window": "Angel / VC Capital — PEAK WINDOW ACTIVE",
        "institutional_loan_window": "Institutional Loan — WINDOW ACTIVE",
        "unconventional_foreign_loan_window": "Foreign / Alternative Credit — WINDOW ACTIVE",
        "sudden_foreign_capital_window": "Foreign Investor Capital — MAJOR WINDOW",
        "patient_capital_due_diligence": "Institutional Capital — Due Diligence Phase",
    }

    # Sort by confidence
    sorted_sigs = sorted(funding_signals, key=lambda s: s.get("confidence", 0), reverse=True)
    primary = sorted_sigs[0]
    primary_signal = primary.get("funding_signal") or primary.get("investment_signal", "")

    # Collect all unique channels
    all_channels = []
    for s in sorted_sigs:
        ch = s.get("funding_signal") or s.get("investment_signal", "")
        if ch and ch not in all_channels:
            all_channels.append(ch)

    # Is there an active transit window?
    active_windows = [s for s in sorted_sigs if s.get("system") == "transit_funding"]
    has_active_window = bool(active_windows)

    # Collect all warnings
    warnings = [s["warning"] for s in sorted_sigs if s.get("warning")]

    return {
        "primary_channel": CHANNEL_LABELS.get(primary_signal, "External Capital"),
        "primary_signal": primary_signal,
        "all_channels": [CHANNEL_LABELS.get(c, c) for c in all_channels[:3]],
        "has_active_window": has_active_window,
        "active_window_type": active_windows[0].get("funding_signal", "") if active_windows else "",
        "primary_confidence": primary.get("confidence", 0),
        "top_warning": warnings[0] if warnings else "",
        "is_delayed": any("delayed" in s.get("funding_signal","") or "patient" in s.get("funding_signal","") for s in sorted_sigs),
        "is_opm": any("investor" in s.get("funding_signal","") or "opm" in s.get("funding_signal","") or "capital" in s.get("funding_signal","") or "windfall" in s.get("funding_signal","") for s in sorted_sigs),
        "is_loan": any("loan" in s.get("funding_signal","") or "institutional" in s.get("funding_signal","") or "bank" in s.get("funding_signal","") or "debt" in s.get("funding_signal","") for s in sorted_sigs),
    }


def apply_lk_aspects_local(chart_data: dict, concern: str) -> list:
    """Wire lk_aspects_rin.apply_lk_aspect_rules into the pipeline."""
    try:
        from antar_engine.lk_aspects_rin import apply_lk_aspect_rules
        return apply_lk_aspect_rules(chart_data, concern)
    except ImportError:
        pass
    # Fallback: inline minimal aspect rules for the most impactful combos
    return _apply_lk_aspects_inline(chart_data, concern)


def apply_rin_rules_local(chart_data: dict, concern: str) -> list:
    """Wire lk_aspects_rin.apply_rin_rules into the pipeline."""
    try:
        from antar_engine.lk_aspects_rin import apply_rin_rules
        return apply_rin_rules(chart_data, concern)
    except ImportError:
        pass
    return _apply_rin_inline(chart_data, concern)


def _apply_lk_aspects_inline(chart_data: dict, concern: str) -> list:
    """Inline fallback: fire 6 highest-impact LK aspect rules."""
    signals = []
    LK_KEY = {
        ("Saturn", 10): ("career",  0.85, False,
            "Saturn aspects your 10th house — career rises through discipline and becomes unshakeable legacy. Government, structured institutions, and senior roles are supported.", ""),
        ("Jupiter", 9): ("spiritual",0.90, False,
            "Jupiter aspects your 9th house — fortune, higher wisdom, and dharma are powerfully blessed. Good luck is genuine and recurring. Teachers and guides appear when needed.", ""),
        ("Jupiter", 7): ("marriage", 0.88, False,
            "Jupiter aspects your 7th house — marriage and partnerships receive Jupiter's full blessing. The spouse brings wisdom, expansion, and prosperity.", ""),
        ("Mars", 7):    ("marriage", 0.82, True,
            "Mars aspects your 7th house — Mangal Dosh in effect. Marriage carries intensity and conflict potential simultaneously.", "Match with partner who also has Mars in 1/4/7/8/12 to neutralize."),
        ("Rahu", 7):    ("marriage", 0.80, True,
            "Rahu aspects your 7th house — partnerships are karmic and unconventional. Written agreements are specifically protective.", ""),
        ("Saturn", 7):  ("marriage", 0.83, True,
            "Saturn aspects your 7th house — marriage is delayed or tested. The right partner arrives late but is exceptionally durable.", ""),
    }
    for planet, pdata in chart_data.get("planets", {}).items():
        house = pdata.get("house", 0)
        if not house:
            continue
        LK_OFFSETS = {"Sun":[4,5,7,9,10],"Moon":[5,7],"Mars":[4,7,8],
                      "Mercury":[4,7],"Jupiter":[5,7,9],"Venus":[3,7],
                      "Saturn":[3,7,10],"Rahu":[5,7,9],"Ketu":[5,7,9]}
        for offset in LK_OFFSETS.get(planet, [7]):
            target = ((house + offset - 1 - 1) % 12) + 1
            rule = LK_KEY.get((planet, target))
            if rule:
                domain, conf, pain, pred, warn = rule
                signals.append({
                    "system": "lk_aspect", "planet": planet,
                    "rule_id": f"LKA_{planet}_H{target}",
                    "domain": domain, "confidence": conf,
                    "prediction": pred, "warning": warn,
                    "remedy_planet": planet,
                    "concern_relevance": 0.88 if domain == concern else 0.55,
                    "is_pain_signal": pain,
                })
    return signals


def _apply_rin_inline(chart_data: dict, concern: str) -> list:
    """Inline fallback: detect the 3 most common rin patterns."""
    signals = []
    planets = chart_data.get("planets", {})
    DEBIT = {"Sun":6,"Moon":7,"Mars":3,"Mercury":11,"Jupiter":9,"Venus":5,"Saturn":0}

    def debit(p):
        return planets.get(p,{}).get("sign_index",-1) == DEBIT.get(p,-1)

    def house(p):
        return planets.get(p,{}).get("house",0)

    # Pitru Rin: Sun debilitated
    if debit("Sun"):
        signals.append({
            "system":"lk_rin","planet":"Saturn","rin_type":"Pitru Rin",
            "rule_id":"RIN_PITRU","domain":"spiritual","confidence":0.75,
            "prediction":"Pitru Rin (Father's Ancestral Debt) is present. "
                "This causes obstacles disproportionate to effort and delayed fortune. "
                "Remedy: Feed crows on Saturdays. Offer water to the Sun at sunrise daily. "
                "Perform Pitru Tarpan on Amavasya (new moon).",
            "warning":"Career recognition comes later than deserved. Father relationship is complex.",
            "remedy_planet":"Saturn",
            "concern_relevance":0.80 if concern=="spiritual" else 0.60,
            "is_pain_signal":True,
        })

    # Matru Rin: Moon debilitated
    if debit("Moon"):
        signals.append({
            "system":"lk_rin","planet":"Moon","rin_type":"Matru Rin",
            "rule_id":"RIN_MATRU","domain":"health","confidence":0.72,
            "prediction":"Matru Rin (Mother's Ancestral Debt) is present. "
                "Emotional security and domestic stability require more effort than for most. "
                "Remedy: Serve your mother or elderly women. Keep a silver glass of water by your bed — "
                "pour it at a tree root each morning. Feed white cows on Mondays.",
            "warning":"Emotional decisions need extra time to process under Matru Rin.",
            "remedy_planet":"Moon",
            "concern_relevance":0.80 if concern=="health" else 0.58,
            "is_pain_signal":True,
        })

    # Stri Rin: Saturn in H7
    if house("Saturn") == 7:
        signals.append({
            "system":"lk_rin","planet":"Venus","rin_type":"Stri Rin",
            "rule_id":"RIN_STRI","domain":"marriage","confidence":0.73,
            "prediction":"Stri Rin (Partner Ancestral Debt) is indicated by Saturn in your 7th house. "
                "Past-life karma with a partner is replaying in relationship patterns. "
                "Remedy: Respect and actively serve the women in your family. "
                "Donate white sweets to married women on Fridays for 11 weeks.",
            "warning":"Relationship patterns repeat until the karmic account is addressed through action.",
            "remedy_planet":"Venus",
            "concern_relevance":0.88 if concern=="marriage" else 0.60,
            "is_pain_signal":True,
        })

    return signals


# ── FINAL run_all_rules — v4 complete ─────────────────────────────────────────

_run_all_rules_v4_base = run_all_rules  # snapshot v3


def run_all_rules(chart_data: dict, dashas: dict, current_transits,
                  concern: str = "general", country_code: str = "IN",
                  user_age: int = 0) -> dict:
    """
    v4 — COMPLETE ENGINE:
    v3 + Ashtakavarga (real BPHS bindus) + LK Aspects + Rin (debt) rules.

    All 15 rule systems now active:
      1.  Lal Kitab natal placements
      2.  Jaimini Karakas (AK/AmK/GK)
      3.  Dasha activation
      4.  Standard transits
      5.  Dushtana 6/8/12 transits
      6.  Rahu/Ketu over natal planets
      7.  D9 Navamsa (planet in sign + house + Vargottama)
      8.  Classical Yoga detection (D1)
      9.  Antardasha MD/AD combinations
      10. Nakshatra Tara (transit nakshatra vs birth star)
      11. Sade Sati (3-phase)
      12. Yoga Engine (domain-specific deep yoga detection)
      13. D10/D3/D60 divisional chart signals
      14. Lal Kitab Varshphal (annual chart)
      15. Ashtakavarga (BPHS bindu tables — real transit strength)
      16. Lal Kitab Aspects (Sun/Moon/Mars/Jupiter/Saturn/Rahu/Ketu)
      17. Rin rules (Pitru/Matru/Stri/Putra/Bhatru debt detection)
    """
    result = _run_all_rules_v4_base(chart_data, dashas, current_transits,
                                     concern, country_code, user_age)

    # New signals
    avarga_sigs  = apply_ashtakavarga_signals_local(chart_data, current_transits, concern)
    lk_asp_sigs  = apply_lk_aspects_local(chart_data, concern)
    rin_sigs     = apply_rin_rules_local(chart_data, concern)
    funding_sigs = apply_funding_rules(chart_data, concern, current_transits)

    all_new = avarga_sigs + lk_asp_sigs + rin_sigs + funding_sigs

    # Merge + re-rank
    prev_signals = (
        result.get("lal_kitab",[]) + result.get("jaimini",[]) +
        result.get("dasha",[])     + result.get("transit",[]) +
        result.get("d9",[])        + result.get("yogas",[]) +
        result.get("antardasha",[])+ result.get("nakshatra_tara",[]) +
        result.get("sade_sati",[]) + result.get("yoga_engine",[]) +
        result.get("d10",[])       + result.get("d3",[]) +
        result.get("d60",[])       + result.get("varshphal",[])
    )
    all_signals = prev_signals + all_new

    karakas     = result["karakas"]
    top_signals = rank_signals(all_signals, concern, karakas)

    # Ashtakavarga boost: apply bindu multipliers to transit signals in top_signals
    try:
        from antar_engine.ashtakavarga import ashtakavarga_transit_boost
        top_signals = ashtakavarga_transit_boost(top_signals, chart_data)
    except ImportError:
        pass  # boost runs on server with full imports

    # Rebuild remedies
    seen_planets, remedies = set(), []
    for s in top_signals:
        rp = s.get("remedy_planet","")
        if rp and rp not in seen_planets:
            rem = format_remedy_for_location(rp, country_code)
            if rem:
                rem["for_domain"] = s["domain"]
                remedies.append(rem)
                seen_planets.add(rp)
        if len(remedies) >= 3:
            break

    # Rin summary for prompt builder
    rin_types = [s["rin_type"] for s in rin_sigs]

    # Ashtakavarga summary (bindus for current slow transits)
    avarga_summary = {s["planet"]: s.get("ashtakavarga_bindus",0)
                      for s in avarga_sigs if "ashtakavarga_bindus" in s}

    from collections import Counter as _C
    domain_votes    = _C(s["domain"] for s in all_signals)
    dominant_domain = domain_votes.most_common(1)[0][0] if domain_votes else "general"
    active_systems  = sorted(set(s.get("system","") for s in all_signals))

    return {
        **result,
        # New signal pools
        "ashtakavarga":     avarga_sigs,
        "lk_aspects":       lk_asp_sigs,
        "rin":              rin_sigs,
        # Updated aggregates
        "top_signals":      top_signals,
        "dominant_domain":  dominant_domain,
        "total_rules_fired":len(all_signals),
        "total_rules_passed_filter": len(top_signals),
        "remedies":         remedies,
        "active_systems":   active_systems,
        # New flags
        "has_ashtakavarga": bool(avarga_sigs),
        "has_lk_aspects":   bool(lk_asp_sigs),
        "has_rin":          bool(rin_sigs),
        "rin_types":        rin_types,
        "ashtakavarga_summary": avarga_summary,
    }
