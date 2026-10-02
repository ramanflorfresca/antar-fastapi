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
        "ref": "2.3", "chapter": 2, "verse": 3,
        "sanskrit": "क्लैब्यं मा स्म गमः पार्थ नैतत्त्वय्युपपद्यते।\nक्षुद्रं हृदयदौर्बल्यं त्यक्त्वोत्तिष्ठ परन्तप",
        "translit": "klaibyaṁ mā sma gamaḥ pārtha naitat tvayyupapadyate | kṣhudraṁ hṛidaya-daurbalyaṁ tyaktvottiṣhṭha parantapa",
        "translation": "Don't give in to weakness — it doesn't become you. Shake off this small faintness of heart and stand up.",
        "themes": ["courage", "confidence", "action"],
    },
    {
        "ref": "2.11", "chapter": 2, "verse": 11,
        "sanskrit": "श्री भगवानुवाच\nअशोच्यानन्वशोचस्त्वं प्रज्ञावादांश्च भाषसे।\nगतासूनगतासूंश्च नानुशोचन्ति पण्डिताः",
        "translit": "śhrī bhagavān uvācha | aśhochyān-anvaśhochas-tvaṁ prajñā-vādānśh cha bhāṣhase | gatāsūn-agatāsūnśh-cha nānuśhochanti paṇḍitāḥ",
        "translation": "You grieve for those who need no grief, yet speak as if wise. The truly wise mourn neither the living nor the dead.",
        "themes": ["wisdom", "self_knowledge", "equanimity"],
    },
    {
        "ref": "2.13", "chapter": 2, "verse": 13,
        "sanskrit": "देहिनोऽस्मिन्यथा देहे कौमारं यौवनं जरा।\nतथा देहान्तरप्राप्तिर्धीरस्तत्र न मुह्यति",
        "translit": "dehino ’smin yathā dehe kaumāraṁ yauvanaṁ jarā | tathā dehāntara-prāptir dhīras tatra na muhyati",
        "translation": "Just as the body passes from childhood to youth to age, so it passes on to another body. The steady are not shaken by this.",
        "themes": ["impermanence", "self_knowledge", "calm"],
    },
    {
        "ref": "2.14", "chapter": 2, "verse": 14,
        "sanskrit": "मात्रास्पर्शास्तु कौन्तेय शीतोष्णसुखदुःखदाः।\nआगमापायिनोऽनित्यास्तांस्तितिक्षस्व भारत",
        "translit": "mātrā-sparśhās tu kaunteya śhītoṣhṇa-sukha-duḥkha-dāḥ | āgamāpāyino ’nityās tans-titikṣhasva bhārata",
        "translation": "Cold and heat, pleasure and pain arrive through the senses — they come and go and never last. Meet them with patience.",
        "themes": ["endurance", "impermanence", "perseverance"],
    },
    {
        "ref": "2.20", "chapter": 2, "verse": 20,
        "sanskrit": "न जायते म्रियते वा कदाचि\nन्नायं भूत्वा भविता वा न भूयः।\nअजो नित्यः शाश्वतोऽयं पुराणो\nन हन्यते हन्यमाने शरीरे",
        "translit": "na jāyate mriyate vā kadāchin | nāyaṁ bhūtvā bhavitā vā na bhūyaḥ | ajo nityaḥ śhāśhvato ’yaṁ purāṇo | na hanyate hanyamāne śharīre",
        "translation": "The self is never born and never dies. Unborn, eternal, ancient — it is not destroyed when the body is destroyed.",
        "themes": ["self_knowledge", "fearlessness", "impermanence"],
    },
    {
        "ref": "2.22", "chapter": 2, "verse": 22,
        "sanskrit": "वासांसि जीर्णानि यथा विहाय\nनवानि गृह्णाति नरोऽपराणि।\nतथा शरीराणि विहाय जीर्णा\nन्यन्यानि संयाति नवानि देही",
        "translit": "vāsānsi jīrṇāni yathā vihāya | navāni gṛihṇāti naro ’parāṇi | tathā śharīrāṇi vihāya jīrṇānya | nyāni sanyāti navāni dehī",
        "translation": "As a person sheds worn-out clothes for new ones, the self lets go of worn-out bodies and takes on new.",
        "themes": ["impermanence", "self_knowledge"],
    },
    {
        "ref": "2.23", "chapter": 2, "verse": 23,
        "sanskrit": "नैनं छिन्दन्ति शस्त्राणि नैनं दहति पावकः।\nन चैनं क्लेदयन्त्यापो न शोषयति मारुतः",
        "translit": "nainaṁ chhindanti śhastrāṇi nainaṁ dahati pāvakaḥ | na chainaṁ kledayantyāpo na śhoṣhayati mārutaḥ",
        "translation": "Weapons cannot cut it, fire cannot burn it, water cannot wet it, wind cannot dry it.",
        "themes": ["fearlessness", "self_knowledge", "endurance"],
    },
    {
        "ref": "2.27", "chapter": 2, "verse": 27,
        "sanskrit": "जातस्य हि ध्रुवो मृत्युर्ध्रुवं जन्म मृतस्य च।\nतस्मादपरिहार्येऽर्थे न त्वं शोचितुमर्हसि",
        "translit": "jātasya hi dhruvo mṛityur dhruvaṁ janma mṛitasya cha | tasmād aparihārye ’rthe na tvaṁ śhochitum arhasi",
        "translation": "For whatever is born, death is certain; for whatever dies, birth is certain. Don't grieve over what cannot be avoided.",
        "themes": ["impermanence", "calm", "equanimity"],
    },
    {
        "ref": "2.38", "chapter": 2, "verse": 38,
        "sanskrit": "सुखदुःखे समे कृत्वा लाभालाभौ जयाजयौ।\nततो युद्धाय युज्यस्व नैवं पापमवाप्स्यसि",
        "translit": "sukha-duḥkhe same kṛitvā lābhālābhau jayājayau | tato yuddhāya yujyasva naivaṁ pāpam avāpsyasi",
        "translation": "Hold pleasure and pain, gain and loss, victory and defeat as equal — then step into your work, and no harm clings to you.",
        "themes": ["equanimity", "action", "courage"],
    },
    {
        "ref": "2.40", "chapter": 2, "verse": 40,
        "sanskrit": "नेहाभिक्रमनाशोऽस्ति प्रत्यवायो न विद्यते।\nस्वल्पमप्यस्य धर्मस्य त्रायते महतो भयात्",
        "translit": "nehābhikrama-nāśho ’sti pratyavāyo na vidyate | svalpam apyasya dharmasya trāyate mahato bhayāt",
        "translation": "On this path no effort is ever wasted and nothing is lost; even a little of it carries you past great fear.",
        "themes": ["perseverance", "practice", "hope"],
    },
    {
        "ref": "2.47", "chapter": 2, "verse": 47,
        "sanskrit": "कर्मण्येवाधिकारस्ते मा फलेषु कदाचन।\nमा कर्मफलहेतुर्भूर्मा ते सङ्गोऽस्त्वकर्मणि",
        "translit": "karmaṇy-evādhikāras te mā phaleṣhu kadāchana | mā karma-phala-hetur bhūr mā te saṅgo ’stvakarmaṇi",
        "translation": "You have a right to your actions, never to their fruits. Don't act for the results — but don't withdraw from action either.",
        "themes": ["action", "detachment", "duty"],
    },
    {
        "ref": "2.48", "chapter": 2, "verse": 48,
        "sanskrit": "योगस्थः कुरु कर्माणि सङ्गं त्यक्त्वा धनञ्जय।\nसिद्ध्यसिद्ध्योः समो भूत्वा समत्वं योग उच्यते",
        "translit": "yoga-sthaḥ kuru karmāṇi saṅgaṁ tyaktvā dhanañjaya | siddhy-asiddhyoḥ samo bhūtvā samatvaṁ yoga uchyate",
        "translation": "Do your work steadily, letting go of attachment, the same in success and failure. That evenness of mind is yoga.",
        "themes": ["equanimity", "action", "balance"],
    },
    {
        "ref": "2.50", "chapter": 2, "verse": 50,
        "sanskrit": "बुद्धियुक्तो जहातीह उभे सुकृतदुष्कृते।\nतस्माद्योगाय युज्यस्व योगः कर्मसु कौशलम्",
        "translit": "buddhi-yukto jahātīha ubhe sukṛita-duṣhkṛite | tasmād yogāya yujyasva yogaḥ karmasu kauśhalam",
        "translation": "A balanced mind sheds both good and bad outcomes here and now. So give yourself to that poise — yoga is skill in action.",
        "themes": ["skill", "action", "balance"],
    },
    {
        "ref": "2.56", "chapter": 2, "verse": 56,
        "sanskrit": "दुःखेष्वनुद्विग्नमनाः सुखेषु विगतस्पृहः।\nवीतरागभयक्रोधः स्थितधीर्मुनिरुच्यते",
        "translit": "duḥkheṣhv-anudvigna-manāḥ sukheṣhu vigata-spṛihaḥ | vīta-rāga-bhaya-krodhaḥ sthita-dhīr munir uchyate",
        "translation": "Unshaken in sorrow, not grasping in pleasure, free of attachment, fear, and anger — such a one is steady in wisdom.",
        "themes": ["equanimity", "calm", "mind"],
    },
    {
        "ref": "2.62", "chapter": 2, "verse": 62,
        "sanskrit": "ध्यायतो विषयान्पुंसः सङ्गस्तेषूपजायते।\nसङ्गात् संजायते कामः कामात्क्रोधोऽभिजायते",
        "translit": "dhyāyato viṣhayān puṁsaḥ saṅgas teṣhūpajāyate | saṅgāt sañjāyate kāmaḥ kāmāt krodho ’bhijāyate",
        "translation": "Dwelling on the objects of desire breeds attachment; from attachment grows wanting; from wanting, anger.",
        "themes": ["mind", "detachment"],
    },
    {
        "ref": "2.63", "chapter": 2, "verse": 63,
        "sanskrit": "क्रोधाद्भवति संमोहः संमोहात्स्मृतिविभ्रमः।\nस्मृतिभ्रंशाद् बुद्धिनाशो बुद्धिनाशात्प्रणश्यति",
        "translit": "krodhād bhavati sammohaḥ sammohāt smṛiti-vibhramaḥ | smṛiti-bhranśhād buddhi-nāśho buddhi-nāśhāt praṇaśhyati",
        "translation": "From anger comes confusion, from confusion a lost memory, from a lost memory a broken judgment — and then one is undone.",
        "themes": ["mind", "detachment"],
    },
    {
        "ref": "2.66", "chapter": 2, "verse": 66,
        "sanskrit": "नास्ति बुद्धिरयुक्तस्य न चायुक्तस्य भावना।\nन चाभावयतः शान्तिरशान्तस्य कुतः सुखम्",
        "translit": "nāsti buddhir-ayuktasya na chāyuktasya bhāvanā | na chābhāvayataḥ śhāntir aśhāntasya kutaḥ sukham",
        "translation": "Without a steady mind there is no clear thought; without clear thought, no peace; and without peace, where is happiness?",
        "themes": ["mind", "calm", "focus"],
    },
    {
        "ref": "2.70", "chapter": 2, "verse": 70,
        "sanskrit": "आपूर्यमाणमचलप्रतिष्ठं\nसमुद्रमापः प्रविशन्ति यद्वत्।\nतद्वत्कामा यं प्रविशन्ति सर्वे\nस शान्तिमाप्नोति न कामकामी",
        "translit": "āpūryamāṇam achala-pratiṣhṭhaṁ | samudram āpaḥ praviśhanti yadvat | tadvat kāmā yaṁ praviśhanti sarve | sa śhāntim āpnoti na kāma-kāmī",
        "translation": "As rivers pour into the ocean, yet it stays full and still — so desires enter the peaceful one, who finds calm, not the one who chases them.",
        "themes": ["calm", "contentment", "equanimity"],
    },
    {
        "ref": "2.71", "chapter": 2, "verse": 71,
        "sanskrit": "विहाय कामान्यः सर्वान्पुमांश्चरति निःस्पृहः।\nनिर्ममो निरहंकारः स शांतिमधिगच्छति",
        "translit": "vihāya kāmān yaḥ sarvān pumānśh charati niḥspṛihaḥ | nirmamo nirahankāraḥ sa śhāntim adhigachchhati",
        "translation": "The one who releases all craving and moves through life without grasping, without 'mine,' without ego — that one finds peace.",
        "themes": ["contentment", "detachment", "calm"],
    },
    {
        "ref": "3.8", "chapter": 3, "verse": 8,
        "sanskrit": "नियतं कुरु कर्म त्वं कर्म ज्यायो ह्यकर्मणः।\nशरीरयात्रापि च ते न प्रसिद्ध्येदकर्मणः",
        "translit": "niyataṁ kuru karma tvaṁ karma jyāyo hyakarmaṇaḥ | śharīra-yātrāpi cha te na prasiddhyed akarmaṇaḥ",
        "translation": "Do the work that is yours to do — action is better than inaction. Even keeping the body going asks for action.",
        "themes": ["duty", "action", "self_reliance"],
    },
    {
        "ref": "3.19", "chapter": 3, "verse": 19,
        "sanskrit": "तस्मादसक्तः सततं कार्यं कर्म समाचर।\nअसक्तो ह्याचरन्कर्म परमाप्नोति पूरुषः",
        "translit": "tasmād asaktaḥ satataṁ kāryaṁ karma samāchara | asakto hyācharan karma param āpnoti pūruṣhaḥ",
        "translation": "So do the work before you without attachment. Working free of attachment, a person reaches the highest.",
        "themes": ["action", "detachment", "duty"],
    },
    {
        "ref": "3.21", "chapter": 3, "verse": 21,
        "sanskrit": "यद्यदाचरति श्रेष्ठस्तत्तदेवेतरो जनः।\nस यत्प्रमाणं कुरुते लोकस्तदनुवर्तते",
        "translit": "yad yad ācharati śhreṣhṭhas tat tad evetaro janaḥ | sa yat pramāṇaṁ kurute lokas tad anuvartate",
        "translation": "Whatever a great person does, others follow; the standard they set, the world takes up.",
        "themes": ["leadership", "character"],
    },
    {
        "ref": "3.27", "chapter": 3, "verse": 27,
        "sanskrit": "प्रकृतेः क्रियमाणानि गुणैः कर्माणि सर्वशः।\nअहङ्कारविमूढात्मा कर्ताऽहमिति मन्यते",
        "translit": "prakṛiteḥ kriyamāṇāni guṇaiḥ karmāṇi sarvaśhaḥ | ahankāra-vimūḍhātmā kartāham iti manyate",
        "translation": "Actions are carried out by nature's own forces, yet the ego-fooled mind thinks, 'I am the doer.'",
        "themes": ["humility", "self_knowledge", "detachment"],
    },
    {
        "ref": "3.35", "chapter": 3, "verse": 35,
        "sanskrit": "श्रेयान्स्वधर्मो विगुणः परधर्मात्स्वनुष्ठितात्।\nस्वधर्मे निधनं श्रेयः परधर्मो भयावहः",
        "translit": "śhreyān swa-dharmo viguṇaḥ para-dharmāt sv-anuṣhṭhitāt | swa-dharme nidhanaṁ śhreyaḥ para-dharmo bhayāvahaḥ",
        "translation": "Better your own path, imperfectly walked, than someone else's walked well. It is safer to live by what is truly yours.",
        "themes": ["authenticity", "dharma", "purpose"],
    },
    {
        "ref": "3.37", "chapter": 3, "verse": 37,
        "sanskrit": "श्री भगवानुवाच\nकाम एष क्रोध एष रजोगुणसमुद्भवः।\nमहाशनो महापाप्मा विद्ध्येनमिह वैरिणम्",
        "translit": "śhrī bhagavān uvācha | kāma eṣha krodha eṣha rajo-guṇa-samudbhavaḥ | mahāśhano mahā-pāpmā viddhyenam iha vairiṇam",
        "translation": "It is desire, it is anger, born of our restless streak — all-devouring and destructive. Know this as the real enemy.",
        "themes": ["mind", "detachment"],
    },
    {
        "ref": "4.7", "chapter": 4, "verse": 7,
        "sanskrit": "यदा यदा हि धर्मस्य ग्लानिर्भवति भारत।\nअभ्युत्थानमधर्मस्य तदाऽऽत्मानं सृजाम्यहम्",
        "translit": "yadā yadā hi dharmasya glānir bhavati bhārata | abhyutthānam adharmasya tadātmānaṁ sṛijāmyaham",
        "translation": "Whenever what is right grows weak and what is wrong rises up, I come forth.",
        "themes": ["hope", "faith", "order"],
    },
    {
        "ref": "4.8", "chapter": 4, "verse": 8,
        "sanskrit": "परित्राणाय साधूनां विनाशाय च दुष्कृताम्।\nधर्मसंस्थापनार्थाय संभवामि युगे युगे",
        "translit": "paritrāṇāya sādhūnāṁ vināśhāya cha duṣhkṛitām | dharma-sansthāpanārthāya sambhavāmi yuge yuge",
        "translation": "To protect the good, to set right what has gone wrong, to restore what is true — I appear, age after age.",
        "themes": ["faith", "hope", "order"],
    },
    {
        "ref": "4.18", "chapter": 4, "verse": 18,
        "sanskrit": "कर्मण्यकर्म यः पश्येदकर्मणि च कर्म यः।\nस बुद्धिमान् मनुष्येषु स युक्तः कृत्स्नकर्मकृत्",
        "translit": "karmaṇyakarma yaḥ paśhyed akarmaṇi cha karma yaḥ | sa buddhimān manuṣhyeṣhu sa yuktaḥ kṛitsna-karma-kṛit",
        "translation": "The one who sees stillness within action and action within stillness is wise — whole in everything they do.",
        "themes": ["wisdom", "self_knowledge", "skill"],
    },
    {
        "ref": "4.38", "chapter": 4, "verse": 38,
        "sanskrit": "न हि ज्ञानेन सदृशं पवित्रमिह विद्यते।\nतत्स्वयं योगसंसिद्धः कालेनात्मनि विन्दति",
        "translit": "na hi jñānena sadṛiśhaṁ pavitramiha vidyate | tatsvayaṁ yogasansiddhaḥ kālenātmani vindati",
        "translation": "Nothing in this world purifies like true knowledge. In time, the one who is ready finds it within.",
        "themes": ["wisdom", "self_knowledge", "practice"],
    },
    {
        "ref": "4.39", "chapter": 4, "verse": 39,
        "sanskrit": "श्रद्धावाँल्लभते ज्ञानं तत्परः संयतेन्द्रियः।\nज्ञानं लब्ध्वा परां शान्तिमचिरेणाधिगच्छति",
        "translit": "śhraddhāvān labhate jñānaṁ tat-paraḥ sanyatendriyaḥ | jñānaṁ labdhvā parāṁ śhāntim achireṇādhigachchhati",
        "translation": "The one with faith — intent and attentive — gains wisdom, and with wisdom comes deep and swift peace.",
        "themes": ["faith", "practice", "calm"],
    },
    {
        "ref": "4.42", "chapter": 4, "verse": 42,
        "sanskrit": "तस्मादज्ञानसंभूतं हृत्स्थं ज्ञानासिनाऽऽत्मनः।\nछित्त्वैनं संशयं योगमातिष्ठोत्तिष्ठ भारत",
        "translit": "tasmād ajñāna-sambhūtaṁ hṛit-sthaṁ jñānāsinātmanaḥ | chhittvainaṁ sanśhayaṁ yogam ātiṣhṭhottiṣhṭha bhārata",
        "translation": "So cut down this doubt in your heart, born of not-knowing, with the blade of knowledge. Steady yourself and rise.",
        "themes": ["courage", "confidence", "action"],
    },
    {
        "ref": "5.10", "chapter": 5, "verse": 10,
        "sanskrit": "ब्रह्मण्याधाय कर्माणि सङ्गं त्यक्त्वा करोति यः।\nलिप्यते न स पापेन पद्मपत्रमिवाम्भसा",
        "translit": "brahmaṇyādhāya karmāṇi saṅgaṁ tyaktvā karoti yaḥ | lipyate na sa pāpena padma-patram ivāmbhasā",
        "translation": "Offer your actions to the greater whole and let go of attachment, and no stain touches you — like a lotus leaf untouched by water.",
        "themes": ["detachment", "action", "calm"],
    },
    {
        "ref": "5.18", "chapter": 5, "verse": 18,
        "sanskrit": "विद्याविनयसंपन्ने ब्राह्मणे गवि हस्तिनि।\nशुनि चैव श्वपाके च पण्डिताः समदर्शिनः",
        "translit": "vidyā-vinaya-sampanne brāhmaṇe gavi hastini | śhuni chaiva śhva-pāke cha paṇḍitāḥ sama-darśhinaḥ",
        "translation": "The wise see with equal eyes — the learned, the humble, the animal, the outcast — the same light in all.",
        "themes": ["character", "equanimity", "humility"],
    },
    {
        "ref": "5.22", "chapter": 5, "verse": 22,
        "sanskrit": "ये हि संस्पर्शजा भोगा दुःखयोनय एव ते।\nआद्यन्तवन्तः कौन्तेय न तेषु रमते बुधः",
        "translit": "ye hi sansparśha-jā bhogā duḥkha-yonaya eva te | ādyantavantaḥ kaunteya na teṣhu ramate budhaḥ",
        "translation": "Pleasures born of the senses are themselves wombs of pain; they begin and they end. The wise don't lose themselves in them.",
        "themes": ["detachment", "impermanence", "contentment"],
    },
    {
        "ref": "5.29", "chapter": 5, "verse": 29,
        "sanskrit": "भोक्तारं यज्ञतपसां सर्वलोकमहेश्वरम्।\nसुहृदं सर्वभूतानां ज्ञात्वा मां शान्तिमृच्छति",
        "translit": "bhoktāraṁ yajña-tapasāṁ sarva-loka-maheśhvaram | suhṛidaṁ sarva-bhūtānāṁ jñātvā māṁ śhāntim ṛichchhati",
        "translation": "Knowing the divine as the friend of all beings and the ground of every effort, a person comes to rest in peace.",
        "themes": ["calm", "faith", "devotion"],
    },
    {
        "ref": "6.5", "chapter": 6, "verse": 5,
        "sanskrit": "उद्धरेदात्मनाऽऽत्मानं नात्मानमवसादयेत्।\nआत्मैव ह्यात्मनो बन्धुरात्मैव रिपुरात्मनः",
        "translit": "uddhared ātmanātmānaṁ nātmānam avasādayet | ātmaiva hyātmano bandhur ātmaiva ripur ātmanaḥ",
        "translation": "Lift yourself by yourself; don't drag yourself down. You are your own best friend — and your own worst enemy.",
        "themes": ["self_reliance", "confidence", "mind"],
    },
    {
        "ref": "6.6", "chapter": 6, "verse": 6,
        "sanskrit": "बन्धुरात्माऽऽत्मनस्तस्य येनात्मैवात्मना जितः।\nअनात्मनस्तु शत्रुत्वे वर्तेतात्मैव शत्रुवत्",
        "translit": "bandhur ātmātmanas tasya yenātmaivātmanā jitaḥ | anātmanas tu śhatrutve vartetātmaiva śhatru-vat",
        "translation": "For the one who has mastered the mind, the mind is a friend; for the one who hasn't, it behaves like an enemy.",
        "themes": ["mind", "self_reliance", "practice"],
    },
    {
        "ref": "6.16", "chapter": 6, "verse": 16,
        "sanskrit": "नात्यश्नतस्तु योगोऽस्ति न चैकान्तमनश्नतः।\nन चातिस्वप्नशीलस्य जाग्रतो नैव चार्जुन",
        "translit": "nātyaśhnatastu yogo ’sti na chaikāntam anaśhnataḥ | na chāti-svapna-śhīlasya jāgrato naiva chārjuna",
        "translation": "This path is not for those who eat too much or too little, nor for those who sleep too much or too little.",
        "themes": ["balance", "wellbeing", "practice"],
    },
    {
        "ref": "6.17", "chapter": 6, "verse": 17,
        "sanskrit": "युक्ताहारविहारस्य युक्तचेष्टस्य कर्मसु।\nयुक्तस्वप्नावबोधस्य योगो भवति दुःखहा",
        "translit": "yuktāhāra-vihārasya yukta-cheṣhṭasya karmasu | yukta-svapnāvabodhasya yogo bhavati duḥkha-hā",
        "translation": "For the one balanced in food, rest, work, and sleep, practice itself becomes the end of sorrow.",
        "themes": ["balance", "wellbeing", "practice"],
    },
    {
        "ref": "6.19", "chapter": 6, "verse": 19,
        "sanskrit": "यथा दीपो निवातस्थो नेङ्गते सोपमा स्मृता।\nयोगिनो यतचित्तस्य युञ्जतो योगमात्मनः",
        "translit": "yathā dīpo nivāta-stho neṅgate sopamā smṛitā | yogino yata-chittasya yuñjato yogam ātmanaḥ",
        "translation": "Like a lamp in a windless place that does not flicker — so is the disciplined mind of one absorbed in practice.",
        "themes": ["focus", "meditation", "mind"],
    },
    {
        "ref": "6.26", "chapter": 6, "verse": 26,
        "sanskrit": "यतो यतो निश्चरति मनश्चञ्चलमस्थिरम्।\nततस्ततो नियम्यैतदात्मन्येव वशं नयेत्",
        "translit": "yato yato niśhcharati manaśh chañchalam asthiram | tatas tato niyamyaitad ātmanyeva vaśhaṁ nayet",
        "translation": "Wherever the restless, unsteady mind wanders off, bring it gently back, again and again, into your own keeping.",
        "themes": ["focus", "practice", "mind"],
    },
    {
        "ref": "6.35", "chapter": 6, "verse": 35,
        "sanskrit": "श्री भगवानुवाच\nअसंशयं महाबाहो मनो दुर्निग्रहं चलं।\nअभ्यासेन तु कौन्तेय वैराग्येण च गृह्यते",
        "translit": "śhrī bhagavān uvācha | asanśhayaṁ mahā-bāho mano durnigrahaṁ chalam | abhyāsena tu kaunteya vairāgyeṇa cha gṛihyate",
        "translation": "Yes — the mind is restless and hard to hold. But through steady practice and a lighter grip on things, it is mastered.",
        "themes": ["perseverance", "practice", "mind"],
    },
    {
        "ref": "7.7", "chapter": 7, "verse": 7,
        "sanskrit": "मत्तः परतरं नान्यत्किञ्चिदस्ति धनञ्जय।\nमयि सर्वमिदं प्रोतं सूत्रे मणिगणा इव",
        "translit": "mattaḥ parataraṁ nānyat kiñchid asti dhanañjaya | mayi sarvam idaṁ protaṁ sūtre maṇi-gaṇā iva",
        "translation": "There is nothing higher than this one ground of all. Everything is strung upon it, like beads on a single thread.",
        "themes": ["faith", "wisdom", "self_knowledge"],
    },
    {
        "ref": "7.19", "chapter": 7, "verse": 19,
        "sanskrit": "बहूनां जन्मनामन्ते ज्ञानवान्मां प्रपद्यते।\nवासुदेवः सर्वमिति स महात्मा सुदुर्लभः",
        "translit": "bahūnāṁ janmanām ante jñānavān māṁ prapadyate | vāsudevaḥ sarvam iti sa mahātmā su-durlabhaḥ",
        "translation": "After many turnings, the one who truly knows comes home, seeing the divine in all. Such a soul is rare.",
        "themes": ["wisdom", "devotion", "self_knowledge"],
    },
    {
        "ref": "8.7", "chapter": 8, "verse": 7,
        "sanskrit": "तस्मात्सर्वेषु कालेषु मामनुस्मर युध्य च।\nमय्यर्पितमनोबुद्धिर्मामेवैष्यस्यसंशयम्",
        "translit": "tasmāt sarveṣhu kāleṣhu mām anusmara yudhya cha | mayyarpita-mano-buddhir mām evaiṣhyasyasanśhayam",
        "translation": "So keep the higher in mind at all times, and do your work. With heart and mind steady, you will arrive without doubt.",
        "themes": ["focus", "devotion", "action"],
    },
    {
        "ref": "9.22", "chapter": 9, "verse": 22,
        "sanskrit": "अनन्याश्चिन्तयन्तो मां ये जनाः पर्युपासते।\nतेषां नित्याभियुक्तानां योगक्षेमं वहाम्यहम्",
        "translit": "ananyāśh chintayanto māṁ ye janāḥ paryupāsate | teṣhāṁ nityābhiyuktānāṁ yoga-kṣhemaṁ vahāmyaham",
        "translation": "To those who are steadily devoted, I carry what they lack and protect what they already hold.",
        "themes": ["support", "surrender", "devotion"],
    },
    {
        "ref": "9.26", "chapter": 9, "verse": 26,
        "sanskrit": "पत्रं पुष्पं फलं तोयं यो मे भक्त्या प्रयच्छति।\nतदहं भक्त्युपहृतमश्नामि प्रयतात्मनः",
        "translit": "patraṁ puṣhpaṁ phalaṁ toyaṁ yo me bhaktyā prayachchhati | tadahaṁ bhaktyupahṛitam aśhnāmi prayatātmanaḥ",
        "translation": "A leaf, a flower, a fruit, a little water — whatever is offered with love, I receive from the sincere heart.",
        "themes": ["devotion", "humility"],
    },
    {
        "ref": "9.27", "chapter": 9, "verse": 27,
        "sanskrit": "यत्करोषि यदश्नासि यज्जुहोषि ददासि यत्।\nयत्तपस्यसि कौन्तेय तत्कुरुष्व मदर्पणम्",
        "translit": "yat karoṣhi yad aśhnāsi yaj juhoṣhi dadāsi yat | yat tapasyasi kaunteya tat kuruṣhva mad-arpaṇam",
        "translation": "Whatever you do, whatever you eat, whatever you give or practice — offer it. Let the act itself become an offering.",
        "themes": ["devotion", "action", "duty"],
    },
    {
        "ref": "9.34", "chapter": 9, "verse": 34,
        "sanskrit": "मन्मना भव मद्भक्तो मद्याजी मां नमस्कुरु।\nमामेवैष्यसि युक्त्वैवमात्मानं मत्परायणः",
        "translit": "man-manā bhava mad-bhakto mad-yājī māṁ namaskuru | mām evaiṣhyasi yuktvaivam ātmānaṁ mat-parāyaṇaḥ",
        "translation": "Fix your mind on the divine, give your heart, and you will arrive.",
        "themes": ["devotion", "focus"],
    },
    {
        "ref": "10.10", "chapter": 10, "verse": 10,
        "sanskrit": "तेषां सततयुक्तानां भजतां प्रीतिपूर्वकम्।\nददामि बुद्धियोगं तं येन मामुपयान्ति ते",
        "translit": "teṣhāṁ satata-yuktānāṁ bhajatāṁ prīti-pūrvakam | dadāmi buddhi-yogaṁ taṁ yena mām upayānti te",
        "translation": "To those steadfast and loving, I give the clear understanding by which they find their way to Me.",
        "themes": ["devotion", "wisdom", "practice"],
    },
    {
        "ref": "10.20", "chapter": 10, "verse": 20,
        "sanskrit": "अहमात्मा गुडाकेश सर्वभूताशयस्थितः।\nअहमादिश्च मध्यं च भूतानामन्त एव च",
        "translit": "aham ātmā guḍākeśha sarva-bhūtāśhaya-sthitaḥ | aham ādiśh cha madhyaṁ cha bhūtānām anta eva cha",
        "translation": "I am the self seated in the heart of all beings — the beginning, the middle, and the end of all that is.",
        "themes": ["self_knowledge", "faith"],
    },
    {
        "ref": "11.33", "chapter": 11, "verse": 33,
        "sanskrit": "तस्मात्त्वमुत्तिष्ठ यशो लभस्व\nजित्वा शत्रून् भुङ्क्ष्व राज्यं समृद्धम्।\nमयैवैते निहताः पूर्वमेव\nनिमित्तमात्रं भव सव्यसाचिन्",
        "translit": "tasmāt tvam uttiṣhṭha yaśho labhasva | jitvā śhatrūn bhuṅkṣhva rājyaṁ samṛiddham | mayaivaite nihatāḥ pūrvam eva | nimitta-mātraṁ bhava savya-sāchin",
        "translation": "So rise and win your honor; the outcome is already set. Be the instrument — act your part with a free hand.",
        "themes": ["courage", "confidence", "victory"],
    },
    {
        "ref": "11.45", "chapter": 11, "verse": 45,
        "sanskrit": "अदृष्टपूर्वं हृषितोऽस्मि दृष्ट्वा\nभयेन च प्रव्यथितं मनो मे।\nतदेव मे दर्शय देव रूपं\nप्रसीद देवेश जगन्निवास",
        "translit": "adṛiṣhṭa-pūrvaṁ hṛiṣhito ’smi dṛiṣhṭvā | bhayena cha pravyathitaṁ mano me | tad eva me darśhaya deva rūpaṁ | prasīda deveśha jagan-nivāsa",
        "translation": "I am thrilled to see what was never seen before — yet my mind trembles. Show me the familiar form; be gracious.",
        "themes": ["awe", "humility", "devotion"],
    },
    {
        "ref": "12.13", "chapter": 12, "verse": 13,
        "sanskrit": "अद्वेष्टा सर्वभूतानां मैत्रः करुण एव च।निर्ममो निरहङ्कारः समदुःखसुखः क्षमी",
        "translit": "adveṣhṭā sarva-bhūtānāṁ maitraḥ karuṇa eva cha | nirmamo nirahankāraḥ sama-duḥkha-sukhaḥ kṣhamī",
        "translation": "Free of ill-will toward any being, warm and kind, without 'mine' or ego, even-keeled in pain and pleasure, patient —",
        "themes": ["character", "equanimity", "humility"],
    },
    {
        "ref": "12.14", "chapter": 12, "verse": 14,
        "sanskrit": "सन्तुष्टः सततं योगी यतात्मा दृढनिश्चयः।मय्यर्पितमनोबुद्धिर्यो मद्भक्तः स मे प्रियः",
        "translit": "santuṣhṭaḥ satataṁ yogī yatātmā dṛiḍha-niśhchayaḥ | mayy arpita-mano-buddhir yo mad-bhaktaḥ sa me priyaḥ",
        "translation": "— ever content, steady in practice, self-possessed, firm in resolve, heart and mind given over: such a one is dear to Me.",
        "themes": ["contentment", "practice", "devotion"],
    },
    {
        "ref": "12.15", "chapter": 12, "verse": 15,
        "sanskrit": "यस्मान्नोद्विजते लोको लोकान्नोद्विजते च यः।हर्षामर्षभयोद्वेगैर्मुक्तो यः स च मे प्रियः",
        "translit": "yasmān nodvijate loko lokān nodvijate cha yaḥ | harṣhāmarṣha-bhayodvegair mukto yaḥ sa cha me priyaḥ",
        "translation": "The one who neither troubles the world nor is troubled by it — free of elation, envy, fear, and anxiety — is dear to Me.",
        "themes": ["equanimity", "character", "calm"],
    },
    {
        "ref": "12.16", "chapter": 12, "verse": 16,
        "sanskrit": "अनपेक्षः शुचिर्दक्ष उदासीनो गतव्यथः।सर्वारम्भपरित्यागी यो मद्भक्तः स मे प्रियः",
        "translit": "anapekṣhaḥ śhuchir dakṣha udāsīno gata-vyathaḥ | sarvārambha-parityāgī yo mad-bhaktaḥ sa me priyaḥ",
        "translation": "Wanting nothing, clean, capable, unruffled, untroubled, not clinging to what they begin — such a one is dear to Me.",
        "themes": ["skill", "calm", "detachment"],
    },
    {
        "ref": "12.20", "chapter": 12, "verse": 20,
        "sanskrit": "ये तु धर्म्यामृतमिदं यथोक्तं पर्युपासते।श्रद्दधाना मत्परमा भक्तास्तेऽतीव मे प्रियाः",
        "translit": "ye tu dharmyāmṛitam idaṁ yathoktaṁ paryupāsate | śhraddadhānā mat-paramā bhaktās te ’tīva me priyāḥ",
        "translation": "Those who hold this path of wisdom with faith, making it their highest aim — these devoted ones are very dear to Me.",
        "themes": ["faith", "devotion", "purpose"],
    },
    {
        "ref": "13.8", "chapter": 13, "verse": 8,
        "sanskrit": "अमानित्वमदम्भित्वमहिंसा क्षान्तिरार्जवम्।आचार्योपासनं शौचं स्थैर्यमात्मविनिग्रहः",
        "translit": "amānitvam adambhitvam ahinsā kṣhāntir ārjavam | āchāryopāsanaṁ śhauchaṁ sthairyam ātma-vinigrahaḥ",
        "translation": "Humility, honesty, non-harming, patience, uprightness, respect for one's teacher, cleanliness, steadiness, self-command —",
        "themes": ["character", "humility", "self_reliance"],
    },
    {
        "ref": "13.28", "chapter": 13, "verse": 28,
        "sanskrit": "समं सर्वेषु भूतेषु तिष्ठन्तं परमेश्वरम्।विनश्यत्स्वविनश्यन्तं यः पश्यति स पश्यति",
        "translit": "samaṁ sarveṣhu bhūteṣhu tiṣhṭhantaṁ parameśhvaram | vinaśhyatsv avinaśhyantaṁ yaḥ paśhyati sa paśhyati",
        "translation": "The one who sees the same undying presence within all perishable things — that one truly sees.",
        "themes": ["wisdom", "self_knowledge", "equanimity"],
    },
    {
        "ref": "14.24", "chapter": 14, "verse": 24,
        "sanskrit": "समदुःखसुखः स्वस्थः समलोष्टाश्मकाञ्चनः।तुल्यप्रियाप्रियो धीरस्तुल्यनिन्दात्मसंस्तुतिः",
        "translit": "sama-duḥkha-sukhaḥ sva-sthaḥ sama-loṣhṭāśhma-kāñchanaḥ | tulya-priyāpriyo dhīras tulya-nindātma-sanstutiḥ",
        "translation": "The same in pleasure and pain, at home in the self, holding a clod, a stone, and gold alike, steady in praise and blame —",
        "themes": ["equanimity", "calm", "detachment"],
    },
    {
        "ref": "15.5", "chapter": 15, "verse": 5,
        "sanskrit": "निर्मानमोहा जितसङ्गदोषा अध्यात्मनित्या विनिवृत्तकामाः।द्वन्द्वैर्विमुक्ताः सुखदुःखसंज्ञै र्गच्छन्त्यमूढाः पदमव्ययं तत्",
        "translit": "nirmāna-mohā jita-saṅga-doṣhā | adhyātma-nityā vinivṛitta-kāmāḥ | dvandvair vimuktāḥ sukha-duḥkha-sanjñair | gachchhanty amūḍhāḥ padam avyayaṁ tat",
        "translation": "Free of pride and delusion, beyond clinging, desires stilled, released from the pull of pleasure and pain — the clear-eyed reach the lasting.",
        "themes": ["detachment", "self_knowledge", "wisdom"],
    },
    {
        "ref": "15.7", "chapter": 15, "verse": 7,
        "sanskrit": "ममैवांशो जीवलोके जीवभूतः सनातनः।मनःषष्ठानीन्द्रियाणि प्रकृतिस्थानि कर्षति",
        "translit": "mamaivānśho jīva-loke jīva-bhūtaḥ sanātanaḥ | manaḥ-ṣhaṣhṭhānīndriyāṇi prakṛiti-sthāni karṣhati",
        "translation": "A spark of the eternal lives in every being — it is that which moves through the mind and the senses in this world.",
        "themes": ["self_knowledge", "faith"],
    },
    {
        "ref": "16.1", "chapter": 16, "verse": 1,
        "sanskrit": "श्री भगवानुवाच\nअभयं सत्त्वसंशुद्धिः ज्ञानयोगव्यवस्थितिः।\nदानं दमश्च यज्ञश्च स्वाध्यायस्तप आर्जवम्",
        "translit": "śhrī-bhagavān uvācha | abhayaṁ sattva-sanśhuddhir jñāna-yoga-vyavasthitiḥ | dānaṁ damaśh cha yajñaśh cha svādhyāyas tapa ārjavam",
        "translation": "Fearlessness, a clear heart, steadiness in wisdom, generosity, self-command, sincerity, study, and uprightness —",
        "themes": ["fearlessness", "character", "courage"],
    },
    {
        "ref": "16.2", "chapter": 16, "verse": 2,
        "sanskrit": "अहिंसा सत्यमक्रोधस्त्यागः शान्तिरपैशुनम्।दया भूतेष्वलोलुप्त्वं मार्दवं ह्रीरचापलम्",
        "translit": "ahinsā satyam akrodhas tyāgaḥ śhāntir apaiśhunam | dayā bhūteṣhv aloluptvaṁ mārdavaṁ hrīr achāpalam",
        "translation": "Non-harming, truth, freedom from anger, letting go, peace, no fault-finding, compassion, gentleness, modesty, steadiness —",
        "themes": ["character", "calm", "humility"],
    },
    {
        "ref": "16.3", "chapter": 16, "verse": 3,
        "sanskrit": "तेजः क्षमा धृतिः शौचमद्रोहो नातिमानिता।\nभवन्ति सम्पदं दैवीमभिजातस्य भारत",
        "translit": "tejaḥ kṣhamā dhṛitiḥ śhaucham adroho nāti-mānitā | bhavanti sampadaṁ daivīm abhijātasya bhārata",
        "translation": "Vigor, forgiveness, fortitude, cleanliness, bearing no ill-will, no vanity — these belong to the one born for the higher nature.",
        "themes": ["character", "courage", "humility"],
    },
    {
        "ref": "16.21", "chapter": 16, "verse": 21,
        "sanskrit": "त्रिविधं नरकस्येदं द्वारं नाशनमात्मनः।कामः क्रोधस्तथा लोभस्तस्मादेतत्त्रयं त्यजेत्",
        "translit": "tri-vidhaṁ narakasyedaṁ dvāraṁ nāśhanam ātmanaḥ | kāmaḥ krodhas tathā lobhas tasmād etat trayaṁ tyajet",
        "translation": "Three gates open onto ruin for the self — wanting, anger, and greed. Let go of all three.",
        "themes": ["mind", "detachment"],
    },
    {
        "ref": "17.3", "chapter": 17, "verse": 3,
        "sanskrit": "सत्त्वानुरूपा सर्वस्य श्रद्धा भवति भारत।श्रद्धामयोऽयं पुरुषो यो यच्छ्रद्धः स एव सः",
        "translit": "sattvānurūpā sarvasya śhraddhā bhavati bhārata | śhraddhā-mayo ‘yaṁ puruṣho yo yach-chhraddhaḥ sa eva saḥ",
        "translation": "Each person's faith follows their own nature. A person is made of their faith — as the faith, so is the person.",
        "themes": ["faith", "character", "self_knowledge"],
    },
    {
        "ref": "17.15", "chapter": 17, "verse": 15,
        "sanskrit": "अनुद्वेगकरं वाक्यं सत्यं प्रियहितं च यत्।स्वाध्यायाभ्यसनं चैव वाङ्मयं तप उच्यते",
        "translit": "anudvega-karaṁ vākyaṁ satyaṁ priya-hitaṁ cha yat | svādhyāyābhyasanaṁ chaiva vāṅ-mayaṁ tapa uchyate",
        "translation": "Words that don't wound — true, kind, and helpful — and the steady study of what uplifts: this is the discipline of speech.",
        "themes": ["character", "practice", "calm"],
    },
    {
        "ref": "17.16", "chapter": 17, "verse": 16,
        "sanskrit": "मनःप्रसादः सौम्यत्वं मौनमात्मविनिग्रहः।भावसंशुद्धिरित्येतत्तपो मानसमुच्यते",
        "translit": "manaḥ-prasādaḥ saumyatvaṁ maunam ātma-vinigrahaḥ | bhāva-sanśhuddhir ity etat tapo mānasam uchyate",
        "translation": "Serenity of mind, gentleness, quiet, self-command, an honest heart — this is the discipline of the mind.",
        "themes": ["mind", "calm", "practice"],
    },
    {
        "ref": "17.20", "chapter": 17, "verse": 20,
        "sanskrit": "दातव्यमिति यद्दानं दीयतेऽनुपकारिणे।देशे काले च पात्रे च तद्दानं सात्त्विकं स्मृतम्",
        "translit": "dātavyam iti yad dānaṁ dīyate ‘nupakāriṇe | deśhe kāle cha pātre cha tad dānaṁ sāttvikaṁ smṛitam",
        "translation": "A gift given because it is right, with nothing expected back, to the right person at the right time and place — that is giving at its purest.",
        "themes": ["character", "duty"],
    },
    {
        "ref": "18.23", "chapter": 18, "verse": 23,
        "sanskrit": "नियतं सङ्गरहितमरागद्वेषतः कृतम्।अफलप्रेप्सुना कर्म यत्तत्सात्त्विकमुच्यते",
        "translit": "niyataṁ saṅga-rahitam arāga-dveṣhataḥ kṛitam | aphala-prepsunā karma yat tat sāttvikam uchyate",
        "translation": "Work done as it should be, free of attachment, without craving or aversion, with no hunger for reward — that is the clearest kind of action.",
        "themes": ["action", "detachment", "duty"],
    },
    {
        "ref": "18.47", "chapter": 18, "verse": 47,
        "sanskrit": "श्रेयान्स्वधर्मो विगुणः परधर्मात्स्वनुष्ठितात्।स्वभावनियतं कर्म कुर्वन्नाप्नोति किल्बिषम्",
        "translit": "śhreyān swa-dharmo viguṇaḥ para-dharmāt sv-anuṣhṭhitāt | svabhāva-niyataṁ karma kurvan nāpnoti kilbiṣham",
        "translation": "Better your own work, imperfectly done, than another's done well. Doing the work your nature calls for, you take on no harm.",
        "themes": ["authenticity", "dharma", "purpose"],
    },
    {
        "ref": "18.48", "chapter": 18, "verse": 48,
        "sanskrit": "सहजं कर्म कौन्तेय सदोषमपि न त्यजेत्।सर्वारम्भा हि दोषेण धूमेनाग्निरिवावृताः",
        "translit": "saha-jaṁ karma kaunteya sa-doṣham api na tyajet | sarvārambhā hi doṣheṇa dhūmenāgnir ivāvṛitāḥ",
        "translation": "Don't abandon the work you were born to, even if it is flawed — every undertaking carries some flaw, as fire carries smoke.",
        "themes": ["perseverance", "duty", "authenticity"],
    },
    {
        "ref": "18.58", "chapter": 18, "verse": 58,
        "sanskrit": "मच्चित्तः सर्वदुर्गाणि मत्प्रसादात्तरिष्यसि।अथ चेत्त्वमहङ्कारान्न श्रोष्यसि विनङ्क्ष्यसि",
        "translit": "mach-chittaḥ sarva-durgāṇi mat-prasādāt tariṣhyasi | atha chet tvam ahankārān na śhroṣhyasi vinaṅkṣhyasi",
        "translation": "With your mind set on the greater whole, you'll cross every obstacle by grace. But if ego makes you deaf to this, you'll lose your way.",
        "themes": ["confidence", "faith", "surrender"],
    },
    {
        "ref": "18.63", "chapter": 18, "verse": 63,
        "sanskrit": "इति ते ज्ञानमाख्यातं गुह्याद्गुह्यतरं मया।विमृश्यैतदशेषेण यथेच्छसि तथा कुरु",
        "translit": "iti te jñānam ākhyātaṁ guhyād guhyataraṁ mayā | vimṛiśhyaitad aśheṣheṇa yathechchhasi tathā kuru",
        "translation": "The knowledge has been laid open to you, deeper than any secret. Weigh it fully — then do as you choose.",
        "themes": ["wisdom", "confidence", "self_reliance"],
    },
    {
        "ref": "18.66", "chapter": 18, "verse": 66,
        "sanskrit": "सर्वधर्मान्परित्यज्य मामेकं शरणं व्रज।अहं त्वा सर्वपापेभ्यो मोक्षयिष्यामि मा शुचः",
        "translit": "sarva-dharmān parityajya mām ekaṁ śharaṇaṁ vraja | ahaṁ tvāṁ sarva-pāpebhyo mokṣhayiṣhyāmi mā śhuchaḥ",
        "translation": "Let go of all else and take refuge in the divine alone. You will be freed from all that binds — do not grieve.",
        "themes": ["surrender", "faith", "devotion"],
    },
    {
        "ref": "18.78", "chapter": 18, "verse": 78,
        "sanskrit": "यत्र योगेश्वरः कृष्णो यत्र पार्थो धनुर्धरः।\nतत्र श्रीर्विजयो भूतिर्ध्रुवा नीतिर्मतिर्मम",
        "translit": "yatra yogeśhvaraḥ kṛiṣhṇo yatra pārtho dhanur-dharaḥ | tatra śhrīr vijayo bhūtir dhruvā nītir matir mama",
        "translation": "Where wisdom and willing effort stand together, there follow fortune, victory, and steady right conduct.",
        "themes": ["victory", "confidence", "leadership"],
    },
]


# ── Season → themes ──────────────────────────────────────────────────────────
EXPANSIVE = {"Jupiter", "Rahu", "Venus", "Sun", "Moon"}
CONTRACTING = {"Saturn", "Ketu", "Mars"}

SEASON_THEMES = {
    "consolidating": ["perseverance", "endurance", "equanimity", "detachment",
                      "duty", "self_reliance", "practice", "calm", "impermanence",
                      "contentment", "humility", "faith", "surrender", "wellbeing"],
    "expansive":     ["purpose", "action", "courage", "confidence", "leadership",
                      "dharma", "devotion", "victory", "hope", "character",
                      "fearlessness", "authenticity", "order"],
    "steady":        ["equanimity", "wisdom", "balance", "mind", "self_knowledge",
                      "skill", "focus", "meditation", "detachment", "calm",
                      "character", "contentment"],
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
