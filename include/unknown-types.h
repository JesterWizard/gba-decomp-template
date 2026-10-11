#ifndef GUARD_UNKNOWN_TYPES_H
#define GUARD_UNKNOWN_TYPES_H

#include "gba/types.h"

/*
 * Shared layouts for still-unnamed objects. Counterpart to unknown-functions.h.
 *
 * Rules:
 * - A struct here is a superset. Adding a field is fine; moving one is not.
 *   Offsets, member types, and sizeof are load-bearing — agbcc picks the
 *   instruction from the member type and the stride from the size.
 * - filler_XX is unexplored space; unkXX is a field something actually accesses.
 *   Narrowing a filler into a field is the normal way this grows.
 * - Prefer `a->unkA0 = v` over `*(u16 *)((u8 *)a + 0xa0) = v`.
 * - Do not mark stores volatile unless the ROM kept extra narrowing
 *   (lsl #24; lsr #24 before strb). Do not use `register` or `asm volatile`
 *   to force registers.
 * - merge structs only when two functions are shown to share an object.
 */

#ifndef MODERN
#define MODERN 0
#endif

#if !MODERN
#define STRUCT_PAD(from, to) unsigned char _pad_##from[(to) - (from)]
#else
#define STRUCT_PAD(from, to)
#endif

/* Add structs here as functions are decompiled (see rules above). */

#endif // GUARD_UNKNOWN_TYPES_H
