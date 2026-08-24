import { useEffect, useState } from 'react'
import { getOdds } from '../api'
import GamesTable from '../components/GamesTable'

const WEEK_RANGE = {
  nfl: { min: 1, max: 18 },
  college: { min: 0, max: 15 },
}

export default function Home() {
  const [league, setLeague] = useState('nfl')
  const [week, setWeek] = useState(WEEK_RANGE.nfl.min)
  const [games, setGames] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const { min, max } = WEEK_RANGE[league]
  const weeks = Array.from({ length: max - min + 1 }, (_, i) => min + i)

  function handleLeagueChange(nextLeague) {
    setLeague(nextLeague)
    setWeek(WEEK_RANGE[nextLeague].min)
  }

  useEffect(() => {
    setLoading(true)
    setError(null)
    getOdds(league, week)
      .then(setGames)
      .catch(() => setError('Could not reach the API. Is the backend running on :8000?'))
      .finally(() => setLoading(false))
  }, [league, week])

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-2xl font-bold">Week {week} Games</h1>
        <div className="flex items-center gap-2">
          <select
            value={league}
            onChange={(e) => handleLeagueChange(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded px-3 py-1.5 text-sm"
          >
            <option value="nfl">NFL</option>
            <option value="college">College</option>
          </select>

          <div className="flex items-center rounded border border-slate-700 overflow-hidden">
            <button
              onClick={() => setWeek((w) => Math.max(min, w - 1))}
              disabled={week <= min}
              className="px-2.5 py-1.5 text-sm bg-slate-800 hover:bg-slate-700 disabled:opacity-30 disabled:hover:bg-slate-800"
              aria-label="Previous week"
            >
              ←
            </button>
            <select
              value={week}
              onChange={(e) => setWeek(Number(e.target.value))}
              className="bg-slate-800 px-3 py-1.5 text-sm border-x border-slate-700"
            >
              {weeks.map((w) => (
                <option key={w} value={w}>
                  Week {w}
                </option>
              ))}
            </select>
            <button
              onClick={() => setWeek((w) => Math.min(max, w + 1))}
              disabled={week >= max}
              className="px-2.5 py-1.5 text-sm bg-slate-800 hover:bg-slate-700 disabled:opacity-30 disabled:hover:bg-slate-800"
              aria-label="Next week"
            >
              →
            </button>
          </div>
        </div>
      </div>

      {error && <p className="text-red-400 text-sm">{error}</p>}
      {loading ? <p className="text-slate-500">Loading odds…</p> : <GamesTable games={games} />}
    </div>
  )
}
