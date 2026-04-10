'use client'

import { useSubject, Subject } from '@/lib/subject-context'
import { useLanguage } from '@/lib/i18n'
import { BookOpen, Languages } from 'lucide-react'

const subjectConfig: Record<Subject, { icon: typeof BookOpen; color: string; bgColor: string }> = {
  english: {
    icon: BookOpen,
    color: 'text-blue-600',
    bgColor: 'bg-blue-100',
  },
  russian: {
    icon: Languages,
    color: 'text-red-600',
    bgColor: 'bg-red-100',
  },
}

export default function SubjectSwitcher() {
  const { subject, setSubject } = useSubject()
  const { t } = useLanguage()

  const subjects: Subject[] = ['english', 'russian']

  return (
    <div className="flex items-center gap-1 p-1 bg-surface-hover rounded-lg border border-border">
      {subjects.map((s) => {
        const config = subjectConfig[s]
        const Icon = config.icon
        const isActive = subject === s

        return (
          <button
            key={s}
            onClick={() => setSubject(s)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-all ${
              isActive
                ? `${config.bgColor} ${config.color}`
                : 'text-text-secondary hover:text-text-primary hover:bg-surface'
            }`}
          >
            <Icon size={16} />
            <span className="hidden sm:inline">{t(`subject.${s}`)}</span>
          </button>
        )
      })}
    </div>
  )
}
