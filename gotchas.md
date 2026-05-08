# Gotchas

Session-level corrections and durable user preferences go here.

- Do not start live backend/frontend servers, send chat-completion probes, or trigger model loading without explicit user permission. Passive LLM status/discovery checks must stay passive; active model loading belongs only on deliberate request paths and must be bounded to avoid multiple heavy models.
- `LLMs/` and `Model_Finetuning/` are protected local artifact folders. They are gitignored and must never be deleted, pruned, moved, or cleaned by agents.
