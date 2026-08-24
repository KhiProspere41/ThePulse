import { formatPrice, formatProb, formatSigned, formatUnits } from '../format'

/**
 * The Super Bowl outrights market against the model.
 *
 * `market_fair_prob` is each book's board normalised to sum to 1 before being
 * averaged — a raw Super Bowl board holds 30%+, so comparing the model to raw
 * implied prices would show "value" on all 32 teams. `best_price` is the
 * longest price anyone is offering, which is what you'd actually bet into, and
 * EV/unit is the model's expectation at that price.
 */
export default function SuperBowlBoard({ teams, onPick }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-800">
      <table className="w-full text-sm">
        <thead className="bg-slate-900 text-slate-400 uppercase text-xs tracking-wide">
          <tr>
            <th className="text-left px-4 py-3">Team</th>
            <th className="text-right px-4 py-3">Model</th>
            <th className="text-right px-4 py-3">Market (no vig)</th>
            <th className="text-right px-4 py-3">Best price</th>
            <th className="text-right px-4 py-3">Edge</th>
            <th className="text-right px-4 py-3">EV / unit</th>
            <th className="px-4 py-3" />
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {teams.map((team) => {
            const market = team.market
            const positive = team.ev_per_unit != null && team.ev_per_unit > 0
            return (
              <tr key={team.team} className="hover:bg-slate-900/60">
                <td className="px-4 py-3 font-medium text-slate-100 whitespace-nowrap">
                  <span className="font-bold text-slate-400 mr-2 text-xs">{team.team}</span>
                  {team.name}
                </td>
                <td className="px-4 py-3 text-right font-mono tabular-nums text-slate-200">
                  {formatProb(team.super_bowl_prob)}
                </td>
                <td className="px-4 py-3 text-right font-mono tabular-nums text-slate-400">
                  {market ? formatProb(market.market_fair_prob) : '—'}
                </td>
                <td className="px-4 py-3 text-right font-mono tabular-nums whitespace-nowrap">
                  {market?.best_price != null ? (
                    <>
                      <span className="text-slate-200">{formatPrice(market.best_price)}</span>
                      <span className="text-slate-500 text-xs ml-2 capitalize">
                        {market.best_book?.replace(/_/g, ' ')}
                      </span>
                    </>
                  ) : (
                    <span className="text-slate-600">—</span>
                  )}
                </td>
                <td
                  className={`px-4 py-3 text-right font-mono tabular-nums ${
                    team.edge == null ? 'text-slate-500' : team.edge > 0 ? 'text-emerald-400' : 'text-red-400'
                  }`}
                >
                  {team.edge == null ? '—' : formatSigned(team.edge)}
                </td>
                <td
                  className={`px-4 py-3 text-right font-mono tabular-nums font-semibold ${
                    team.ev_per_unit == null ? 'text-slate-500' : positive ? 'text-emerald-400' : 'text-red-400'
                  }`}
                >
                  {formatUnits(team.ev_per_unit)}
                </td>
                <td className="px-4 py-3 text-right">
                  {market?.best_price != null && (
                    <button
                      onClick={() => onPick?.(team)}
                      className="text-emerald-400 hover:text-emerald-300 text-xs font-semibold"
                    >
                      Log pick
                    </button>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
