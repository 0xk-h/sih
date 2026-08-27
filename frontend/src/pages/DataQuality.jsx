import { useEffect, useState } from 'react'
import { getDataQuality } from '../api/client'
import { LoadingSpinner, ErrorState } from '../components/LoadingSpinner'

function healthLevel(obs24h, obs7d) {
  if (obs7d === 0) return 'bad'
  if (obs24h === 0) return 'warning'
  return 'good'
}

function formatTimestamp(ts) {
  if (!ts) return '—'
  try {
    return new Date(ts).toLocaleString('en-IN', {
      day: '2-digit', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit', hour12: false
    })
  } catch { return ts }
}

export default function DataQuality() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    getDataQuality()
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="main-content"><LoadingSpinner message="Loading quality metrics..." /></div>
  if (error)   return <div className="main-content"><div className="page-body"><ErrorState message={error} /></div></div>

  const goodCount = data.routes.filter(r => healthLevel(r.obs_last_24h, r.obs_last_7d) === 'good').length
  const total = data.routes.length

  return (
    <div className="main-content">
      <div className="page-header">
        <h2>Data Quality</h2>
        <p>
          Sample sizes, last collection timestamps, and coverage gaps per route × DTD bucket.
          Transparency is a core requirement for a CPI-adjacent measurement tool.
        </p>
      </div>

      <div className="page-body">
        {/* Summary KPIs */}
        <div className="kpi-grid" style={{ marginBottom: 20 }}>
          <div className="kpi-card">
            <div className="kpi-label">Coverage Health</div>
            <div className="kpi-value">{goodCount}/{total}</div>
            <div className="kpi-sub">Route/bucket combos with recent data</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Report Generated</div>
            <div className="kpi-value" style={{ fontSize: 14, marginTop: 8 }}>
              {formatTimestamp(data.generated_at)}
            </div>
            <div className="kpi-sub">UTC</div>
          </div>
        </div>

        <div className="card">
          <div className="card-title">Coverage by Route × DTD Bucket</div>
          <table className="quality-table">
            <thead>
              <tr>
                <th>Health</th>
                <th>Route</th>
                <th>DTD Bucket</th>
                <th>Last Collected</th>
                <th>Obs (24h)</th>
                <th>Obs (7d)</th>
                <th>Avg Sample Size</th>
              </tr>
            </thead>
            <tbody>
              {data.routes.map((row, i) => {
                const level = healthLevel(row.obs_last_24h, row.obs_last_7d)
                return (
                  <tr key={i}>
                    <td>
                      <span className={`health-dot ${level}`} />
                      {level === 'good' ? 'Good' : level === 'warning' ? 'Stale' : 'No Data'}
                    </td>
                    <td><span className="route-pill">{row.route_label}</span></td>
                    <td style={{ fontFamily: 'JetBrains Mono', color: row.dtd_bucket === 14 ? '#3b82f6' : '#f59e0b' }}>
                      DTD={row.dtd_bucket}
                    </td>
                    <td style={{ fontSize: 11 }}>{formatTimestamp(row.last_collected_at)}</td>
                    <td style={{ fontFamily: 'JetBrains Mono' }}>{row.obs_last_24h}</td>
                    <td style={{ fontFamily: 'JetBrains Mono' }}>{row.obs_last_7d}</td>
                    <td style={{ fontFamily: 'JetBrains Mono' }}>
                      {row.avg_sample_size ? row.avg_sample_size.toFixed(1) : '—'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        <div className="card" style={{ marginTop: 16 }}>
          <div className="card-title">Legend</div>
          <div style={{ display: 'flex', gap: 24, fontSize: 13, color: 'var(--text-secondary)' }}>
            <div><span className="health-dot good" /> <strong>Good</strong> — observations in last 24h</div>
            <div><span className="health-dot warning" /> <strong>Stale</strong> — observations in last 7d, but not 24h</div>
            <div><span className="health-dot bad" /> <strong>No Data</strong> — no observations in 7 days</div>
          </div>
        </div>
      </div>
    </div>
  )
}
