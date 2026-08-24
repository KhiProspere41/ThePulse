import { useState } from 'react'
import { useSlip } from '../slipContext'
import { createSlip } from '../api'
import { formatPrice } from '../format'
import { parlayCombinedPrice } from '../parlayMath'

export default function SlipPanel() {
  const { legs, removeLeg, clearSlip } = useSlip()
  const [open, setOpen] = useState(false)
  const [mode, setMode] = useState('straight')
  const [parlayStake, setParlayStake] = useState(1)
  const [stakes, setStakes] = useState({}) // key -> stake, straight mode
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [placed, setPlaced] = useState(null) // last-placed slip summary, shown briefly

  if (legs.length === 0 && !placed) return null

  const canParlay = legs.length >= 2
  const combinedPreview = canParlay ? parlayCombinedPrice(legs.map((l) => l.entry_price)) : null

  function stakeFor(key) {
    return stakes[key] ?? 1
  }

  async function handlePlace() {
    setSaving(true)
    setError(null)
    try {
      const payload =
        mode === 'parlay'
          ? {
              mode: 'parlay',
              stake: Number(parlayStake),
              legs: legs.map((l) => ({
                game_id: l.game_id,
                bet_type: l.bet_type,
                market: l.market,
                selection: l.selection,
                player: l.player,
                point: l.point,
                entry_price: l.entry_price,
              })),
            }
          : {
              mode: 'straight',
              legs: legs.map((l) => ({
                game_id: l.game_id,
                bet_type: l.bet_type,
                market: l.market,
                selection: l.selection,
                player: l.player,
                point: l.point,
                entry_price: l.entry_price,
                stake: Number(stakeFor(l.key)),
              })),
            }
      const slip = await createSlip(payload)
      setPlaced({ mode: slip.mode, legCount: slip.legs.length })
      clearSlip()
      setStakes({})
      setOpen(false)
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Failed to place slip')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed bottom-4 right-4 z-20 w-80">
      {placed && !open && legs.length === 0 && (
        <div className="mb-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-400 flex items-center justify-between">
          <span>
            Placed {placed.legCount} {placed.mode === 'parlay' ? 'leg parlay' : 'pick(s)'} ✓
          </span>
          <button onClick={() => setPlaced(null)} className="text-emerald-400/70 hover:text-emerald-300">
            ✕
          </button>
        </div>
      )}

      {legs.length > 0 && (
        <div className="rounded-lg border border-slate-800 bg-slate-950 shadow-xl overflow-hidden">
          <button
            onClick={() => setOpen((o) => !o)}
            className="w-full flex items-center justify-between px-4 py-3 bg-slate-900 hover:bg-slate-800 transition-colors"
          >
            <span className="font-semibold text-slate-100">Bet Slip</span>
            <span className="flex items-center gap-2">
              <span className="bg-emerald-500 text-slate-950 text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center">
                {legs.length}
              </span>
              <span className="text-slate-500 text-xs">{open ? '▾' : '▴'}</span>
            </span>
          </button>

          {open && (
            <div className="p-4 space-y-3 max-h-[70vh] overflow-y-auto">
              <div className="space-y-2">
                {legs.map((leg) => (
                  <div key={leg.key} className="flex items-start justify-between gap-2 border-b border-slate-800 pb-2">
                    <div className="min-w-0">
                      <div className="text-sm text-slate-100 truncate">{leg.label}</div>
                      <div className="text-xs text-slate-500 truncate">{leg.matchup}</div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="text-sm font-mono tabular-nums text-slate-300">
                        {formatPrice(leg.entry_price)}
                      </span>
                      <button
                        onClick={() => removeLeg(leg.key)}
                        className="text-slate-500 hover:text-red-400 text-xs"
                        aria-label="Remove"
                      >
                        ✕
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              {canParlay && (
                <div className="flex gap-1 rounded-md bg-slate-900 p-1 text-xs">
                  {['straight', 'parlay'].map((m) => (
                    <button
                      key={m}
                      onClick={() => setMode(m)}
                      className={`flex-1 rounded py-1.5 font-medium capitalize transition-colors ${
                        mode === m ? 'bg-emerald-500/15 text-emerald-400' : 'text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      {m}
                    </button>
                  ))}
                </div>
              )}

              {mode === 'straight' || !canParlay ? (
                <div className="space-y-2">
                  {legs.map((leg) => (
                    <label key={leg.key} className="flex items-center justify-between text-xs text-slate-400 gap-2">
                      <span className="truncate">{leg.label}</span>
                      <input
                        type="number"
                        step="0.25"
                        min="0"
                        value={stakeFor(leg.key)}
                        onChange={(e) => setStakes((s) => ({ ...s, [leg.key]: e.target.value }))}
                        className="w-16 bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-100 text-right"
                      />
                    </label>
                  ))}
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-slate-400">Combined odds</span>
                    <span className="font-mono tabular-nums text-emerald-400 font-semibold">
                      {combinedPreview != null ? formatPrice(combinedPreview) : '—'}
                    </span>
                  </div>
                  <label className="flex items-center justify-between text-xs text-slate-400">
                    Stake (units)
                    <input
                      type="number"
                      step="0.25"
                      min="0"
                      value={parlayStake}
                      onChange={(e) => setParlayStake(e.target.value)}
                      className="w-16 bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-100 text-right"
                    />
                  </label>
                </div>
              )}

              {error && <p className="text-red-400 text-xs">{error}</p>}

              <div className="flex gap-2">
                <button
                  onClick={clearSlip}
                  className="flex-1 rounded py-2 text-xs font-medium text-slate-400 hover:text-slate-200 border border-slate-800"
                >
                  Clear
                </button>
                <button
                  onClick={handlePlace}
                  disabled={saving}
                  className="flex-[2] bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-slate-950 font-semibold rounded py-2 text-sm transition-colors"
                >
                  {saving
                    ? 'Placing…'
                    : mode === 'parlay' && canParlay
                      ? `Place Parlay (${legs.length} legs)`
                      : `Place ${legs.length} Bet${legs.length > 1 ? 's' : ''}`}
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
