import { useEffect, useState } from 'react'
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement,
  LineElement, Title, Tooltip, Legend, Filler, BarElement
} from 'chart.js'
import { Line, Bar } from 'react-chartjs-2'
import { getRoutes, getRouteIndex, getFares, getAirlineMedians } from '../api/client'
import { LoadingSpinner, ErrorState } from '../components/LoadingSpinner'

ChartJS.register(
  CategoryScale, LinearScale, PointElement, LineElement,
  Title, Tooltip, Legend, Filler, BarElement
)

const lineOpts = (title) => ({
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'index', intersect: false },
  plugins: {
    legend: {
      labels: { color: '#94a3b8', font: { family: 'Inter', size: 12 }, boxWidth: 10, usePointStyle: true }
    },
    tooltip: {
      backgroundColor: '#1a2235',
      borderColor: '#1f2d47',
      borderWidth: 1,
      titleColor: '#f1f5f9',
      bodyColor: '#94a3b8',
    },
    title: {
      display: false,
    }
  },
  scales: {
    x: { grid: { color: '#1f2d47' }, ticks: { color: '#475569', font: { size: 11 }, maxTicksLimit: 10 } },
    y: { grid: { color: '#1f2d47' }, ticks: { color: '#475569', font: { size: 11 } } }
  }
})

export default function RouteExplorer() {
  const [routes, setRoutes] = useState([])
  const [selectedRouteId, setSelectedRouteId] = useState(null)
  const [indexData, setIndexData] = useState({ dtd14: [], dtd1: [] })
  const [fareData, setFareData] = useState([])
  const [airlineData, setAirlineData] = useState([])
  const [loading, setLoading] = useState(true)
  const [loadingRoute, setLoadingRoute] = useState(false)
  const [error, setError] = useState(null)

  // Load routes on mount
  useEffect(() => {
    getRoutes()
      .then(r => {
        setRoutes(r)
        if (r.length > 0) setSelectedRouteId(r[0].route_id)
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  // Load data for selected route
  useEffect(() => {
    if (!selectedRouteId) return
    setLoadingRoute(true)

    Promise.all([
      getRouteIndex(selectedRouteId, { dtd: 14 }),
      getRouteIndex(selectedRouteId, { dtd: 1 }),
      getFares(selectedRouteId, { limit: 200 }),
      getAirlineMedians(selectedRouteId, { dtd: 14 })
    ])
      .then(([i14, i1, fares, airlines]) => {
        setIndexData({ dtd14: i14, dtd1: i1 })
        setFareData(fares)
        setAirlineData(airlines)
      })
      .catch(e => console.error('Route load error:', e))
      .finally(() => setLoadingRoute(false))
  }, [selectedRouteId])

  if (loading) return <div className="main-content"><LoadingSpinner message="Loading routes..." /></div>
  if (error)   return <div className="main-content"><div className="page-body"><ErrorState message={error} /></div></div>

  const selectedRoute = routes.find(r => r.route_id === selectedRouteId)
  const routeLabel = selectedRoute
    ? `${selectedRoute.origin.iata_code}–${selectedRoute.destination.iata_code}`
    : ''

  // Index chart
  const allDates = [...new Set([
    ...indexData.dtd14.map(d => d.index_date),
    ...indexData.dtd1.map(d => d.index_date),
  ])].sort()

  const dtd14Map = Object.fromEntries(indexData.dtd14.map(d => [d.index_date, d.value]))
  const dtd1Map  = Object.fromEntries(indexData.dtd1.map(d => [d.index_date, d.value]))

  const indexChartData = {
    labels: allDates.map(d => new Date(d).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })),
    datasets: [
      {
        label: 'DTD=14 (Advance)',
        data: allDates.map(d => dtd14Map[d] ?? null),
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59,130,246,0.05)',
        borderWidth: 2, pointRadius: 0, pointHoverRadius: 4,
        tension: 0.3, fill: true, spanGaps: true,
      },
      {
        label: 'DTD=1 (Last Minute)',
        data: allDates.map(d => dtd1Map[d] ?? null),
        borderColor: '#f59e0b',
        backgroundColor: 'rgba(245,158,11,0.04)',
        borderWidth: 2, pointRadius: 0, pointHoverRadius: 4,
        tension: 0.3, fill: true, spanGaps: true,
      }
    ]
  }

  // Fare distribution: median fare per day per dtd from fare_observations
  const fareDateMap14 = {}
  const fareDateMap1 = {}
  fareData.forEach(f => {
    const k = f.departure_date
    if (f.dtd_bucket === 14) {
      if (!fareDateMap14[k]) fareDateMap14[k] = []
      fareDateMap14[k].push(f.total_fare)
    }
    if (f.dtd_bucket === 1) {
      if (!fareDateMap1[k]) fareDateMap1[k] = []
      fareDateMap1[k].push(f.total_fare)
    }
  })

  const fareLabels = [...new Set(fareData.map(f => f.departure_date))].sort().slice(-30)
  const medianOf = (arr) => {
    if (!arr || arr.length === 0) return null
    const sorted = [...arr].sort((a, b) => a - b)
    return sorted[Math.floor(sorted.length / 2)]
  }

  const fareChartData = {
    labels: fareLabels.map(d => new Date(d).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })),
    datasets: [
      {
        label: 'Median Fare DTD=14 (₹)',
        data: fareLabels.map(d => medianOf(fareDateMap14[d])),
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59,130,246,0.08)',
        borderWidth: 2, pointRadius: 2, pointHoverRadius: 5,
        tension: 0.2, spanGaps: true,
      },
      {
        label: 'Median Fare DTD=1 (₹)',
        data: fareLabels.map(d => medianOf(fareDateMap1[d])),
        borderColor: '#f59e0b',
        backgroundColor: 'rgba(245,158,11,0.06)',
        borderWidth: 2, pointRadius: 2, pointHoverRadius: 5,
        tension: 0.2, spanGaps: true,
      }
    ]
  }

  const fareOpts = {
    ...lineOpts(),
    scales: {
      ...lineOpts().scales,
      y: {
        grid: { color: '#1f2d47' },
        ticks: {
          color: '#475569', font: { size: 11 },
          callback: v => `₹${v.toLocaleString('en-IN')}`
        }
      }
    }
  }

  return (
    <div className="main-content">
      <div className="page-header">
        <h2>Route Explorer</h2>
        <p>
          Price trend and index movement by DTD bucket for individual routes.
          DTD buckets are tracked as separate time series (§3.1 comparability).
        </p>
      </div>

      <div className="page-body">
        {/* Route selector */}
        <div className="select-group">
          <span className="select-label">Route:</span>
          <select
            id="route-selector"
            className="route-select"
            value={selectedRouteId || ''}
            onChange={e => setSelectedRouteId(Number(e.target.value))}
          >
            {routes.map(r => (
              <option key={r.route_id} value={r.route_id}>
                {r.origin.iata_code}–{r.destination.iata_code} · {r.origin.city} → {r.destination.city}
              </option>
            ))}
          </select>

          {selectedRoute && (
            <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                Weight: <strong style={{ color: 'var(--text-secondary)', fontFamily: 'JetBrains Mono' }}>
                  {(selectedRoute.current_weight * 100).toFixed(0)}%
                </strong>
              </span>
              {selectedRoute.distance_km && (
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  {selectedRoute.distance_km} km
                </span>
              )}
            </div>
          )}
        </div>

        {loadingRoute ? (
          <LoadingSpinner message={`Loading ${routeLabel} data...`} />
        ) : (
          <>
            {/* Route Index Chart */}
            <div className="card" style={{ marginBottom: 16 }}>
              <div className="card-title">{routeLabel} — Route Price Index (Base=100)</div>
              <div className="legend">
                <div className="legend-item">
                  <div className="legend-dot" style={{ background: '#3b82f6' }} />
                  DTD=14 Advance purchase
                </div>
                <div className="legend-item">
                  <div className="legend-dot" style={{ background: '#f59e0b' }} />
                  DTD=1 Last-minute
                </div>
              </div>
              <div className="chart-container-lg">
                {allDates.length > 0
                  ? <Line data={indexChartData} options={lineOpts()} />
                  : <div className="loading-state" style={{ height: '100%' }}>No index data for this route yet.</div>
                }
              </div>
            </div>

            {/* Absolute Fare Chart */}
            <div className="card" style={{ marginBottom: 16 }}>
              <div className="card-title">{routeLabel} — Median Absolute Fare (INR, last 30 days)</div>
              <div className="chart-container">
                {fareLabels.length > 0
                  ? <Line data={fareChartData} options={fareOpts} />
                  : <div className="loading-state" style={{ height: '100%' }}>No fare observations yet.</div>
                }
              </div>
            </div>

            {/* Airline Comparison Chart */}
            <div className="card">
              <div className="card-title">{routeLabel} — Airline Price Comparison (DTD=14, last 30 days)</div>
              <div className="chart-container">
                {airlineData.length > 0
                  ? <Line data={(() => {
                      const labels = airlineData.map(d => new Date(d.date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }));
                      const allAirlines = [...new Set(airlineData.flatMap(d => Object.keys(d.airlines)))];
                      const colors = ['#8b5cf6', '#ec4899', '#10b981', '#f59e0b', '#3b82f6'];
                      const datasets = allAirlines.map((airline, i) => ({
                        label: airline,
                        data: airlineData.map(d => d.airlines[airline] ?? null),
                        borderColor: colors[i % colors.length],
                        backgroundColor: colors[i % colors.length] + '20',
                        borderWidth: 2, pointRadius: 2, pointHoverRadius: 5,
                        tension: 0.2, spanGaps: true,
                      }));
                      return { labels, datasets };
                    })()} options={{
                      ...fareOpts,
                      plugins: {
                        ...fareOpts.plugins,
                        legend: { ...fareOpts.plugins.legend, display: true }
                      }
                    }} />
                  : <div className="loading-state" style={{ height: '100%' }}>No airline breakdown data available.</div>
                }
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
