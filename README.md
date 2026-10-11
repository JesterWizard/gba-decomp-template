# GBA matching-decomp template

A ready-to-run scaffold for **byte-matching decompilation of a Game Boy Advance game**
with agbcc, distilled from the Beyblade G Revolution project (633 functions, 400+
commits of tooling and hard-won lessons). It is built to be driven by an autonomous
coding agent (see [CLAUDE.md](CLAUDE.md)) but works fine by hand.

What you get:

| Layer | Contents |
|---|---|
| Day-zero bootstrap | `./init_project.sh` (header → `project.mk`, scaffold ROM that already passes `make compare`, Luvdis disassembly) and `bootstrap_stubs.py` (one byte-exact opcode stub per function) |
| Matching loop | `script_first.py` (patterns + cleaned m2c), `agent_packet.py`, `match_function.py` (0.1 s compile + diff), `integrate_c.py`, permuter glue, `park_wip.py` for near-misses |
| Analysis DB | `analyze.py` → `analysis/*.json` (call graph, RAM refs, structs, subsystems), `symbols.py` (evidence-backed names), `document.py` (generated docs) |
| Repo plumbing | Per-function objects at fixed VMAs (`rom_layout.ld`), group files (`src/<group>.c`), content-addressed object cache, shift/grow tests that prove which pointer words are relocations |
| Agent rules | `CLAUDE.md`, `.cursor/rules`, `.cursor/skills` |
| Lessons | [docs/lessons/agbcc-matching-tricks.md](docs/lessons/agbcc-matching-tricks.md) (~170 lines of codegen tells), [docs/lessons/workflow.md](docs/lessons/workflow.md) |

## Quick start

```bash
git clone <this repo> my_game_decomp && cd my_game_decomp
cp /path/to/clean_dump.gba baserom.gba
bash build_tools.sh
./init_project.sh --name my_game --game-name "My Game"
python3 tools/decomp/bootstrap_stubs.py && make compare     # my_game.gba: OK
make analyze queue scores symbols tier
python3 tools/decomp/script_first.py 40 && make compare
```

Details, the list of game-specific files to fill in, and sharp edges:
[docs/new-game-checklist.md](docs/new-game-checklist.md).

## Layout

See [docs/architecture.md](docs/architecture.md) and
[docs/decomp-pipeline.md](docs/decomp-pipeline.md). Examples in the docs use function
names and addresses from the original Beyblade G Revolution project.

## Not included (on purpose)

The mod layer (`mods/`, hook patcher, emulator harness, graphics extractors) and all
Beyblade-specific data, names, structs and RAM maps. Those belong on top of a finished
decomp, not in the template.

## Known limitations

- ROMs are assumed to be Thumb-heavy agbcc builds with Luvdis-discoverable functions.
  Games compiled with another toolchain, or with large ARM-mode sections, need extra work
  in `generate_asm.py` / `gen_rom_layout.py`.
- Bootstrapped on one game only; expect small portability bugs (the first run found two:
  a wrong `ROOT` in `generate_asm.py` and a hardcoded 4 MB ROM size, both fixed here).
