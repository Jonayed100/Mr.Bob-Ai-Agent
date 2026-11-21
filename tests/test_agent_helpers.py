from datetime import datetime, timezone

from app.agent.intent import wants_briefing
from app.services.memory_text import is_duplicate, normalize, worth_learning_from
from app.services.reminders import clean_choice, next_due


# ---- "Hey Mr. Bob, tell me about my important tasks" ----
def test_briefing_english():
    assert wants_briefing("Hey Mr. Bob, tell me about my important tasks")
    assert wants_briefing("Give me today's report")
    assert wants_briefing("brief me please")


def test_briefing_bangla_and_banglish():
    assert wants_briefing("আমার গুরুত্বপূর্ণ কাজগুলো বলো")
    assert wants_briefing("আজকের রিপোর্ট দাও")
    assert wants_briefing("Bob, ajker important kaj gula bolo")


def test_normal_chat_is_not_a_briefing():
    assert not wants_briefing("What's the weather like?")
    assert not wants_briefing("Remind me to call Ammu at 8 PM")
    assert not wants_briefing("Add an important task: submit the CV tomorrow")


# ---- repeating reminders ----
def test_next_due():
    d = datetime(2026, 1, 31, 9, 0, tzinfo=timezone.utc)
    assert next_due(d, "daily") == datetime(2026, 2, 1, 9, 0, tzinfo=timezone.utc)
    assert next_due(d, "weekly") == datetime(2026, 2, 7, 9, 0, tzinfo=timezone.utc)
    assert next_due(d, "monthly") == datetime(2026, 2, 28, 9, 0, tzinfo=timezone.utc)  # no 31 Feb
    assert next_due(datetime(2026, 12, 15, tzinfo=timezone.utc), "monthly").year == 2027
    assert next_due(d, "none") is None


def test_clean_choice():
    assert clean_choice("Important", ("normal", "important"), "normal") == "important"
    assert clean_choice("urgent!!", ("normal", "important"), "normal") == "normal"


# ---- memory ----
def test_memory_duplicates():
    have = ["His sister Nusrat's birthday is 12 March"]
    assert is_duplicate("his sister nusrat's birthday is 12 March.", have)
    assert not is_duplicate("He prefers tea over coffee", have)


def test_normalize_keeps_bangla():
    assert normalize("আমার নাম জোনায়েদ!") == "আমার নাম জোনায়েদ"


def test_worth_learning():
    assert not worth_learning_from("hi bob")
    assert not worth_learning_from("What time is it now?")
    assert worth_learning_from("My sister Nusrat's birthday is on 12 March")
