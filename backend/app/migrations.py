"""Add new columns to an existing database without losing data.

SQLAlchemy's create_all() makes new tables but never changes old ones, so each
column added after the first release is listed here.
"""

import logging

from sqlalchemy import inspect, text

log = logging.getLogger("mrbob")

ADDED_COLUMNS = {
    "reminders": {
        "notes": "TEXT DEFAULT ''",
        "priority": "VARCHAR(10) DEFAULT 'normal'",
        "repeat": "VARCHAR(10) DEFAULT 'none'",
        "done_at": "DATETIME",
        "notified_at": "DATETIME",
        "seen_on_web": "BOOLEAN DEFAULT 1",
    },
}


def upgrade(engine) -> None:
    insp = inspect(engine)
    with engine.begin() as conn:
        for table, columns in ADDED_COLUMNS.items():
            if not insp.has_table(table):
                continue
            have = {c["name"] for c in insp.get_columns(table)}
            for name, ddl in columns.items():
                if name not in have:
                    conn.execute(text(f'ALTER TABLE {table} ADD COLUMN "{name}" {ddl}'))
                    log.info("Database upgraded: %s.%s", table, name)
