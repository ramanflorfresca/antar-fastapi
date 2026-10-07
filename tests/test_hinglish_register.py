from antar_engine.hinglish_register import to_aap


def test_live_examples_become_aap():
    assert to_aap("Tera partnership potential strong hai.") == "Aapka partnership potential strong hai."
    assert to_aap("Kya tum genuinely ready ho?") == "Kya aap genuinely ready hain?"
    assert to_aap("Is hafte apne aap mein invest kar — dekho kya kaam aata hai.") == \
        "Is hafte apne aap mein invest kijiye — dekhiye kya kaam aata hai."
    assert to_aap("Call karo aur likho.") == "Call kijiye aur likhiye."


def test_leaves_aap_text_and_english_alone():
    s = "Aapka money window Nov 2026 mein khulta hai. Tomorrow is a good day to tune your pitch."
    assert to_aap(s) == s
    assert to_aap("Tumhari reading strong hai") == "Aapki reading strong hai"
    assert to_aap("") == "" and to_aap(None) is None
