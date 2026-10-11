# Contributing

There are two ways to work with this repository.

## Decompiling a game with the template

Clone it, drop in your `baserom.gba` and follow
[docs/new-game-checklist.md](docs/new-game-checklist.md). The loop is the same one pret
projects use: code starts out as assembly, a function is rewritten in C, and the build
must still produce a byte-identical ROM (`make compare` → `<FILE_NAME>.gba: OK`).
This template automates most of that loop:

1. `python3 tools/decomp/script_first.py` converts what patterns and cleaned m2c output can match.
2. `python3 tools/decomp/agent_packet.py --next` prints a compact context packet for the next leftover function.
3. Write the C, check it with `python3 tools/decomp/match_function.py`, land it with `integrate_c.py`.
4. Near misses are parked with `park_wip.py` in `src/decompiled/`; never throw unmatched C away.

Read [docs/lessons/agbcc-matching-tricks.md](docs/lessons/agbcc-matching-tricks.md) before
fighting a same-size diff, and [docs/lessons/workflow.md](docs/lessons/workflow.md) before
reaching for the permuter.

## Improving the template itself

- **Stay game-agnostic.** No hardcoded ROM/RAM addresses, symbol names or struct layouts
  from a particular game in `tools/`. Read them from `baserom.gba`, `project.mk` or the
  analysis DB instead.
- **Test on a real ROM.** CI only checks syntax, because a template has no baserom. Run the
  day-zero path from the checklist on at least one game and say which in the PR.
- **Matching C is C89** and follows `.clang-format` (Allman braces, 4-space indent).
- **Write lessons down.** A codegen trick that cost you an afternoon belongs in
  `docs/lessons/` as symptom → cause → the C that fixed it.
- Never commit ROMs, `.elf`/`.map` outputs, or extracted game assets.

By contributing you agree that your contribution is licensed under the [MIT License](LICENSE).
