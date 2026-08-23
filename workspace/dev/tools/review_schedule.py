from datetime import datetime


INTERVALS = (1, 3, 7, 14, 30)


def next_interval_days(
    stage: int, passed: bool, hint_level: int, transferred: bool
) -> int:
    """Return the next review interval in days from deterministic evidence."""
    if not passed:
        return 1
    next_stage = min(max(stage, 0), len(INTERVALS) - 1)
    days = INTERVALS[next_stage]
    if hint_level >= 4:
        days = min(days, 3)
    if transferred:
        days = max(days, 14)
    return days


def due_items(
    items: list[dict], now: datetime, limit: int = 5
) -> list[dict]:
    """Return due items ordered by priority, due time, and stable concept ID."""
    if limit < 0:
        raise ValueError("limit must be non-negative")
    due = [
        item
        for item in items
        if datetime.fromisoformat(item["next_review_at"]) <= now
    ]
    due.sort(
        key=lambda item: (
            -item.get("priority", 0),
            item["next_review_at"],
            item["concept_id"],
        )
    )
    return due[:limit]
