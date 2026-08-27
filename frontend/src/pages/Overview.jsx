import { useEffect, useState } from 'react'
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, PointElement, LineElement,
  Title, Tooltip, Legend, Filler
} from 'chart.js'
import { Line } from 'react-chartjs-2'
import { getDashboardSummary, getNationalIndex, triggerScrape } from '../api/client'
import { LoadingSpinner, ErrorState } from '../components/LoadingSpinner'

ChartJS.register(
  CategoryScale, LinearScale, PointElement, LineElement,
  Title, Tooltip, Legend, Filler
)

const CHART_OPTS = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'index', intersect: false },
  plugins: {
    legend: {
      labels: {
        color: '#94a3b8',
        font: { family: 'Inter', size: 12 },
        boxWidth: 10,
        usePointStyle: true,
      }
    },
    tooltip: {
      backgroundColor: '#1a2235',
      borderColor: '#1f2d47',
      borderWidth: 1,
      titleColor: '#f1f5f9',
      bodyColor: '#94a3b8',
      callbacks: {
        label: ctx => ` ${ctx.dataset.label}: ${ctx.parsed.y.toFixed(2)}`
      }
    }
  },
  scales: {
    x: {
      grid: { color: '#1f2d47' },
      ticks: {
        color: '#475569',
        font: { size: 11 },
        maxTicksLimit: 12,
      }
    },
    y: {
      grid: { color: '#1f2d47' },
      ticks: {
        color: '#475569',
        font: { size: 11 },
        callback: v => v.toFixed(1)
      }
    }
  }
}

export default function Overview() {
  const [summary, setSummary] = useState(null)
  const [indexSeries14, setIndexSeries14] = useState([])
  const [indexSeries1, setIndexSeries1] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [scrapeStatus, setScrapeStatus] = useState(null)

  useEffect(() => {
    const load = async () => {
      try {
        const [sum, idx14, idx1] = await Promise.all([
          getDashboardSummary(),
          getNationalIndex({ dtd: 14 }),
          getNationalIndex({ dtd: 1 }),
        ])
        setSummary(sum)
        setIndexSeries14(idx14)
        setIndexSeries1(idx1)
      } catch (e) {
        setError(e.message)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const handleTriggerScrape = async () => {
    setScrapeStatus('Triggering...')
    try {
      const res = await triggerScrape()
      setScrapeStatus(`✓ ${res.message}`)
    } catch {
      setScrapeStatus('✗ Failed to trigger scrape')
    }
  }

  if (loading) return <div className="main-content"><LoadingSpinner message="Loading national index..." /></div>
  if (error)   return <div className="main-content"><div className="page-body"><ErrorState message={error} /></div></div>

  // Build chart data
  const allDates = [...new Set([
    ...indexSeries14.map(d => d.index_date),
    ...indexSeries1.map(d => d.index_date),
  ])].sort()

  const dtd14Map = Object.fromEntries(indexSeries14.map(d => [d.index_date, d.value]))
  const dtd1Map  = Object.fromEntries(indexSeries1.map(d => [d.index_date, d.value]))

  const chartData = {
    labels: allDates.map(d => {
      const dt = new Date(d)
      return dt.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })
    }),
    datasets: [
      {
        label: 'DTD=14 (Advance)',
        data: allDates.map(d => dtd14Map[d] ?? null),
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59,130,246,0.06)',
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        tension: 0.3,
        fill: true,
        spanGaps: true,
      },
      {
        label: 'DTD=1 (Last Minute)',
        data: allDates.map(d => dtd1Map[d] ?? null),
        borderColor: '#f59e0b',
        backgroundColor: 'rgba(245,158,11,0.04)',
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        tension: 0.3,
        fill: true,
        spanGaps: true,
      }
    ]
  }

  const mom = summary?.mom_change_pct
  const momClass = mom === null || mom === undefined ? '' : mom > 0 ? 'positive' : 'negative'
  const momSymbol = mom > 0 ? '▲' : '▼'

  return (
    <div className="main-content">
      <div className="page-header">
        <h2>National Index Overview</h2>
        <p>
          Laspeyres chain-linked weighted airfare price index across 6 domestic routes.
          Base = 100 on first observation date. DTD buckets: 14-day advance and last-minute (1-day).
        </p>
      </div>

      <div className="page-body">

        {/* KPI cards */}
        <div className="kpi-grid">
          <div className="kpi-card">
            <div className="kpi-label">National Index (DTD=14)</div>
            <div className="kpi-value mono">{summary?.latest_index?.toFixed(2) ?? '–'}</div>
            {mom !== null && mom !== undefined && (
              <span className={`kpi-change ${momClass}`}>
                {momSymbol} {Math.abs(mom).toFixed(2)}% MoM
              </span>
            )}
            <div className="kpi-sub">Base = 100 · {summary?.index_date}</div>
          </div>

          <div className="kpi-card">
            <div className="kpi-label">Methodology</div>
            <div className="kpi-value" style={{ fontSize: 16, marginTop: 4 }}>Laspeyres</div>
            <div className="kpi-sub">Chain-linked · DGCA FY25 weights</div>
          </div>

          <div className="kpi-card">
            <div className="kpi-label">Routes in Basket</div>
            <div className="kpi-value">6</div>
            <div className="kpi-sub">DEL-BOM · DEL-BLR · BOM-BLR · +3</div>
          </div>

          <div className="kpi-card">
            <div className="kpi-label">DTD Buckets</div>
            <div className="kpi-value">2</div>
            <div className="kpi-sub">14-day advance · 1-day last-minute</div>
          </div>
        </div>

        {/* Main trend chart */}
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="card-title">National Index — 60-Day Trend</div>
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
            <Line data={chartData} options={CHART_OPTS} />
          </div>
        </div>

        {/* Top movers + trigger */}
        <div className="charts-row">
          <div className="card">
            <div className="card-title">Top Route Movers (30-day)</div>
            {summary?.top_movers?.length > 0 ? (
              <table className="movers-table">
                <thead>
                  <tr>
                    <th>Route</th>
                    <th>30-day Change</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.top_movers.map(m => (
                    <tr key={m.route_id}>
                      <td><span className="route-pill">{m.route_label}</span></td>
                      <td className={m.change_pct > 0 ? 'change-up' : m.change_pct < 0 ? 'change-down' : 'change-flat'}>
                        {m.change_pct > 0 ? '▲' : m.change_pct < 0 ? '▼' : '–'} {Math.abs(m.change_pct).toFixed(2)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>No mover data yet.</div>
            )}
          </div>

          <div className="card">
            <div className="card-title">Demo Controls</div>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 16, lineHeight: 1.6 }}>
              Trigger the index recomputation pipeline on-demand.
              With Amadeus credentials, this also fetches live fare data.
            </p>
            <button
              onClick={handleTriggerScrape}
              style={{
                background: 'rgba(59,130,246,0.1)',
                border: '1px solid rgba(59,130,246,0.3)',
                color: '#3b82f6',
                padding: '10px 18px',
                borderRadius: 8,
                cursor: 'pointer',
                fontSize: 13,
                fontWeight: 600,
                width: '100%',
                fontFamily: 'Inter, sans-serif',
                transition: 'all 0.15s',
              }}
            >
              ⚡ Trigger Index Recompute
            </button>
            {scrapeStatus && (
              <div style={{ marginTop: 12, fontSize: 12, color: 'var(--text-secondary)' }}>
                {scrapeStatus}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
