import { useEffect, useState } from 'react'
import { createPick } from '../api'

const SELECTION_OPTIONS = (game) => ({
  spreads: [game.home_team, game.away_team],
  h2h: [game.home_team, game.away_team],
  totals: ['over', 'under'],
})

export default function PickForm({ game, prefill, onSaved }) {
  const [market, setMarket] = useState('h2h')
  const [selection, setSelection] = useState(game.home_team)
  const [point, setPoint] = useState('')
  const [price, setPrice] = useState('')
  const [stake, setStake] = useState(1)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!prefill) return
    setMarket(prefill.row.market)
    setSelection(
      prefill.row.side === 'home'
        ? game.home_team
        : prefill.row.side === 'away'
          ? game.away_team
          : prefill.row.side
    )
    setPoint(prefill.odd.point ?? '')
    setPrice(prefill.odd.price)
  }, [prefill, game])

  const options = SELECTION_OPTIONS(game)[market]

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      await createPick({
        game_id: game.id,
        market,
        selection,
        point: point === '' ? null : Number(point),
        entry_price: Number(price),
        stake: Number(stake),
      })
      onSaved?.()
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Failed to save pick')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-slate-900 border border-slate-800 rounded-lg p-4 space-y-3">
      <h3 className="font-semibold text-slate-200">Log a pick</h3>

      <div className="grid grid-cols-2 gap-3">
        <label className="text-xs text-slate-400">
          Market
          <select
            value={market}
            onChange={(e) => {
              setMarket(e.target.value)
              setSelection(SELECTION_OPTIONS(game)[e.target.value][0])
            }}
            className="mt-1 w-full bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-slate-100"
          >
            <option value="h2h">Moneyline</option>
            <option value="spreads">Spread</option>
            <option value="totals">Total</option>
          </select>
        </label>

        <label className="text-xs text-slate-400">
          Selection
          <select
            value={selection}
            onChange={(e) => setSelection(e.target.value)}
            className="mt-1 w-full bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-slate-100 capitalize"
          >
            {options.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </label>

        {market !== 'h2h' && (
          <label className="text-xs text-slate-400">
            Point
            <input
              type="number"
              step="0.5"
              value={point}
              onChange={(e) => setPoint(e.target.value)}
              className="mt-1 w-full bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-slate-100"
            />
          </label>
        )}

        <label className="text-xs text-slate-400">
          Odds (American)
          <input
            type="number"
            required
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            className="mt-1 w-full bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-slate-100"
          />
        </label>

        <label className="text-xs text-slate-400">
          Stake (units)
          <input
            type="number"
            step="0.25"
            min="0"
            value={stake}
            onChange={(e) => setStake(e.target.value)}
            className="mt-1 w-full bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-slate-100"
          />
        </label>
      </div>

      {error && <p className="text-red-400 text-xs">{error}</p>}

      <button
        type="submit"
        disabled={saving}
        className="w-full bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-slate-950 font-semibold rounded py-2 text-sm transition-colors"
      >
        {saving ? 'Saving…' : 'Save Pick'}
      </button>
    </form>
  )
}
