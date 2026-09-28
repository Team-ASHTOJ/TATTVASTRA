"""A small option parser for jocky's own composed commands.

jockyc's parser rejects any option it does not know (E001), so a composed
command must consume its own options first and build a clean jockyc argv from
what remains. Anything a caller does not declare is rejected here rather than
forwarded.
"""

from __future__ import annotations

import re
from collections.abc import Collection

_HEX = re.compile(r"[0-9a-fA-F]{1,16}")
_DECIMAL = re.compile(r"[0-9]{1,20}")
_MAX_SEED = 0xFFFFFFFFFFFFFFFF


class UsageError(ValueError):
    """The caller's arguments cannot be satisfied. Reported as exit status 2."""


def parse(
    argv: list[str],
    valued: Collection[str] = (),
    flags: Collection[str] = (),
) -> tuple[list[str], dict[str, str], set[str]]:
    """Split argv into positionals, `option -> value`, and present flags."""
    valued_set = set(valued)
    flags_set = set(flags)
    positionals: list[str] = []
    values: dict[str, str] = {}
    present: set[str] = set()

    index = 0
    while index < len(argv):
        argument = argv[index]
        index += 1
        if argument in valued_set:
            if argument in values:
                raise UsageError(f"duplicate option {argument}")
            if index >= len(argv):
                raise UsageError(f"{argument} needs a value")
            values[argument] = argv[index]
            index += 1
        elif argument in flags_set:
            if argument in present:
                raise UsageError(f"duplicate option {argument}")
            present.add(argument)
        elif argument.startswith("--"):
            raise UsageError(f"unknown option {argument}")
        else:
            positionals.append(argument)
    return positionals, values, present


def parse_seed(text: str, name: str = "--seed") -> int:
    """The seed jockyc would read from this text.

    Mirrors jockyc's rule: `0x` means hexadecimal, a 16-character value means
    hexadecimal, anything else is decimal. Keeping the rule identical means a
    user-supplied seed still means the same thing after jocky reformats it into
    the unambiguous hexadecimal form it forwards.
    """
    digits = text.strip()
    base = 10
    if digits[:2].lower() == "0x":
        digits = digits[2:]
        base = 16
    elif len(digits) == 16:
        base = 16
    pattern = _HEX if base == 16 else _DECIMAL
    if not pattern.fullmatch(digits):
        raise UsageError(f"{name}: seed must be an unsigned 64-bit decimal or hexadecimal value")
    value = int(digits, base)
    if value > _MAX_SEED:
        raise UsageError(f"{name}: seed does not fit in 64 bits")
    return value


def count(text: str, name: str = "--count") -> int:
    """jockyc's bounded variant count: 1 to 64 inclusive (E261)."""
    if not _DECIMAL.fullmatch(text.strip()):
        raise UsageError(f"{name} must be a decimal number")
    value = int(text)
    if value < 1 or value > 64:
        raise UsageError(f"{name} must be between 1 and 64")
    return value
