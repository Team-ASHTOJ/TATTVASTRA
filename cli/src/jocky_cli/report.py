"""Layout helpers for jocky's composed commands.

Every value printed through these helpers comes from jockyc's own output. They
choose spacing and alignment only: they never compute, infer, summarise or
re-derive compiler state.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from typing import Any

#: Wide enough for the longest label these commands print, plus a gutter.
LABEL_WIDTH = 24


def field(label: str, value: Any, width: int = LABEL_WIDTH) -> None:
    """One `label   value` line."""
    print(f"  {label:<{width}}{value}")


def note(text: str) -> None:
    """One indented line without a label."""
    print(f"  {text}")


def heading(text: str) -> None:
    """A short section separator inside command output."""
    print()
    print(f"  {text}")


def table(
    headers: Sequence[str],
    rows: Iterable[Sequence[str]],
    right: Sequence[int] = (),
) -> None:
    """A left-aligned table, with the listed columns right-aligned."""
    materialized = [list(row) for row in rows]
    widths = [len(header) for header in headers]
    for row in materialized:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def line(cells: Sequence[str]) -> str:
        padded = [
            cell.rjust(widths[index]) if index in right else cell.ljust(widths[index])
            for index, cell in enumerate(cells)
        ]
        return "  " + "  ".join(padded).rstrip()

    print(line(list(headers)))
    for row in materialized:
        print(line(row))


def emit_json(payload: Any) -> None:
    """A deterministic JSON document for `--json`."""
    print(json.dumps(payload, indent=2, sort_keys=True))
