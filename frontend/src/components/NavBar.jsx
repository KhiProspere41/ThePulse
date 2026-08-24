import { useEffect, useState } from 'react'
import { NavLink } from 'react-router-dom'
import { getApiUsage } from '../api'

const links = [
  { to: '/', label: 'Games' },
  { to: '/futures', label: 'Futures' },
  { to: '/player-stats', label: 'Player Stats' },
  { to: '/picks', label: 'Pick Tracker' },
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/elo', label: 'Elo vs. Market' },
]

/**
 * The Odds API's free tier is 500 requests a month and player props are billed
 * per market per event, so the remaining balance is worth keeping on screen —
 * it's the difference between the app working all month and going dark on day
 * two.
 */
function QuotaBadge() {
  const [usage, setUsage] = useState(null)

  useEffect(() => {
    getApiUsage().then(setUsage).catch(() => setUsage(null))
  }, [])

  if (!usage || usage.requests_remaining == null) return null

  const total = (usage.requests_remaining ?? 0) + (usage.requests_used ?? 0)
  const low = total > 0 && usage.requests_remaining / total < 0.15

  return (
    <span
      title={`${usage.requests_used ?? '?'} of ${total || '?'} Odds API requests used this period`}
      className={`ml-auto text-xs font-mono tabular-nums px-2 py-1 rounded border ${
        low
          ? 'border-amber-500/30 bg-amber-500/10 text-amber-400'
          : 'border-slate-800 text-slate-500'
      }`}
    >
      {usage.requests_remaining} API credits left
    </span>
  )
}

export default function NavBar() {
  return (
    <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-10">
      <div className="max-w-6xl mx-auto px-4 py-3 flex items-center gap-8">
        <span className="font-bold text-lg tracking-tight text-emerald-400">ThePulse</span>
        <nav className="flex gap-1">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === '/'}
              className={({ isActive }) =>
                `px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-emerald-500/10 text-emerald-400'
                    : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800'
                }`
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
        <QuotaBadge />
      </div>
    </header>
  )
}
