import { useCallback, useEffect, useState } from 'react'
import { getProps } from '../api'
import PlayerPropsTable from './PlayerPropsTable'
import { formatDate } from '../format'

/**
 * Loads and displays player props for one game.
 *
 * Props are billed per market per event by The Odds API, so this only ever
 * reads the cache on mount — the refresh button is the single path that spends
 * credits, and it says so.
 */
export default function PlayerPropsPanel({ gameId, onPick }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState(null)

  // Memoised on gameId so the effect below re-runs when the game changes and
  // at no other time — this endpoint can spend API credits, so an accidental
  // re-fetch on every render is not a cosmetic problem.
  const load = useCallback(
    (refresh = false) => {
      if (refresh) setRefreshing(true)
      else setLoading(true)
      setError(null)
      return getProps(gameId, refresh)
        .then(setData)
        .catch(() => setError('Could not load player props.'))
        .finally(() => {
          setLoading(false)
          setRefreshing(false)
        })
    },
    [gameId]
  )

  useEffect(() => {
    load(false)
  }, [load])

  const books = data ? [...new Set(data.props.map((p) => p.bookmaker))].sort() : []

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h2 className="text-lg font-semibold text-slate-100">Player props</h2>
          {data?.fetched_at && (
            <p className="text-xs text-slate-500">Prices as of {formatDate(data.fetched_at)}</p>
          )}
        </div>
        <button
          onClick={() => load(true)}
          disabled={refreshing || loading}
          title="Refetch from the sportsbooks — uses Odds API credits"
          className="text-xs font-semibold px-3 py-1.5 rounded border border-slate-700 text-slate-300 hover:bg-slate-800 disabled:opacity-40"
        >
          {refreshing ? 'Refreshing…' : 'Refresh (uses credits)'}
        </button>
      </div>

      {error && <p className="text-red-400 text-sm">{error}</p>}

      {data?.detail && (
        <p className={`text-xs ${data.stale ? 'text-amber-400' : 'text-slate-500'}`}>{data.detail}</p>
      )}

      {loading ? (
        <p className="text-slate-500 text-sm">Loading props…</p>
      ) : data && data.props.length > 0 ? (
        <PlayerPropsTable props={data.props} books={books} onPick={onPick} />
      ) : (
        !data?.detail && <p className="text-slate-500 text-sm">No player props available.</p>
      )}
    </section>
  )
}
