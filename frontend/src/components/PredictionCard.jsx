const COLORS = {
  DMK: '#E63946', AIADMK: '#2A9D8F', BJP: '#F4A261',
  Congress: '#457B9D', PMK: '#8338EC', VCK: '#06D6A0', NTK: '#FFB703',
}

function ConfidenceBar({ score }) {
  const pct = Math.round((score || 0) * 100)
  const color = pct > 70 ? '#2A9D8F' : pct > 40 ? '#F4A261' : '#E63946'
  return (
    <div className="conf-bar-bg">
      <div className="conf-bar-fill" style={{ width: `${pct}%`, background: color }} />
      <span className="conf-label">{pct}% conf.</span>
    </div>
  )
}

export default function PredictionCards({ predictions }) {
  if (!predictions?.predictions?.length) {
    return <div className="chart-empty">Running predictions…</div>
  }

  const top = predictions.predictions
    .filter(p => p.predicted_seats >= 1)
    .sort((a, b) => b.predicted_seats - a.predicted_seats)
    .slice(0, 6)

  return (
    <div className="pred-grid">
      {top.map(p => {
        const color = COLORS[p.party] || '#607080'
        const majority = p.predicted_seats >= (predictions.majority_threshold || 118)
        return (
          <div key={p.party} className="pred-card" style={{ borderTopColor: color }}>
            {majority && <div className="majority-badge">MAJORITY</div>}
            <div className="pred-party" style={{ color }}>{p.party}</div>
            <div className="pred-seats">{p.predicted_seats}
              <span className="pred-seats-label"> seats</span>
            </div>
            <div className="pred-vote">{p.predicted_vote_share?.toFixed(1)}% vote share</div>
            <div className="pred-win">
              Win prob: <strong>{Math.round((p.win_probability || 0) * 100)}%</strong>
            </div>
            <ConfidenceBar score={p.confidence_score} />
            {p.using_fallback && (
              <div className="fallback-tag">⚠ using baseline</div>
            )}
          </div>
        )
      })}
    </div>
  )
}
