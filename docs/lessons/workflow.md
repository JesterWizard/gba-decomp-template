# Workflow lessons

Process lessons from the Beyblade G Revolution decomp. Each has a *why* so you can
judge edge cases.

## Matching

- **Root-cause, don't chase.** When a same-size DIFF remains: (1) decode both sides with a
  normalised objdump diff, (2) sweep small *semantically meaningful* source shapes with the
  0.1 s `match_function.py` loop (or `test_variants.py`), (3) bisect by truncating the
  function, (4) read allocator dumps (`-dl -dg`, see agbcc-matching-tricks). Park with notes
  only if that fails. *Why:* hand-reordering statements and long permuter runs (240 s+)
  burned hours and produced non-semantic C; the real answers always came from the dumps.
- **Bounded permuter only** (`permuter/auto.py`, 60 s, one at a time — a second instance
  reaps the first). Read `nonmatchings/<fn>/output-N-*` early: low-score diffs often show a
  one-token type fix (`u8` → `int`, `s32` → `s16`).
- **Score under both compilers** (`agbcc` and `old_agbcc`); a register-destination DIFF on a
  load/shift is often an `old_agbcc`-only match (`/* match-compiler: old_agbcc */`).
- **Data symbols first.** Retail addressed globals/ROM tables through symbols, not literals;
  a literal changes pool sharing and CSE. Add `SET_DATA`/`SET_ROM_DATA` in
  `asm/data_symbols.s` plus an extern in `include/data_symbols.h`.
- **Never accept without `make compare`.** `make audit` finds matched C that does not even
  compile (matched C is not linked by `make compare` until it is in the layout).

## Repo hygiene

- **Manifests are tracked.** `analysis/matched.json` and `analysis/semantic_verified.json`
  are the identity/verification records. The original project kept them under `build/` and
  lost them to a `make tidy`; recovering took a reconstruction pass. Keep generated-and-
  ignored things regenerable, tracked things in tracked directories.
- **`asm/matchings/` is tracked** (sizes for gap peels); `asm/nonmatchings/` is regenerated
  from the ROM (`generate_asm.py --force`).
- **`prune_drafts.py --apply` has no per-function filter.** It wipes every superseded draft,
  including the user's own uncommitted work. Dry-run first; delete only your own drafts and
  call `queue_toml.remove_blocks({...})` for them.
- **Renames go through the tools.** `symbols.py set` → `fnfiles.py sync --apply` (renames
  `src/matched/sub_X.c` → `<Symbol>.c`, fixes `rom_layout.ld`); `rename_struct.py` for
  struct/member names (compiler-driven, because `unkNN` repeats across structs). A plain
  text replace corrupts `asm("...")` literals. Never assume `path.stem` is the function
  name — use `fnfiles.name_for/matched_file/stem_for`.
- **After a struct rename batch:** `audit_c_compiles.py --dirs matched` / `--dirs decompiled`,
  `matched_rescore.py --kind semantic`, then `make analyze document`; keep a baseline of
  known failures so regressions are visible.

## Emulator / save testing (if you add mods or runtime tests)

- `Emu(rom)` without an explicit `.sav` uses the repo-root real save and **clobbers it**.
  Always pass a copy.

## Agent etiquette (user preferences carried over)

- Hands-off batches; commit only when asked and never with a failing `make compare`.
- Run `tools/notify_done.sh "<game> decomp" "<summary>"` as the last step of any task.
- Always run `make` after changes and say so explicitly, with the result.
