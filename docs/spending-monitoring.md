# Spending monitoring and recovery

`GET /planning/status` evaluates saved plans against income, actual spending, recurring commitments and debt obligations. Deterministic rules precede AI explanation or adjustment. Targets are not spending. Services distinguish paid debt and outstanding installments and avoid duplicating a derived debt budget allocation.

Forecasts consider upcoming commitments and up to three tracked historical months. Sparse history uses budget-based fallback with lower confidence; a few days of everyday spending are not simply extrapolated as certainty.

| Level | Meaning |
| --- | --- |
| 0 | No detected adjustment risk |
| 1 | Category overrun without demonstrated goal failure; advice only |
| 2 | Credible forecast goal risk or allocations exceed the goal-protected buffer |
| 3 | Committed spending leaves less than the required contribution; recovery |

`POST /planning/adjustments/proposal` generates constrained suggestions. Unknown categories and fixed-commitment cuts are rejected. Floors protect spent amounts plus due commitments; flexible reductions are capped against expected remaining spending. Level 1 remains advice rather than a writable adjustment.

`POST /planning/adjustments/accept` explicitly accepts a reviewed proposal using a separate monitoring fingerprint, write lock and UUID request key. Acceptance reduces budget targets and records adjustment history, never changes transactions or actual savings. Optional later deadline/contribution choices require a separate reviewed plan edit.

This is estimated risk monitoring, not bank synchronization or guaranteed recovery. See [planning](financial-planning.md) and [calculations](core-algorithms.md).
