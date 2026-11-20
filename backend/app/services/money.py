"""Store bKash transactions and summarise the month."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import Transaction, is_enabled
from ..timeutil import friendly, now_local, to_utc
from .activity import record
from .bkash import KIND_LABEL, looks_like_bkash, parse_sms
from .notify import notify


def tk(x: float | None) -> str:
    if x is None:
        return "—"
    return f"৳{x:,.0f}" if float(x).is_integer() else f"৳{x:,.2f}"


def record_sms(db: Session, sender: str, text: str) -> dict | None:
    if not is_enabled(db, "bkash") or not looks_like_bkash(sender, text):
        return None
    tx = parse_sms(text)
    if not tx:
        return None
    if tx["trx_id"] and db.scalar(select(Transaction).where(Transaction.trx_id == tx["trx_id"])):
        return tx  # already saved (phones sometimes forward twice)
    db.add(Transaction(raw=text[:1000], **tx))
    label = KIND_LABEL.get(tx["kind"], tx["kind"])
    record(db, f"bKash: {label} {tk(tx['amount'])}" + (f" ({tx['party']})" if tx["party"] else ""), "bkash")

    s = get_settings()
    if tx["direction"] == "in" and tx["amount"] >= s.bkash_big_amount_bdt:
        notify(db, f"💰 bKash: you received {tk(tx['amount'])}" + (f" from {tx['party']}" if tx["party"] else ""))
    if tx["balance"] is not None and tx["balance"] < s.bkash_low_balance_bdt:
        notify(db, f"⚠️ bKash balance is low: {tk(tx['balance'])}")
    return tx


def month_summary(db: Session) -> dict:
    start = now_local().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    rows = db.scalars(
        select(Transaction).where(Transaction.created_at >= to_utc(start)).order_by(Transaction.id.desc())
    ).all()
    money_in = sum(r.amount for r in rows if r.direction == "in")
    money_out = sum(r.amount + (r.fee or 0) for r in rows if r.direction == "out")
    last = db.scalar(select(Transaction).where(Transaction.balance.is_not(None)).order_by(Transaction.id.desc()))
    return {
        "in": round(money_in, 2),
        "out": round(money_out, 2),
        "fees": round(sum(r.fee or 0 for r in rows), 2),
        "balance": last.balance if last else None,
        "count": len(rows),
        "recent": [
            {
                "label": KIND_LABEL.get(r.kind, r.kind),
                "direction": r.direction,
                "amount": r.amount,
                "party": r.party,
                "when": friendly(r.created_at),
            }
            for r in rows[:6]
        ],
    }
