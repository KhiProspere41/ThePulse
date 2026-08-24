import { useMemo, useState } from 'react'
import { formatPrice, marketLabel } from '../format'

const SIDE_ORDER = { over: 0, under: 1, yes: 0, no: 1 }
const SIDE_LABEL = { over: 'Over', under: 'Under', yes: 'Yes', no: 'No' }

/**
 * Groups a flat list of prop snapshots into market -> player -> side -> book,
 * which is the shape the table renders. Also records the best (longest) price
 * per player/side so line shopping is a glance rather than a scan.
 */
function groupProps(props) {
  const byMarket = new Map()
  for (const prop of props) {
    if (!byMarket.has(prop.market)) byMarket.set(prop.market, new Map())
    const players = byMarket.get(prop.market)
    if (!players.has(prop.player)) players.set(prop.player, new Map())
    const sides = players.get(prop.player)
    if (!sides.has(prop.side)) sides.set(prop.side, new Map())
    sides.get(prop.side).set(prop.bookmaker, prop)
  }
  return byMarket
}

function bestBook(bookMap) {
  let best = null
  for (const prop of bookMap.values()) {
    if (best === null || prop.price > best.price) best = prop
  }
  return best
}

export default function PlayerPropsTable({ props, books, onPick }) {
  const grouped = useMemo(() => groupProps(props), [props])
  const markets = useMemo(() => [...grouped.keys()].sort(), [grouped])
  const [active, setActive] = useState(null)

  if (!markets.length) return null

  const market = active && grouped.has(active) ? active : markets[0]
  const players = grouped.get(market)
  const bookNames = books.length ? books : [...new Set(props.map((p) => p.bookmaker))].sort()

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-1">
        {markets.map((key) => (
          <button
            key={key}
            onClick={() => setActive(key)}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors ${
              key === market
                ? 'bg-emerald-500/10 text-emerald-400'
                : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800'
            }`}
          >
            {marketLabel(key)}
          </button>
        ))}
      </div>

      <div className="overflow-x-auto rounded-lg border border-slate-800">
        <table className="w-full text-sm">
          <thead className="bg-slate-900 text-slate-400 uppercase text-xs tracking-wide">
            <tr>
              <th className="text-left px-4 py-3">Player</th>
              <th className="text-left px-2 py-3">Side</th>
              {bookNames.map((book) => (
                <th key={book} className="text-right px-4 py-3 capitalize whitespace-nowrap">
                  {book.replace(/_/g, ' ')}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {[...players.entries()]
              .sort(([a], [b]) => a.localeCompare(b))
              .flatMap(([player, sides]) => {
                const ordered = [...sides.entries()].sort(
                  ([a], [b]) => (SIDE_ORDER[a] ?? 9) - (SIDE_ORDER[b] ?? 9)
                )
                return ordered.map(([side, bookMap], index) => {
                  const best = bestBook(bookMap)
                  return (
                    <tr key={`${player}-${side}`} className="hover:bg-slate-900/60">
                      {index === 0 && (
                        <td
                          rowSpan={ordered.length}
                          className="px-4 py-3 font-medium text-slate-100 align-top whitespace-nowrap"
                        >
                          {player}
                        </td>
                      )}
                      <td className="px-2 py-3 text-slate-400 text-xs uppercase">
                        {SIDE_LABEL[side] ?? side}
                      </td>
                      {bookNames.map((book) => {
                        const prop = bookMap.get(book)
                        if (!prop) {
                          return (
                            <td key={book} className="px-4 py-3 text-right text-slate-600">
                              —
                            </td>
                          )
                        }
                        const isBest = best && prop.price === best.price
                        return (
                          <td key={book} className="px-4 py-3 text-right font-mono tabular-nums whitespace-nowrap">
                            <button
                              onClick={() => onPick?.(prop)}
                              title="Log this line as a pick"
                              className={`hover:underline decoration-dotted ${
                                isBest ? 'text-emerald-400 font-semibold' : 'hover:text-emerald-400'
                              }`}
                            >
                              {prop.point != null && (
                                <span className="text-slate-400 mr-1">{prop.point}</span>
                              )}
                              {formatPrice(prop.price)}
                            </button>
                          </td>
                        )
                      })}
                    </tr>
                  )
                })
              })}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-slate-500">
        Best available price per player and side is highlighted. Click any price to log it as a pick.
      </p>
    </div>
  )
}
