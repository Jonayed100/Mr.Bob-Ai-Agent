from app.services.bkash import looks_like_bkash, parse_sms


def test_received():
    tx = parse_sms("You have received Tk 1,500.00 from 01712345678. Ref rent. Fee Tk 0.00. Balance Tk 2,345.50. TrxID BKA1X2Y3Z4 at 21/11/2026 10:15")
    assert tx["kind"] == "received" and tx["direction"] == "in"
    assert tx["amount"] == 1500 and tx["balance"] == 2345.5
    assert tx["party"] == "01712345678" and tx["trx_id"] == "BKA1X2Y3Z4"


def test_send_money():
    tx = parse_sms("Send Money Tk 500.00 to 01812345678 successful. Ref lunch. Fee Tk 5.00. Balance Tk 1,840.50. TrxID BKB9 at 21/11/2026 12:30")
    assert tx["kind"] == "send_money" and tx["direction"] == "out"
    assert tx["amount"] == 500 and tx["fee"] == 5 and tx["party"] == "01812345678"


def test_cash_out():
    tx = parse_sms("Cash Out Tk 1,000.00 to 01912345678 successful. Fee Tk 18.50. Balance Tk 822.00. TrxID BKC7 at 21/11/2026 13:00")
    assert tx["kind"] == "cash_out" and tx["amount"] == 1000 and tx["fee"] == 18.5


def test_payment():
    tx = parse_sms("Payment Tk 250.00 to Daraz Bangladesh successful. Balance Tk 572.00. TrxID BKD1 at 21/11/2026 14:00")
    assert tx["kind"] == "payment" and tx["party"] == "Daraz Bangladesh"


def test_bill():
    tx = parse_sms("Bill successfully paid. Biller: DESCO Prepaid. Account: 123456. Amount: Tk 1,240.00. Fee: Tk 0.00. Balance: Tk 332.00. TrxID BKE2 at 21/11/2026 15:00")
    assert tx["kind"] == "bill" and tx["amount"] == 1240 and tx["party"] == "DESCO Prepaid" and tx["balance"] == 332


def test_not_a_transaction():
    assert parse_sms("Your bKash verification code is 123456. Do not share it.") is None


def test_sender_check():
    assert looks_like_bkash("bKash", "anything")
    assert not looks_like_bkash("Robi", "Get 10GB at Tk 99")
