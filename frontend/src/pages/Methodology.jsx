export default function Methodology() {
  return (
    <div className="main-content">
      <div className="page-header">
        <h2>Methodology</h2>
        <p>
          Plain-language explanation of the index formula, base period, and basket weights.
          Transparency is part of the product — CPI-adjacent tools must show their work.
        </p>
      </div>

      <div className="page-body">
        <div className="methodology-content" style={{ maxWidth: '1200px', margin: '0 auto', display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '24px' }}>

          <div className="card">
            <div className="card-title">1. The Comparability Problem (§3.1)</div>
            <div className="methodology-content">
              <p>
                A fare quoted 45 days before departure and one quoted 1 day before departure are
                <strong> not the same product</strong> — the same way a "500g rice pack" and a
                "5kg pack" are not the same CPI item. CPI methodology fixes item specifications;
                we do the equivalent by fixing <strong>Days-to-Departure (DTD) buckets</strong>.
              </p>
              <p>
                We collect fares at fixed DTD checkpoints for every route, every day. Each bucket
                is tracked as its own separate time series. This directly neutralizes "index bias
                from scrape timing."
              </p>
              <div className="formula-block">
                DTD Buckets (MVP): 14 days advance, 1 day last-minute<br/>
                Full system: 30 / 14 / 7 / 1
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-title">2. Representative Price per Route/Day (§3.2)</div>
            <div className="methodology-content">
              <p>
                For route <em>r</em>, date <em>t</em>, DTD bucket <em>b</em>, across all
                airlines/OTAs collected that day:
              </p>
              <div className="formula-block">
                P(r, t, b) = median(all normalized total fares collected)
              </div>
              <p>
                We use <strong>median</strong>, not mean — it's robust to scraping outliers
                (a single mis-parsed fare won't distort the series). Min/max/sample size are stored
                alongside in <code>daily_route_price</code> for data-quality auditing.
              </p>
            </div>
          </div>

          <div className="card">
            <div className="card-title">3. Route-Level Relative (§3.3)</div>
            <div className="methodology-content">
              <p>Analogous to a CPI "item relative" — measures movement, not absolute price:</p>
              <div className="formula-block">
                I_r(t) = [ P(r, t) / P(r, base_period) ] × 100
              </div>
              <p>
                Base period = first date with complete coverage across all active routes.
                Index = 100 on the base date, moves above/below as prices change.
              </p>
            </div>
          </div>

          <div className="card">
            <div className="card-title">4. Weighted Chain-Linked National Index (§3.4)</div>
            <div className="methodology-content">
              <p>
                Routes don't matter equally — DEL–BOM carries far more passengers than a thin
                regional route, so it should move the index more, exactly like CPI weights
                "cereals" heavier than "spices."
              </p>
              <p><strong>Laspeyres base-weighted index:</strong></p>
              <div className="formula-block">
                I(t) = Σ_r [ w_r × I_r(t) ]
              </div>
              <p><strong>Chain-linking (standard CPI practice):</strong></p>
              <div className="formula-block">
                I(t) = I(t−1) × Σ_r [ w_r(t−1) × P_r(t) / P_r(t−1) ]
              </div>
              <p>
                Chain-linking limits substitution bias in multi-month series and allows weights
                to be updated periodically (e.g., annually from DGCA data) without resetting
                the index.
              </p>
            </div>
          </div>

          <div className="card" style={{ gridRow: 'span 2' }}>
            <div className="card-title">5. Basket Weights (DGCA FY25 Traffic Share)</div>
            <div className="methodology-content">
              <p>
                Route weights derived from DGCA domestic passenger traffic statistics (FY2024-25).
                Weights are refreshed annually, not per-scrape.
              </p>
              <table className="weight-table">
                <thead>
                  <tr>
                    <th>Route</th>
                    <th>Cities</th>
                    <th>DGCA Weight</th>
                    <th>Basis</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    ['DEL–BOM', 'New Delhi → Mumbai', '28%', 'Busiest domestic corridor'],
                    ['DEL–BLR', 'New Delhi → Bengaluru', '18%', 'Tech hub route'],
                    ['BOM–BLR', 'Mumbai → Bengaluru', '14%', 'High business traffic'],
                    ['DEL–HYD', 'New Delhi → Hyderabad', '13%', 'Significant tech/gov route'],
                    ['DEL–CCU', 'New Delhi → Kolkata', '12%', 'East India corridor'],
                    ['BOM–GOI', 'Mumbai → Goa', '10%', 'High leisure demand'],
                  ].map(([route, cities, weight, basis]) => (
                    <tr key={route}>
                      <td><span className="route-pill">{route}</span></td>
                      <td style={{ color: 'var(--text-secondary)' }}>{cities}</td>
                      <td style={{ fontFamily: 'JetBrains Mono', fontWeight: 600 }}>{weight}</td>
                      <td style={{ color: 'var(--text-muted)', fontSize: 11 }}>{basis}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p style={{ marginTop: 12, fontSize: 12, color: 'var(--text-muted)' }}>
                Source: DGCA Domestic Air Traffic Statistics FY24-25 (approximate shares).
                In production, weights would be updated annually from official DGCA publications.
              </p>
            </div>
          </div>

          <div className="card">
            <div className="card-title">6. Path to Production</div>
            <div className="methodology-content">
              <p>
                For a production-grade system, the sustainable path is <strong>official data
                partnerships/APIs</strong> rather than web scraping at scale:
              </p>
              <ul style={{ paddingLeft: 20, fontSize: 13.5, color: 'var(--text-secondary)', lineHeight: 2 }}>
                <li><strong>Amadeus Self-Service API</strong> — already integrated (sandbox tier in MVP)</li>
                <li><strong>IATA NDC APIs</strong> — direct airline distribution feeds</li>
                <li><strong>Sabre/Galileo GDS APIs</strong> — comprehensive fare data</li>
                <li>Scraping remains a "bridge technique" until partnerships are established</li>
              </ul>
            </div>
          </div>

        </div>
      </div>
    </div>
  )
}
