"""Capacity scoring helpers for the unified compute registry."""

from __future__ import annotations

import time
from typing import Any


def node_capacity_score(node: Any, *, now: float | None = None) -> float:
    """Score a compute node for request routing."""
    current = time.time() if now is None else now
    if not getattr(node, "is_healthy", False):
        return -1
    if getattr(node, "health_state", "") in {
        "auth_required",
        "no_model_loaded",
        "no_model_server",
        "timeout",
        "unreachable",
    }:
        return -1
    if getattr(node, "active_requests", 0) >= getattr(node, "max_active_requests", 0):
        return -1
    if getattr(node, "health_state", "") == "cooldown" and current < getattr(
        node, "cooldown_until", 0
    ):
        return -1

    score = 100.0
    score -= getattr(node, "active_requests", 0) * 15
    latency_ms = getattr(node, "latency_ms", 0) or 0
    if latency_ms:
        score -= min(latency_ms / 10, 30)
    score -= getattr(node, "priority", 10)

    ram_available_gb = getattr(node, "ram_available_gb", 0) or 0
    ram_total_gb = getattr(node, "ram_total_gb", 0) or 0
    if ram_available_gb:
        score += min(ram_available_gb * 2, 20)
    if ram_total_gb and ram_available_gb / max(ram_total_gb, 0.1) < 0.15:
        score -= 20

    cpu_load_pct = getattr(node, "cpu_load_pct", 0) or 0
    if cpu_load_pct > 70:
        score -= min((cpu_load_pct - 70) * 0.75, 20)
    return score


def compute_capacity_envelope(nodes: list[Any]) -> dict:
    """Summarize pool capacity for telemetry, UI, and rehearsal checks."""
    total_slots = sum(max(0, getattr(node, "max_active_requests", 0)) for node in nodes)
    used_slots = sum(max(0, getattr(node, "active_requests", 0)) for node in nodes)
    available_slots = sum(
        max(0, getattr(node, "max_active_requests", 0) - getattr(node, "active_requests", 0))
        for node in nodes
        if getattr(node, "is_healthy", False)
    )
    saturated_nodes = sum(
        1
        for node in nodes
        if getattr(node, "active_requests", 0) >= getattr(node, "max_active_requests", 0)
        and getattr(node, "max_active_requests", 0) > 0
    )
    cpu_values = [
        getattr(node, "cpu_load_pct", 0) for node in nodes if getattr(node, "cpu_load_pct", 0)
    ]
    hardware_load_pct = round(sum(cpu_values) / len(cpu_values), 1) if cpu_values else 0.0
    return {
        "request_slots_total": total_slots,
        "request_slots_used": used_slots,
        "request_slots_available": available_slots,
        "request_slot_utilization_pct": round((used_slots / total_slots) * 100, 1)
        if total_slots
        else 0.0,
        "saturated_nodes": saturated_nodes,
        "hardware_load_pct": hardware_load_pct,
    }
