#ifndef GUARD_DATA_SYMBOLS_H
#define GUARD_DATA_SYMBOLS_H

// Absolute data-address symbols referenced by decompiled C.
//
// Retail addressed ROM tables and globals through *symbols*, not bare integer
// literals. agbcc folds / reschedules a literal address but cannot do that to
// a symbol reference, so functions that only match with symbol addressing use
// the `gData_*` names declared here (values: asm/data_symbols.s).

#endif // GUARD_DATA_SYMBOLS_H
