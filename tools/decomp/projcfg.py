"""Per-game settings shared by every tool (parsed from project.mk)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_LINE = re.compile(r"^([A-Z][A-Z0-9_]*)\s*:?=\s*(.*?)\s*$")


def _load() -> dict[str, str]:
    out: dict[str, str] = {}
    for line in (ROOT / "project.mk").read_text().splitlines():
        m = _LINE.match(line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


CFG = _load()
FILE_NAME = CFG["FILE_NAME"]
GAME_NAME = CFG.get("GAME_NAME", FILE_NAME)
ROM = ROOT / f"{FILE_NAME}.gba"
ELF = ROOT / f"{FILE_NAME}.elf"
TOML = ROOT / f"{FILE_NAME}.toml"
OBJ_DIR = ROOT / "build" / "obj"
