"""Exact-identity hashing (generalised from the old document hash_service)."""
from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def sha256_bytes(data: bytes) -> str:
    """SHA-256 of in-memory bytes (e.g. an uploaded file)."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(file_path: str) -> str:
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"No such file: {file_path}")
    digest = hashlib.sha256()
    with open(file_path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_hash(payload: Any) -> str:
    """Deterministic commitment to structured metadata (sorted keys, no whitespace).

    Used so private details (prompts, parameters) can be committed to without
    ever being stored or published.
    """
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return sha256_bytes(canonical.encode("utf-8"))


def is_sha256(value: str) -> bool:
    return bool(value) and bool(_SHA256_RE.match(value.lower()))
