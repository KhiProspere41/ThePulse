import { useState } from 'react'
import { formatProb } from '../format'

// The three thresholds worth looking at first for a rebuilding team; every
// other threshold is one click away.
const DEFAULT_THRESHOLDS = [4, 5, 6]

function probColor(value) {
  if (value >= 0.66) return 'text-emerald-400'
  if (value >= 0.33) return 'text-slate-200'
  return 'text-slate-500'
}

/**
 * Season win totals as a cumulative ladder: P(the team wins at least k games),
 * for whichever thresholds are selected.
 *
 * Also model output, not a market. Sportsbooks price season win totals as an
 * over/under, but The Odds API doesn't carry that market, so there's nothing
 * to shop against here — this is the projection on its own.
 */
export default function WinTotalsTable({ teams, thresholds }) {
  const [selected, setSelected] = useState(DEFAULT_THRESHOLDS)
  const [sortBy, setSortBy] = useState('mean_wins')

  function toggle(threshold) {
    setSelected((current) =>
      current.includes(threshold)
        ? current.filter((t) => t !== threshold)
        : [...current, threshold].sort((a, b) => a - b)
    )
  }

  const columns = selected.length ? selected : DEFAULT_THRESHOLDS
  const sorted = [...teams].sort((a, b) =>
    sortBy === 'mean_wins'
      ? b.mean_wins - a.mean_wins
      : (b.win_at_least[sortBy] ?? 0) - (a.win_at_least[sortBy] ?? 0)
  )

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-slate-500 uppercase tracking-wide mr-1">At least</span>
        {thresholds.map((threshold) => (
          <button
            key={threshold}
            onClick={() => toggle(threshold)}
            className={`w-9 py-1 rounded text-xs font-semibold font-mono tabular-nums transition-colors ${
              columns.includes(threshold)
                ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                : 'border border-slate-800 text-slate-500 hover:text-slate-200 hover:border-slate-700'
            }`}
          >
            {threshold}
          </button>
        ))}
        <span className="text-xs text-slate-500">wins</span>
      </div>

      <div className="overflow-x-auto rounded-lg border border-slate-800">
        <table className="w-full text-sm">
          <thead className="bg-slate-900 text-slate-400 uppercase text-xs tracking-wide">
            <tr>
              <th className="text-left px-4 py-3">Team</th>
              <th className="text-left px-4 py-3">Division</th>
              <th className="text-right px-4 py-3">Elo</th>
              <th className="text-right px-4 py-3">
                <button onClick={() => setSortBy('mean_wins')} className="hover:text-slate-200">
                  Proj. wins
                </button>
              </th>
              {columns.map((threshold) => (
                <th key={threshold} className="text-right px-4 py-3 whitespace-nowrap">
                  <button
                    onClick={() => setSortBy(String(threshold))}
                    className="hover:text-slate-200"
                  >
                    {threshold}+ W
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {sorted.map((team) => (
              <tr key={team.team} className="hover:bg-slate-900/60">
                <td className="px-4 py-3 font-medium text-slate-100 whitespace-nowrap">
                  <span className="font-bold text-slate-400 mr-2 text-xs">{team.team}</span>
                  {team.name}
                </td>
                <td className="px-4 py-3 text-slate-500 text-xs">{team.division}</td>
                <td className="px-4 py-3 text-right font-mono tabular-nums text-slate-400">{team.elo}</td>
                <td className="px-4 py-3 text-right font-mono tabular-nums text-slate-200 font-semibold">
                  {team.mean_wins.toFixed(1)}
                </td>
                {columns.map((threshold) => {
                  const value = team.win_at_least[String(threshold)] ?? 0
                  return (
                    <td
                      key={threshold}
                      className={`px-4 py-3 text-right font-mono tabular-nums ${probColor(value)}`}
                    >
                      {formatProb(value)}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
