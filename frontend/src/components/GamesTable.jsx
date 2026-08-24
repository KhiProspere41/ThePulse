import { Link } from 'react-router-dom'
import { formatDate, formatPoint, formatPrice } from '../format'

function findOdd(odds, market, side) {
  return odds.find((o) => o.market === market && o.side === side)
}

export default function GamesTable({ games }) {
  if (!games.length) {
    return (
      <div className="text-center py-16 text-slate-500">
        No games loaded yet. Set <code className="text-slate-400">ODDS_API_KEY</code> in the backend
        .env and wait for the next scheduler refresh (or restart the API).
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-800">
      <table className="w-full text-sm">
        <thead className="bg-slate-900 text-slate-400 uppercase text-xs tracking-wide">
          <tr>
            <th className="text-left px-4 py-3">Matchup</th>
            <th className="text-left px-4 py-3">Kickoff</th>
            <th className="text-right px-4 py-3">Spread</th>
            <th className="text-right px-4 py-3">Moneyline</th>
            <th className="text-right px-4 py-3">Total</th>
            <th className="px-4 py-3" />
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {games.map((game) => {
            const homeSpread = findOdd(game.odds, 'spreads', 'home')
            const homeMl = findOdd(game.odds, 'h2h', 'home')
            const awayMl = findOdd(game.odds, 'h2h', 'away')
            const over = findOdd(game.odds, 'totals', 'over')

            return (
              <tr key={game.id} className="hover:bg-slate-900/60 transition-colors">
                <td className="px-4 py-3">
                  <div className="font-medium text-slate-100">
                    {game.away_team} @ {game.home_team}
                  </div>
                  {game.completed && (
                    <div className="text-xs text-slate-500">
                      Final: {game.away_score}–{game.home_score}
                    </div>
                  )}
                </td>
                <td className="px-4 py-3 text-slate-400">{formatDate(game.commence_time)}</td>
                <td className="px-4 py-3 text-right tabular-nums">
                  {homeSpread ? `${formatPoint(homeSpread.point)} (${formatPrice(homeSpread.price)})` : '—'}
                </td>
                <td className="px-4 py-3 text-right tabular-nums">
                  {homeMl && awayMl ? `${formatPrice(homeMl.price)} / ${formatPrice(awayMl.price)}` : '—'}
                </td>
                <td className="px-4 py-3 text-right tabular-nums">
                  {over ? `O ${over.point} (${formatPrice(over.price)})` : '—'}
                </td>
                <td className="px-4 py-3 text-right">
                  <Link to={`/game/${game.id}`} className="text-emerald-400 hover:text-emerald-300 text-xs font-semibold">
                    Compare &amp; Pick →
                  </Link>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
