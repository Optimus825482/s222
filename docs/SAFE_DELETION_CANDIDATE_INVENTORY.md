# Safe Deletion Candidate Inventory

Date: 2026-03-11
Scope: orphan/placeholder/non-product files requested by task assignment.

## Classification Legend
- **SAFE-DELETE**: low-risk deletion candidate; no known runtime linkage.
- **NEEDS-REVIEW**: potentially non-product, but ownership/intent should be confirmed before deletion.
- **ALREADY-REMOVED**: candidate is not present on disk.

## Inventory

| Path | Type | Presence/Tracking | Evidence | Classification |
|---|---|---|---|---|
| `backend/main_monolith_backup.py` | legacy backup file | Missing from filesystem; referenced only by root ignore rule | Not found on disk (`MISSING`); only mention in `.gitignore` (`backend/main_monolith_backup.py`) | **ALREADY-REMOVED** |
| `frontend/src/components/xp-about-dialog.tsx` | placeholder source file | Present and tracked | File size is `0` bytes; active import points to `frontend/src/components/xp/xp-about-dialog.tsx` via `frontend/src/components/xp/xp-desktop.tsx` | **SAFE-DELETE** |
| `frontend/.next/` | Next.js build output | Present, ignored (frontend-local) | Large generated tree (`~186 MB`); ignored by `frontend/.gitignore` (`.next/`) | **SAFE-DELETE** |
| `frontend/node_modules/` | dependency install output | Present, ignored (frontend-local) | Large generated tree (`~637 MB`); ignored by `frontend/.gitignore` (`node_modules/`) | **SAFE-DELETE** |
| `logs/` (`backend-error.log`, `backend-out.log`, `frontend-error.log`, `frontend-out.log`) | local runtime logs | Present and **tracked** | Small local logs (total `457` bytes), currently committed (`git ls-files` includes all four) | **NEEDS-REVIEW** |
| `docs/pi-mono/node_modules/` | dependency install output in nested repo/submodule | Present, ignore-managed inside nested repo | Large generated tree (`~534 MB`); ignore rule exists in nested repo (`docs/pi-mono/.gitignore`) | **SAFE-DELETE** |
| `services/pi-gateway/node_modules/` | dependency install output | Present, ignored (root) | Generated tree (`~110 MB`); ignored by root `.gitignore` (`node_modules/`) | **SAFE-DELETE** |
| `_check2.py` | ad-hoc local check script | Present, untracked/ignored | Root ignore pattern `_check*.py`; script contains manual OpenAPI probing code | **SAFE-DELETE** |
| `_check3.py` | ad-hoc local check script | Present, untracked/ignored | Root ignore pattern `_check*.py`; script contains manual route/line inspection code | **SAFE-DELETE** |
| `_check4.py` | ad-hoc local check script | Present, untracked/ignored | Root ignore pattern `_check*.py`; script contains manual route decorator scanning code | **SAFE-DELETE** |
| `_check5.py` | ad-hoc local check script | Present, untracked/ignored | Root ignore pattern `_check*.py`; script contains ad-hoc module load test code | **SAFE-DELETE** |
| `aa.py` | scratch utility script | Present and tracked | Script performs one-off external image download using hardcoded bearer token and writes `image.jpg` | **NEEDS-REVIEW** |
| `presentation (1).html` | standalone presentation artifact | Present and tracked | Non-app static export style presentation deck (Turkish content), not part of app source tree | **NEEDS-REVIEW** |
| `presentation (2).html` | standalone presentation artifact | Present and tracked | Non-app static export style presentation deck (Turkish content), not part of app source tree | **NEEDS-REVIEW** |
| `presentation (3).html` | standalone presentation artifact | Present and tracked | Non-app static export style presentation deck (Turkish content), not part of app source tree | **NEEDS-REVIEW** |

## Summary Buckets

### SAFE-DELETE (8)
- `frontend/src/components/xp-about-dialog.tsx`
- `frontend/.next/`
- `frontend/node_modules/`
- `docs/pi-mono/node_modules/`
- `services/pi-gateway/node_modules/`
- `_check2.py`, `_check3.py`, `_check4.py`, `_check5.py`

### NEEDS-REVIEW (5)
- `logs/` tracked log files
- `aa.py`
- `presentation (1).html`, `presentation (2).html`, `presentation (3).html`

### ALREADY-REMOVED (1)
- `backend/main_monolith_backup.py`

## Notes
- This inventory is intentionally **non-destructive**: no deletions were performed.
- Because `docs/pi-mono/` is a nested Git repository/submodule, deletion decisions there should be coordinated with that repo’s maintainers.
