interface ProgressCardProps {
  title: string
  current: number
  total: number
  icon?: React.ReactNode
  color?: 'primary' | 'accent' | 'green' | 'orange'
}

export default function ProgressCard({
  title,
  current,
  total,
  icon,
  color = 'primary',
}: ProgressCardProps) {
  const percentage = (current / total) * 100

  const colorClasses = {
    primary: 'bg-primary',
    accent: 'bg-accent',
    green: 'bg-green-500',
    orange: 'bg-orange-500',
  }

  return (
    <div className="bg-surface border border-border rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-text-primary">{title}</h3>
        {icon && <span className="text-text-secondary">{icon}</span>}
      </div>

      <div className="space-y-3">
        <div className="flex items-end justify-between">
          <span className="text-2xl font-bold text-text-primary">{current}</span>
          <span className="text-sm text-text-secondary">of {total}</span>
        </div>

        <div className="w-full h-3 bg-surface-hover rounded-full overflow-hidden">
          <div
            className={`h-full ${colorClasses[color]} rounded-full transition-all duration-500`}
            style={{ width: `${percentage}%` }}
          />
        </div>

        <div className="text-right">
          <span className="text-xs font-medium text-text-secondary">{Math.round(percentage)}%</span>
        </div>
      </div>
    </div>
  )
}
