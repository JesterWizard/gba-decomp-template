@ =============================================================================
@ IWRAM occupancy map (provisional — rescan baserom before relying on pool)
@ =============================================================================
@ Hardware window: 0x03000000 – 0x03008000 (32 KiB); top ~0x300 bytes are the
@ user/IRQ/SVC stacks (verify in the game's startup code).
@ Rescan: python3 tools/scan_ram_literals.py [--emit-asm]
@
@ Named symbols: SET_DATA name, addr   /   SET_ARRAY name, addr, size
@ =============================================================================
