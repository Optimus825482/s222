# Root-Level Orphan Artifacts — Risk Tags

This file records classification and quarantine actions for non-runtime root artifacts.

## Quarantined to `scripts/experimental/`

| Original root file | New path | Risk tag | Rationale |
|---|---|---|---|
| `_count.py` | `scripts/experimental/_count.py` | LOW-RISK-ORPHAN | One-off local inspection helper for line counting in frontend component. |
| `_fix_runtab.py` | `scripts/experimental/_fix_runtab.py` | MEDIUM-RISK-ORPHAN | Ad-hoc in-place code rewriting helper targeting `run-tab.tsx`; not runtime code. |
| `_test_hygiene.py` | `scripts/experimental/_test_hygiene.py` | MEDIUM-RISK-ORPHAN | Local endpoint smoke-test script against localhost; not production/runtime path. |
| `_write_run_tab.py` | `scripts/experimental/_write_run_tab.py` | MEDIUM-RISK-ORPHAN | One-off file writer script that overwrites frontend component source. |
| `_write_runtab.py` | `scripts/experimental/_write_runtab.py` | MEDIUM-RISK-ORPHAN | One-off file writer script for benchmark UI source. |

## Quarantined to `artifacts/`

| Original root file | New path | Risk tag | Rationale |
|---|---|---|---|
| `presentation (1).html` | `artifacts/presentation (1).html` | LOW-RISK-NONRUNTIME | Standalone generated presentation deck, not imported by app runtime. |
| `presentation (2).html` | `artifacts/presentation (2).html` | LOW-RISK-NONRUNTIME | Standalone generated presentation deck, not imported by app runtime. |
| `presentation (3).html` | `artifacts/presentation (3).html` | LOW-RISK-NONRUNTIME | Standalone generated presentation deck, not imported by app runtime. |
| `backend-pw4w0wwcsossc0o8ws0888gc-152930476776-all-logs-2026-03-11-17-33-29.txt` | `artifacts/backend-pw4w0wwcsossc0o8ws0888gc-152930476776-all-logs-2026-03-11-17-33-29.txt` | LOW-RISK-LOG-DUMP | Point-in-time exported logs; archival artifact only. |
| `all-icons.zip` | `artifacts/all-icons.zip` | LOW-RISK-BINARY-BUNDLE | Bulk binary bundle for static assets; non-runtime at root. |

## Notes

- No files were hard-deleted in this task; all assigned items were quarantined by relocation.
- This preserves recoverability while reducing root-level clutter and accidental coupling.
