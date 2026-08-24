import { Fragment } from 'react'
import { formatPoint, formatPrice, marketLabel } from '../format'
import { setPickResult } from '../api'

const RESULT_STYLES = {
  win: 'text-emerald-400',
  loss: 'text-red-400',
  push: 'text-slate-400',
  pending: 'text-amber-400',
}

function legLabel(pick) {
  return (
    <>
      {pick.player && <span className="text-slate-300">{pick.player}: </span>}
      <span className="capitalize">{pick.selection}</span> {formatPoint(pick.point)}
      <span className="text-slate-500 text-[10px] ml-1.5 uppercase tracking-wide">{marketLabel(pick.market)}</span>
    </>
  )
}

function legMatchup(pick) {
  return pick.game ? `${pick.game.away_team} @ ${pick.game.home_team}` : pick.bet_type === 'futures' ? 'Season futures' : pick.game_id
}

function ResultSelect({ pick, onChanged }) {
  async function handleResult(result) {
    await setPickResult(pick.id, result)
    onChanged?.()
  }
  return (
    <select
      value={pick.result}
      onChange={(e) => handleResult(e.target.value)}
      className={`bg-slate-800 border border-slate-700 rounded px-2 py-1 text-xs font-semibold ${RESULT_STYLES[pick.result]}`}
    >
      <option value="pending">Pending</option>
      <option value="win">Win</option>
      <option value="loss">Loss</option>
      <option value="push">Push</option>
    </select>
  )
}

export default function PicksList({ slips, onChanged }) {
  if (!slips.length) {
    return <div className="text-center py-16 text-slate-500">No picks logged yet. Go pick a game.</div>
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-800">
      <table className="w-full text-sm">
        <thead className="bg-slate-900 text-slate-400 uppercase text-xs tracking-wide">
          <tr>
            <th className="text-left px-4 py-3">Game</th>
            <th className="text-left px-4 py-3">Pick</th>
            <th className="text-right px-4 py-3">Entry</th>
            <th className="text-right px-4 py-3">Closing</th>
            <th className="text-right px-4 py-3">CLV</th>
            <th className="text-center px-4 py-3">Result</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {slips.map((slip) =>
            slip.mode === 'parlay' ? (
              <Fragment key={`slip-${slip.id}`}>
                <tr className="bg-slate-900/40">
                  <td className="px-4 py-3 text-slate-300" colSpan={2}>
                    <span className="text-emerald-400 font-semibold text-xs uppercase tracking-wide mr-2">
                      Parlay
                    </span>
                    {slip.legs.length} legs · stake {slip.stake}u
                  </td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums font-semibold text-slate-100">
                    {formatPrice(slip.combined_price)}
                  </td>
                  <td className="px-4 py-3 text-right text-slate-600">—</td>
                  <td className="px-4 py-3 text-right text-slate-600">n/a</td>
                  <td className="px-4 py-3 text-center">
                    <span className={`text-xs font-semibold uppercase ${RESULT_STYLES[slip.result] ?? 'text-amber-400'}`}>
                      {slip.result}
                    </span>
                  </td>
                </tr>
                {slip.legs.map((leg) => (
                  <tr key={leg.id} className="hover:bg-slate-900/60">
                    <td className="pl-8 pr-4 py-2 text-slate-500 text-xs">{legMatchup(leg)}</td>
                    <td className="px-4 py-2 text-slate-300 text-xs">{legLabel(leg)}</td>
                    <td className="px-4 py-2 text-right font-mono tabular-nums text-xs text-slate-400">
                      {formatPrice(leg.entry_price)}
                    </td>
                    <td className="px-4 py-2 text-right font-mono tabular-nums text-xs text-slate-400">
                      {formatPrice(leg.closing_price)}
                    </td>
                    <td className="px-4 py-2 text-right text-xs text-slate-500">
                      {leg.clv == null ? '—' : `${leg.clv > 0 ? '+' : ''}${leg.clv}%`}
                    </td>
                    <td className="px-4 py-2 text-center">
                      <ResultSelect pick={leg} onChanged={onChanged} />
                    </td>
                  </tr>
                ))}
              </Fragment>
            ) : (
              slip.legs.map((pick) => (
                <tr key={pick.id} className="hover:bg-slate-900/60">
                  <td className="px-4 py-3 text-slate-300">{legMatchup(pick)}</td>
                  <td className="px-4 py-3 font-medium text-slate-100">{legLabel(pick)}</td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums">{formatPrice(pick.entry_price)}</td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums">{formatPrice(pick.closing_price)}</td>
                  <td
                    className={`px-4 py-3 text-right font-mono tabular-nums font-semibold ${
                      pick.clv == null ? 'text-slate-500' : pick.clv >= 0 ? 'text-emerald-400' : 'text-red-400'
                    }`}
                  >
                    {pick.bet_type === 'futures' ? 'n/a' : pick.clv == null ? '—' : `${pick.clv > 0 ? '+' : ''}${pick.clv}%`}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <ResultSelect pick={pick} onChanged={onChanged} />
                  </td>
                </tr>
              ))
            )
          )}
        </tbody>
      </table>
    </div>
  )
}
