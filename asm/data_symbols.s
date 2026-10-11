@ =============================================================================
@ Data symbols referenced by decompiled C (see include/data_symbols.h)
@ =============================================================================
@ Single source of truth for match_function.py / compile_matched.py, which pass
@ these to the assembler as --defsym so the .text blob matches retail pools.
@ SET_DATA pins RAM/IO; SET_ROM_DATA is a no-op in ram_map.s because
@ gen_rom_layout.py emits the ROM labels in the peel.
@
@ SET_ROM_DATA gData_08091004, 0x08091004
