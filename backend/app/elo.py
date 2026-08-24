"""Simple Elo rating system for NFL teams."""

INITIAL_RATING = 1500.0
K_FACTOR = 20.0
HOME_FIELD_ADVANTAGE = 55.0  # Elo points added to the home team's rating pre-game


def expected_score(rating_a: float, rating_b: float) -> float:
    """Probability that team A beats team B, given their ratings."""
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def update_ratings(
    home_rating: float,
    away_rating: float,
    home_score: int,
    away_score: int,
    k: float = K_FACTOR,
) -> tuple[float, float]:
    """Return (new_home_rating, new_away_rating) after one game."""
    home_expected = expected_score(home_rating + HOME_FIELD_ADVANTAGE, away_rating)
    home_actual = 1.0 if home_score > away_score else (0.0 if home_score < away_score else 0.5)

    margin = abs(home_score - away_score)
    # Margin-of-victory multiplier (a common Elo variant, e.g. FiveThirtyEight's NFL model)
    mov_multiplier = ((margin + 3) ** 0.8) / (7.5 + 0.006 * abs(home_rating - away_rating))

    delta = k * mov_multiplier * (home_actual - home_expected)
    return home_rating + delta, away_rating - delta


def elo_win_prob(home_rating: float, away_rating: float) -> float:
    """Home team's win probability implied by Elo, including home-field advantage."""
    return expected_score(home_rating + HOME_FIELD_ADVANTAGE, away_rating)
