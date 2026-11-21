"""Pure helpers for Mr. Bob's memory (kept separate so they're easy to test)."""

import re

KINDS = ("fact", "preference", "person", "goal", "routine")


def normalize(text: str) -> str:
    text = re.sub(r"[^\w\sঀ-৿]", " ", (text or "").lower())
    return " ".join(text.split())


def is_duplicate(new: str, existing: list[str]) -> bool:
    n = normalize(new)
    if not n:
        return True
    for old in existing:
        o = normalize(old)
        if n == o or (len(n) > 12 and n in o) or (len(o) > 12 and o in n):
            return True
        a, b = set(n.split()), set(o.split())
        if a and b and len(a & b) / len(a | b) >= 0.8:
            return True
    return False


def worth_learning_from(text: str) -> bool:
    """Skip tiny messages and plain questions: they rarely contain something to remember."""
    words = (text or "").split()
    if len(words) < 4:
        return False
    stripped = text.strip()
    if stripped.endswith("?") and not re.search(r"\b(i am|i'm|my|ami|amar)\b", stripped, re.I):
        return False
    return True
