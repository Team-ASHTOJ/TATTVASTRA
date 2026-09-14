"""Local content-addressed object adapter; metadata remains in PostgreSQL."""

import os
import tempfile
from pathlib import Path

from jocky_control_plane.security import digest


class ObjectStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def path(self, key: str) -> Path:
        if len(key) != 64 or any(c not in "0123456789abcdef" for c in key):
            raise ValueError("Invalid content-addressed object key")
        candidate = (self.root / key[:2] / key).resolve()
        if not candidate.is_relative_to(self.root):
            raise ValueError("Object path escapes storage root")
        return candidate

    def put(self, content: bytes) -> str:
        key = digest(content)
        path = self.path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix="staged-", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temporary, path)
            except FileExistsError:
                if path.read_bytes() != content:
                    raise ValueError("Existing object fails integrity verification") from None
        finally:
            Path(temporary).unlink(missing_ok=True)
        return key

    def get(self, key: str) -> bytes:
        return self.path(key).read_bytes()
