import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getLines } from '../api'
import OddsComparisonTable from '../components/OddsComparisonTable'
import PickForm from '../components/PickForm'
import { formatDate } from '../format'

export default function GameDetail() {
  const { id } = useParams()
  const [data, setData] = useState(null)
  const [prefill, setPrefill] = useState(null)
  const [error, setError] = useState(null)
  const [savedMsg, setSavedMsg] = useState(false)

  function refresh() {
    getLines(id)
      .then(setData)
      .catch(() => setError('Could not load lines for this game.'))
  }

  useEffect(refresh, [id])

  if (error) return <div className="max-w-6xl mx-auto px-4 py-8 text-red-400">{error}</div>
  if (!data) return <div className="max-w-6xl mx-auto px-4 py-8 text-slate-500">Loading…</div>

  const { game, bookmakers } = data

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
      <Link to="/" className="text-emerald-400 text-sm hover:underline">
        ← All games
      </Link>

      <div>
        <h1 className="text-2xl font-bold">
          {game.away_team} @ {game.home_team}
        </h1>
        <p className="text-slate-400 text-sm">{formatDate(game.commence_time)}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <OddsComparisonTable
            game={game}
            bookmakers={bookmakers}
            onPick={(odd, row) => {
              setSavedMsg(false)
              setPrefill({ odd, row })
            }}
          />
        </div>
        <div>
          <PickForm
            game={game}
            prefill={prefill}
            onSaved={() => {
              setSavedMsg(true)
              setPrefill(null)
            }}
          />
          {savedMsg && <p className="text-emerald-400 text-xs mt-2">Pick saved ✓</p>}
        </div>
      </div>
    </div>
  )
}
