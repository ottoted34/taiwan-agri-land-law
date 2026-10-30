"""Collector contract. Each source is an independent adapter; adding a source = add a module
plus a YAML entry in config/sources/. Collectors only *fetch and parse*; persistence,
validation, dedup and anomaly checks happen centrally in sync.py."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..http import Client


@dataclass
class CollectResult:
    source_id: str
    kind: str  # law | interpretation | technical | relation | audit
    records: list[dict[str, Any]] = field(default_factory=list)
    complete: bool = True  # False when only a partial window was fetched (daily incremental)
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    status: str = "ok"  # ok | partial | failed | robots_disallowed | unavailable
    requests: int = 0


class Collector:
    source_id: str = ""
    kind: str = ""

    def __init__(self, cfg: dict, client: Client):
        self.cfg = cfg
        self.client = client

    def collect(self, mode: str) -> CollectResult:  # mode: daily | weekly | monthly | full
        raise NotImplementedError
