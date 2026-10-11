# agbcc matching tricks

Codegen tells that pointed to the right C, collected over ~100 hard functions in the
Beyblade G Revolution decomp (function names/addresses below are that project's, kept
as worked examples). **Read this before spending time on a same-size or size DIFF.**
Append new entries as you learn them: symptom → cause → the C that fixed it.

Learned while matching size-DIFF / WIP functions (2026-09-27):

- **Default to data symbols.** Retail used real symbols for globals and ROM tables. A `*(T **)0x0300xxxx` macro or `(T *)0x08xxxxxx` literal changes pool sharing, constant folding (`base+0x80` folded into one literal) and reload/CSE behaviour. Add `SET_DATA gData_X` in `asm/data_symbols.s` plus an extern in `data_symbols.h`. This alone fixed sub_080474AC, sub_0802FA94, sub_08033188, sub_08045D3C and sub_08035D68.
- A global pointer that is not reloaded after a u16/u32 struct store (but is reloaded after a u8 store) is a scalar symbol (`extern T *gData_X;`), not `gData_X[0]`.
- A table base kept as `base + 0x18` across a loop is a typed struct-array symbol, not a u8 array cast.
- `_08073C40/44/48/4C` are libgcc `_call_via_r0..r3` thunks. Write the source as a function-pointer call (`((void (*)(T *))p->cb)(a)`) and let the compiler choose the register.
- Stack param loaded at entry with no truncation, only used as `x & 3`: it is a `u8` param.
- `muls` by a constant materialized after a call: the constant came from a local variable.
- A grouped `(expr | CONST)` or `(a - 1) + b` that agbcc re-associates can be pinned with an inline assignment `(t = expr | CONST)`.
- A giv counter such as `y = 0x40; y += 16` that retail spills to the stack is usually written as `i * 16 + 0x40` in the source.
- Callers built against an older prototype use a cast macro at the call site (`#define f(a,b,c) ((void (*)(s8, s8, u8))f)(a,b,c)`).
- Permuter output dirs (`nonmatchings/<fn>/output-N-*`) are worth reading early: low-score diffs often show a one-token type fix (e.g. `u8 flag` → `int flag`, `s32 index` → `s16`).
- Only one `permuter/auto.py` can run at a time. A second one reaps the first.

- Block-scoped temporaries matter: `{ s32 *pos = f(); ... }` inside the if matched sub_080436B0 where a function-level `pos` got an extra copy.
- Splitting a compare into separate statements (`off = ...; end = ...; lookup = base + off;`) fixed instruction order in sub_08068598.
- A missing `return` on one path (retail UB) can be the match: sub_080739E8 returns the NULL arg by falling off the end.
- `-O1` functions (EEPROM code, sub_08067504/sub_08067584): the permuter's compile.sh ignores `-O1`; add it by hand in nonmatchings/<fn>/compile.sh and run tools/decomp-permuter/permuter.py directly.

- `x / n` compiles to `bl __divsi3`; match_function.py now maps it to retail `_080740B0`, so plain `/` matches (sub_08072A38).
- Retail loading a mask constant into a register before the load (`movs r4,#0x1F; ands r4,r1`) = constant in a local: `r = 0x1F; r &= color;`.
- Duplicated param copies (arg kept in a reg and on the stack) mean two locals: `e1 = e; e2 = e;` one per call site (sub_08069270, still unmatched).
- Typed prototypes (u16/u8 params, struct pointers) instead of `void *`/u32 + local copies often fix param register order; check callers still match.

**Why:** each of these took many variants to find.
**How to apply:** check these first when a draft is a size DIFF.

Added 2026-09-28 (parked-WIP retry, 6/10 matched):
- **Register-priority debugging:** compile with `-dl -dg` and read `x.i.lreg` ("Register N used R times across L insns") and `.greg` (conflicts, preferences, dispositions). Global alloc order = floor_log2(R)*R/L. In pass 0, find_reg skips regs other conflicting allocnos prefer *and* regs that are not yet live. Refs are counted after CSE, so literal 0s that CSE folds into a zero variable still count as its refs.
- **Same variable in different regs in two parts of a function** means two pseudos: use a block-scoped second set of locals (sub_08030F38).
- **`cmp rX, rY` against a constant too big for an immediate** (e.g. 0x100) means the constant came from a variable (`step = 0x100`); a literal becomes `cmp #0xff`.
- **Retail reloads addresses after a join where ours keeps them in r8+:** `-fcse-skip-blocks` carried them across. An assignment inside the condition, `if ((flag = a != NULL) || b != NULL)`, breaks the skip (sub_08062F90). Test the theory with `-fno-cse-skip-blocks`.
- **Loop "found" blocks ending in `return` get moved out of the loop** by loop.c `find_and_verify_loops` unless a label, jump or loop note sits inside the block (sub_08038438, unsolved).
- All EEPROM library functions (0x080674xx-0x080677xx) need `/* match-flags: -O1 */`.
- Pointer init order: `&buf[n + 0x43]` then `ptr--` gave `(n*2 + sp) + 0x84` operand order; `&buf[n + 0x42]` did not.
- **`ldr base; add #0x80; ldr [r0]` for a global field beyond ldr's 124-byte immediate:** the global is a struct *symbol* (`gData_X.unk80`). A literal-address macro folds to a single constant (sub_08043C70).
- **Retail keeps `asr` on an s16 before a subtract** (ours drops it): compute into an `s32` temp first, `s32 v = (s16)x - step; x = v;` (sub_08065CD0).
- **Narrowing a callee's params breaks callers** that pass wider values: keep the prototype params `u32` and narrow into `u8`/`u16` locals in the body. It gives identical callee code (sub_08061EF8, sub_08043C70).
- **Run `make audit` after changing prototypes:** naked readable-Thumb stubs with the old signature break the compile, but `make compare` doesn't notice. `make repair-signatures` fixes them.

Added 2026-09-28 (final sweep, +11):
- **`make compare` never compiles `src/matched/*.c`** (C_SRCS is empty; the ROM links asm/matchings). After any header/type/symbol change, re-verify all semantic C with `python3 tools/decomp/matched_rescore.py --kind semantic --jobs 4`. 3 known pre-existing non-matches: sub_08038314, sub_0807309C, sub_08047594.
- **`(base + K) + i*size` vs `ldrh [x, #K]`:** gcc adds the field offset to the base first only when the field's mode alignment equals the element alignment. An `s16` read of a 4-aligned element folds. Retail read an **s32 field narrowed to s16**, which gives `ldrh` with the pre-add (sub_0806F05C/6EEC8).
- **Extern `u8 gData_X[]` stores expand as bit-field (and 0 | v) RTL** and change CSE/reassociation. When a byte global is a scalar, declare it `extern u8 gData_X;` (sub_08068BD4, 03000108/1B0/1A8).
- **Zero register shared by NULL stores and a later pointer local** (`movs r4,#0` early, `str r4` after frees, later `r4 = icon`): initialise the pointer local to NULL at that point (`icon = NULL;`) (sub_0804D420, sub_08056BA4).
- **Table base loaded before the index** for a `u8 *[]` string table: use a local `strings = (u8 **)gData_X; strings[idx]` (sub_08053690). For struct arrays inside loops this was NOT solved (sub_08044648/447E8: a local gets hoisted by loop.c).
- **Retail merges two switch cases mid-block** (`ldr r1,=A; b shared`): write both cases in full with identical tails (a macro is fine). jump2 cross-jumping produces the merge; a `goto` does not (sub_08054120).
- **Param copied before narrowing another param** (`adds r7,r0` first): take the struct pointer as the typed parameter, not `void *` plus a local, and cast at the callers (sub_08068BD4/68A08).
- **Early exits that jump straight to the epilogue with r0 already 0:** the source fell off the end with no return (sub_08070930).
- The sprite-group functions around 0x080709xx/0AF8 want old_agbcc.

Added 2026-09-29 (sub_0806B764 matched; 08067CE8/0806E060/08060E48 near):
- **Diff workflow that works:** compile scratch with `cc -O2`, assemble both retail `asm/nonmatchings/<fn>.s` and ours, `objdump -d -M force-thumb`, strip addresses, `diff`. Normalising registers to `rX` (`sed -E 's/\br[0-9]+\b/rX/g'`) separates structural diffs from regalloc diffs. `match_function.py`'s byte % is useless for size-mismatch tuning; the permuter score is noisy (thousands) until sizes are equal.
- **Try `old_agbcc` first** for anything near 0x0806xxxx text/sprite code: sub_0806B764 jumped 31% -> 61% just from the switch. Check a 3-line mini test (`w->penX += w->spacing`) under both compilers against the retail prologue to pick the compiler.
- **`vu16 *reg` for a pointer returned by a register accessor** (`BgGetCntReg`): retail loads `ldrh` before materialising the `0x80` mask; a plain `u16 *` puts `movs #0x80` first. Only volatile flips it.
- **`int pin; ... (pin = base + (start << 5))` inside a sum** stops agbcc reassociating `(charBlock << 14) + (0x06000000 + (start << 5))` (permuter found it: score 790 -> 230; combined with s32 loop counters it matched).
- **Loop counters `while (n-- != 0)` must be signed `s32`**, unsigned makes agbcc compare against -1 after pre-decrement.
- **`u8 a1 = ...; ... (mask & 3)` constant that keeps its `lsls/asrs` sign-extension** in retail = mask lives in a local `m3` (`(x & (m3 = 3))` at first use, later `& m3`). A literal 3 lets combine drop the sext.
- **Stack locals passed by address to a callback can be bigger than what you read** (sub_08067CE8: `s32 out[3]` although only [0],[1] read); frame size tells you.
- **A struct-typed prototype in unknown-functions.h** (not `void *`) avoids a param alias copy (`adds r2,r4,#0` at entry).
- **Free-path-before-draw layout:** `if (!visible) { free; return; }` with the draw code inline afterwards, not `if (visible) {draw} else {free}`.
- `pkill -f` from Bash kills your own shell (pattern matches the command line): kill by pid from `pgrep`.
- `prune_drafts.py --apply` was blocked by the auto-mode classifier; stale draft for a landed function has to be pruned by the user.

Added 2026-09-29 (parked-WIP sweep):
- **Score every parked draft under BOTH compilers before hand-tuning.** sub_08045C5C sat at 127/136 (agbcc) through several sessions; the same source is 136/136 under old_agbcc. Cheap sweep: strip/add the `match-compiler` line and run match_function.py on each draft (also on older `git show <rev>:` revisions).
- `-fno-gcse` / `-dG` dump: agbcc runs PRE gcse; "PRE/HOIST: end of bb N" copies of an address load explain an unexpected `adds rX, r0, #0` copy before a compare.
- auto.py's `reap_stale_permuters` SIGKILLs any `permuter.py` launched by absolute path from another process tree (e.g. a second agent). Launch by relative path (`python3 tools/decomp-permuter/permuter.py nonmatchings/<fn>`) to coexist.
- **Constant kept in a stack slot / not rematerialised** (sub_08043DB4, solved by permuter): write a neighbouring test so it uses the same constant, e.g. `if (ok > (0 - 1))` instead of `ok >= 0` next to `none = -1;`. The shared -1 pseudo loses its REG_EQUIV and spills like retail.
- `agent_packet.py` (even `--help`) also runs reap_stale_permuters and kills another session's live permuter workers. Don't run it while another agent is permuting.
- **Spill slot order follows declaration order** (sub_0806C7D4, 91% -> 100%): stack slots for spilled pseudos go in pseudo-number order, i.e. the order locals are declared. Read retail's sp offsets, then declare function-level locals in that order (loop-scoped declarations came out in the wrong order).
- Reusing one local for two sweeps (y then x) forces it to the stack; retail kept the second sweep in registers, so it had separate locals.

Added 2026-10-01 (sub_08040680 matched after a long hunt):
- **Copy-from-r0 quantities allocate first.** local-alloc.c (source at ../agbcc/gcc) sorts qtys with hard-reg suggestions ahead of the rest, so a call result copied `(set p (reg r0))` grabs r0 and pushes later temps (store address) to r1. Retail had the result in r1 and the address in r0 -> the result stayed live past the next `r0 = arg` set, i.e. it was passed as an extra (ignored) argument to the next call: `_080408E4(value, buf)`. Any "result in r1, address in r0" swap: look for a later call the value silently rides into as arg 2/3.
- Source for the compiler is in ../agbcc/gcc (local-alloc.c, global.c); read it instead of guessing; `-dl -dg` dumps + QTY_CMP_PRI = floor_log2(refs)*refs*size/life.

**Debug agbcc build (2026-10-01):** `/tmp/v/agbcc_dbg/gcc/agbcc` = copy of ../agbcc built with `ALLOCDBG=1` traces (local-alloc sugg/priority passes: qty regs/birth/death/refs/pri/-> reg; global alloc order per pseudo). Rebuild: `cp -r ../agbcc /tmp/v/agbcc_dbg && make -C gcc` and patch fprintf into local-alloc.c (~line 1359/1415) and global.c (~line 580). Output is byte-identical to tools/agbcc/bin/agbcc apart from -g. /tmp is volatile: rebuild if missing.
- Loop-depth weighting works as a priority knob: a `do { stmt } while (0);` around a statement multiplies refs of pseudos referenced inside (used on sub_08038D68: 86 -> 104/112). Priority = floor_log2(refs)*refs*size/len, so crossing a power of two (refs 8, 16) is what flips order.
- Big-constant address adds (`a + 0x2FC`) are NOT pseudos: `const_int` inside `plus`, reload picks the scratch via order_regs_for_reload (first call-used reg with no live pseudo, r0..r3), then reload_cse_move2add turns a second `movs r1,#0x300` into `adds r1,#4` when r1 still holds 0x2FC. Retail using a different scratch (r3) means some pseudo in the lower scratch reg was live across that insn.

Added 2026-10-01 (sub_08038D68 matched after hours of reload-scratch chasing):
- **Scratch register of a big-constant add (r1 vs r3) is decided by the function-wide reload spill list**, not per insn: finish_spills builds `spill_regs` = union of every chain's spill regs, and allocate_reload_reg round-robins through it from `last_spill_reg`. r3 appears in retail's list only if some other insn *reloads* a constant (r0-r2 busy). If ours keeps that constant as a shared pseudo, the list is {r1} and earlier adds all use r1 (+ move2add `adds r1,#4`).
- **Constant forced into a pseudo (expand_binop, cost>2) is CSE-shared across stores** (cse and cse2). `(x << 11) + 0x7800` twice = one pseudo. Source written as `(x * 8 + 0x78) << 8` has no big constant until combine pushes the shift through the plus, so each use reloads it (inheriting the reg). Look for `(a + small) << n` / `(a + small) * 2^n` whenever retail re-materialises a big constant at each use.
- Debug-build hack knobs (in /tmp/v/agbcc_dbg, volatile): env `NOCV=<int,..>` stops combine merging a const set, `NOCSEK=<int>` makes cse skip const sets, `RLDBG=1` prints reload needs/live sets. Running the experiment that makes retail match (NOCSEK) then asking "what source gives that RTL" found it fast. Rebuilding the dbg compiler while a parallel search runs kills the search (binary replaced).

Added 2026-10-01 (sub_080447E8 matched; sub_0803E0CC analysed):
- **Always try `/* match-compiler: old_agbcc */` on a draft first** (sub_080447E8: 98.9% -> 100%): agbcc ties a byte load to its shift result (`ldrb r1; lsl r1,r1`), old_agbcc keeps them apart as retail does. Several verified matched functions (sub_08062790) rely on it. `/tmp/v/agbcc_dbg_old/gcc/agbcc` is the OLD compiler source (the `old_agbcc` file in that dir is stale).
- **Two pseudos that share one local (`def` used in two branches) get refs/priority summed**; retail used separate variables per branch -> different hi-reg assignment. And `tbl = gData_X; def = &tbl[id];` makes the symbol load precede id*28 (table-base-first) while other field reads still use the symbol directly.
- Global alloc facts (global.c): order = int(floor_log2(refs)*refs/len*10000) then pseudo number; callee-saved lo regs first, then caller-save (only if 4*calls < refs) *before* the alt (hi-reg) class pass; hi regs are handed out r8,r9,r10 in allocation order. A reload eviction (retry_global_alloc) can re-home a pseudo later. Reload scratch = lowest `uses` (sum of refs of pseudos live in that reg), ties by regno; final scratch picked round-robin over the function-wide spill list.
- Debug-compiler env hooks used (volatile, /tmp/v/agbcc_dbg*): REFADJ, NOCS, NOLOCAL, NOTIE, SPILLEQ, NOCV, NOCSEK, RLDBG, ALLOCDBG. Searching "what single hack makes retail match" first is much faster than blind source mutation.

- **Check DebugPrint (sub_08067B98) format strings for hidden varargs** (sub_0803E0CC, solved after hours of allocator archaeology): read the string at the r0 literal in baserom; `%d`/`%s` means extra args in r2/r3 that retail sets with no visible move when the value already sits there. An unexplained value "alive" in r2/r3 across to a call, or an unused `add sp,#-4` caller-save slot, is the tell.
- Reload evicts the pseudo whose hard reg has the lowest summed REG_N_REFS among live pseudos (order_regs_for_reload); an evicted caller-saved pseudo is re-homed by retry_global_alloc after the others, and its stack slot stays allocated but unused.
- `pkill -f`/`pgrep -f` with a plain pattern matches the calling shell too: use `pgrep -f "tmp/v/[g]s.py"`.
- **Flag variable kept in a stack slot (`str 1,[sp]` then `ldr/cmp`)**: write the loop body as `if (ok) { body } else done = TRUE;` so the done=1 block comes after the body. With `if (!ok) done = TRUE; else {...}`, cse threads it to the exit and `done` disappears (sub_080737C0).
- **A value that retail re-reads from its stack slot right after storing it** means a label separates the store from the use. Splitting the last `|| x == 0` of an early-return chain into its own `if (x == 0) return -1;` creates that label, and it also decides which `return -1` copy cross-jumping keeps (sub_080737C0).
- **Two-pseudo register swap workflow** (sub_08035054): use `/tmp/v/ga.sh file.c` to get the global-alloc order with refs and len. Test the swap with `REFADJ=pseudo:+N` on the debug old compiler, then make it real with a `do { do { set; } while (0); } while (0);` around a single set of that variable. Each nesting level adds +1 weight per ref inside it. Put a comment in the source saying the nesting is load-bearing (precedent: sub_08033158).
- **Retail register/stack pairs (rX at loop head + sp slot across the inner loop + reload at the bottom)** are gcse PRE copies. Write the update (`rows -= 8; yt++;`) at the END of the loop body; PRE hoists it to the head and leaves a copy (sub_08060E48).
- **Loop-invariant hoisting order follows the first textual occurrence in the loop.** Locals like `u32 shl = sx * 4;` declared in the innermost loop control which invariant lands in which register. To get "copy then shift-in-place" for two shifts of one value, write `hi = v; v <<= shl; hi >>= rsh;` (sub_08060E48).
- **`ptr + int` canonicalises with the pointer first.** To get retail's `add rd, rIdx, rBase` operand order, make the base a `u32` and write `(T *)(idx + base)` (sub_08060E48).

Added 2026-10-01 (sub_08044A8C / SaveDataVerify matched, after the permuter had stalled at 425):
- **A global-pointer load (`ldr rX,[pc]` of `gData_X`) used before AND inside a nested loop** gets a loop.c-hoisted second pseudo (preheader `(set G2 G1)` copy). The allocator then refuses to share one reg between them unless the function's *later* pseudos leave r4 free; otherwise G1 is pushed to r8 (`ldr r1; mov r8,r1`, a `sub sp,#4`, n/invalid shifted to r10/r9). Truncating the function (`return` after loop N) and watching where the symbol load lands bisects which later statement is the cause.
- **Culprit was a reused local (`hdr = base; hdr += i;` used twice).** Retail has no such local: the second access was a direct `((T *)&gData->unk1688[i])->field` and the FIRST was `((T *)&gData->unk1688[i])->unk04 != SaveDataChecksum(...)`. Direct field access forces the address (`adds r4, rIdx, rBase`, index first, kept across the call) while the load happens after the call. Reusing one named pointer for two checks changes pseudo priorities and the `adds` operand order (base,idx vs idx,base) at once. When retail shows two different regs for "the same" pointer in sequential checks, drop the local and index directly.
- A plain constant store `gData->f = 0;` (zero materialised AFTER the address `ldr/adds`) plus a later `for (i = 0;` / `REG_IME = 0` / `invalid = 0` CSE-shared into one zero pseudo (=i, copied to r8 for invalid) reproduces `ldr; adds; movs r6,#0; strb r6`. `f = i = 0;` puts the `movs` before the address.
- `*(buf = *h)` chain vs separate `buf = *h;` AFTER the second store: separate gives retail's `ldr r3,[r5]; str r3; ... adds r7,r3,#0`.
- Fast toolkit: `/tmp/.../scratchpad/dis.py` style diff (compile via match_function.compile_c, objdump both, normalise) + `-dg -dl -dj -ds -dL -dt -dN` dumps; one compile is ~0.1s so sweeps of a few hundred source variants are cheap; declaration order of locals did NOT matter here (5040-perm sweep all identical).

Added 2026-10-01 (sub_08067CE8 / AnimObjDraw matched, 548/548):
- **Two-register swap of a param vs a local (retail px=r4, a=r5)**: `REFADJ=<pseudo>:+N /tmp/v/ga.sh file.c` showed px needed ~+18 refs to outrank `a` (prio = floor_log2(refs)*refs/len). Made real with a single statement nested 9 deep in `do { } while (0)` (macro `PX_WEIGHT`); wrapping several px statements shallower also works only at depth 5 each, and wrapping `slot->unk08 = px << 8` breaks slot CSE (new `adds r4,r5,#184` pseudo).
- **`m3` mask var only where retail needs it**: first AND terms use literal `& 3` (cse shares the const pseudo, giving `mov r2,r8; ands r2,r3` operand order); `m3 = 3` inline in the *third* term only (`(a->unk39 & (m3 = 3))`) keeps the later `(s8)x & m3` sext. Inline in the first term gives `[unk38, tmp]` operand order instead.
- A lone global/field address pseudo (`a->unkB8` slot ptr, `&a->unk31`) needs no explicit local: cse shares `a+const` addresses; naming `fp`/`slot` locals changed the code.

Added 2026-10-01 (sub_08044648 / BeybladeSpawnList matched, 364/364, ~10 min):
- Recipe that solved it immediately: `/* match-compiler: old_agbcc */` + `s16 key = *ids` local reused by both GetIndexedRecordWord calls + `tbl = gData_X; def = &tbl[id];` (table-base-first). agbcc (new) was same-size but never reached it; old_agbcc dupes the loop-test load unless `key` exists. Try this trio first on any "table base before id*size" draft.

Added 2026-10-01 (sub_080618EC / TextTypewriterTick parked at 375/428, not matched):
- **`x | 0xFF` stored to a byte folds to a constant** in combine unless the OR operand has unknown nonzero bits (combine.c: `(ior A C) is C if nonzero_bits(A)` covered; also QI-narrowed store forces it). Retail's `movs r0,#255; orrs r0,r3` survives only when the operand is an unnamed gcse-PRE reaching reg (write `t->state |= 0xFF` with NO local for t->state): that gives the right OR but a `ldrb r0; adds r3,r0,#0` copy that retail lacks. Any user local loaded once from the u8 field folds it (u8/u32/s32/s16 all tried); a second sign-extending set of the local (`state = (s8)t->state` in the early return) keeps the OR and matches the OR lines but costs an extra copy in the return path.
- The same PRE-copy shape appears for `gData_X` loaded once and used by two ANDs (`ldrh r1; adds r0,r1,#0`): retail has the load straight into the reg and the AND operand order [temp, keys]; commutative operand order follows pseudo number, so retail's `keys` is a high-numbered PRE temp, not a local.
- `old_agbcc` + no `goto` + `if (t != NULL) {...} else return -1;` gave same-size 428 where the plain `if (t == NULL) return -1;` stayed at 432.

Added 2026-10-01 (sub_080618EC parked again; one-line diff left):
- Fold mechanism: combine folds `(ior A 255)` stored to a byte only when `reg_nonzero_bits[A]` is known (reg set directly from a mem load). A pseudo set by a reg-reg copy (e.g. gcse PRE reaching reg) or multi-set has unknown bits -> OR survives. PRE's copy insn is invisible to the second cprop pass, so `ldrb r0; adds r3,r0,#0` stays.
- Constant 255 held in a user var set in an earlier block (`done = 0xFF` before the timer test) keeps `movs r0,#255; orrs` unfolded and makes the state a global pseudo with a direct `ldrb r3`; with `s8 done` regs/operand order match retail but a `lsls/asrs #24` appears.
- Commutative operand order `gData_X & t->skipKeys` (global first) made keys load straight into r2 as retail. Case order in a switch changes the `bne default; b end` polarity (case 10 first).
- Tools used: debug compiler copy /tmp/v/agbcc_dbg3 (TCDBG/TCPAT combine traces, LAFORCE=pseudo:minreg local-alloc hack, GCDBG gcse); scratchpad dmetric.py counts differing instruction lines vs retail (better than byte score when a 2-byte shift misaligns everything).

Added 2026-10-01 (sub_080618EC / TextTypewriterTick matched 428/428 after two parked sessions):
- **`ldrb r3` direct + unfolded `state | 0xFF` later:** `s8 state; if ((state = t->state) != 1) return (s8)t->state; ... t->state |= 0xFF;` with old_agbcc. Brute-forcing local type x init form x OR form (a 30-line script, 0.1s/compile) found it in one pass; hand variants had missed the *signed* local. Do that sweep before reasoning about gcse/combine. Cause: PRE inserts a second QI load (REG_N_SETS=0 pseudo => unknown nonzero bits), which is why the plain `t->state` form copies via r0.
- When a function sits at "N diff lines, all register choice", write the diff metric (normalise `[pc,#n]`/branch targets, count differing insns vs retail objdump) and sweep the cross product of the 3-4 knobs mechanically.
- sub_08035624 (parked): K/L2 address regs r4/r2 not reproduced; forcing them in a debug compiler (FORCEREG hook in global.c) makes the rest equal retail, so only that choice is open.

Added 2026-10-01 (sub_08038438 / PaletteSlotAcquire matched after a long-parked "loop.c moves found block" case):
- The real fix for the "found block hoisted out of the loop + *slots hoisted" blocker was NOT the found-body wrapper but (a) reading the global pointer directly (`gData_030003CC->x`, no `**slots` local), and (b) wrapping the *whole `if` of each loop body* in `do { } while (0)` (depth 2/1): loop notes then sit in the found block, so it stays inline and the memory load stays non-invariant.
- Hi-reg order: the FIRST hi pseudo allocated gets r12 (ip), the next r8, then r9... To swap which pseudo lands in ip vs r8 flip their GA priority; priority = floor_log2(refs)*refs/len so +3 refs on the long-life pseudo is enough. Done by nesting depth on loop 0 (k=3), loop 1 body (2) and loop 2 body (1); then nest on `i++` (2) flipped the r1/r2 order of the sign-extended index vs i*2.
- Workflow that found it in ~1 hour: debug compiler (agbcc_x with REFADJ=pseudo:+N and FORCEREG hooks) to learn which refs adjustments reach retail, then a mechanical sweep of nest depths per statement group scored by diff-line count vs retail (sc.sh-style). Do the sweep first next time; each compile is 0.1s.
- `s16 key` (not u16) makes `key++` compile as `(key<<16)+0x10000` shared with the `(s16)key*4` index, as retail.

Added 2026-10-01 (sub_0806EC20, sub_0807309C, sub_08038314 and sub_08047594 all matched):
- **`(base + K) + idx*stride` with K added before the index** (`adds rX, rB, #0; adds rX, #K; adds rX, rX, rI`) only comes from an array *member* (`p->arr[i].f`). `p[i].f` folds to `ldr [r, #K]`. Model the param as a struct holding the array (MapOrigins).
- **`movs #2; negs; ldrb; ands; strb` (old_agbcc) is a 1-bit bitfield clear.** Prefer a bitfield over the `s32 m = -2` local trick; check sibling functions that touch the same byte.
- **An `orrs` whose destination is the mask, not the accumulator**, means the accumulator is a full-width int with a `(u8)(...)` truncation. A `u8` accumulator makes the front end narrow `1 << i`, and regmove then ties the result to the variable (more refs, higher alloc priority).
- **Global-alloc priority = floor_log2(refs)*refs/live_length.** Live length counts insns as they stood *before combine*, so constants and loads that combine later folds still count. Use `prio.sh`-style dumps (`-dl -dg`, then read `.lreg` / `.greg`) to see the tie, and the flow-vs-lreg insn diff to see what combine removed.
- Ways to shorten a pointer's live length without changing the code: take generic params (`void *view, void *table, u32 mode, void *origins`) and copy them into typed locals, which keeps the original copy order; use a `do { } while (++i <= 3)` loop instead of `for` (saves the initial jump); write the sign extension as `(bits << 24) >> 16` with `s32 bits` instead of `(s8)bits << 8` (saves one).
- **Spill-slot order follows pseudo (declaration) order, not assignment order.** Declare a local early and assign it later to swap two stack slots (`u16 dispcnt;` before `pos = origins`, then `dispcnt = mode;`).
- agbcc expands `u8field = 0xFF` as load, ior 0xFF, store (combine folds it later), so it costs 2 extra pre-combine insns.
- Retail `ldr rX,[sp]` zero stores before any use mean the 0 was CSE'd into a spilled user variable (the bitmask). Check that variable's priority, not the stores.
- A null check followed by `table = g` that loads `g` before the copy: write `if (g == 0) return 0; table = g;` (sub_0807309C).

Added 2026-10-01 (sub_0806E060):
- **`muls` by a register constant that gets rematerialized (`movs r5,#0xC0; lsls r5,#1` repeated)** = a function-scope local set once at the top (`s32 radius = 0x180;`). A literal gets synth_mult'd into shifts. A block-scoped local keeps a hard reg. Because the top-level local lives a long time, it has low priority, so it spills and reload rebuilds it from REG_EQUIV.
- **Variable reuse matters a lot.** Retail reused locals: the midpoint was written back into `x`, the final result was assigned to `x` before both `out[]` stores, and `next -= 0x80` reused the heading variable. Using fresh temps for each step raised register pressure and moved the global regs. A fast sweep with `itertools.product` over these source shapes (difflib ratio against an objdump of the retail bytes, ~0.1s each) found the match in a few minutes.
- `ldrh` in both branches followed by a single `lsls/lsrs #24` after the join means an s16/u16 variable used as `(u8)v`. A `u8` variable narrows the load to `ldrb`.
- Other Claude sessions may run `make` in this repo at the same time. A race leaves 0xFF-filled 4 KB pages in the .gba and gives a false `make compare` FAILED. Run `make -B compare` before you treat it as real.

Added 2026-10-01 (sub_0804BD38 + sub_0804C8BC matched; both had been parked for several sessions):
- **Retail reloading a global address at every use (`ldr rX,=sym` each time) inside a loop** usually means the address *was* hoisted, lost global alloc and was **rematerialized by reload** from its REG_EQUIV. Don't fake it with alias symbols (`gData_X_A/_B`). A local `s16 *top = &gData_X;` set before the loop gets REG_EQUIV, so its live length doubles and it loses the register cleanly.
- Reload picks spill regs **round-robin**, so the scratch regs further down depend on how many reloads came earlier. A table base that retail loads *after* the index (`labels = gData_T;` local, spilled and rematerialized) adds a reload and shifts every later scratch reg by one.
- Pass-1 vs pass-2 loop hoisting shows in the pre-loop order. A constant (e.g. 0) whose init comes *after* the giv inits was hoisted by the second loop pass. That happens when an earlier pass-1 move lowered `threshold` by 3 (in BD38 an in-loop `labels = gData_T;` did that).
- **combine_givs has a bug** (the second penalty loop indexes `can_combine[m*n + j]` with j as both a sort position and an array index), so which identical giv becomes the representative depends on list positions. That controls where the increment goes (rep = first-discovered giv means its increment comes last). Semantically equal rewrites of *other* givs move it: `(u16)(2 * i + 7)` / `(u16)((i + 4) * 2)` instead of `i * 2 + 7/8`, or `((i << 4) + 0x38) << 8` instead of `(i * 16 + 0x38) << 8`.
- Workflow that worked: a debug compiler copy of ~/Github/agbcc/gcc in scratch with env hooks (GIVREP=uid:+N to bias combine stats, FORCEGIV=uid / FORCEUSER to force reduction, REFADJ=regno:+N to adjust allocno refs). First prove "only knobs X and Y differ", then sweep natural source forms with the real compiler (sweep.py with an @{a|b}@ template, about 40 variants/s on 8 cores).
- A short-lived block-local pseudo landing in a callee-saved reg (r4) can't come from local-alloc, which picks the lowest free reg and has no r4 suggestion source. It has to be a global allocno whose r0..r3 are excluded by conflicts. Debug hooks in the scratch agbcc copy (worth rebuilding: `make old -j1` for old_agbcc): FORCEHARD=regno:hard (override before reload), NOLOCAL=regno,..., GADBG=1 (find_reg sets), RLDBG=1 (reload order/live sets). sub_08035624's open problem is in its notes.
- **Redundant store inside the `if` = retail's callee-saved address reg** (sub_08035624, solved 2026-10-01 after 7 sessions): `p->key = v; if (p->list) { p->key = v; Resort(p->list, v); }`. The second store keeps the key address live past the list load, so it becomes a global allocno that conflicts with r0..r3 (gets r4), and reload_cse_noop_set_p deletes the store afterwards, leaving no code. Same reload_cse rule also deletes a re-load of a value a reg already holds. Short-lived address in r4 with no visible later use -> try a duplicated store/load. Do-while(0) wrappers break it (loop labels reset reload_cse).
- Global-alloc order fix: an `s8` param instead of `s32` + `(s8)` cast in the body removed one ref from another pseudo's competition (REFADJ `25:-1` showed it first). Check caller types before widening params.
