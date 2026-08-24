import { useEffect, useState } from 'react'
import { getDashboard } from '../api'
import StatCard from '../components/StatCard'
import ClvTrendChart from '../components/ClvTrendChart'
import { formatPct } from '../format'

export default function Dashboard() {
  const [stats, setStats] = useState(null)

  useEffect(() => {
    getDashboard().then(setStats)
  }, [])

  if (!stats) return <div className="max-w-6xl mx-auto px-4 py-8 text-slate-500">Loading…</div>

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-8">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Win Rate" value={formatPct(stats.win_rate)} />
        <StatCard
          label="ROI"
          value={formatPct(stats.roi)}
          accent={stats.roi > 0 ? 'text-emerald-400' : stats.roi < 0 ? 'text-red-400' : undefined}
        />
        <StatCard label="Avg CLV" value={stats.avg_clv == null ? '—' : `${stats.avg_clv}%`} />
        <StatCard label="Settled Picks" value={`${stats.settled_picks} / ${stats.total_picks}`} />
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
        <h2 className="font-semibold text-slate-200 mb-2">CLV Trend</h2>
        <ClvTrendChart data={stats.clv_trend} />
      </div>
    </div>
  )
}
