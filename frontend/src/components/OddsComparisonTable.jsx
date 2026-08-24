import { formatPoint, formatPrice } from '../format'

const ROWS = [
  { market: 'spreads', side: 'home', label: (g) => `${g.home_team} spread` },
  { market: 'spreads', side: 'away', label: (g) => `${g.away_team} spread` },
  { market: 'h2h', side: 'home', label: (g) => `${g.home_team} ML` },
  { market: 'h2h', side: 'away', label: (g) => `${g.away_team} ML` },
  { market: 'totals', side: 'over', label: () => 'Total Over' },
  { market: 'totals', side: 'under', label: () => 'Total Under' },
]

export default function OddsComparisonTable({ game, bookmakers, onPick }) {
  const bookNames = Object.keys(bookmakers)

  if (!bookNames.length) {
    return <div className="text-slate-500 text-sm py-6">No odds captured for this game yet.</div>
  }

  const cell = (book, market, side) => bookmakers[book].find((o) => o.market === market && o.side === side)

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-800">
      <table className="w-full text-sm">
        <thead className="bg-slate-900 text-slate-400 uppercase text-xs tracking-wide">
          <tr>
            <th className="text-left px-4 py-3">Market</th>
            {bookNames.map((b) => (
              <th key={b} className="text-right px-4 py-3 capitalize">
                {b.replace(/_/g, ' ')}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {ROWS.map((row) => (
            <tr key={`${row.market}-${row.side}`} className="hover:bg-slate-900/60">
              <td className="px-4 py-3 font-medium text-slate-200">{row.label(game)}</td>
              {bookNames.map((book) => {
                const odd = cell(book, row.market, row.side)
                return (
                  <td key={book} className="px-4 py-3 text-right tabular-nums">
                    {odd ? (
                      <button
                        onClick={() => onPick(odd, row)}
                        className="hover:text-emerald-400 hover:underline decoration-dotted"
                        title="Log this line as a pick"
                      >
                        {odd.point != null ? `${formatPoint(odd.point)} ` : ''}
                        {formatPrice(odd.price)}
                      </button>
                    ) : (
                      <span className="text-slate-600">—</span>
                    )}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
