import { useEffect, useState } from 'react'
import { getFuturesBoard } from '../api'
import SuperBowlBoard from '../components/SuperBowlBoard'
import DivisionRaces from '../components/DivisionRaces'
import WinTotalsTable from '../components/WinTotalsTable'
import PickForm from '../components/PickForm'
import { formatDate } from '../format'

const TABS = [
  { key: 'superbowl', label: 'Super Bowl' },
  { key: 'divisions', label: 'Division titles' },
  { key: 'wins', label: 'Season win totals' },
]

export default function Futures() {
  const [tab, setTab] = useState('superbowl')
  const [board, setBoard] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [prefill, setPrefill] = useState(null)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    setLoading(true)
    getFuturesBoard()
      .then(setBoard)
      .catch(() => setError('Could not reach the API. Is the backend running on :8000?'))
      .finally(() => setLoading(false))
  }, [])

  if (error) return <div className="max-w-6xl mx-auto px-4 py-8 text-red-400">{error}</div>
  if (loading || !board) {
    return <div className="max-w-6xl mx-auto px-4 py-8 text-slate-500">Simulating the season…</div>
  }

  const { schedule } = board

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold">{board.season} Team Futures</h1>
          <p className="text-slate-500 text-sm mt-1">
            {board.iterations.toLocaleString()} simulated seasons ({schedule.games_completed} games played,{' '}
            {schedule.games_remaining} to go) · updated {formatDate(board.generated_at)}
          </p>
        </div>
        <nav className="flex gap-1">
          {TABS.map((entry) => (
            <button
              key={entry.key}
              onClick={() => setTab(entry.key)}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                tab === entry.key
                  ? 'bg-emerald-500/10 text-emerald-400'
                  : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800'
              }`}
            >
              {entry.label}
            </button>
          ))}
        </nav>
      </div>

      {!schedule.complete && (
        <p className="text-xs text-amber-400 border border-amber-500/20 bg-amber-500/5 rounded px-3 py-2">
          Only {schedule.games_known} of {schedule.games_expected} games are loaded, so each team's
          remaining schedule is padded with league-average opponents. Run{' '}
          <code className="text-amber-300">python -m app.scripts.load_schedule</code> for the real one.
        </p>
      )}

      {tab === 'superbowl' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <SuperBowlBoard
              teams={board.teams}
              onPick={(team) => {
                setSaved(false)
                setPrefill({
                  betType: 'futures',
                  market: 'outrights',
                  selection: team.name,
                  price: team.market.best_price,
                  point: null,
                })
              }}
            />
          </div>
          <div className="space-y-3">
            {prefill ? (
              <>
                <PickForm
                  prefill={prefill}
                  onSaved={() => {
                    setSaved(true)
                    setPrefill(null)
                  }}
                />
                {saved && <p className="text-emerald-400 text-xs">Pick saved ✓</p>}
              </>
            ) : (
              <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-400 space-y-2">
                <p className="font-semibold text-slate-200">Model vs. market</p>
                <p className="text-xs leading-relaxed">
                  Super Bowl prices are the only NFL futures feed The Odds API carries. Each book's
                  board is stripped of vig before comparison. Raw Super Bowl boards hold well over
                  30%, which would make every team look like value.
                </p>
                <p className="text-xs leading-relaxed">
                  Division titles and win totals have no feed at all, so those tabs are pure model
                  output from the same simulation.
                </p>
                <p className="text-xs text-slate-500">Click “Log pick” on any row to track a bet.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {tab === 'divisions' && <DivisionRaces teams={board.teams} divisions={board.divisions} />}

      {tab === 'wins' && <WinTotalsTable teams={board.teams} thresholds={board.win_thresholds} />}

      {tab !== 'superbowl' && (
        <p className="text-xs text-slate-500 border-t border-slate-800 pt-4">
          Model output, not market prices. No sportsbook feed for these markets is available through
          The Odds API. Simulated from current Elo ratings; ties in the standings are broken at random
          rather than by the real NFL tiebreakers.
        </p>
      )}
    </div>
  )
}
