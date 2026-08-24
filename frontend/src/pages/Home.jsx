import { useEffect, useState } from 'react'
import { getOdds } from '../api'
import GamesTable from '../components/GamesTable'
import LeagueWeekSelector from '../components/LeagueWeekSelector'
import { WEEK_RANGE } from '../weeks'

export default function Home() {
  const [league, setLeague] = useState('nfl')
  const [week, setWeek] = useState(WEEK_RANGE.nfl.min)
  const [games, setGames] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

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
        <LeagueWeekSelector
          league={league}
          week={week}
          onLeagueChange={handleLeagueChange}
          onWeekChange={setWeek}
        />
      </div>

      {error && <p className="text-red-400 text-sm">{error}</p>}
      {loading ? <p className="text-slate-500">Loading odds…</p> : <GamesTable games={games} />}
    </div>
  )
}
