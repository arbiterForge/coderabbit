import atexit
from functools import lru_cache
import hashlib
import os
from pathlib import Path
import tempfile

import requests


SCHEMA_URL = "https://storage.googleapis.com/coderabbit_public_assets/schema.v2.json"
SCHEMA_SHA256 = "8c34e033182463bd4f2a823b144077cb21cc327927fb82ce49791bdae2b9da13"
_schema_path: Path | None = None


@lru_cache(maxsize=1)
def schema_bytes() -> bytes:
    supplied_schema = os.environ.get("CODERABBIT_TEST_SCHEMA_FILE")
    if supplied_schema:
        schema = Path(supplied_schema).read_bytes()
    else:
        response = requests.get(SCHEMA_URL, timeout=30)
        response.raise_for_status()
        schema = response.content

    schema_hash = hashlib.sha256(schema).hexdigest()
    if schema_hash != SCHEMA_SHA256:
        raise AssertionError(
            f"authoritative schema SHA256 changed: {schema_hash}; "
            f"expected {SCHEMA_SHA256}"
        )
    return schema


def schema_path() -> Path:
    global _schema_path
    if _schema_path is None:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as schema_file:
            schema_file.write(schema_bytes())
            _schema_path = Path(schema_file.name)
    return _schema_path


def remove_schema_snapshot() -> None:
    if _schema_path is not None:
        _schema_path.unlink(missing_ok=True)


atexit.register(remove_schema_snapshot)
