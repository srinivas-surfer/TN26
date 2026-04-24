import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts'

const COLORS = {
  DMK: '#E63946', AIADMK: '#2A9D8F', BJP: '#F4A261',
  Congress: '#457B9D', PMK: '#8338EC', VCK: '#06D6A0', NTK: '#FFB703',
}

function buildChartData(parties) {
  if (!parties) return []
  const dateMap = {}
  for (const [party, points] of Object.entries(parties)) {
    for (const pt of points) {
      if (!dateMap[pt.date]) dateMap[pt.date] = { date: pt.date }
      dateMap[pt.date][party] = pt.vote_share
    }
  }
  return Object.values(dateMap).sort((a, b) => a.date.localeCompare(b.date))
}

export default function VoteTrendChart({ trends }) {
  const parties = trends?.parties || {}
  const chartData = buildChartData(parties)
  const activeParties = Object.keys(parties)

  if (!chartData.length) {
    return <div className="chart-empty">No trend data available</div>
  }

  return (
    <div className="chart-container">
      <h3 className="chart-title">Vote Share Trends</h3>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={chartData} margin={{ top: 8, right: 20, left: 0, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.07)" />
          <XAxis
            dataKey="date"
            tick={{ fill: '#8B9CB6', fontSize: 11 }}
            tickFormatter={v => v.slice(2, 10)}
          />
          <YAxis
            tick={{ fill: '#8B9CB6', fontSize: 11 }}
            domain={[0, 55]}
            tickFormatter={v => `${v}%`}
          />
          <Tooltip
            contentStyle={{ background: '#1A2332', border: '1px solid #2D3F55', borderRadius: 8 }}
            labelStyle={{ color: '#CBD5E1' }}
            formatter={(v, name) => [`${v}%`, name]}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {activeParties.map(party => (
            <Line
              key={party}
              type="monotone"
              dataKey={party}
              stroke={COLORS[party] || '#888'}
              strokeWidth={2.5}
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
