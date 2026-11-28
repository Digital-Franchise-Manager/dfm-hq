"""Deterministic Draft waiver-priority queue operations."""
from __future__ import annotations


def validate_priority(priority: tuple[str, ...], franchise_ids: tuple[str, ...]) -> None:
    if len(priority) != len(set(priority)) or set(priority) != set(franchise_ids):
        raise ValueError("waiver priority must contain every league franchise exactly once")


def priority_rank(priority: tuple[str, ...], franchise_id: str) -> int:
    try:
        return priority.index(franchise_id)
    except ValueError as exc:
        raise ValueError("franchise is not in waiver priority") from exc


def rotate_priority(priority: tuple[str, ...], winner: str) -> tuple[str, ...]:
    if winner not in priority:
        raise ValueError("waiver winner is not in priority queue")
    return tuple(item for item in priority if item != winner) + (winner,)
