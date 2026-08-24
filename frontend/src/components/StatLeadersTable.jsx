const COLUMNS = {
  overall: [
    { label: 'Pass Yds', key: 'passing_yards' },
    { label: 'Rush Yds', key: 'rushing_yards' },
    { label: 'Rec Yds', key: 'receiving_yards' },
    { label: 'Fantasy Pts (PPR)', key: 'fantasy_points_ppr', highlight: true },
  ],
  passing: [
    { label: 'Yds', key: 'passing_yards', highlight: true },
    { label: 'TD', key: 'passing_tds' },
    { label: 'INT', key: 'interceptions' },
    { label: 'aDOT', key: 'passing_air_yards_per_att', title: 'Intended air yards per attempt (PFR)' },
    { label: 'On Tgt%', key: 'passing_on_tgt_pct', pct: true, title: 'On-target throw rate (PFR)' },
    { label: 'Pressure%', key: 'passing_pressure_pct', pct: true, title: 'Pressured dropback rate (PFR)' },
  ],
  rushing: [
    { label: 'Yds', key: 'rushing_yards', highlight: true },
    { label: 'TD', key: 'rushing_tds' },
    { label: 'YBC', key: 'rush_yards_before_contact', title: 'Yards before contact (PFR)' },
    { label: 'YAC', key: 'rush_yards_after_contact', title: 'Yards after contact (PFR)' },
    { label: 'Broken Tkl', key: 'rush_broken_tackles', title: 'Broken tackles forced (PFR)' },
  ],
  receiving: [
    { label: 'Rec', key: 'receptions' },
    { label: 'Yds', key: 'receiving_yards', highlight: true },
    { label: 'TD', key: 'receiving_tds' },
    { label: 'aDOT', key: 'rec_avg_depth_of_target', title: 'Average depth of target (PFR)' },
    { label: 'YAC', key: 'rec_yards_after_catch', title: 'Yards after catch (PFR)' },
    { label: 'Drop%', key: 'rec_drop_pct', pct: true, title: 'Drop rate (PFR)' },
  ],
  defense: [
    { label: 'Sacks', key: 'sacks', highlight: true },
    { label: 'Tackles', key: 'combined_tackles' },
    { label: 'INT', key: 'def_interceptions' },
  ],
}

const fmt = (value, pct) => {
  if (value == null) return '—'
  if (pct) return `${(value * 100).toFixed(1)}%`
  return Number.isInteger(value) ? value : value.toFixed(1)
}

export default function StatLeadersTable({ category, players }) {
  const columns = COLUMNS[category] ?? COLUMNS.overall

  if (!players.length) {
    return <p className="text-slate-500 text-sm py-16 text-center">No stats loaded for this season yet.</p>
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-800">
      <table className="w-full text-sm">
        <thead className="bg-slate-900 text-slate-400 uppercase text-xs tracking-wide">
          <tr>
            <th className="text-left px-4 py-3 w-10">#</th>
            <th className="text-left px-4 py-3">Player</th>
            <th className="text-left px-4 py-3">Team</th>
            {columns.map((col) => (
              <th key={col.key} className="text-right px-4 py-3" title={col.title}>
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {players.map((p, i) => (
            <tr key={p.player_id} className="hover:bg-slate-900/60">
              <td className="px-4 py-3 text-slate-500 font-mono tabular-nums">{i + 1}</td>
              <td className="px-4 py-3 font-medium text-slate-100">
                {p.name}
                <span className="text-slate-500 text-[10px] ml-1.5 uppercase tracking-wide">{p.position}</span>
              </td>
              <td className="px-4 py-3 text-slate-400 text-xs">{p.team}</td>
              {columns.map((col) => (
                <td
                  key={col.key}
                  className={`px-4 py-3 text-right font-mono tabular-nums ${
                    col.highlight ? 'text-emerald-400 font-semibold' : 'text-slate-300'
                  }`}
                >
                  {fmt(p[col.key], col.pct)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
