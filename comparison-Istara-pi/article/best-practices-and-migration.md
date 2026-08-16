# Best Practices And Migration

Migration recommendation is evidence-gated.

Candidate practices to evaluate:

- Pi evented loop and tool preflight hooks.
- Pi provider catalog and usage accounting.
- Pi CLI/RPC or sidecar process boundary.
- Pi session and skill-loading patterns.
- Reference-only lessons from Pi review and chat extensions.

Hard rejection criteria remain: Pi must not bypass Istara authorization, become source of
truth for product data without a separate migration, store secrets or uncapped traces, require
local models, or require broad Istara product-code rewrites.

