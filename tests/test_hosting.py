import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("pydantic_settings")


def test_postgres_links_are_accepted_as_given():
    from app.db import normalize_url

    assert normalize_url("postgresql://u:p@host:5432/postgres").startswith("postgresql+psycopg://u:p@host")
    assert normalize_url("postgres://u:p@host/db").startswith("postgresql+psycopg://")
    assert normalize_url("sqlite:///./data/mrbob.db") == "sqlite:///./data/mrbob.db"


def test_render_address_is_picked_up(monkeypatch):
    from app.config import Settings

    monkeypatch.delenv("PUBLIC_URL", raising=False)
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://mr-bob.onrender.com")
    assert Settings(_env_file=None).public_url == "https://mr-bob.onrender.com"
    monkeypatch.setenv("PUBLIC_URL", "https://bob.example.com")
    assert Settings(_env_file=None).public_url == "https://bob.example.com"  # your own address wins
