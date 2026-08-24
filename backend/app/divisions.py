"""NFL conference/division structure, keyed by the same nflverse abbreviations
used by `teams.to_elo_key` and the `team_elo` table.

The Odds API has no division-winner or season-win-total feed (its only NFL
futures sport key is `americanfootball_nfl_super_bowl_winner`), so these
markets are modelled locally by `app.simulate` rather than aggregated. This
module supplies the league structure that simulation needs.
"""

DIVISIONS: dict[str, tuple[str, ...]] = {
    "AFC East": ("BUF", "MIA", "NE", "NYJ"),
    "AFC North": ("BAL", "CIN", "CLE", "PIT"),
    "AFC South": ("HOU", "IND", "JAX", "TEN"),
    "AFC West": ("DEN", "KC", "LAC", "LV"),
    "NFC East": ("DAL", "NYG", "PHI", "WAS"),
    "NFC North": ("CHI", "DET", "GB", "MIN"),
    "NFC South": ("ATL", "CAR", "NO", "TB"),
    "NFC West": ("ARI", "LA", "SEA", "SF"),
}

TEAM_TO_DIVISION: dict[str, str] = {
    team: division for division, teams in DIVISIONS.items() for team in teams
}

TEAM_TO_CONFERENCE: dict[str, str] = {
    team: division.split()[0] for division, teams in DIVISIONS.items() for team in teams
}

ALL_TEAMS: tuple[str, ...] = tuple(sorted(TEAM_TO_DIVISION))

CONFERENCES: tuple[str, ...] = ("AFC", "NFC")

# Historical abbreviations that appear in older nflverse schedules, mapped to
# the franchise's current abbreviation so replayed history lands on the right
# team. Without these, e.g. 2019 Raiders games would create a phantom "OAK".
LEGACY_ABBR: dict[str, str] = {
    "OAK": "LV",
    "SD": "LAC",
    "STL": "LA",
    "LAR": "LA",
    "WSH": "WAS",
    "ARZ": "ARI",
    "BLT": "BAL",
    "CLV": "CLE",
    "HST": "HOU",
    "JAC": "JAX",
}


def normalize(abbr: str) -> str:
    """Map any known historical abbreviation onto the current franchise code."""
    return LEGACY_ABBR.get(abbr, abbr)


def division_of(abbr: str) -> str | None:
    return TEAM_TO_DIVISION.get(normalize(abbr))


def conference_of(abbr: str) -> str | None:
    return TEAM_TO_CONFERENCE.get(normalize(abbr))
