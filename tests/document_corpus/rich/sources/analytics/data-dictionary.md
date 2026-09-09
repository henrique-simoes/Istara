# Analytics data dictionary + reader notes

- Grain: one row per ISO week. Population: Harbor Ledger pilot cohort (412 small businesses).
- deposits_completed dips in 2026-W19: mobile deposit limit incidents (see T10), NOT a tracking bug. Treated as stale-after-fix from W20 on.
- payments_matched_auto is a percent string in this export (source quirk) — parse before averaging.
- support_tickets declines as in-app guidance shipped (W16); do not read as satisfaction without the survey.
