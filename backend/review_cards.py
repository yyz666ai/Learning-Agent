"""Small persistent Anki-style review card records."""

from __future__ import annotations

import json
import re
import hashlib
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Literal

from .learning_content import SAFE_USER_ID

ReviewRating = Literal["forgot", "hard", "easy"]
SAFE_CARD_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
INTERVAL_DAYS: dict[str, int] = {"forgot": 1, "hard": 3, "easy": 7}


def _path(server_root: Path, user_id: str) -> Path:
    if not SAFE_USER_ID.fullmatch(user_id):
        raise ValueError("invalid user_id")
    return server_root / "userdir" / f"u_{user_id}" / "memory" / "review-cards.json"


def read_cards(server_root: Path, user_id: str) -> dict[str, Any]:
    path = _path(server_root, user_id)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"cards": {}}
    return value if isinstance(value, dict) and isinstance(value.get("cards"), dict) else {"cards": {}}


def rate_card(
    server_root: Path,
    user_id: str,
    *,
    card_id: str,
    title: str,
    rating: ReviewRating,
    today: date | None = None,
) -> dict[str, Any]:
    if not SAFE_CARD_ID.fullmatch(card_id):
        raise ValueError("invalid card_id")
    if rating not in INTERVAL_DAYS:
        raise ValueError("invalid rating")
    selected_today = today or date.today()
    payload = read_cards(server_root, user_id)
    cards = payload["cards"]
    previous = cards.get(card_id) if isinstance(cards.get(card_id), dict) else {}
    attempts = int(previous.get("attempts") or 0) + 1
    next_review = (selected_today + timedelta(days=INTERVAL_DAYS[rating])).isoformat()
    history = list(previous.get("review_history") or [])
    history.append({
        "rating": rating,
        "reviewed_at": selected_today.isoformat(),
        "interval_days": INTERVAL_DAYS[rating],
        "next_review": next_review,
    })
    card = {
        **previous,
        "card_id": card_id,
        "title": title[:240],
        "last_rating": rating,
        "attempts": attempts,
        "last_reviewed": selected_today.isoformat(),
        "next_review": next_review,
        "review_history": history,
    }
    cards[card_id] = card
    path = _path(server_root, user_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    return card


def add_question_card(
    server_root: Path,
    user_id: str,
    *,
    topic: str,
    question: str,
    summary: str,
    today: date | None = None,
) -> dict[str, Any]:
    """Schedule an important learner question for a future review."""
    selected_today = today or date.today()
    digest = hashlib.sha256(f"{topic}\n{question}".encode("utf-8")).hexdigest()[:20]
    card_id = f"question:{digest}"
    payload = read_cards(server_root, user_id)
    card = {
        "card_id": card_id,
        "title": question[:240],
        "topic": topic[:240],
        "summary": summary[:2_000],
        "last_rating": None,
        "attempts": 0,
        "last_reviewed": None,
        "next_review": selected_today.isoformat(),
    }
    payload["cards"][card_id] = card
    path = _path(server_root, user_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    return card
