"""Work out how the user is writing: English, Bangla script, or Banglish.

Mr. Bob answers in the same style, and picks the matching voice.
"""

import re

BANGLA_CHARS = re.compile(r"[ঀ-৿]")
WORDS = re.compile(r"[a-zA-Z']+")

# Common Banglish words. If enough of these show up in Latin script,
# the message is Banglish rather than English.
BANGLISH_HINTS = {
    "ami", "amar", "amake", "tumi", "tomar", "tomake", "apni", "apnar", "ki", "kí", "keno", "kemon",
    "kothay", "kobe", "koto", "ache", "achi", "achen", "nai", "nei", "na", "hobe", "hoye", "hoyeche",
    "korbo", "koro", "korte", "korchi", "korsi", "bolo", "bolen", "dao", "jabo", "jao", "ajke",
    "aaj", "kal", "kalke", "ekhon", "pore", "bhalo", "valo", "kharap", "shob", "sob", "onek",
    "ektu", "jinish", "kaj", "kaaj", "taka", "bhai", "vai", "apu", "ammu", "abbu", "acha", "accha",
    "thik", "hoise", "hocche", "hoche", "lagbe", "lage", "dekhao", "dekho", "shuno", "bujhlam",
    "mone", "koriye", "diyo", "dio", "brishti", "bristi", "abohawa", "khobor", "kichu", "keu", "jodi",
    "tahole", "kintu", "ar", "theke", "porjonto", "shathe", "sathe", "moddhe", "ber", "jete",
}


def detect_style(text: str) -> str:
    """Return 'bangla', 'banglish' or 'english'."""
    if not text or not text.strip():
        return "english"
    letters = [c for c in text if c.isalpha()]
    if letters:
        bangla = len(BANGLA_CHARS.findall(text))
        if bangla / len(letters) >= 0.3:
            return "bangla"
    words = [w.lower() for w in WORDS.findall(text)]
    if not words:
        return "english"
    hits = sum(1 for w in words if w in BANGLISH_HINTS)
    # short messages need fewer hits ("ajke ki?" is clearly Banglish)
    if hits >= 2 or (hits >= 1 and len(words) <= 3) or hits / len(words) >= 0.25:
        return "banglish"
    return "english"


LANGUAGE_RULES = {
    "auto": (
        "Reply in the SAME style the user used. English -> English. Bangla script -> Bangla script. "
        "Banglish (Bangla written in English letters) or a mix -> the same natural Banglish mix."
    ),
    "english": "Always reply in English.",
    "bangla": "Always reply in Bangla, using Bangla script.",
    "banglish": "Always reply in Banglish: Bangla words written in English letters, mixed naturally with English.",
}


def language_rule(choice: str | None) -> str:
    return LANGUAGE_RULES.get((choice or "auto").lower(), LANGUAGE_RULES["auto"])


def reply_style(reply: str, choice: str | None, user_text: str = "") -> str:
    """Which voice should read this reply aloud."""
    if detect_style(reply) == "bangla":
        return "bangla"  # Bangla script always gets the Bangla voice
    choice = (choice or "auto").lower()
    if choice in ("english", "banglish"):
        return choice
    return detect_style(reply or user_text)
