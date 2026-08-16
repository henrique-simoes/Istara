# Full Istara Pi Wiring Handoff Status

Generated: 2026-07-19 15:40 BRT

Status: handoff_ready_for_next_conductor_round

Scope:
- Main Istara checkout: read/evidence only; do not mutate app code here.
- Replacement worktree: `/Users/user/Documents/Istara-main-pi-replacement`.
- Candidate branch: `comparison/pi-replacement-core`.
- Candidate implementation path so far: `labs/pi-replacement/`, plus Build Stream/recipe artifacts in the replacement worktree.
- Next round may modify production app code only inside the replacement worktree, behind a reversible candidate flag or dependency-injection boundary.

Budget:
- Original DeepSeek cap: USD 0.50.
- Latest conservative total used: about USD 0.09335561.
- Remaining conservative cap: about USD 0.40564439.
- No local models.
- DeepSeek key must be read only at runtime from macOS Keychain and never logged.

Compass Forge state:
- Target/workspace: `/Users/user/Documents/Istara-main-pi-replacement`.
- Recipe: `istara-main-pi-replacement`.
- Classification for this continuation: `security_or_architecture`, full blast radius.
- `compass-forge refresh` completed before this handoff.
- Latest gate still reports inherited large-file failures and complexity warnings; these are not caused by the Pi work unless a later gate reports new drift.

Current completed evidence:
- Real-loop bridge run: `comparison-Istara-pi/runs/20260719T145107-0300-real-istara-loop-bridge/`.
- 15/15 deterministic baseline scenarios passed.
- 15/15 deterministic Pi candidate scenarios passed.
- 56/56 Pi canonical tool calls succeeded.
- 10/10 mapped surfaces covered in lab bridge mode.
- Raw capture exists for 44 prompts and 44 outputs.

Current limitation:
- The existing candidate is a strong lab bridge, not a production replacement.
- The next round must bridge real Istara route/service contracts in the isolated replacement worktree, then run the harnesses against that candidate.

Next action:
- Start a durable conductor round from `conductor-handoff.md` and `missing-surface-audit.md`.
