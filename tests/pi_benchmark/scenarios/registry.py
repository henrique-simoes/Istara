"""Pack registry — the one place packs are named and loaded (task B0-5)."""

from __future__ import annotations

from . import a2a, canonical, deep_research, industry, probes_pack, spine
from .base import Scenario

# The `features` and `probes` packs are produced by their own compilers (B0-6, B0-8)
# rather than by static scenario lists, so they are not loadable here; the runner routes
# them to their dedicated builders.
PACK_NAMES: tuple[str, ...] = ("canonical", "spine", "a2a", "industry", "probes", "deep_research")

_LOADERS = {
    "canonical": canonical.scenarios,
    "spine": spine.scenarios,
    "a2a": a2a.scenarios,
    "industry": industry.scenarios,
    "probes": probes_pack.scenarios,
    "deep_research": deep_research.scenarios,
}


def load_pack(name: str) -> tuple[Scenario, ...]:
    """Return the scenarios in ``name``.

    Raises ``KeyError`` for an unknown pack — the runner surfaces this as a CLI error
    rather than running an empty, silently-wrong pack.
    """
    if name not in _LOADERS:
        raise KeyError(f"unknown scenario pack {name!r}; known: {', '.join(PACK_NAMES)}")
    return _LOADERS[name]()
