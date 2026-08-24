import { useEffect, useState } from 'react'
import { getDashboard, getEloValue } from '../api'
import StatCard from '../components/StatCard'
import ClvTrendChart from '../components/ClvTrendChart'
import LeagueWeekSelector from '../components/LeagueWeekSelector'
import { formatPct } from '../format'
import { WEEK_RANGE } from '../weeks'

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [eloLeague, setEloLeague] = useState('nfl')
  const [eloWeek, setEloWeek] = useState(WEEK_RANGE.nfl.min)
  const [eloValue, setEloValue] = useState([])

  function handleEloLeagueChange(nextLeague) {
    setEloLeague(nextLeague)
    setEloWeek(WEEK_RANGE[nextLeague].min)
  }

  useEffect(() => {
    getDashboard().then(setStats)
  }, [])

  useEffect(() => {
    getEloValue(eloLeague, eloWeek)
      .then(setEloValue)
      .catch(() => setEloValue([]))
  }, [eloLeague, eloWeek])

  if (!stats) return <div className="max-w-6xl mx-auto px-4 py-8 text-slate-500">Loading…</div>

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-8">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Win Rate" value={formatPct(stats.win_rate)} />
        <StatCard
          label="ROI"
          value={formatPct(stats.roi)}
          accent={stats.roi > 0 ? 'text-emerald-400' : stats.roi < 0 ? 'text-red-400' : undefined}
        />
        <StatCard label="Avg CLV" value={stats.avg_clv == null ? '—' : `${stats.avg_clv}%`} />
        <StatCard label="Settled Picks" value={`${stats.settled_picks} / ${stats.total_picks}`} />
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
        <h2 className="font-semibold text-slate-200 mb-2">CLV Trend</h2>
        <ClvTrendChart data={stats.clv_trend} />
      </div>

      <div>
        <div className="flex items-center justify-between flex-wrap gap-3 mb-2">
          <h2 className="font-semibold text-slate-200">
            Elo vs. Market — Week {eloWeek} (potential value)
          </h2>
          <LeagueWeekSelector
            league={eloLeague}
            week={eloWeek}
            onLeagueChange={handleEloLeagueChange}
            onWeekChange={setEloWeek}
          />
        </div>

        {eloValue.length === 0 ? (
          <p className="text-slate-500 text-sm py-6 text-center">
            No week {eloWeek} games with both an Elo rating and a moneyline yet. Run{' '}
            <code className="text-slate-400">compute_elo.py --league {eloLeague}</code> after loading
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
    </div>
  )
}
