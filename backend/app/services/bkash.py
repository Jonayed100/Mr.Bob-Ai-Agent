"""Read bKash SMS messages and keep track of money in and out.

Your phone forwards bKash SMS to Mr. Bob (see README). The parser below
understands the usual bKash message shapes; anything it can't read is ignored.
"""

import re

AMOUNT = r"Tk\.?\s*([\d,]+(?:\.\d+)?)"

# (kind, direction, pattern that must match at the start of the message)
KINDS = [
    ("received", "in", re.compile(r"you have received\s+(?:tk|money)", re.I)),
    ("cash_in", "in", re.compile(r"cash ?in\s+tk", re.I)),
    ("send_money", "out", re.compile(r"send money\s+tk", re.I)),
    ("cash_out", "out", re.compile(r"cash ?out\s+tk", re.I)),
    ("payment", "out", re.compile(r"payment\s+tk", re.I)),
    ("recharge", "out", re.compile(r"(mobile )?recharge\s+tk", re.I)),
    ("bill", "out", re.compile(r"bill (successfully )?paid|bill payment", re.I)),
]


def _money(text: str | None) -> float | None:
    if not text:
        return None
    try:
        return float(text.replace(",", ""))
    except ValueError:
        return None


def parse_sms(text: str) -> dict | None:
    """Turn one bKash SMS into a dict, or None if it isn't a transaction."""
    if not text:
        return None
    t = " ".join(text.split())
    kind = direction = None
    for k, d, pattern in KINDS:
        if pattern.search(t):
            kind, direction = k, d
            break
    if not kind:
        return None

    amount = None
    labelled = re.search(r"amount:?\s*" + AMOUNT, t, re.I)
    if labelled:
        amount = _money(labelled.group(1))
    else:
        first = re.search(AMOUNT, t, re.I)
        amount = _money(first.group(1)) if first else None
    if amount is None:
        return None

    fee = re.search(r"fee:?\s*" + AMOUNT, t, re.I)
    balance = re.search(r"balance:?\s*" + AMOUNT, t, re.I)
    trx = re.search(r"trx\s*id:?\s*([A-Z0-9]+)", t, re.I)
    party = ""
    if kind in ("received", "cash_in"):
        m = re.search(r"from\s+([^.]+?)(?:\.|\s+ref|\s+fee|\s+successful|$)", t, re.I)
    elif kind == "bill":
        m = re.search(r"(?:biller|organization):?\s*([^.]+?)(?:\.|\s+account|\s+amount|$)", t, re.I)
    else:
        m = re.search(r"to\s+([^.]+?)(?:\s+successful|\.|\s+ref|\s+fee|$)", t, re.I)
    if m:
        party = m.group(1).strip()[:120]

    return {
        "kind": kind,
        "direction": direction,
        "amount": amount,
        "fee": _money(fee.group(1)) if fee else 0.0,
        "balance": _money(balance.group(1)) if balance else None,
        "party": party,
        "trx_id": trx.group(1) if trx else "",
    }


def looks_like_bkash(sender: str, text: str) -> bool:
    return "bkash" in (sender or "").lower() or bool(re.search(r"\bTrxID\b", text or "", re.I))


KIND_LABEL = {
    "received": "Received", "cash_in": "Cash in", "send_money": "Sent", "cash_out": "Cash out",
    "payment": "Payment", "recharge": "Recharge", "bill": "Bill paid",
}
