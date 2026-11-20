"""Decide how important an email is.

Cheap keyword rules go first. Only emails the rules can't decide are sent
to Claude, which keeps the monthly bill small.
"""

import re

HIGH_WORDS = [
    "interview", "offer letter", "job offer", "shortlisted", "selected", "admission", "visa", "cas ",
    "university", "deadline", "due date", "due on", "overdue", "payment due", "bill", "invoice",
    "urgent", "important", "action required", "security alert", "password", "suspicious",
    "court", "exam", "result", "appointment", "desco", "dpdc", "wasa", "titas", "nesco",
    "জরুরি", "সাক্ষাৎকার", "বিল", "পরীক্ষা", "ফলাফল",
]
LOW_WORDS = [
    "unsubscribe", "newsletter", "% off", "sale", "discount", "deal", "promo", "offer ends",
    "webinar", "digest", "weekly roundup", "recommended for you", "new follower", "liked your",
    "reacted to", "starred", "trending", "flash sale", "coupon", "cashback offer",
]
NOISY_SENDERS = re.compile(r"(no-?reply|newsletter|marketing|promo|notifications?|mailer|news@|info@)", re.I)
OTP = re.compile(r"\b(otp|one[- ]time (pass)?code|verification code)\b", re.I)


def rule_score(sender: str, subject: str, snippet: str = "") -> int | None:
    """Return a score 0-100 when the rules are sure, or None to ask the AI."""
    text = f"{subject} {snippet}".lower()
    if OTP.search(text):
        return 10  # codes are useless once read
    high = sum(1 for w in HIGH_WORDS if w in text)
    low = sum(1 for w in LOW_WORDS if w in text)
    noisy = bool(NOISY_SENDERS.search(sender or ""))

    if low >= 2 or (low >= 1 and noisy and high == 0):
        return 15
    if high >= 2 and low == 0:
        return 85
    if high >= 1 and low == 0 and not noisy:
        return 75
    if noisy and high == 0:
        return 25
    return None


def clamp(score: int | float) -> int:
    return max(0, min(100, int(round(score))))
