import { NavLink } from 'react-router-dom'

const linkClass = ({ isActive }) =>
  `block px-4 py-2.5 rounded-sm text-sm tracking-wide transition-colors ${
    isActive
      ? 'bg-white/10 text-white border-l-2 border-gold-600'
      : 'text-white/60 hover:text-white/90 hover:bg-white/5 border-l-2 border-transparent'
  }`

export default function Sidebar() {
  return (
    <aside className="w-60 shrink-0 bg-ink-900 min-h-screen flex flex-col">
      <div className="px-5 pt-7 pb-6 border-b border-white/10">
        <div className="font-display text-white text-xl leading-tight">MPLADS</div>
        <div className="font-display text-gold-600 text-lg leading-tight -mt-1">Sentinel</div>
        <div className="text-white/40 text-[11px] mt-2 font-mono tracking-wide">
          RISK SCREENING SYSTEM
        </div>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-1">
        <NavLink to="/" end className={linkClass}>Case Register</NavLink>
        <NavLink to="/entities" className={linkClass}>Repeat Patterns</NavLink>
        <NavLink to="/about" className={linkClass}>How Scoring Works</NavLink>
      </nav>
      <div className="px-5 py-5 border-t border-white/10 text-white/35 text-[11px] leading-relaxed">
        An anomaly is a warning signal, not proof of wrongdoing. A human
        official makes the final call.
      </div>
    </aside>
  )
}
