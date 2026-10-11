# Architecture

A commercial GBA ROM (`baserom.gba`, never committed) is decompiled into matching C.
Every build must reproduce the retail ROM bit for bit (`make compare` → `<FILE_NAME>.gba: OK`).

## The mental model

1. `baserom.gba` is the unmodified retail ROM. It is never edited directly.
2. `src/matched/*.c` (and the grouped `src/<group>.c` files) hold decompiled functions.
   `make` compiles each one with agbcc (per-file `match-compiler` / `match-flags`
   comments) and places its `.text` at its retail address.
3. `asm/` supplies the rest of the image: `rom.s` (head at 0x08000000), then
   `rom_layout.ld` packs matched `.text` and gap `.incbin`s in order (`SUBALIGN(2)`).
   Functions land at retail addresses only while they keep retail sizes.

## Directory map

| Path | What's in it |
|---|---|
| `project.mk` | Per-game settings (output name, header fields). Read by the Makefile and `tools/decomp/projcfg.py`. |
| `src/<group>.c`, `src/matched/` | Matched C. Groups (`groups.py`) are the authoring view; `src/matched/` is the inbox. `build/split/` is the generated one-file-per-function view the compiler sees. |
| `src/decompiled/` | Unmatched C seeds + notes (the DECOMPILED tier). Not linked. See `docs/decomp-wip.md`. |
| `analysis/` | Analysis DB (functions, xrefs, structs, systems, symbols) **and the tracked manifests** `matched.json` / `semantic_verified.json`. Never under `build/`: `make tidy` would delete them. |
| `include/*.h` | Types (`unknown-types.h`), prototypes (`unknown-functions.h`), generated `symbols.h`, `ram_map.h`, `data_symbols.h`. |
| `asm/` | `rom.s`, `rom_tail.s`, `rom_gap_*.s` (generated peel), `rom_layout.ld`, `matchings/` (byte-exact sizes, tracked), `nonmatchings/` (Luvdis output, regenerated), `ram_map*.s`, `data_symbols.s`. |
| `docs/` | Pipeline notes, lessons, generated system/function docs, progress counter. |
| `tools/decomp/` | The matching pipeline. `tools/agbcc`, `tools/luvdis`, `tools/m2c`, `tools/decomp-permuter` are fetched by `build_tools.sh` and git-ignored. |

## Matching

`make compare` checks `rom.sha1` against the retail dump. Growing or shrinking a
function slides later peels; `make shift-test` inserts 0x1000 after `.rom_head`,
`make grow-test` inserts 4 bytes after the first matched `.text`, to prove which
pointer words are relocations (`.4byte`) and which are data. Function-entry words and
`gData_*` table words in gap/tail peels are `.4byte`. Dense graphics-like `0x08……`
clusters stay absolute.
