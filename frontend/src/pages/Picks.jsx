import { useEffect, useState } from 'react'
import { getPicks } from '../api'
import PicksList from '../components/PicksList'

export default function Picks() {
  const [picks, setPicks] = useState([])
  const [loading, setLoading] = useState(true)

  function refresh() {
    setLoading(true)
    getPicks()
      .then(setPicks)
      .finally(() => setLoading(false))
  }

  useEffect(refresh, [])

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
      <h1 className="text-2xl font-bold">Pick Tracker</h1>
      {loading ? <p className="text-slate-500">Loading…</p> : <PicksList picks={picks} onChanged={refresh} />}
    </div>
  )
}
