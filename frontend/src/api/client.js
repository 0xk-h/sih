import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || ''

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
})

// ── Routes ─────────────────────────────────────────────────────────────
export const getRoutes = () => api.get('/v1/routes').then(r => r.data)

export const getAirlineMedians = (routeId, params = {}) =>
  api.get(`/v1/routes/${routeId}/airline-medians`, { params }).then(r => r.data)

// ── Index ──────────────────────────────────────────────────────────────
export const getNationalIndex = (params = {}) =>
  api.get('/v1/index/national', { params }).then(r => r.data)

export const getRouteIndex = (routeId, params = {}) =>
  api.get(`/v1/index/route/${routeId}`, { params }).then(r => r.data)

// ── Fares ──────────────────────────────────────────────────────────────
export const getFares = (routeId, params = {}) =>
  api.get(`/v1/fares/${routeId}`, { params }).then(r => r.data)

// ── Dashboard ──────────────────────────────────────────────────────────
export const getDashboardSummary = () =>
  api.get('/v1/dashboard/summary').then(r => r.data)

// ── Data Quality ───────────────────────────────────────────────────────
export const getDataQuality = () =>
  api.get('/v1/data-quality').then(r => r.data)

// ── Scrape trigger ─────────────────────────────────────────────────────
export const triggerScrape = () =>
  api.post('/v1/scrape/trigger').then(r => r.data)

export default api
