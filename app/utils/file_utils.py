import re
from pathlib import Path
from typing import Iterable


INVALID_CHARS = re.compile(r"[^a-zA-Z0-9._-]+")
MULTI_UNDERSCORE = re.compile(r"_+")


def sanitize_file_name(name: str, default: str = "file") -> str:
    cleaned = INVALID_CHARS.sub("_", name).strip("._") or default
    cleaned = MULTI_UNDERSCORE.sub("_", cleaned)
    return cleaned[:120]


def ensure_directories(paths: Iterable[Path]) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)
