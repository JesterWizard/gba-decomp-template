# Single source of truth for per-game settings. Read by the Makefile and by
# tools/decomp/projcfg.py (simple `NAME := value` lines only, no expansion).
# `./init_project.sh` overwrites this from the baserom header.

# Output name: <FILE_NAME>.gba / .elf / .map, symbol TOML <FILE_NAME>.toml
FILE_NAME  := mygame
# Display name used in reports and notifications
GAME_NAME  := My Game

# GBA header fields (`python3 tools/decomp/print_header.py`)
TITLE      := MYGAME
GAME_CODE  := ABCE
MAKER_CODE := 01
REVISION   := 0

# Optional: ROM address of libgcc __divsi3 (the `bl` target of a signed `x / n`).
# `_call_via_rN` thunks are found in the baserom automatically (tools/decomp/libgcc.py).
DIVSI3_ADDR :=
