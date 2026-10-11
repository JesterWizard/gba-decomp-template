# New game checklist

From an empty clone to the first semantic-C batch. Everything below is verified: the
day-zero path (header → scaffold ROM → 633 opcode stubs → `make compare OK` → one
`script_first.py` MATCH integrated) was smoke-tested on the Beyblade G Revolution ROM
before this template was cut.

## 0. Prerequisites

```bash
sudo apt install -y build-essential git python3 libpng-dev binutils-arm-none-eabi gcc-arm-none-eabi
cp /path/to/clean_dump.gba baserom.gba      # gitignored; never commit it
```

## 1. Toolchain (once per machine/checkout)

```bash
bash build_tools.sh      # agbcc + old_agbcc (pret/agbcc), Luvdis, m2c, decomp-permuter
```

`tools/agbcc`, `tools/luvdis`, `tools/m2c`, `tools/decomp-permuter` are git-ignored.
If the game was built with a different compiler (check strings / function prologues
against pret projects: agbcc vs. `old_agbcc` vs. SDK gcc 2.9x), see "Compiler" below.

## 2. Day zero

```bash
./init_project.sh --name my_game --game-name "My Game"
```

Reads the cartridge header, writes `project.mk` + `rom.sha1` + `<name>.toml`, emits the
scaffold ROM (whole baserom as one `.incbin`), runs Luvdis into `asm/nonmatchings/`, and
runs `make compare` (must print `<name>.gba: OK`). Then:

```bash
python3 tools/decomp/bootstrap_stubs.py          # one byte-exact opcode stub per function
make compare
python3 tools/scan_ram_literals.py --emit-asm && python3 tools/scan_ram_literals.py --emit-h
make analyze queue scores symbols tier           # analysis DB + work queue
python3 tools/decomp/script_first.py 40          # first deterministic batch
make compare
```

Expect a handful of MATCHes from `script_first.py` at first (trivial getters/setters);
the early ceiling rises as you add prototypes to `include/unknown-functions.h`, struct
fields to `include/unknown-types.h`, and named RAM/ROM symbols.

## 3. Things that are game-specific — fill these in

| Item | Where | Notes |
|---|---|---|
| Header fields, output name | `project.mk` | `init_project.sh` does it |
| RAM map | `asm/ram_map_{iwram,ewram,sram}.s`, `include/ram_map.h` | stack top, heap, save medium (SRAM/Flash/EEPROM) |
| Group rules | `GROUPS` in `tools/decomp/groups.py` | name-prefix → `src/<group>.c`; start empty, add as names appear |
| Name vocabulary | `docs/decomp-pipeline.md` § Vocabulary | use the game's own words; evidence-backed |
| ROM size / layout | automatic from baserom size | 4/8/16/32 MB all handled by `gen_rom_layout.py` |
| Engine/library functions | `docs/lessons/` | Recognise Nintendo/Gax/EEPROM/Flash libs early; they are matchable with known sources |

## 4. Compiler

Default is pret `agbcc` (`-O2 -mthumb-interwork -fhex-asm`) with `old_agbcc` selectable per
function (`/* match-compiler: old_agbcc */`). Some functions need `-O1`
(`/* match-flags: -O1 */`), EEPROM/flash library code frequently does. If most functions
mismatch systematically, the game likely used another compiler — settle that before
investing in C.

## 5. Session loop

See `CLAUDE.md`. Short form: `report_status.py` → `make compare` → `script_first.py 5` →
`agent_packet.py --next` (max one attempt, then `park_wip.py`) → report →
`tools/notify_done.sh`.

## 6. Known sharp edges

- `make tidy`/`clean` removes `build/` and the ROM only; manifests live in `analysis/`.
- A fresh clone needs `bash build_tools.sh` and `generate_asm.py` (nonmatchings are
  git-ignored) before `script_first.py` has targets; `make` itself works from tracked files.
- Mods/hooks (`mods/`, `tools/mod/`, `tools/gfx/`) were deliberately **not** carried over;
  they are a separate layer built on a finished decomp. See the Beyblade repo for the design.
