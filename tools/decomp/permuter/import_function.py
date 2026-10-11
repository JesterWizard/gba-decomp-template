#!/usr/bin/env python3
"""Import one function into decomp-permuter's nonmatchings/ workdir.

Converts Luvdis nonmatching asm to `glabel` form, builds a semantic C seed
(m2c, cleaned, or existing readable src), then runs import.py.

Does not replace src/matched/*.c — integrate only after permuter score 0
and match_function.py MATCH.
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "decomp"))

from fnfiles import matched_file  # noqa: E402
from m2c_asm import m2c_decompile  # noqa: E402
from m2c_cleanup import cleanup_text  # noqa: E402
from opcode_stubs import is_opcode_stub  # noqa: E402

NON = ROOT / "asm" / "nonmatchings"
MATCHED = ROOT / "src" / "matched"
WIP = ROOT / "src" / "decompiled"
PERM = ROOT / "tools" / "decomp-permuter"
COMPILE_SH = ROOT / "tools" / "decomp" / "permuter" / "compile.sh"

# Per-function agbcc flags carried in a `/* match-flags: ... */` comment.
# Must stay in sync with match_function.py ALLOWED_MATCH_FLAGS, and with the
# whitelist in permuter/compile.sh.
MATCH_FLAGS_RE = re.compile(r"/\*\s*match-flags:\s*(.*?)\s*\*/")
ALLOWED_MATCH_FLAGS = frozenset({"-fprologue-bugfix", "-fomit-frame-pointer"})

# Must stay in sync with match_function.py MATCH_COMPILER_RE / COMPILERS, and with
# the `compiler` sidecar handling in permuter/compile.sh. pret/agbcc installs two
# compilers; a subset of functions only reaches retail with the older one.
MATCH_COMPILER_RE = re.compile(r"/\*\s*match-compiler:\s*(\S+?)\s*\*/")
ALLOWED_COMPILERS = ("agbcc", "old_agbcc")

_UNCOMPILABLE = ("?", "M2C_FIELD", "M2C_UNK", "BITCAST", "/* extern */")


def to_glabel_asm(function: str) -> str:
    src = (NON / f"{function}.s").read_text()
    lines: list[str] = []
    for line in src.splitlines():
        stripped = line.strip()
        if stripped.startswith("@") or stripped.startswith(".syntax") or stripped in (
            ".thumb",
            ".text",
        ):
            continue
        if stripped == f"{function}:":
            lines.append(f"glabel {function}")
            continue
        lines.append(line.rstrip())
    return "\n".join(lines) + "\n"


def clean_m2c(text: str) -> str | None:
    if not text or "M2C_ERROR" in text or "Decompilation failure" in text:
        return None
    # `*(expr)` without a type is invalid; wrap as u8* when it's a return of byte load.
    text = re.sub(
        r"return \*\(([^;]+)\);",
        r"return *(u8 *)(\1);",
        text,
    )
    text = text.replace("->unk", "->unk_")
    return text


def looks_uncompilable(body: str) -> bool:
    return any(tok in body for tok in _UNCOMPILABLE)


def match_flags(function: str, seed_text: str) -> list[str]:
    """Flags from the seed, else the parked/matched C for this function.

    The permuter preprocesses base.c before calling compile.sh, so the comment
    cannot be read at compile time — this is written to a `matchflags` sidecar
    that compile.sh picks up from the workdir.
    """
    texts = [seed_text]
    for path in (WIP / f"{function}.c", matched_file(function)):
        if path.is_file():
            texts.append(path.read_text())
    for text in texts:
        found = MATCH_FLAGS_RE.search(text)
        if not found:
            continue
        flags = [f for f in shlex.split(found.group(1)) if f in ALLOWED_MATCH_FLAGS]
        if flags:
            return flags
    return []


def match_compiler(function: str, seed_text: str) -> str:
    """Compiler from the seed, else the parked/matched C for this function.

    Like match_flags, this has to be a sidecar: the permuter preprocesses base.c,
    so compile.sh cannot read the comment itself.
    """
    texts = [seed_text]
    for path in (WIP / f"{function}.c", matched_file(function)):
        if path.is_file():
            texts.append(path.read_text())
    for text in texts:
        found = MATCH_COMPILER_RE.search(text)
        if not found:
            continue
        name = found.group(1).strip()
        if name in ALLOWED_COMPILERS:
            return name
        print(
            f"warning: unsupported match-compiler `{name}` for {function}; "
            f"allowed: {', '.join(ALLOWED_COMPILERS)}",
            file=sys.stderr,
        )
    return "agbcc"


def seed_c(function: str) -> str:
    wip = WIP / f"{function}.c"
    if wip.is_file():
        return wip.read_text()
    existing = matched_file(function)
    if existing.is_file() and not is_opcode_stub(existing):
        return existing.read_text()

    header = '#include "global.h"\n#include "ram_map.h"\n\n'
    m2c = m2c_decompile(function, valid_syntax=True) or m2c_decompile(function)
    if not m2c:
        raise SystemExit(
            f"no semantic seed for {function}: m2c failed and src is an opcode stub"
        )
    # Prefer the same cleaned seed the agent packet shows; the permuter can only
    # reshuffle correct C, so a m2c-valid seed that still has `?` types is worse
    # than a slightly less literal cleaned one.
    cleaned = cleanup_text(m2c, function)
    if cleaned.strip() and not looks_uncompilable(cleaned):
        return header + cleaned.rstrip() + "\n"
    fallback = clean_m2c(m2c)
    if fallback and not looks_uncompilable(fallback):
        return header + fallback.rstrip() + "\n"
    raise SystemExit(
        f"no semantic seed for {function}: m2c output is not compilable C"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("function")
    parser.add_argument(
        "--keep",
        action="store_true",
        help="keep existing nonmatchings/<function>* workdirs instead of a fresh import",
    )
    args = parser.parse_args()
    name = args.function

    if not (NON / f"{name}.s").is_file():
        print(f"missing {NON / name}.s", file=sys.stderr)
        return 1
    if not PERM.is_dir():
        print("run tools/decomp/permuter/setup.sh first", file=sys.stderr)
        return 1

    staging = ROOT / "build" / "permuter-import"
    staging.mkdir(parents=True, exist_ok=True)
    c_path = staging / f"{name}.c"
    s_path = staging / f"{name}.s"
    existing_workdirs = set((ROOT / "nonmatchings").glob(f"{name}*"))
    if not args.keep:
        # Stale workdirs force import.py into `<name>-2`, `<name>-3` … and the
        # permuter then runs on an out-of-date seed. Re-import is always fresh.
        for old in sorted(existing_workdirs):
            shutil.rmtree(old, ignore_errors=True)
            print(f"removed stale workdir {old.relative_to(ROOT)}")
        existing_workdirs = set()
    seed = seed_c(name)
    c_path.write_text(seed)
    s_path.write_text(to_glabel_asm(name))
    result = subprocess.run(
        [sys.executable, str(PERM / "import.py"), str(c_path), str(s_path)],
        cwd=str(ROOT),
    )
    if result.returncode != 0:
        return result.returncode

    matches = sorted(
        set((ROOT / "nonmatchings").glob(f"{name}*")) - existing_workdirs
    )
    if matches:
        workdir = matches[-1]
    else:
        workdir = ROOT / "nonmatchings" / name
        if not workdir.is_dir():
            print("import.py did not create nonmatchings/", file=sys.stderr)
            return 1

    shutil.copy(COMPILE_SH, workdir / "compile.sh")
    (workdir / "compile.sh").chmod(0o755)

    flags = match_flags(name, seed)
    flags_path = workdir / "matchflags"
    if flags:
        flags_path.write_text("\n".join(flags) + "\n")
    else:
        flags_path.unlink(missing_ok=True)

    compiler = match_compiler(name, seed)
    compiler_path = workdir / "compiler"
    if compiler == "agbcc":
        compiler_path.unlink(missing_ok=True)
    else:
        compiler_path.write_text(compiler + "\n")

    print(f"imported {name} -> {workdir.relative_to(ROOT)}")
    if flags:
        print(f"match-flags: {' '.join(flags)} (permuter compile.sh honours these)")
    else:
        print("match-flags: none")
    print(f"match-compiler: {compiler}")
    print(
        f"next: tools/decomp/permuter/permute.sh run {workdir.relative_to(ROOT)} "
        f"-j {os.cpu_count() or 4} --stop-on-zero"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
