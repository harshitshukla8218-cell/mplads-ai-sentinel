const LEVEL_STYLES = {
  High: { color: '#B23A2E', label: 'High Risk' },
  Medium: { color: '#B8862E', label: 'Medium Risk' },
  Low: { color: '#3F7A56', label: 'Low Risk' },
}

export default function StampBadge({ level, score, size = 'md' }) {
  const style = LEVEL_STYLES[level] || LEVEL_STYLES.Low
  const dims = size === 'lg' ? 'w-32 h-32 text-sm' : 'w-20 h-20 text-[10px]'

  return (
    <div
      className={`stamp ${dims} flex-col leading-tight`}
      style={{ color: style.color }}
    >
      <span className="font-mono font-bold" style={{ fontSize: size === 'lg' ? '1.6rem' : '1rem' }}>
        {Math.round(score)}
      </span>
      <span className="uppercase" style={{ fontSize: size === 'lg' ? '0.6rem' : '0.5rem' }}>
        {style.label}
      </span>
    </div>
  )
}
