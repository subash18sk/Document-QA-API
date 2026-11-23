import pytest

from app.config import Settings


@pytest.mark.parametrize("given,expected", [
    ("postgres://u:p@host:5432/db", "postgresql+psycopg2://u:p@host:5432/db"),    # Render/Heroku style
    ("postgresql://u:p@host/db", "postgresql+psycopg2://u:p@host/db"),            # driver pinned explicitly
    ("postgresql+psycopg2://u@host/db", "postgresql+psycopg2://u@host/db"),       # already explicit
    ("sqlite:///./local.db", "sqlite:///./local.db"),                             # untouched
])
def test_database_url_is_normalised(given, expected):
    assert Settings(database_url=given).sqlalchemy_url == expected


def test_default_jwt_secret_meets_minimum_length():
    assert len(Settings().jwt_secret.encode()) >= 32   # RFC 7518: HS256 keys should be >= 32 bytes
