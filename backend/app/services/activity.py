import logging

from sqlalchemy.orm import Session

from ..models import Activity

log = logging.getLogger("mrbob")


def record(db: Session, text: str, kind: str = "info") -> None:
    """Add a line to the 'What Mr. Bob did' list on the dashboard."""
    db.add(Activity(text=text[:300], kind=kind))
    log.info("activity: %s", text)
