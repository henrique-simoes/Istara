"""Typed decision-model providers (layer 2 of the evaluation stack).

Product code obtains a decider only through ``app.core.decider.access.open_decider``, which enforces
the project's egress authorization and resolves the API key. ``contract`` holds the
``/v1/systemone`` wire contract, ``registry`` the configured endpoints, ``credentials`` key lookup,
and ``client`` the HTTP client. The mathematics that consumes the answers lives in
``app.core.decision``. Deciders triage research items for human review; they never accept or
promote evidence.
"""
