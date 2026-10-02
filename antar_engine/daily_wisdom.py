"""
Daily Wisdom — a chart-aware daily-scripture surface (prototype).

A curated Bhagavad Gita corpus (Sanskrit + transliteration + a plain-English
rendering written for Antar, so nothing is lifted from a copyrighted modern
translation). The verse of the day is chosen to match the reader's CURRENT
season — this is Antar's edge over a generic daily-verse feed: om.ai gives
everyone the same verse; here the verse fits what the person is actually moving
through, and the conversational follow-ups can route into the chart.

INTEGRITY: the corpus is fixed and reviewed. The LLM is NEVER used to generate
scripture (it hallucinates Sanskrit and mis-numbers verses) — only the
downstream "tell me more" chat (handled by /ask) runs on the LLM, with the
verse passed as context. This mirrors the no-invention discipline of the Today
engine.

v1 scope: ~25 verses, 3 seasons, deterministic per-reader-per-day pick. The
verse's English rendering is EN-only for now (Spanish/Portuguese curation is a
fast follow); the UI strings (why_now, suggested questions) are localized
deterministically here, no LLM.
"""

from __future__ import annotations
from datetime import date
import hashlib
from typing import Optional


# ── Curated corpus ───────────────────────────────────────────────────────────
# Each verse: ref, sanskrit (Devanagari), translit (IAST-ish), translation
# (Antar's own plain rendering), themes[]. Themes drive the season match.
VERSES = [
    {
        "ref": "2.47", "chapter": 2, "verse": 47,
        "sanskrit": "कर्मण्येवाधिकारस्ते मा फलेषु कदाचन।\nमा कर्मफलहेतुर्भूर्मा ते सङ्गोऽस्त्वकर्मणि॥",
        "translit": "karmaṇy-evādhikāras te mā phaleṣu kadācana | mā karma-phala-hetur bhūr mā te saṅgo 'stv akarmaṇi",
        "translation": "You have a right to your actions, never to their fruits. Don't act for the results — but don't withdraw from action either.",
        "themes": ["action", "detachment", "duty"],
    },
    {
        "ref": "2.48", "chapter": 2, "verse": 48,
        "sanskrit": "योगस्थः कुरु कर्माणि सङ्गं त्यक्त्वा धनञ्जय।\nसिद्ध्यसिद्ध्योः समो भूत्वा समत्वं योग उच्यते॥",
        "translit": "yoga-sthaḥ kuru karmāṇi saṅgaṁ tyaktvā dhanañjaya | siddhy-asiddhyoḥ samo bhūtvā samatvaṁ yoga ucyate",
        "translation": "Do your work steadily, letting go of attachment, the same in success and failure. That evenness of mind is yoga.",
        "themes": ["equanimity", "action", "balance"],
    },
    {
        "ref": "2.14", "chapter": 2, "verse": 14,
        "sanskrit": "मात्रास्पर्शास्तु कौन्तेय शीतोष्णसुखदुःखदाः।\nआगमापायिनोऽनित्यास्तांस्तितिक्षस्व भारत॥",
        "translit": "mātrā-sparśās tu kaunteya śītoṣṇa-sukha-duḥkha-dāḥ | āgamāpāyino 'nityās tāṁs titikṣasva bhārata",
        "translation": "Cold and heat, pleasure and pain come and go; they never last. Meet them with patience.",
        "themes": ["endurance", "impermanence", "perseverance"],
    },
    {
        "ref": "2.20", "chapter": 2, "verse": 20,
        "sanskrit": "न जायते म्रियते वा कदाचिन्नायं भूत्वा भविता वा न भूयः।\nअजो नित्यः शाश्वतोऽयं पुराणो न हन्यते हन्यमाने शरीरे॥",
        "translit": "na jāyate mriyate vā kadācin nāyaṁ bhūtvā bhavitā vā na bhūyaḥ | ajo nityaḥ śāśvato 'yaṁ purāṇo na hanyate hanyamāne śarīre",
        "translation": "The self is never born and never dies. Unborn and eternal, it is not harmed when the body is harmed.",
        "themes": ["self_knowledge", "fearlessness", "impermanence"],
    },
    {
        "ref": "2.22", "chapter": 2, "verse": 22,
        "sanskrit": "वासांसि जीर्णानि यथा विहाय नवानि गृह्णाति नरोऽपराणि।\nतथा शरीराणि विहाय जीर्णान्यन्यानि संयाति नवानि देही॥",
        "translit": "vāsāṁsi jīrṇāni yathā vihāya navāni gṛhṇāti naro 'parāṇi | tathā śarīrāṇi vihāya jīrṇāny anyāni saṁyāti navāni dehī",
        "translation": "As a person sheds worn-out clothes for new ones, the soul lets go of worn-out bodies for new.",
        "themes": ["impermanence", "self_knowledge"],
    },
    {
        "ref": "2.56", "chapter": 2, "verse": 56,
        "sanskrit": "दुःखेष्वनुद्विग्नमनाः सुखेषु विगतस्पृहः।\nवीतरागभयक्रोधः स्थितधीर्मुनिरुच्यते॥",
        "translit": "duḥkheṣv anudvigna-manāḥ sukheṣu vigata-spṛhaḥ | vīta-rāga-bhaya-krodhaḥ sthita-dhīr munir ucyate",
        "translation": "Unshaken in sorrow, not grasping in pleasure, free of attachment, fear, and anger — such a one is steady in wisdom.",
        "themes": ["equanimity", "calm", "mind"],
    },
    {
        "ref": "2.70", "chapter": 2, "verse": 70,
        "sanskrit": "आपूर्यमाणमचलप्रतिष्ठं समुद्रमापः प्रविशन्ति यद्वत्।\nतद्वत्कामा यं प्रविशन्ति सर्वे स शान्तिमाप्नोति न कामकामी॥",
        "translit": "āpūryamāṇam acala-pratiṣṭhaṁ samudram āpaḥ praviśanti yadvat | tadvat kāmā yaṁ praviśanti sarve sa śāntim āpnoti na kāma-kāmī",
        "translation": "As rivers pour into the ocean, yet it stays full and unmoved — so desires enter the peaceful one, who finds calm, not the one who chases them.",
        "themes": ["calm", "contentment", "equanimity"],
    },
    {
        "ref": "2.3", "chapter": 2, "verse": 3,
        "sanskrit": "क्लैब्यं मा स्म गमः पार्थ नैतत्त्वय्युपपद्यते।\nक्षुद्रं हृदयदौर्बल्यं त्यक्त्वोत्तिष्ठ परन्तप॥",
        "translit": "klaibyaṁ mā sma gamaḥ pārtha naitat tvayy upapadyate | kṣudraṁ hṛdaya-daurbalyaṁ tyaktvottiṣṭha parantapa",
        "translation": "Don't give in to weakness — it doesn't suit you. Shake off this small faint-heartedness and rise.",
        "themes": ["courage", "confidence", "action"],
    },
    {
        "ref": "2.50", "chapter": 2, "verse": 50,
        "sanskrit": "बुद्धियुक्तो जहातीह उभे सुकृतदुष्कृते।\nतस्माद्योगाय युज्यस्व योगः कर्मसु कौशलम्॥",
        "translit": "buddhi-yukto jahātīha ubhe sukṛta-duṣkṛte | tasmād yogāya yujyasva yogaḥ karmasu kauśalam",
        "translation": "Act with a balanced mind and you rise above both good and bad outcomes. Yoga is skill in action.",
        "themes": ["action", "skill", "balance"],
    },
    {
        "ref": "3.21", "chapter": 3, "verse": 21,
        "sanskrit": "यद्यदाचरति श्रेष्ठस्तत्तदेवेतरो जनः।\nस यत्प्रमाणं कुरुते लोकस्तदनुवर्तते॥",
        "translit": "yad yad ācarati śreṣṭhas tat tad evetaro janaḥ | sa yat pramāṇaṁ kurute lokas tad anuvartate",
        "translation": "Whatever a leader does, others follow; the standard they set, the world takes up.",
        "themes": ["leadership", "character"],
    },
    {
        "ref": "3.35", "chapter": 3, "verse": 35,
        "sanskrit": "श्रेयान्स्वधर्मो विगुणः परधर्मात्स्वनुष्ठितात्।\nस्वधर्मे निधनं श्रेयः परधर्मो भयावहः॥",
        "translit": "śreyān sva-dharmo viguṇaḥ para-dharmāt sv-anuṣṭhitāt | sva-dharme nidhanaṁ śreyaḥ para-dharmo bhayāvahaḥ",
        "translation": "Better your own path, imperfectly walked, than someone else's walked well. It is safer to live by what is truly yours.",
        "themes": ["authenticity", "dharma", "purpose"],
    },
    {
        "ref": "4.7", "chapter": 4, "verse": 7,
        "sanskrit": "यदा यदा हि धर्मस्य ग्लानिर्भवति भारत।\nअभ्युत्थानमधर्मस्य तदात्मानं सृजाम्यहम्॥",
        "translit": "yadā yadā hi dharmasya glānir bhavati bhārata | abhyutthānam adharmasya tadātmānaṁ sṛjāmy aham",
        "translation": "Whenever what is right grows weak and what is wrong rises, I come forth.",
        "themes": ["hope", "faith", "order"],
    },
    {
        "ref": "4.38", "chapter": 4, "verse": 38,
        "sanskrit": "न हि ज्ञानेन सदृशं पवित्रमिह विद्यते।\nतत्स्वयं योगसंसिद्धः कालेनात्मनि विन्दति॥",
        "translit": "na hi jñānena sadṛśaṁ pavitram iha vidyate | tat svayaṁ yoga-saṁsiddhaḥ kālenātmani vindati",
        "translation": "Nothing in this world purifies like true knowledge. In time, the one who is ready finds it within.",
        "themes": ["self_knowledge", "wisdom"],
    },
    {
        "ref": "6.5", "chapter": 6, "verse": 5,
        "sanskrit": "उद्धरेदात्मनात्मानं नात्मानमवसादयेत्।\nआत्मैव ह्यात्मनो बन्धुरात्मैव रिपुरात्मनः॥",
        "translit": "uddhared ātmanātmānaṁ nātmānam avasādayet | ātmaiva hy ātmano bandhur ātmaiva ripur ātmanaḥ",
        "translation": "Lift yourself by yourself; don't drag yourself down. You are your own best friend — and your own worst enemy.",
        "themes": ["self_reliance", "confidence", "mind"],
    },
    {
        "ref": "6.19", "chapter": 6, "verse": 19,
        "sanskrit": "यथा दीपो निवातस्थो नेङ्गते सोपमा स्मृता।\nयोगिनो यतचित्तस्य युञ्जतो योगमात्मनः॥",
        "translit": "yathā dīpo nivāta-stho neṅgate sopamā smṛtā | yogino yata-cittasya yuñjato yogam ātmanaḥ",
        "translation": "Like a lamp in a windless place that does not flicker — so is the steady mind of one absorbed in practice.",
        "themes": ["focus", "meditation", "mind"],
    },
    {
        "ref": "6.35", "chapter": 6, "verse": 35,
        "sanskrit": "असंशयं महाबाहो मनो दुर्निग्रहं चलम्।\nअभ्यासेन तु कौन्तेय वैराग्येण च गृह्यते॥",
        "translit": "asaṁśayaṁ mahā-bāho mano durnigrahaṁ calam | abhyāsena tu kaunteya vairāgyeṇa ca gṛhyate",
        "translation": "Yes — the mind is restless and hard to hold. But through steady practice and a lighter grip on things, it is mastered.",
        "themes": ["perseverance", "practice", "mind"],
    },
    {
        "ref": "6.17", "chapter": 6, "verse": 17,
        "sanskrit": "युक्ताहारविहारस्य युक्तचेष्टस्य कर्मसु।\nयुक्तस्वप्नावबोधस्य योगो भवति दुःखहा॥",
        "translit": "yuktāhāra-vihārasya yukta-ceṣṭasya karmasu | yukta-svapnāvabodhasya yogo bhavati duḥkha-hā",
        "translation": "For the one balanced in food, rest, work, and sleep, practice itself becomes the end of sorrow.",
        "themes": ["balance", "wellbeing"],
    },
    {
        "ref": "9.22", "chapter": 9, "verse": 22,
        "sanskrit": "अनन्याश्चिन्तयन्तो मां ये जनाः पर्युपासते।\nतेषां नित्याभियुक्तानां योगक्षेमं वहाम्यहम्॥",
        "translit": "ananyāś cintayanto māṁ ye janāḥ paryupāsate | teṣāṁ nityābhiyuktānāṁ yoga-kṣemaṁ vahāmy aham",
        "translation": "To those who are steadily devoted, I carry what they lack and protect what they have.",
        "themes": ["surrender", "support", "devotion"],
    },
    {
        "ref": "9.34", "chapter": 9, "verse": 34,
        "sanskrit": "मन्मना भव मद्भक्तो मद्याजी मां नमस्कुरु।\nमामेवैष्यसि युक्त्वैवमात्मानं मत्परायणः॥",
        "translit": "man-manā bhava mad-bhakto mad-yājī māṁ namaskuru | mām evaiṣyasi yuktvaivam ātmānaṁ mat-parāyaṇaḥ",
        "translation": "Fix your mind on Me, give your heart, and you will come to Me.",
        "themes": ["devotion"],
    },
    {
        "ref": "11.45", "chapter": 11, "verse": 45,
        "sanskrit": "अदृष्टपूर्वं हृषितोऽस्मि दृष्ट्वा भयेन च प्रव्यथितं मनो मे।\nतदेव मे दर्शय देव रूपं प्रसीद देवेश जगन्निवास॥",
        "translit": "adṛṣṭa-pūrvaṁ hṛṣito 'smi dṛṣṭvā bhayena ca pravyathitaṁ mano me | tad eva me darśaya deva rūpaṁ prasīda deveśa jagan-nivāsa",
        "translation": "I am thrilled to see what was never seen before — yet my mind trembles with fear. Show me the familiar form; be gracious.",
        "themes": ["awe", "humility"],
    },
    {
        "ref": "12.15", "chapter": 12, "verse": 15,
        "sanskrit": "यस्मान्नोद्विजते लोको लोकान्नोद्विजते च यः।\nहर्षामर्षभयोद्वेगैर्मुक्तो यः स च मे प्रियः॥",
        "translit": "yasmān nodvijate loko lokān nodvijate ca yaḥ | harṣāmarṣa-bhayodvegair mukto yaḥ sa ca me priyaḥ",
        "translation": "The one who neither troubles the world nor is troubled by it — free of elation, envy, fear, and anxiety — is dear to Me.",
        "themes": ["equanimity", "character", "calm"],
    },
    {
        "ref": "15.5", "chapter": 15, "verse": 5,
        "sanskrit": "निर्मानमोहा जितसङ्गदोषा अध्यात्मनित्या विनिवृत्तकामाः।\nद्वन्द्वैर्विमुक्ताः सुखदुःखसंज्ञैर्गच्छन्त्यमूढाः पदमव्ययं तत्॥",
        "translit": "nirmāna-mohā jita-saṅga-doṣā adhyātma-nityā vinivṛtta-kāmāḥ | dvandvair vimuktāḥ sukha-duḥkha-saṁjñair gacchanty amūḍhāḥ padam avyayaṁ tat",
        "translation": "Free of pride and delusion, beyond clinging, desires stilled, released from the pull of pleasure and pain — the clear-eyed reach the lasting.",
        "themes": ["detachment", "self_knowledge"],
    },
    {
        "ref": "18.66", "chapter": 18, "verse": 66,
        "sanskrit": "सर्वधर्मान्परित्यज्य मामेकं शरणं व्रज।\nअहं त्वां सर्वपापेभ्यो मोक्षयिष्यामि मा शुचः॥",
        "translit": "sarva-dharmān parityajya mām ekaṁ śaraṇaṁ vraja | ahaṁ tvāṁ sarva-pāpebhyo mokṣayiṣyāmi mā śucaḥ",
        "translation": "Let go of all else and take refuge in Me alone. I will free you from all that binds — do not grieve.",
        "themes": ["surrender", "faith"],
    },
    {
        "ref": "18.78", "chapter": 18, "verse": 78,
        "sanskrit": "यत्र योगेश्वरः कृष्णो यत्र पार्थो धनुर्धरः।\nतत्र श्रीर्विजयो भूतिर्ध्रुवा नीतिर्मतिर्मम॥",
        "translit": "yatra yogeśvaraḥ kṛṣṇo yatra pārtho dhanur-dharaḥ | tatra śrīr vijayo bhūtir dhruvā nītir matir mama",
        "translation": "Where wisdom and willing effort stand together, there follow fortune, victory, and steady right conduct.",
        "themes": ["victory", "confidence", "leadership"],
    },
]


# ── Season → themes ──────────────────────────────────────────────────────────
EXPANSIVE = {"Jupiter", "Rahu", "Venus", "Sun", "Moon"}
CONTRACTING = {"Saturn", "Ketu", "Mars"}

SEASON_THEMES = {
    "consolidating": ["perseverance", "endurance", "equanimity", "detachment",
                      "duty", "self_reliance", "practice", "calm"],
    "expansive":     ["purpose", "action", "courage", "confidence", "leadership",
                      "dharma", "devotion", "victory"],
    "steady":        ["equanimity", "wisdom", "balance", "mind", "self_knowledge",
                      "skill", "focus"],
}

WHY_NOW = {
    "consolidating": {
        "en": "You're in a season that rewards patience and steady effort — let this sit with you as you build through the slow stretch.",
        "es": "Estás en una temporada que premia la paciencia y el esfuerzo constante — deja que esto te acompañe mientras construyes en el tramo lento.",
        "pt": "Você está numa temporada que recompensa a paciência e o esforço constante — deixe isto te acompanhar enquanto constrói no trecho lento.",
    },
    "expansive": {
        "en": "You're in a forward-leaning, expansive season — let this give shape to the push.",
        "es": "Estás en una temporada expansiva y de impulso — deja que esto dé forma al empuje.",
        "pt": "Você está numa temporada expansiva e de impulso — deixe isto dar forma ao avanço.",
    },
    "steady": {
        "en": "You're in a steady, clear stretch — let this keep your mind even and sharp.",
        "es": "Estás en un tramo estable y claro — deja que esto mantenga tu mente serena y lúcida.",
        "pt": "Você está num trecho estável e claro — deixe isto manter sua mente equilibrada e lúcida.",
    },
}

SUGGESTED = [
    {"en": "What does this verse mean for everyday life?",
     "es": "¿Qué significa este verso para la vida diaria?",
     "pt": "O que este verso significa para o dia a dia?"},
    {"en": "How do I actually practice this today?",
     "es": "¿Cómo lo pongo en práctica hoy?",
     "pt": "Como coloco isto em prática hoje?"},
    {"en": "Which mantra fits what I'm moving through right now?",
     "es": "¿Qué mantra encaja con lo que estoy atravesando ahora?",
     "pt": "Qual mantra combina com o que estou vivendo agora?",
     "chart_aware": True},
    {"en": "Explain this in simpler terms",
     "es": "Explícalo en términos más simples",
     "pt": "Explique em termos mais simples"},
    {"en": "How can I start a steadier spiritual routine?",
     "es": "¿Cómo empiezo una rutina espiritual más constante?",
     "pt": "Como começo uma rotina espiritual mais constante?"},
]


def _lang(language: Optional[str]) -> str:
    l = (language or "en").split("-")[0].lower()
    return l if l in ("en", "es", "pt") else "en"


def _current_md_lord(dashas: dict) -> Optional[str]:
    """Current Vimsottari mahadasha lord (season source). Never raises."""
    try:
        rows = (dashas or {}).get("vimsottari") or (dashas or {}).get("vimshottari") or []
        today = date.today().isoformat()
        for r in rows:
            if str(r.get("level") or r.get("type", "")).lower() not in ("mahadasha", "maha", "md"):
                continue
            s = str(r.get("start_date") or r.get("start") or "")[:10]
            e = str(r.get("end_date") or r.get("end") or "")[:10]
            if s and e and s <= today <= e:
                return r.get("planet_or_sign") or r.get("lord_or_sign")
    except Exception:
        pass
    return None


def _season(dashas: dict) -> str:
    lord = _current_md_lord(dashas)
    if lord in CONTRACTING:
        return "consolidating"
    if lord in EXPANSIVE:
        return "expansive"
    return "steady"  # Mercury, or unknown → steady/clear


def _pick(candidates: list, seed_str: str) -> dict:
    if not candidates:
        candidates = VERSES
    h = int(hashlib.md5(seed_str.encode("utf-8")).hexdigest(), 16)
    return candidates[h % len(candidates)]


def build_daily_wisdom(chart_data: dict, dashas: dict, chart_id: str = "",
                       language: str = "en", today: Optional[str] = None) -> dict:
    """The verse of the day, matched to the reader's season, + conversational
    follow-ups. Fail-open: with no chart/dashas it still returns a verse
    (steady season). Never raises."""
    try:
        lang = _lang(language)
        today = today or date.today().isoformat()
        season = _season(dashas)

        prefs = SEASON_THEMES.get(season, [])
        candidates = [v for v in VERSES if set(v["themes"]) & set(prefs)] or VERSES
        verse = _pick(candidates, f"{chart_id}|{today}|{season}")

        # primary theme = first of the verse's themes that the season prefers
        primary = next((t for t in verse["themes"] if t in prefs), verse["themes"][0])

        suggested = [s[lang] for s in SUGGESTED]
        ask_context = (
            f"The reader is reflecting on Bhagavad Gita {verse['ref']}: "
            f"\"{verse['translation']}\" (theme: {primary}). Answer their question "
            f"about this verse or about spiritual practice in plain, warm language — "
            f"no Sanskrit jargon unless they ask for it."
        )

        return {
            "available": True,
            "season": season,
            "theme": primary,
            "verse": {
                "source": f"Bhagavad Gita {verse['ref']}",
                "reference": verse["ref"],
                "sanskrit": verse["sanskrit"],
                "transliteration": verse["translit"],
                "translation": verse["translation"],
            },
            "why_now": WHY_NOW.get(season, WHY_NOW["steady"])[lang],
            "suggested_questions": suggested,
            "ask_context": ask_context,
            "language": lang,
            "corpus_size": len(VERSES),
        }
    except Exception as _e:
        print(f"[daily-wisdom] build non-fatal: {_e}")
        # last-resort universal verse
        v = VERSES[0]
        return {
            "available": True, "season": "steady", "theme": v["themes"][0],
            "verse": {"source": f"Bhagavad Gita {v['ref']}", "reference": v["ref"],
                      "sanskrit": v["sanskrit"], "transliteration": v["translit"],
                      "translation": v["translation"]},
            "why_now": WHY_NOW["steady"]["en"],
            "suggested_questions": [s["en"] for s in SUGGESTED],
            "ask_context": "", "language": "en", "corpus_size": len(VERSES),
        }
