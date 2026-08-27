import { NavLink } from 'react-router-dom'

const NAV_ITEMS = [
  { to: '/',           icon: '📊', label: 'Overview' },
  { to: '/routes',     icon: '✈️',  label: 'Route Explorer' },
  { to: '/quality',    icon: '🔍', label: 'Data Quality' },
  { to: '/methodology',icon: '📐', label: 'Methodology' },
]

export default function Navbar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <h1>India Airfare<br/>Price Index</h1>
        <span className="team-badge">SIH26056 · Runtime Rulers</span>
      </div>

      <nav className="sidebar-nav">
        {NAV_ITEMS.map(({ to, icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
          >
            <span className="nav-icon">{icon}</span>
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        Methodology: Laspeyres<br/>
        Chain-linked · v1.0
      </div>
    </aside>
  )
}
