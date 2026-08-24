from __future__ import annotations

from hashlib import sha256
from pathlib import Path


MAX_ITL_SIZE = 500 * 1024 * 1024


def validate_readable_itl(path: str | Path) -> Path:
    source = Path(path).expanduser().resolve()
    if source.suffix.casefold() != ".itl":
        raise ValueError("Select a Bentley .itl template library")
    if not source.is_file():
        raise FileNotFoundError(f"ITL file not found: {source}")
    if source.stat().st_size > MAX_ITL_SIZE:
        raise ValueError("ITL exceeds the 500 MB safety limit")
    return source


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def detect_format(path: Path) -> str:
    with path.open("rb") as stream:
        head = stream.read(512).lstrip()
    if head.startswith((b"<InRoads", b"<?xml", b"<")):
        return "XML"
    if head.startswith(b"PK\x03\x04"):
        return "ZIP archive"
    if head.startswith(b"SQLite format 3\x00"):
        return "SQLite database"
    if b"\x00" in head:
        return "binary/proprietary"
    return "plain text or proprietary structured text"
