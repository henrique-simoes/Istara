"""Scenario packs for the Pi-vs-Legacy benchmark (task B0-5, master plan §10.3).

A *pack* is a named, engine-agnostic set of :class:`Scenario` definitions. Engine is a
run-level parameter (injected by the runner through the dispatcher header), never baked
into a scenario — so pairing and fixture identity hold by construction, not convention
(winning plan §2.2 principle 1).

Every pack is import-safe at determinism tier T0: loading a pack never touches the
backend, the database, a network endpoint, or a model. The canonical pack derives its 15
ids from the production coverage contract by an AST read (no import of the production
package), so B1 measures the shipped behavior rather than a parallel lab fiction
(winning plan §2.2 principle 4).
"""

from __future__ import annotations

from .base import Scenario, deterministic_check_result
from .registry import PACK_NAMES, load_pack

__all__ = ["Scenario", "deterministic_check_result", "PACK_NAMES", "load_pack"]
