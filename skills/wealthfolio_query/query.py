"""Read-only Python primitives for the wealthfolio-query wrapper.

SPEC §6.8, §17, §18.1, §19.2 invariants 11 and 14. See
plans/M2/M2.4-wrapper-skeleton.md for the contract.
"""

from __future__ import annotations

import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Mapping

# Exit codes — mirrored as comments in skills/wealthfolio_query/query.sh.
EXIT_OK = 0
EXIT_USAGE = 1
EXIT_DB = 2
EXIT_DATA = 3

_SQL_RELATIVE = "skills/sql/wealthfolio-queries.sql"
_CONFIG_RELATIVE = "config/wealthfolio.md"
_VERSION_PREFIX = "-- version:"


class SchemaVersionError(RuntimeError):
    """Raised when the SQL header pin diverges from config/wealthfolio.md."""


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def sql_file_path() -> Path:
    return repo_root() / _SQL_RELATIVE


def load_queries() -> dict[str, str]:
    text = sql_file_path().read_text()
    chunks = re.split(r"^-- name: ", text, flags=re.MULTILINE)
    queries: dict[str, str] = {}
    for chunk in chunks[1:]:
        slug, _, body = chunk.partition("\n")
        slug = slug.strip()
        body = body.strip()
        if not slug:
            continue
        if slug in queries:
            raise ValueError(f"duplicate named query slug: {slug}")
        queries[slug] = body
    return queries


def load_query(slug: str) -> str:
    queries = load_queries()
    try:
        return queries[slug]
    except KeyError as exc:
        known = ", ".join(sorted(queries)) or "(none)"
        raise KeyError(f"unknown named query slug: {slug!r}; known: {known}") from exc


def sql_version() -> str:
    for line in sql_file_path().read_text().splitlines():
        if line.startswith(_VERSION_PREFIX):
            return line[len(_VERSION_PREFIX):].strip()
    raise ValueError(
        f"{_SQL_RELATIVE} is missing the '{_VERSION_PREFIX} ...' preamble line"
    )


def configured_wealthfolio_version() -> tuple[str, str]:
    """Return (version, build) parsed from the §8 pin table in config/wealthfolio.md.

    Intentionally narrow: only the table rows whose first cell mentions
    CFBundleShortVersionString / CFBundleVersion are recognized. Any drift in
    the file structure should fail loudly so the pin contract stays explicit.
    """
    text = (repo_root() / _CONFIG_RELATIVE).read_text()
    version_match = re.search(r"CFBundleShortVersionString[^\n]*\|\s*`([^`]+)`", text)
    build_match = re.search(r"CFBundleVersion[^\n]*\|\s*`([^`]+)`", text)
    if not version_match or not build_match:
        raise ValueError(
            f"{_CONFIG_RELATIVE} is missing the CFBundleShortVersionString / "
            "CFBundleVersion pin table rows"
        )
    return version_match.group(1), build_match.group(1)


def validate_schema_version() -> None:
    sql_header = sql_version()
    version, build = configured_wealthfolio_version()
    normalized = f"wealthfolio v{version} (build {build})"
    if sql_header != normalized:
        raise SchemaVersionError(
            f"SQL header pin {sql_header!r} does not match "
            f"{_CONFIG_RELATIVE} pin {normalized!r}"
        )


def readonly_uri(db_path: str | Path) -> str:
    p = Path(db_path)
    if not p.is_absolute():
        p = p.resolve()
    return f"{p.as_uri()}?mode=ro&immutable=1"


def connect_readonly(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(readonly_uri(db_path), uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def execute(
    slug: str,
    params: Mapping[str, object],
    db_path: str | Path | None = None,
) -> list[sqlite3.Row]:
    sql = load_query(slug)
    if db_path is None:
        db_path = os.environ.get("WEALTHFOLIO_DB")
        if not db_path:
            raise ValueError("WEALTHFOLIO_DB is not set")
    with connect_readonly(db_path) as conn:
        return list(conn.execute(sql, dict(params)).fetchall())


def _err(message: str) -> None:
    print(f"wealthfolio-query: {message}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    args = list(argv) if argv is not None else sys.argv[1:]
    if not args:
        _err("missing internal subcommand (try: validate-schema)")
        return EXIT_USAGE

    cmd, rest = args[0], args[1:]
    if rest:
        _err(f"{cmd} takes no arguments at this stage")
        return EXIT_USAGE

    if cmd == "validate-schema":
        try:
            validate_schema_version()
        except SchemaVersionError as exc:
            _err(str(exc))
            return EXIT_DB
        except (FileNotFoundError, ValueError) as exc:
            _err(str(exc))
            return EXIT_DB
        return EXIT_OK

    _err(f"unknown internal subcommand: {cmd}")
    return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
