const AWARDS = [
  { key: 'mvp', label: 'MVP' },
  { key: 'opoy', label: 'Offensive Player of the Year' },
  { key: 'dpoy', label: 'Defensive Player of the Year' },
]

export default function AwardsPanel({ data }) {
  return (
    <div className="space-y-6">
      <p className="text-xs text-amber-400 border border-amber-500/20 bg-amber-500/5 rounded px-3 py-2">
        Not betting odds and not a prediction of actual voting. There's no MVP/OPOY/DPOY market from any
        odds feed. These are simple stats-based rankings; each list's exact formula is shown below it.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {AWARDS.map(({ key, label }) => (
          <div key={key} className="space-y-2">
            <h3 className="font-semibold text-slate-200">{label}</h3>
            <div className="rounded-lg border border-slate-800 divide-y divide-slate-800">
              {data[key].map((p, i) => (
                <div key={p.player_id} className="flex items-center justify-between px-3 py-2 text-sm">
                  <span className="flex items-center gap-2 min-w-0">
                    <span className="text-slate-500 font-mono tabular-nums w-4 shrink-0">{i + 1}</span>
                    <span className="text-slate-100 truncate">{p.name}</span>
                    <span className="text-slate-500 text-[10px] uppercase tracking-wide shrink-0">
                      {p.team}
                    </span>
                  </span>
                </div>
              ))}
              {data[key].length === 0 && (
                <p className="text-slate-500 text-xs px-3 py-4 text-center">No candidates yet.</p>
              )}
            </div>
            <p className="text-[11px] text-slate-500 leading-relaxed">{data.methodology[key]}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
