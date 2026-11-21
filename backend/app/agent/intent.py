"""Spot requests for the night briefing ("Hey Mr. Bob, tell me about my important tasks")."""

import re

PATTERNS = [
    r"\b(tell|show|give|list|explain|what are|what's|whats)\b.{0,30}\bimportant (task|tasks|work|things|stuff)\b",
    r"\bmy important (tasks|things|work)\b(?!.{0,10}\b(add|is|to)\b)",
    r"\b(today'?s|todays|daily|night|tonight'?s) (report|briefing|summary|tasks|plan)\b",
    r"\bmy (report|briefing|daily summary)\b",
    r"\bbrief me\b",
    r"\bwhat (do|should) i (need to )?do (today|tomorrow)\b",
    r"\b(give|tell) me (my|the) (report|briefing|summary|update)\b",
    r"\bajker (report|kaj|important|gurutto)",
    r"\b(important|gurutto?purno) kaj\b",
    r"\bkaj gula\b",
    r"\breport (dao|den|bolo|shonao)\b",
    r"গুরুত্বপূর্ণ (কাজ|কাজগুলো)",
    r"আজকের (রিপোর্ট|কাজ|সারাংশ)",
    r"রিপোর্ট (দাও|বলো|শোনাও)",
    r"কাজগুলো (বলো|কী|কি)",
]
_RX = re.compile("|".join(PATTERNS), re.I)


def wants_briefing(text: str) -> bool:
    return bool(text and _RX.search(text))
