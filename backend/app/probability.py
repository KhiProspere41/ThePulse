"""Odds <-> implied-probability conversions."""

import math


def american_to_implied_prob(price: int) -> float:
    """Convert American odds to raw (vig-included) implied win probability, 0-1."""
    if price > 0:
        return 100 / (price + 100)
    return -price / (-price + 100)


def remove_vig(prob_a: float, prob_b: float) -> tuple[float, float]:
    """Normalize two implied probabilities that sum to >1 (the vig) back to 1."""
    total = prob_a + prob_b
    if total <= 0:
        return prob_a, prob_b
    return prob_a / total, prob_b / total


# Standard deviation of NFL final-score margin, commonly used to translate a
# point spread into a win probability via the normal CDF.
NFL_MARGIN_STDEV = 13.86


def spread_to_implied_prob(spread: float, stdev: float = NFL_MARGIN_STDEV) -> float:
    """Win probability for the team favored by `spread` points (negative = favorite)."""
    return 0.5 * (1 + math.erf(-spread / (stdev * math.sqrt(2))))


def american_to_decimal(price: int) -> float:
    """American odds -> decimal odds (the multiplier on stake for a win, stake included)."""
    return 1 + price / 100 if price > 0 else 1 + 100 / -price


def decimal_to_american(decimal: float) -> int:
    """Decimal odds -> American odds, rounded to the nearest whole number."""
    return round((decimal - 1) * 100) if decimal >= 2 else round(-100 / (decimal - 1))


def parlay_combined_price(leg_prices: list[int]) -> int:
    """Combined American odds for a parlay: each leg's decimal odds multiply
    together (the standard sportsbook calculation), then convert back."""
    combined_decimal = 1.0
    for price in leg_prices:
        combined_decimal *= american_to_decimal(price)
    return decimal_to_american(combined_decimal)
