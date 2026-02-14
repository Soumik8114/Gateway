import os
from pathlib import Path


def get_database_url() -> str:
    default_db_path = (
        Path(__file__).resolve().parent / "../../control_plane/db.sqlite3"
    ).resolve()
    default_database_url = f"sqlite:///{default_db_path}"
    return os.environ.get("DATABASE_URL", default_database_url)


def get_redis_url() -> str:
    return os.environ.get("REDIS_URL", "redis://localhost:6379")
