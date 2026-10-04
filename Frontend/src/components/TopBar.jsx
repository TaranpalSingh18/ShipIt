import { Link, NavLink } from 'react-router-dom'
import { useTheme } from '../theme'

export function Wordmark({ to = '/app' }) {
  return (
    <Link to={to} className="wordmark" aria-label="ShipIt home">
      <span className="wordmark-mark" aria-hidden="true" />
      ShipIt
    </Link>
  )
}

export function ThemeToggle() {
  const [theme, toggle] = useTheme()
  const next = theme === 'dark' ? 'light' : 'dark'
  return (
    <button type="button" className="icon-btn" onClick={toggle} aria-label={`Switch to ${next} theme`}>
      {theme === 'dark' ? (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round">
          <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z" />
        </svg>
      )}
    </button>
  )
}

export default function TopBar({ session, onSignOut }) {
  return (
    <header className="topbar">
      <div className="shell topbar-in">
        <Wordmark />
        <nav className="topnav" aria-label="Main">
          <NavLink to="/app" end>
            Cases
          </NavLink>
          <NavLink to="/app/new">New case</NavLink>
        </nav>
        <div className="topbar-end">
          <span className="who">{session.email}</span>
          <ThemeToggle />
          <button type="button" className="btn quiet sm" onClick={onSignOut}>
            Sign out
          </button>
        </div>
      </div>
    </header>
  )
}
