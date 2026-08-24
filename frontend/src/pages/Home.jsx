import { useEffect, useState } from 'react'
import { getOdds } from '../api'
import GamesTable from '../components/GamesTable'

export default function Home() {
  const [league, setLeague] = useState('nfl')
  const [week, setWeek] = useState('')
  const [games, setGames] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    getOdds(league, week || undefined)
      .then(setGames)
      .catch(() => setError('Could not reach the API. Is the backend running on :8000?'))
      .finally(() => setLoading(false))
  }, [league, week])

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-2xl font-bold">This Week's Games</h1>
        <div className="flex gap-2">
          <select
            value={league}
            onChange={(e) => setLeague(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded px-3 py-1.5 text-sm"
          >
            <option value="nfl">NFL</option>
            <option value="college">College</option>
          </select>
          <input
            type="number"
            placeholder="Week #"
            value={week}
            onChange={(e) => setWeek(e.target.value)}
            className="w-24 bg-slate-800 border border-slate-700 rounded px-3 py-1.5 text-sm"
          />
        </div>
      </div>

      {error && <p className="text-red-400 text-sm">{error}</p>}
      {loading ? <p className="text-slate-500">Loading odds…</p> : <GamesTable games={games} />}
    </div>
  )
}
