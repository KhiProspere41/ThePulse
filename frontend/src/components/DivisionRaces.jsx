import { formatProb } from '../format'

/**
 * Division-title probabilities, grouped by division.
 *
 * No sportsbook feed publishes division winners through The Odds API, so these
 * are model numbers straight out of the season simulation — not market prices.
 * The header says so, because a probability with no price attached is easy to
 * mistake for one.
 */
export default function DivisionRaces({ teams, divisions }) {
  const byDivision = divisions.map((division) => ({
    division,
    teams: teams
      .filter((t) => t.division === division)
      .sort((a, b) => b.division_title_prob - a.division_title_prob),
  }))

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {byDivision.map(({ division, teams: divisionTeams }) => (
        <div key={division} className="rounded-lg border border-slate-800 bg-slate-900/40 p-4">
          <h3 className="font-semibold text-slate-200 text-sm mb-3">{division}</h3>
          <div className="space-y-2">
            {divisionTeams.map((team) => (
              <div key={team.team} className="flex items-center gap-3">
                <span className="w-10 text-xs font-bold text-slate-400 font-mono tabular-nums">{team.team}</span>
                <div className="flex-1 h-2 rounded-full bg-slate-800 overflow-hidden">
                  <div
                    className="h-full bg-emerald-500/70 rounded-full"
                    style={{ width: `${Math.max(1, team.division_title_prob * 100)}%` }}
                  />
                </div>
                <span className="w-16 text-right text-xs font-mono tabular-nums text-slate-300">
                  {formatProb(team.division_title_prob)}
                </span>
                <span className="w-16 text-right text-xs font-mono tabular-nums text-slate-500">
                  {team.mean_wins.toFixed(1)} W
                </span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
