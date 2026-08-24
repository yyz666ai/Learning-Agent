from datetime import date
from pathlib import Path

from backend.review_cards import add_question_card, rate_card, read_cards


def test_anki_ratings_persist_and_schedule_different_intervals(tmp_path: Path) -> None:
    today = date(2026, 8, 20)
    forgot = rate_card(tmp_path, "learner", card_id="go.variables", title="变量", rating="forgot", today=today)
    hard = rate_card(tmp_path, "learner", card_id="go.channel", title="Channel", rating="hard", today=today)
    easy = rate_card(tmp_path, "learner", card_id="go.defer", title="Defer", rating="easy", today=today)

    assert forgot["next_review"] == "2026-08-21"
    assert hard["next_review"] == "2026-08-23"
    assert easy["next_review"] == "2026-08-27"
    assert len(read_cards(tmp_path, "learner")["cards"]) == 3


def test_repeated_rating_increments_attempts(tmp_path: Path) -> None:
    rate_card(tmp_path, "learner", card_id="go.variables", title="变量", rating="forgot")
    result = rate_card(tmp_path, "learner", card_id="go.variables", title="变量", rating="hard")

    assert result["attempts"] == 2
    assert result["last_rating"] == "hard"


def test_rating_important_question_preserves_answer_and_history(tmp_path: Path) -> None:
    card = add_question_card(
        tmp_path, "learner", topic="Go", question="为什么要用 context？",
        summary="context 用于传递取消信号、截止时间和请求级数据。",
    )

    rated = rate_card(
        tmp_path, "learner", card_id=card["card_id"], title=card["title"],
        rating="forgot", today=date(2026, 8, 24),
    )

    assert rated["summary"].startswith("context")
    assert rated["topic"] == "Go"
    assert rated["review_history"][0]["rating"] == "forgot"
