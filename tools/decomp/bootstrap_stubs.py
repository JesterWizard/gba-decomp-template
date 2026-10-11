#!/usr/bin/env python3
"""Phase 1 in one shot: peel every function as a byte-exact opcode stub.

For each `asm/nonmatchings/sub_*.s` (Luvdis output) this writes

  asm/matchings/<fn>.s       the retail bytes (sizes for the gap peels)
  src/matched/<fn>.c         `__attribute__((naked))` + `asm(".byte ...")`
  analysis/matched.json      identity: name -> address, kind "opcode"

then regenerates the ROM layout once. The result is a ROM that is built from
one C object per function, still byte-identical to baserom.gba, where every
function is a placeholder awaiting real C (script_first.py / agent_packet.py
pick them up as work items).

  python3 tools/decomp/bootstrap_stubs.py            # all functions
  python3 tools/decomp/bootstrap_stubs.py --limit 20 # first 20 (smoke test)

Idempotent: functions already in the manifest are skipped.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "decomp"))

from asm_bytes import addr_from_name, retail_bytes, write_matching_bytes  # noqa: E402
from fnfiles import stem_for  # noqa: E402
from match_function import reference_size  # noqa: E402

MANIFEST = ROOT / "analysis" / "matched.json"
NON = ROOT / "asm" / "nonmatchings"
MATCH = ROOT / "asm" / "matchings"
SRC = ROOT / "src" / "matched"


def stub_c(name: str, data: bytes) -> str:
    byte_str = ", ".join(f"0x{b:02X}" for b in data)
    return (
        '#include "global.h"\n\n'
        f"// @ 0x{addr_from_name(name):08x}\n"
        "__attribute__((naked))\n"
        f"void {name}(void)\n"
        "{\n"
        f'    asm(".byte {byte_str}");\n'
        "}\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--skip-layout", action="store_true")
    args = ap.parse_args()

    if not NON.is_dir() or not any(NON.glob("sub_*.s")):
        print("error: asm/nonmatchings is empty; run generate_asm.py first", file=sys.stderr)
        return 1
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.is_file() else {"functions": []}
    have = {f["name"] for f in manifest["functions"]}
    MATCH.mkdir(parents=True, exist_ok=True)
    SRC.mkdir(parents=True, exist_ok=True)

    names = sorted(p.stem for p in NON.glob("sub_*.s") if p.stem not in have)
    if args.limit:
        names = names[: args.limit]
    done = 0
    for name in names:
        try:
            size = reference_size(name)
        except (FileNotFoundError, ValueError, subprocess.CalledProcessError):
            print(f"skip {name}: cannot size", file=sys.stderr)
            continue
        data = retail_bytes(name, size)
        if len(data) != size or size < 2:
            print(f"skip {name}: bad size {size}", file=sys.stderr)
            continue
        write_matching_bytes(name, data, MATCH / f"{name}.s")
        (SRC / f"{stem_for(name)}.c").write_text(stub_c(name, data))
        manifest["functions"].append(
            {
                "name": name,
                "addr": f"0x{addr_from_name(name):08X}",
                "src": f"src/matched/{stem_for(name)}.c",
                "mode": "c",
                "kind": "opcode",
            }
        )
        done += 1

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"bootstrap_stubs: {done} stub(s) written, {len(manifest['functions'])} total")
    if args.skip_layout:
        return 0
    return subprocess.run([sys.executable, str(ROOT / "tools/decomp/gen_rom_layout.py")]).returncode


if __name__ == "__main__":
    raise SystemExit(main())
