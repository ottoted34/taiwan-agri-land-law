"""JSON-file record store. One file per record so git diffs stay readable and a failed
run can never corrupt unrelated records. Writes are atomic (util.write_json)."""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

from .util import read_json, sha256, write_json


class Store:
    def __init__(self, folder: Path):
        self.folder = folder

    def path(self, rid: str) -> Path:
        return self.folder / f"{rid}.json"

    def get(self, rid: str) -> dict | None:
        return read_json(self.path(rid))

    def put(self, rec: dict) -> None:
        write_json(self.path(rec["id"]), rec)

    def ids(self) -> list[str]:
        if not self.folder.exists():
            return []
        return sorted(p.stem for p in self.folder.glob("*.json") if not p.name.startswith("."))

    def all(self) -> Iterator[dict]:
        for rid in self.ids():
            r = self.get(rid)
            if r:
                yield r


CONTENT_FIELDS = {
    "interpretation": ["docno", "date", "agency_text", "category", "subject", "content"],
    "technical": ["title", "series", "issue", "authors", "date", "url"],
    "law": ["name", "level", "modified_date", "status", "articles", "attachments", "effective_note", "abandon_note"],
}


def content_hash(kind: str, rec: dict) -> str:
    return sha256({k: rec.get(k) for k in CONTENT_FIELDS[kind]})
