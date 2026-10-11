# Installation

## Dependencies (Debian/Ubuntu/WSL)

```bash
sudo apt update
sudo apt install -y build-essential git python3 libpng-dev binutils-arm-none-eabi gcc-arm-none-eabi
```

Optional: install [devkitPro](https://devkitpro.org/wiki/Getting_Started) `gba-dev` and ensure `DEVKITARM` is set. The Makefile prefers `arm-none-eabi-*` on `PATH`.

## Baserom

Place a clean dump of the target game in the repo root as:

```text
baserom.gba
```

Confirm header fields (and update the Makefile if needed):

```bash
python3 tools/decomp/print_header.py
```

`./init_project.sh` records its SHA1 in `rom.sha1`.

## Build tools (optional at scaffold stage)

```bash
make tools
```

This sparse-clones [pret/pokeemerald](https://github.com/pret/pokeemerald) and builds `gbafix`, `scaninc`, `preproc`, `ramscrgen`, and `gbagfx`.

## Install agbcc (needed once you compile matching C with `make`)

```bash
git clone https://github.com/pret/agbcc ../agbcc
cd ../agbcc
./build.sh
./install.sh "$OLDPWD"
cd "$OLDPWD"
```

## Build / compare

```bash
make compare     # builds and checks rom.sha1 (vanilla rebuild)
```

## AI decompilation toolchain

```bash
bash build_tools.sh               # agbcc, Luvdis, m2c — no API key needed
python3 tools/decomp/script_first.py
python3 tools/decomp/agent_packet.py --next
```

See [README.md](README.md) § Decompilation and [CLAUDE.md](CLAUDE.md).

## decomp-permuter (agbcc matching)

For functions whose C is the right logic but agbcc emits a different literal-pool or instruction order:

```bash
tools/decomp/permuter/setup.sh
tools/decomp/permuter/permute.sh import sub_08001234
tools/decomp/permuter/permute.sh run nonmatchings/sub_08001234 -j 4 --stop-on-zero
```

On score 0, copy the winning `output-0-*.c` over `src/matched/sub_XXXXXXXX.c` and `python3 tools/decomp/match_function.py` + `integrate_c.py --kind semantic`.
