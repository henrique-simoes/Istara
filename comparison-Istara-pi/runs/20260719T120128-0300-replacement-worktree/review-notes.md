# Review Notes

## Findings

No blocking findings remain for the lab prototype.

## Fixed During Review

- The first implementation used a non-existent Node `spawnFileSync` export. Fixed to
  `spawnSync`; validation then passed.
- The DeepSeek smoke initially deleted `DEEPSEEK_API_KEY` after the request but not in a
  failure-safe block. Fixed with `try/finally`.
- Follow-up CF remediation found that provider setup/model-resolution errors could still
  return before env cleanup. Moved provider setup and model lookup inside the same
  `try/finally` so all keyed paths delete `DEEPSEEK_API_KEY`.

## Compass Forge Review

- `compass-forge status` and `next` were run after the owner steering update.
- `agent-brief`, `context`, and six targeted `intelligence impact` maps were run and
  recorded in `cf-dependency-maps.md`.
- CF state was usable for tree-sitter impact maps but stale/unregistered for durable
  snapshot state; the limitation is recorded in `cf-dependency-maps.md`.
- `compass-forge gate after --summary` reported no failures and no route/type/contract
  drift; only inherited large-file complexity warnings remained.

## Residual Risk

- The no-model scenario uses Pi's faux provider for deterministic tool-call generation. This
  is valid for loop/tool plumbing but not for quality comparison.
- The live DeepSeek smoke proves provider routing, not tool-use quality.
- No production Istara API route is switched to the adapter in this phase.
