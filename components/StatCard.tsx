import { ReactNode } from 'react'
import { ArrowUp, ArrowDown } from 'lucide-react'

interface StatCardProps {
  title: string
  value: string | number
  subtitle?: string
  icon?: ReactNode
  trend?: {
    value: number
    isPositive: boolean
  }
  variant?: 'default' | 'primary' | 'accent'
}

export default function StatCard({
  title,
  value,
  subtitle,
  icon,
  trend,
  variant = 'default',
}: StatCardProps) {
  const variantClasses = {
    default: 'bg-surface border border-border',
    primary: 'bg-primary/10 border border-primary/20',
    accent: 'bg-accent/10 border border-accent/20',
  }

  return (
    <div className={`${variantClasses[variant]} rounded-lg p-6 transition-all hover:shadow-glass`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-text-secondary text-sm font-medium mb-1">{title}</p>
          <p className="text-3xl font-bold text-text-primary">{value}</p>
          {subtitle && <p className="text-text-secondary text-sm mt-2">{subtitle}</p>}
        </div>
        {icon && (
          <div className="ml-4 p-3 rounded-lg bg-surface-hover">
            {icon}
          </div>
        )}
      </div>
      {trend && (
        <div className="flex items-center gap-1 mt-4">
          {trend.isPositive ? (
            <ArrowUp size={16} className="text-green-500" />
          ) : (
            <ArrowDown size={16} className="text-red-500" />
          )}
          <span className={`text-sm font-medium ${trend.isPositive ? 'text-green-500' : 'text-red-500'}`}>
            {Math.abs(trend.value)}%
          </span>
        </div>
      )}
    </div>
  )
}
