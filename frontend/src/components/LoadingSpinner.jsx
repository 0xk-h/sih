export function LoadingSpinner({ message = 'Loading...' }) {
  return (
    <div className="loading-state">
      <div className="spinner" />
      <span>{message}</span>
    </div>
  )
}

export function ErrorState({ message }) {
  return (
    <div className="error-state">
      ⚠ {message || 'Failed to load data. Is the backend running?'}
    </div>
  )
}
