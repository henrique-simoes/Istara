# Cleanup Report

## Retained

- Replacement worktree: `/Users/user/Documents/Istara-main-pi-replacement`.
- Lab package source, tests, scenario runner, `package.json`, and `package-lock.json`.
- `node_modules/` retained only inside isolated worktree for repeat smoke runs.
- Comparison run artifacts under
  `comparison-Istara-pi/runs/20260719T120128-0300-replacement-worktree/`.

## Deleted

- No generated artifacts were deleted in this run.
- No `node_modules`, `dist`, `coverage`, `.cache`, or temp folders were retained inside
  `comparison-Istara-pi/`.

## Storage Measurements

- `/Users/user/Documents/Istara-main-pi-replacement`: 275M.
- `/Users/user/Documents/Istara-main-pi-replacement/labs`: 131M.
- `/Users/user/Documents/Istara-main-pi-replacement/labs/pi-replacement/node_modules`: 130M
  reported by `du -sh`; retained only in isolated worktree and ignored by git.
- `/Users/user/Documents/Istara-main/comparison-Istara-pi`: 464K after final artifact writes.

## Policy Check

- No dependency tree was stored inside `comparison-Istara-pi/`.
- No local models were used.
- No API key value was stored.
