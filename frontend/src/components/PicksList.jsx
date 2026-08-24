import { formatPoint, formatPrice, marketLabel } from '../format'
import { setPickResult } from '../api'

const RESULT_STYLES = {
  win: 'text-emerald-400',
  loss: 'text-red-400',
  push: 'text-slate-400',
  pending: 'text-amber-400',
}

export default function PicksList({ picks, onChanged }) {
  if (!picks.length) {
    return <div className="text-center py-16 text-slate-500">No picks logged yet. Go pick a game.</div>
  }

  async function handleResult(id, result) {
    await setPickResult(id, result)
    onChanged?.()
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
          {picks.map((pick) => (
            <tr key={pick.id} className="hover:bg-slate-900/60">
              <td className="px-4 py-3 text-slate-300">
                {pick.game
                  ? `${pick.game.away_team} @ ${pick.game.home_team}`
                  : pick.bet_type === 'futures'
                    ? 'Season futures'
                    : pick.game_id}
              </td>
              <td className="px-4 py-3 font-medium text-slate-100">
                {pick.player && <span className="text-slate-300">{pick.player}: </span>}
                <span className="capitalize">{pick.selection}</span> {formatPoint(pick.point)}
                <span className="text-slate-500 text-[10px] ml-1.5 uppercase tracking-wide">
                  {marketLabel(pick.market)}
                </span>
              </td>
              <td className="px-4 py-3 text-right font-mono tabular-nums">{formatPrice(pick.entry_price)}</td>
              <td className="px-4 py-3 text-right font-mono tabular-nums">{formatPrice(pick.closing_price)}</td>
              <td
                className={`px-4 py-3 text-right font-mono tabular-nums font-semibold ${
                  pick.clv == null ? 'text-slate-500' : pick.clv >= 0 ? 'text-emerald-400' : 'text-red-400'
                }`}
              >
                {pick.bet_type === 'futures'
                  ? 'n/a'
                  : pick.clv == null
                    ? '—'
                    : `${pick.clv > 0 ? '+' : ''}${pick.clv}%`}
              </td>
              <td className="px-4 py-3 text-center">
                <select
                  value={pick.result}
                  onChange={(e) => handleResult(pick.id, e.target.value)}
                  className={`bg-slate-800 border border-slate-700 rounded px-2 py-1 text-xs font-semibold ${RESULT_STYLES[pick.result]}`}
                >
                  <option value="pending">Pending</option>
                  <option value="win">Win</option>
                  <option value="loss">Loss</option>
                  <option value="push">Push</option>
                </select>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
