@ =============================================================================
@ EWRAM occupancy map (provisional — rescan baserom before relying on pool)
@ =============================================================================
@ Hardware window: 0x02000000 – 0x02040000 (256 KiB)
@ Format: SET_ARRAY name, start, size   @ kind: evidence
@ kind = heap | stack | bios. Read by tools/ram_coverage.py (docs/ram-coverage.md).
@ =============================================================================
