from __future__ import annotations

from dataclasses import dataclass

import httpx
from databases import Database


@dataclass
class AppState:
    database: Database
    http_client: httpx.AsyncClient
    redis_client: object
