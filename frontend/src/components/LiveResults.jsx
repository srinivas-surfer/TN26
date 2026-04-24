import { useState, useEffect } from 'react'

const COLORS = {
  DMK: '#E63946', AIADMK: '#2A9D8F', BJP: '#F4A261',
  Congress: '#457B9D', PMK: '#8338EC', VCK: '#06D6A0', NTK: '#FFB703',
}

function SeatBar({ party, leading, won, total, color }) {
  const totalSeats = won + leading
  const pct = (totalSeats / 234) * 100
  return (
    <div className="seat-bar-row">
      <div className="seat-bar-party" style={{ color }}>{party}</div>
      <div className="seat-bar-track">
        <div className="seat-bar-won" style={{ width: `${(won / 234) * 100}%`, background: color }} />
        <div className="seat-bar-leading" style={{ width: `${(leading / 234) * 100}%`, background: color + '66' }} />
      </div>
      <div className="seat-bar-count">
        <span className="seat-won">{won}</span>
        {leading > 0 && <span className="seat-leading">+{leading}</span>}
      </div>
    </div>
  )
}

export default function LiveResults({ liveResults }) {
  const [prevTally, setPrevTally] = useState({})
  const [flashParties, setFlashParties] = useState(new Set())

  useEffect(() => {
    if (!liveResults?.tally) return
    const newFlash = new Set()
    for (const [party, data] of Object.entries(liveResults.tally)) {
      const prev = prevTally[party]
      if (prev && (data.won + data.leading) > (prev.won + prev.leading)) {
        newFlash.add(party)
      }
    }
    setFlashParties(newFlash)
    setPrevTally(liveResults.tally)
    if (newFlash.size) {
      setTimeout(() => setFlashParties(new Set()), 800)
    }
  }, [liveResults])

  if (!liveResults) {
    return <div className="chart-empty">Awaiting results…</div>
  }

  const { tally = {}, total_declared, total_seats, majority, mode, counting_complete } = liveResults
  const declared_pct = Math.round((total_declared / total_seats) * 100)

  const sorted = Object.entries(tally).sort(
    (a, b) => (b[1].won + b[1].leading) - (a[1].won + a[1].leading)
  )

  const leader = sorted[0]
  const leaderSeats = leader ? leader[1].won + leader[1].leading : 0
  const leaderParty = leader ? leader[0] : '—'

  return (
    <div className="live-container">
      <div className="live-header">
        <div className="live-badge">
          {mode === 'live' ? '🔴 LIVE' : '⚡ SIMULATION'}
        </div>
        <div className="live-progress">
          <span>{total_declared} / {total_seats} declared</span>
          <div className="progress-track">
            <div className="progress-fill" style={{ width: `${declared_pct}%` }} />
          </div>
          <span>{declared_pct}%</span>
        </div>
      </div>

      {leaderSeats >= majority && (
        <div className="majority-banner" style={{ borderColor: COLORS[leaderParty] }}>
          🏆 {leaderParty} crosses majority ({leaderSeats} seats)
        </div>
      )}

      <div className="seat-bars">
        {sorted.map(([party, data]) => (
          <div
            key={party}
            className={`seat-bar-wrapper ${flashParties.has(party) ? 'flash' : ''}`}
          >
            <SeatBar
              party={party}
              leading={data.leading}
              won={data.won}
              total={total_seats}
              color={COLORS[party] || '#999'}
            />
          </div>
        ))}
      </div>

      <div className="live-legend">
        <span className="legend-won">■ Won</span>
        <span className="legend-leading">■ Leading</span>
        <span className="legend-majority">— Majority ({majority})</span>
      </div>
    </div>
  )
}
