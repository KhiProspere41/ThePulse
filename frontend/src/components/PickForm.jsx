import { useEffect, useState } from 'react'
import { createPick } from '../api'
import { marketLabel } from '../format'

const GAME_MARKETS = ['h2h', 'spreads', 'totals']

const gameSelections = (game) => ({
  spreads: [game.home_team, game.away_team],
  h2h: [game.home_team, game.away_team],
  totals: ['over', 'under'],
})

/**
 * Logs a pick. Handles all three bet types the tracker supports:
 *
 *   game        — moneyline / spread / total on a specific game
 *   player_prop — a player's over/under or anytime-TD price
 *   futures     — an outright, which has no game attached at all
 *
 * The market, selection and player are fixed by whatever line was clicked for
 * the last two: those come from a real posted price, and letting them be
 * retyped just invites a pick that matches nothing when CLV is backfilled.
 */
export default function PickForm({ game, prefill, onSaved }) {
  const betType = prefill?.betType ?? 'game'
  const [market, setMarket] = useState('h2h')
  const [selection, setSelection] = useState(game ? game.home_team : '')
  const [point, setPoint] = useState('')
  const [price, setPrice] = useState('')
  const [stake, setStake] = useState(1)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!prefill) return
    setMarket(prefill.market)
    setSelection(prefill.selection)
    setPoint(prefill.point ?? '')
    setPrice(prefill.price)
    setError(null)
  }, [prefill])

  const isGameBet = betType === 'game'
  const options = isGameBet && game ? gameSelections(game)[market] : []

  async function handleSubmit(event) {
    event.preventDefault()
    setSaving(true)
    setError(null)
    try {
      await createPick({
        // A futures pick belongs to a season, not a game — the API rejects it
        // outright if a game_id comes along for the ride.
        game_id: betType === 'futures' ? null : game?.id,
        bet_type: betType,
        market,
        selection,
        player: betType === 'player_prop' ? prefill?.player : null,
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

      {!isGameBet && (
        <div className="rounded border border-slate-800 bg-slate-950/50 px-3 py-2 text-xs">
          <div className="text-slate-500 uppercase tracking-wide text-[10px]">
            {betType === 'futures' ? 'Futures' : marketLabel(market)}
          </div>
          <div className="text-slate-100 font-medium mt-0.5">
            {prefill?.player ? `${prefill.player} — ` : ''}
            <span className="capitalize">{selection}</span>
            {point !== '' && point != null ? ` ${point}` : ''}
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3">
        {isGameBet && (
          <>
            <label className="text-xs text-slate-400">
              Market
              <select
                value={market}
                onChange={(e) => {
                  setMarket(e.target.value)
                  setSelection(gameSelections(game)[e.target.value][0])
                }}
                className="mt-1 w-full bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-slate-100"
              >
                {GAME_MARKETS.map((key) => (
                  <option key={key} value={key}>
                    {marketLabel(key)}
                  </option>
                ))}
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
          </>
        )}

        {isGameBet && market !== 'h2h' && (
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
        disabled={saving || price === ''}
        className="w-full bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-slate-950 font-semibold rounded py-2 text-sm transition-colors"
      >
        {saving ? 'Saving…' : 'Save Pick'}
      </button>

      {betType === 'futures' && (
        <p className="text-[11px] text-slate-500">
          Futures settle at the end of the season and have no kickoff, so no closing line or CLV is
          tracked for them.
        </p>
      )}
    </form>
  )
}
