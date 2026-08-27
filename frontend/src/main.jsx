import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import './index.css'
import Navbar from './components/Navbar'
import Overview from './pages/Overview'
import RouteExplorer from './pages/RouteExplorer'
import DataQuality from './pages/DataQuality'
import Methodology from './pages/Methodology'

function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <Navbar />
        <Routes>
          <Route path="/"            element={<Overview />} />
          <Route path="/routes"      element={<RouteExplorer />} />
          <Route path="/quality"     element={<DataQuality />} />
          <Route path="/methodology" element={<Methodology />} />
          <Route path="*"            element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
