import { useState } from 'react'
import VoteTrendChart from './components/VoteTrendChart'
import SeatProjection from './components/SeatProjection'
import LiveResults from './components/LiveResults'
import RegionBreakdown from './components/RegionBreakdown'
import PredictionCards from './components/PredictionCard'
import { useElectionData } from './hooks/useElectionData'
import './index.css'

const TABS = ['Overview', 'Trends', 'Live Results', 'Regions']

export default function App() {
  const [tab, setTab] = useState('Overview')
  const {
    trends, predictions, liveResults,
    constituencies, selectedRegion,
    setSelectedRegion, loading, error, refresh,
  } = useElectionData()

  if (loading) {
    return (
      <div className="app-loading">
        <div className="loading-spinner" />
        <p>Loading election data…</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="app-error">
        <p>⚠ Could not connect to API: {error}</p>
        <button onClick={refresh}>Retry</button>
      </div>
    )
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="app-header">
        <div className="header-left">
          <div className="logo-mark">tn</div>
          <div>
            <h1 className="app-title">Election Intelligence</h1>
            <p className="app-subtitle">Tamil Nadu Assembly 2026 · 234 Constituencies</p>
          </div>
        </div>
        <div className="header-right">
          <div className="live-dot" />
          <span className="live-text">LIVE TRACKING</span>
          <button className="refresh-btn" onClick={refresh} title="Refresh data">⟳</button>
        </div>
      </header>

      {/* Tabs */}
      <nav className="tab-nav">
        {TABS.map(t => (
          <button
            key={t}
            className={`tab-btn ${tab === t ? 'active' : ''}`}
            onClick={() => setTab(t)}
          >
            {t}
          </button>
        ))}
      </nav>

      {/* Content */}
      <main className="app-main">
        {tab === 'Overview' && (
          <div className="grid-2col">
            <div className="card">
              <PredictionCards predictions={predictions} />
            </div>
            <div className="card">
              <SeatProjection predictions={predictions} />
            </div>
            <div className="card span-2">
              <VoteTrendChart trends={trends} />
            </div>
          </div>
        )}

        {tab === 'Trends' && (
          <div className="grid-1col">
            <div className="card">
              <VoteTrendChart trends={trends} />
            </div>
            <div className="card">
              <RegionBreakdown onRegionChange={setSelectedRegion} />
            </div>
          </div>
        )}

        {tab === 'Live Results' && (
          <div className="grid-1col">
            <div className="card">
              <LiveResults liveResults={liveResults} />
            </div>
          </div>
        )}

        {tab === 'Regions' && (
          <div className="grid-1col">
            <div className="card">
              <RegionBreakdown onRegionChange={setSelectedRegion} />
            </div>
          </div>
        )}
      </main>

      <footer className="app-footer">
        TN2026 Election Intelligence · Data refreshes every 6 hours · Predictions by ML ensemble
      </footer>
    </div>
  )
}
