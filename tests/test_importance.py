from app.services.importance import clamp, rule_score


def test_interview_is_important():
    assert rule_score("hr@technest.com", "Interview confirmed for 3 PM", "") >= 70


def test_bill_due_is_important():
    assert rule_score("billing@desco.org.bd", "Your DESCO bill is due on 25 Nov", "") >= 70


def test_promotions_are_low():
    assert rule_score("deals@shop.com", "Flash sale: 50% off today", "Unsubscribe anytime") < 40


def test_otp_is_low():
    assert rule_score("noreply@bank.com", "Your OTP is 123456", "") < 40


def test_unclear_mail_goes_to_ai():
    assert rule_score("rahim@gmail.com", "Hey, quick question", "Are you free this weekend?") is None


def test_clamp():
    assert clamp(140) == 100 and clamp(-5) == 0 and clamp(55.4) == 55
