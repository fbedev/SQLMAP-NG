from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from app.config import settings


class JsonFileStore:
    def __init__(self, file_name: str) -> None:
        self.file_path = settings.data_dir / file_name
        self._ensure_file()

    def _ensure_file(self) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self.file_path.write_text(json.dumps({"data": []}, indent=2), encoding="utf-8")

    def _read(self) -> List[Dict[str, Any]]:
        raw = self.file_path.read_text(encoding="utf-8")
        payload = json.loads(raw)
        data = payload.get("data", [])
        if not isinstance(data, list):
            raise ValueError(f"Invalid data format in {self.file_path}")
        return data

    def _write(self, data: List[Dict[str, Any]]) -> None:
        payload = {"data": data}
        self.file_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    def list(self) -> List[Dict[str, Any]]:
        return self._read()

    def append(self, record: Dict[str, Any]) -> Dict[str, Any]:
        data = self._read()
        data.append(record)
        self._write(data)
        return record

    def upsert(self, key: str, record: Dict[str, Any]) -> Dict[str, Any]:
        data = self._read()
        for index, existing in enumerate(data):
            if existing.get(key) == record.get(key):
                data[index] = record
                self._write(data)
                return record
        data.append(record)
        self._write(data)
        return record

    def find_one(self, predicate: Callable[[Dict[str, Any]], bool]) -> Optional[Dict[str, Any]]:
        for record in self._read():
            if predicate(record):
                return record
        return None

    def filter(self, predicate: Callable[[Dict[str, Any]], bool]) -> List[Dict[str, Any]]:
        return [record for record in self._read() if predicate(record)]


def resolve_authorization_path(consent_id: str, file_name: str) -> Path:
    base = settings.data_dir / settings.authorization_subdir / consent_id
    base.mkdir(parents=True, exist_ok=True)
    return base / file_name
