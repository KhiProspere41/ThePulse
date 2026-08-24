import { useEffect, useState } from 'react'
import { getPlayerStatsAwards, getPlayerStatsLeaders } from '../api'
import StatLeadersTable from '../components/StatLeadersTable'
import AwardsPanel from '../components/AwardsPanel'

const TABS = [
  { key: 'overall', label: 'Top 50' },
  { key: 'passing', label: 'Passing' },
  { key: 'rushing', label: 'Rushing' },
  { key: 'receiving', label: 'Receiving' },
  { key: 'defense', label: 'Defense' },
  { key: 'awards', label: 'Awards' },
]

export default function PlayerStats() {
  const [tab, setTab] = useState('overall')
  const [season, setSeason] = useState(null)
  const [leaders, setLeaders] = useState(null)
  const [awards, setAwards] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    setError(null)
    const onError = (e) =>
      setError(e.response?.data?.detail ?? 'Could not reach the API. Is the backend running on :8000?')

    if (tab === 'awards') {
      getPlayerStatsAwards()
        .then((d) => {
          setSeason(d.season)
          setAwards(d)
        })
        .catch(onError)
    } else {
      getPlayerStatsLeaders(tab)
        .then((d) => {
          setSeason(d.season)
          setLeaders(d)
        })
        .catch(onError)
    }
  }, [tab])

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold">NFL Player Stats{season ? ` (${season})` : ''}</h1>
          <p className="text-slate-500 text-sm mt-1">Real season stats from nflverse, not sportsbook props.</p>
        </div>
        <nav className="flex gap-1 flex-wrap">
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

      {error && (
        <p className="text-red-400 text-sm border border-red-500/20 bg-red-500/5 rounded px-3 py-2">
          {error}
        </p>
      )}

      {!error && tab === 'awards' &&
        (awards ? <AwardsPanel data={awards} /> : <p className="text-slate-500">Loading…</p>)}

      {!error && tab !== 'awards' &&
        (leaders && leaders.category === tab ? (
          <StatLeadersTable category={tab} players={leaders.players} />
        ) : (
          <p className="text-slate-500">Loading…</p>
        ))}
    </div>
  )
}
