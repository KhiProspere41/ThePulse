import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getLines } from '../api'
import OddsComparisonTable from '../components/OddsComparisonTable'
import PlayerPropsPanel from '../components/PlayerPropsPanel'
import { formatDate, formatPoint, marketLabel } from '../format'
import { useSlip } from '../slipContext'

export default function GameDetail() {
  const { id } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const { addLeg } = useSlip()

  function refresh() {
    getLines(id)
      .then(setData)
      .catch(() => setError('Could not load lines for this game.'))
  }

  useEffect(refresh, [id])

  if (error) return <div className="max-w-6xl mx-auto px-4 py-8 text-red-400">{error}</div>
  if (!data) return <div className="max-w-6xl mx-auto px-4 py-8 text-slate-500">Loading…</div>

  const { game, bookmakers } = data
  const matchup = `${game.away_team} @ ${game.home_team}`

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
      <Link to="/" className="text-emerald-400 text-sm hover:underline">
        ← All games
      </Link>

      <div>
        <h1 className="text-2xl font-bold">{matchup}</h1>
        <p className="text-slate-400 text-sm">{formatDate(game.commence_time)}</p>
      </div>

      <div>
        <OddsComparisonTable
          game={game}
          bookmakers={bookmakers}
          onPick={(odd, row) => {
            const selection =
              row.side === 'home' ? game.home_team : row.side === 'away' ? game.away_team : row.side
            addLeg({
              key: `${game.id}-${row.market}-${row.side}`,
              matchup,
              label: `${selection}${odd.point != null ? ` ${formatPoint(odd.point)}` : ''} (${marketLabel(row.market)})`,
              game_id: game.id,
              bet_type: 'game',
              market: row.market,
              selection,
              player: null,
              point: odd.point,
              entry_price: odd.price,
            })
          }}
        />
      </div>

      {game.league === 'nfl' && (
        <PlayerPropsPanel
          gameId={game.id}
          onPick={(prop) => {
            addLeg({
              key: `${game.id}-${prop.market}-${prop.player}-${prop.side}`,
              matchup,
              label: `${prop.player} ${prop.side}${prop.point != null ? ` ${prop.point}` : ''} (${marketLabel(prop.market)})`,
              game_id: game.id,
              bet_type: 'player_prop',
              market: prop.market,
              selection: prop.side,
              player: prop.player,
              point: prop.point,
              entry_price: prop.price,
            })
          }}
        />
      )}
    </div>
  )
}
