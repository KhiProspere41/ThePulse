import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

export default function ClvTrendChart({ data }) {
  if (!data.length) {
    return <div className="text-slate-500 text-sm py-10 text-center">No settled picks with CLV yet.</div>
  }

  const chartData = data.map((d, i) => ({ index: i + 1, clv: d.clv }))

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
        <XAxis dataKey="index" stroke="#64748b" fontSize={12} label={{ value: 'Pick #', position: 'insideBottom', offset: -2, fill: '#64748b', fontSize: 11 }} />
        <YAxis stroke="#64748b" fontSize={12} unit="%" />
        <Tooltip
          contentStyle={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 8, fontSize: 12 }}
          formatter={(value) => [`${value}%`, 'CLV']}
          labelFormatter={(label) => `Pick #${label}`}
        />
        <ReferenceLine y={0} stroke="#475569" />
        <Line type="monotone" dataKey="clv" stroke="#34d399" strokeWidth={2} dot={{ r: 3 }} />
      </LineChart>
    </ResponsiveContainer>
  )
}
