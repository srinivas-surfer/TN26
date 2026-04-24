const BASE = import.meta.env.VITE_API_URL || '/api'

async function apiFetch(path, opts = {}) {
  const res = await fetch(`${BASE}${path}`, opts)
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`)
  return res.json()
}

export const api = {
  trends: (region = 'statewide') => apiFetch(`/trends?region=${encodeURIComponent(region)}`),
  predictions: () => apiFetch('/prediction'),
  partyPrediction: (party) => apiFetch(`/prediction/${party}`),
  constituencies: () => apiFetch('/constituencies'),
  constituency: (id) => apiFetch(`/constituency/${id}`),
  regions: () => apiFetch('/regions'),
  region: (name) => apiFetch(`/region/${encodeURIComponent(name)}`),
  liveResults: (tick = 0) => apiFetch(`/live-results?tick=${tick}`),
  health: () => apiFetch('/health'),
}
