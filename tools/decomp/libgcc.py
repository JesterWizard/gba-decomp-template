#!/usr/bin/env python3
"""Locate libgcc helpers in the baserom, so no tool hardcodes one game's addresses.

`_call_via_r0` .. `_call_via_lr` are 15 consecutive `bx rN; nop` thunks that agbcc
calls for indirect calls; they are found by scanning the ROM. `__divsi3` has no
fixed byte signature across libgcc builds, so its address comes from the optional
`DIVSI3_ADDR` setting in project.mk.

Usage: python3 tools/decomp/libgcc.py      # print what was found
"""

from __future__ import annotations

import functools
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import projcfg  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
BASEROM = ROOT / "baserom.gba"
ROM_BASE = 0x08000000

CALL_VIA_REGS = (
    "r0", "r1", "r2", "r3", "r4", "r5", "r6", "r7", "r8", "r9",
    "sl", "fp", "ip", "sp", "lr",
)
# `bx rN` (0x4700 | N << 3) followed by `nop` (`mov r8, r8` = 0x46C0), N = 0..14.
_CALL_VIA_BYTES = b"".join(
    struct.pack("<HH", 0x4700 | (n << 3), 0x46C0) for n in range(len(CALL_VIA_REGS))
)


@functools.lru_cache(maxsize=None)
def call_via_base() -> int | None:
    """ROM address of `_call_via_r0`, or None without a baserom or thunk table."""
    if not BASEROM.is_file():
        return None
    rom = BASEROM.read_bytes()
    off = rom.find(_CALL_VIA_BYTES)
    while off >= 0 and off % 2:
        off = rom.find(_CALL_VIA_BYTES, off + 1)
    return ROM_BASE + off if off >= 0 else None


def call_via_addr(reg: str) -> int | None:
    """ROM address of `_call_via_<reg>` (`r10`/`r11`/`r12` aliases accepted)."""
    reg = {"r10": "sl", "r11": "fp", "r12": "ip"}.get(reg, reg)
    base = call_via_base()
    if base is None or reg not in CALL_VIA_REGS:
        return None
    return base + 4 * CALL_VIA_REGS.index(reg)


@functools.lru_cache(maxsize=None)
def divsi3_addr() -> int | None:
    """`DIVSI3_ADDR` from project.mk, or None while it is unset."""
    value = projcfg.CFG.get("DIVSI3_ADDR", "").strip()
    return int(value, 0) if value else None


if __name__ == "__main__":
    base = call_via_base()
    div = divsi3_addr()
    print(f"_call_via_r0: {base:#010x}" if base is not None else "_call_via_r0: not found")
    print(
        f"__divsi3:     {div:#010x}"
        if div is not None
        else "__divsi3:     unset (DIVSI3_ADDR in project.mk)"
    )
