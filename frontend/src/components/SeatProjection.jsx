import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Cell, ResponsiveContainer, ReferenceLine,
} from 'recharts'

const COLORS = {
  DMK: '#E63946', AIADMK: '#2A9D8F', BJP: '#F4A261',
  Congress: '#457B9D', PMK: '#8338EC', VCK: '#06D6A0', NTK: '#FFB703',
}

const CustomBar = (props) => {
  const { x, y, width, height, party } = props
  const color = COLORS[party] || '#607080'
  return (
    <g>
      <rect x={x} y={y} width={width} height={height} fill={color} rx={4} />
    </g>
  )
}

export default function SeatProjection({ predictions }) {
  if (!predictions?.predictions?.length) {
    return <div className="chart-empty">No prediction data available</div>
  }

  const data = predictions.predictions
    .filter(p => p.predicted_seats > 0)
    .map(p => ({
      party: p.party,
      seats: p.predicted_seats,
      low: p.seat_low || p.predicted_seats - 8,
      high: p.seat_high || p.predicted_seats + 8,
      win_prob: Math.round((p.win_probability || 0) * 100),
    }))
    .sort((a, b) => b.seats - a.seats)
    .slice(0, 8)

  const majority = predictions.majority_threshold || 118

  return (
    <div className="chart-container">
      <h3 className="chart-title">
        Seat Projection
        <span className="chart-subtitle"> — Majority: {majority}</span>
      </h3>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data} margin={{ top: 8, right: 20, left: 0, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.07)" vertical={false} />
          <XAxis dataKey="party" tick={{ fill: '#8B9CB6', fontSize: 12 }} />
          <YAxis tick={{ fill: '#8B9CB6', fontSize: 11 }} domain={[0, 234]} />
          <Tooltip
            contentStyle={{ background: '#1A2332', border: '1px solid #2D3F55', borderRadius: 8 }}
            labelStyle={{ color: '#CBD5E1' }}
            formatter={(v, name, props) => {
              const d = props.payload
              return [`${v} seats (${d.low}–${d.high})`, d.party]
            }}
          />
          <ReferenceLine
            y={majority}
            stroke="#FFD700"
            strokeDasharray="6 3"
            label={{ value: 'Majority', fill: '#FFD700', fontSize: 11, position: 'insideTopRight' }}
          />
          <Bar dataKey="seats" radius={[4, 4, 0, 0]}>
            {data.map((entry) => (
              <Cell key={entry.party} fill={COLORS[entry.party] || '#607080'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Win probability pills */}
      <div className="win-prob-row">
        {data.map(d => d.win_prob > 1 && (
          <span key={d.party} className="win-pill" style={{ borderColor: COLORS[d.party] }}>
            {d.party} {d.win_prob}%
          </span>
        ))}
      </div>
    </div>
  )
}
