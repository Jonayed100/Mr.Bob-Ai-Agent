from app.agent.language import detect_style, reply_style


def test_english():
    assert detect_style("What's on my calendar today?") == "english"


def test_bangla_script():
    assert detect_style("আজকের আবহাওয়া কেমন?") == "bangla"


def test_banglish():
    assert detect_style("Ajke amar schedule ki?") == "banglish"
    assert detect_style("Bob, ajke ki ki korte hobe suggest koro") == "banglish"


def test_mixed_english_with_one_bangla_word_stays_english():
    assert detect_style("Can you check my email and tell me about the meeting tomorrow") == "english"


def test_bangla_reply_always_gets_bangla_voice():
    assert reply_style("ঢাকায় এখন ২৪ ডিগ্রি", "english") == "bangla"


def test_fixed_choice_is_respected():
    assert reply_style("Done! I'll remind you at 8 PM.", "banglish") == "banglish"
