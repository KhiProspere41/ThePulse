import { useEffect, useState } from 'react'
import { getEloValue } from '../api'
import LeagueWeekSelector from '../components/LeagueWeekSelector'
import { formatPct } from '../format'
import { WEEK_RANGE } from '../weeks'

export default function EloValue() {
  const [league, setLeague] = useState('nfl')
  const [week, setWeek] = useState(WEEK_RANGE.nfl.min)
  const [eloValue, setEloValue] = useState([])

  function handleLeagueChange(nextLeague) {
    setLeague(nextLeague)
    setWeek(WEEK_RANGE[nextLeague].min)
  }

  useEffect(() => {
    getEloValue(league, week)
      .then(setEloValue)
      .catch(() => setEloValue([]))
  }, [league, week])

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-2xl font-bold">Elo vs. Market — Week {week}</h1>
        <LeagueWeekSelector
          league={league}
          week={week}
          onLeagueChange={handleLeagueChange}
          onWeekChange={setWeek}
        />
      </div>

      {eloValue.length === 0 ? (
        <p className="text-slate-500 text-sm py-16 text-center">
          No week {week} games with both an Elo rating and a moneyline yet. Run{' '}
          <code className="text-slate-400">compute_elo.py --league {league}</code> after loading
          historical data.
        </p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-800">
          <table className="w-full text-sm">
            <thead className="bg-slate-900 text-slate-400 uppercase text-xs tracking-wide">
              <tr>
                <th className="text-left px-4 py-3">Matchup</th>
                <th className="text-right px-4 py-3">Elo Home Win %</th>
                <th className="text-right px-4 py-3">Market Home Win %</th>
                <th className="text-right px-4 py-3">Edge</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {eloValue.map((g) => (
                <tr key={g.game_id} className="hover:bg-slate-900/60">
                  <td className="px-4 py-3">{g.matchup}</td>
                  <td className="px-4 py-3 text-right tabular-nums">{formatPct(g.elo_home_win_prob)}</td>
                  <td className="px-4 py-3 text-right tabular-nums">{formatPct(g.market_home_win_prob)}</td>
                  <td
                    className={`px-4 py-3 text-right tabular-nums font-semibold ${
                      g.edge >= 0 ? 'text-emerald-400' : 'text-red-400'
                    }`}
                  >
                    {g.edge > 0 ? '+' : ''}
                    {formatPct(g.edge)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
