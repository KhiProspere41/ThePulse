# ThePulse

**[the-pulse-liard-eight.vercel.app](https://the-pulse-liard-eight.vercel.app)**

A football betting odds aggregator and pick tracker. Live lines from real
sportsbooks, side-by-side comparison, a pick tracker that scores itself
against the closing line, and a model that prices markets no sportsbook
feed covers.

## What it does

- **Live odds**, every week of the NFL and college football (FBS) season —
  spread, moneyline, and total, aggregated from multiple sportsbooks
- **Side-by-side book comparison** for every game, so the best number is
  obvious at a glance
- **NFL player props** — passing/rushing/receiving yards, touchdowns,
  receptions, anytime TD
- **Team futures** — Super Bowl odds priced against the real market, plus
  division titles and season win totals, which no sportsbook publishes a
  feed for and are instead modeled by a Monte Carlo season simulation
- **Pick tracking** that captures the line at the moment you make a pick and
  scores it against the closing line (CLV), with win rate, ROI, and a CLV
  trend chart
- **An Elo model**, for both NFL and college teams, flagging games where the
  model's win probability diverges from the market's

## Built with

FastAPI · SQLAlchemy · PostgreSQL (Neon) · React · Vite · TailwindCSS
Deployed on Render (API) and Vercel (frontend).

---

Want to run this yourself or read about how it's built? See
[docs/SETUP.md](docs/SETUP.md).
