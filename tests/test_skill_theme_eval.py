"""The SK3 grader counts a theme only when a nugget quotes one of its planted quotes."""

from app.evals.skill_theme_eval import theme_recall

THEMES = {
    "T1": ["I spend the first ninety minutes every day figuring out who owes me money."],
    "T2": ["The aging report lists amounts but not owners, so nobody knows who chased it last."],
}


def test_quoted_theme_counts_and_paraphrase_does_not():
    report = theme_recall(
        [
            "“I spend the first ninety minutes   every day figuring out who owes me money.”",
            "The owner says reports lack owner names.",
        ],
        THEMES,
    )
    assert report["per_theme"] == {"T1": True, "T2": False}
    assert report["recall"] == 0.5


def test_short_shared_fragment_is_not_enough():
    assert theme_recall(["who owes me money"], THEMES)["themes_found"] == 0
