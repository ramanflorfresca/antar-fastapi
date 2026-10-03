"""Hinglish detection must not fire on plain English (live WhatsApp miss, 2026-10-03)."""
from dotenv import load_dotenv
load_dotenv()
import main


def test_english_with_repeated_the_is_not_hinglish():
    q = ("Will I make good money doing defence deals with the goverment? Being part of the "
         "company that connect manufacturers from India with govermwnt institutions")
    assert main._ask_detect_hinglish(q) is None
    assert main._wa_lang(q, "hinglish") == "en"


def test_english_with_main_and_or_is_not_hinglish():
    assert main._ask_detect_hinglish("Is the main office move a good idea, ya or no? Should we ho") is None


def test_real_hinglish_still_detected():
    assert main._ask_detect_hinglish("meri shaadi kab hogi?") == "hinglish"
    assert main._ask_detect_hinglish("main naukri badlu ya nahi") == "hinglish"
    assert main._wa_lang("kya mujhe paisa milega is saal?") == "hinglish"


def test_code_mixed_hinglish_still_detected():
    assert main._ask_detect_hinglish("meri job kab lagegi is this year?") == "hinglish"
    assert main._ask_detect_hinglish("kya mera business is year grow karega") == "hinglish"


def test_long_english_with_two_collisions_is_english():
    q = ("Should I take the job offer from the bank or stay where I am, given that my "
         "manager says there will be a promotion and the pay is better ho")
    assert main._ask_detect_hinglish(q) is None
