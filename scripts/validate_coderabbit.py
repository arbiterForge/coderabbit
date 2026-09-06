#!/usr/bin/env python3
"""Validate CodeRabbit YAML against a hash-pinned copy of its official schema."""

import argparse
from collections.abc import Iterator, Mapping, Sequence
import hashlib
import importlib.util
import math
from pathlib import Path
import subprocess
import sys
import tempfile

import requests
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError


SCHEMA_URL = "https://storage.googleapis.com/coderabbit_public_assets/schema.v2.json"
SCHEMA_SHA256 = "8c34e033182463bd4f2a823b144077cb21cc327927fb82ce49791bdae2b9da13"


def non_finite_paths(
    value: object, path: str = "$", seen: set[int] | None = None
) -> Iterator[str]:
    if isinstance(value, float) and not math.isfinite(value):
        yield path
        return

    if seen is None:
        seen = set()
    if isinstance(value, Mapping):
        identity = id(value)
        if identity in seen:
            return
        seen.add(identity)
        for key, child in value.items():
            yield from non_finite_paths(child, f"{path}.{key}", seen)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        identity = id(value)
        if identity in seen:
            return
        seen.add(identity)
        for index, child in enumerate(value):
            yield from non_finite_paths(child, f"{path}[{index}]", seen)


def preflight_configs(configs: list[Path]) -> int:
    yaml = YAML(typ="safe")
    yaml.allow_duplicate_keys = False
    invalid = False
    for config in configs:
        try:
            parsed = yaml.load(config.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, YAMLError) as error:
            print(f"{config}: YAML parsing failed: {error}", file=sys.stderr)
            invalid = True
            continue

        for path in non_finite_paths(parsed):
            print(
                f"{config}: non-finite number at {path} is not valid JSON",
                file=sys.stderr,
            )
            invalid = True
    return 1 if invalid else 0


def fetch_schema(schema_file: Path | None = None) -> bytes:
    if schema_file is not None:
        try:
            schema = schema_file.read_bytes()
        except OSError as error:
            raise RuntimeError(f"could not read supplied schema: {error}") from error
    else:
        try:
            response = requests.get(SCHEMA_URL, timeout=30)
            response.raise_for_status()
            schema = response.content
        except requests.RequestException as error:
            raise RuntimeError(f"could not retrieve authoritative schema: {error}") from error

    actual_hash = hashlib.sha256(schema).hexdigest()
    if actual_hash != SCHEMA_SHA256:
        raise RuntimeError(
            "authoritative schema SHA256 changed: "
            f"{actual_hash}; expected {SCHEMA_SHA256}"
        )
    return schema


def run_validator(schema: bytes, configs: list[Path]) -> int:
    if importlib.util.find_spec("check_jsonschema") is None:
        raise RuntimeError("check-jsonschema is not installed")

    schema_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as schema_file:
            schema_file.write(schema)
            schema_path = Path(schema_file.name)

        metaschema = subprocess.run(
            [sys.executable, "-m", "check_jsonschema", "--check-metaschema", str(schema_path)],
            check=False,
        )
        if metaschema.returncode != 0:
            return metaschema.returncode

        validation = subprocess.run(
            [
                sys.executable,
                "-m",
                "check_jsonschema",
                "--schemafile",
                str(schema_path),
                *(str(config) for config in configs),
            ],
            check=False,
        )
        return validation.returncode
    finally:
        if schema_path is not None:
            schema_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--schema-file",
        type=Path,
        help="use local schema bytes after verifying the pinned SHA-256",
    )
    parser.add_argument(
        "configs",
        metavar="CONFIG",
        type=Path,
        nargs="+",
        help="CodeRabbit YAML file to validate",
    )
    args = parser.parse_args()

    missing = [str(config) for config in args.configs if not config.is_file()]
    if missing:
        print(f"configuration file not found: {', '.join(missing)}", file=sys.stderr)
        return 2

    preflight_result = preflight_configs(args.configs)
    if preflight_result != 0:
        return preflight_result

    try:
        return run_validator(fetch_schema(args.schema_file), args.configs)
    except RuntimeError as error:
        print(f"validation infrastructure error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
