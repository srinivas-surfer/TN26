import { useState, useEffect, useCallback, useRef } from 'react'
import { api } from '../utils/api'

export function useElectionData() {
  const [trends, setTrends] = useState(null)
  const [predictions, setPredictions] = useState(null)
  const [liveResults, setLiveResults] = useState(null)
  const [constituencies, setConstituencies] = useState([])
  const [selectedRegion, setSelectedRegion] = useState('statewide')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const tickRef = useRef(0)
  const liveIntervalRef = useRef(null)

  const fetchTrends = useCallback(async (region) => {
    try {
      const data = await api.trends(region)
      setTrends(data)
    } catch (e) {
      console.error('trends error', e)
    }
  }, [])

  const fetchPredictions = useCallback(async () => {
    try {
      const data = await api.predictions()
      setPredictions(data)
    } catch (e) {
      console.error('predictions error', e)
    }
  }, [])

  const fetchLive = useCallback(async () => {
    try {
      const data = await api.liveResults(tickRef.current)
      setLiveResults(data)
      tickRef.current += 1
    } catch (e) {
      console.error('live error', e)
    }
  }, [])

  // Initial load
  useEffect(() => {
    const init = async () => {
      setLoading(true)
      try {
        const [constData] = await Promise.all([
          api.constituencies(),
          fetchTrends('statewide'),
          fetchPredictions(),
          fetchLive(),
        ])
        setConstituencies(constData.constituencies || [])
      } catch (e) {
        setError(e.message)
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [])

  // Live polling every 30s
  useEffect(() => {
    liveIntervalRef.current = setInterval(fetchLive, 30000)
    return () => clearInterval(liveIntervalRef.current)
  }, [fetchLive])

  // Re-fetch trends when region changes
  useEffect(() => {
    fetchTrends(selectedRegion)
  }, [selectedRegion, fetchTrends])

  return {
    trends, predictions, liveResults,
    constituencies, selectedRegion,
    setSelectedRegion,
    loading, error,
    refresh: () => { fetchTrends(selectedRegion); fetchPredictions(); fetchLive() },
  }
}
