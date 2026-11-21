from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import Usage
from ..timeutil import now_local, to_utc


def claude_cost_usd(input_tokens: int, output_tokens: int) -> float:
    s = get_settings()
    return input_tokens / 1e6 * s.claude_input_usd_per_mtok + output_tokens / 1e6 * s.claude_output_usd_per_mtok


def stt_cost_usd(seconds: float) -> float:
    return max(seconds, 1) / 60 * get_settings().stt_usd_per_minute


def tts_cost_usd(seconds: float) -> float:
    return max(seconds, 1) / 60 * get_settings().tts_usd_per_minute


def add_usage(db: Session, service: str, units: float, cost_usd: float) -> None:
    db.add(Usage(service=service, units=units, cost_usd=cost_usd))


def month_summary(db: Session) -> dict:
    """What this month costs so far, in taka, against the budget."""
    s = get_settings()
    start = now_local().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    rows = db.execute(
        select(Usage.service, func.sum(Usage.cost_usd)).where(Usage.created_at >= to_utc(start)).group_by(Usage.service)
    ).all()
    spent = {svc: float(total or 0) for svc, total in rows}

    def bdt(usd: float) -> int:
        return round(usd * s.usd_to_bdt)

    claude = bdt(spent.get("claude", 0))
    stt = bdt(spent.get("stt", 0))
    voice = bdt(spent.get("tts", 0))
    vat = round((claude + stt + voice) * s.vat_rate)
    items = [
        {"label": "Server (VPS)", "bdt": s.server_cost_bdt, "color": "#1d1d1f"},
        {"label": "AI brain (Claude)", "bdt": claude, "color": "#e0142f"},
        {"label": "Speech-to-text", "bdt": stt, "color": "#ff9500"},
        {"label": "Natural voice", "bdt": voice, "color": "#af52de"},
        {"label": "Domain", "bdt": s.domain_cost_bdt_per_month, "color": "#0a84ff"},
        {"label": "VAT on USD services", "bdt": vat, "color": "#8e8e93"},
        {"label": "Telegram, WhatsApp, backup AI", "bdt": 0, "color": "#34c759"},
    ]
    total = sum(i["bdt"] for i in items)
    return {"items": items, "total": total, "budget": s.monthly_budget_bdt, "left": s.monthly_budget_bdt - total}
