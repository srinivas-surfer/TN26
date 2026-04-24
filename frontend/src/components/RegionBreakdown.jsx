import { useState, useEffect } from 'react'
import { api } from '../utils/api'

const REGIONS = ['statewide', 'Chennai', 'Western TN', 'Southern TN', 'Central TN', 'Northern TN', 'Delta TN']
const COLORS = {
  DMK: '#E63946', AIADMK: '#2A9D8F', BJP: '#F4A261',
  Congress: '#457B9D', PMK: '#8338EC', VCK: '#06D6A0', NTK: '#FFB703',
}

export default function RegionBreakdown({ onRegionChange }) {
  const [selected, setSelected] = useState('statewide')
  const [regionData, setRegionData] = useState(null)
  const [loading, setLoading] = useState(false)

  const loadRegion = async (region) => {
    setLoading(true)
    try {
      const data = region === 'statewide'
        ? await api.trends('statewide')
        : await api.region(region)
      setRegionData({ region, data })
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadRegion(selected) }, [selected])

  const handleSelect = (r) => {
    setSelected(r)
    onRegionChange?.(r)
  }

  const parties = regionData?.data?.parties || {}
  // For display, get latest vote share per party
  const latestVotes = Object.entries(parties).map(([party, pts]) => {
    const sorted = [...pts].sort((a, b) => a.date.localeCompare(b.date))
    return { party, vote_share: sorted[sorted.length - 1]?.vote_share || 0 }
  }).sort((a, b) => b.vote_share - a.vote_share)

  return (
    <div className="region-container">
      <h3 className="chart-title">Region Breakdown</h3>
      <div className="region-tabs">
        {REGIONS.map(r => (
          <button
            key={r}
            className={`region-tab ${selected === r ? 'active' : ''}`}
            onClick={() => handleSelect(r)}
          >
            {r === 'statewide' ? '🗺 All TN' : r}
          </button>
        ))}
      </div>

      {loading && <div className="loading-pulse">Loading…</div>}
      {!loading && latestVotes.length > 0 && (
        <div className="region-vote-grid">
          {latestVotes.slice(0, 6).map(({ party, vote_share }) => (
            <div key={party} className="region-vote-card">
              <div className="party-dot" style={{ background: COLORS[party] || '#888' }} />
              <div className="party-name">{party}</div>
              <div className="party-vote" style={{ color: COLORS[party] || '#888' }}>
                {vote_share.toFixed(1)}%
              </div>
              <div className="vote-bar-bg">
                <div
                  className="vote-bar-fill"
                  style={{ width: `${Math.min(vote_share * 2, 100)}%`, background: COLORS[party] || '#888' }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
