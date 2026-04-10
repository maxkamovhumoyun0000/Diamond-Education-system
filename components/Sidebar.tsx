'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { 
  LayoutDashboard, 
  Users, 
  BookOpen, 
  BarChart3, 
  Settings,
  FileText,
  Trophy,
  Calendar,
  ChevronRight,
  X,
  FolderOpen
} from 'lucide-react'
import { useState, useEffect } from 'react'
import { useLanguage } from '@/lib/i18n'

interface NavItem {
  label: string
  href: string
  icon: React.ReactNode
  badge?: number | string
}

interface SidebarProps {
  role: 'admin' | 'student' | 'teacher' | 'support'
  isOpen?: boolean
  onClose?: () => void
}

export default function Sidebar({ role, isOpen = true, onClose }: SidebarProps) {
  const [pathname, setPathname] = useState<string>('')
  const pathnameHook = usePathname()
  const { t } = useLanguage()

  useEffect(() => {
    setPathname(pathnameHook)
  }, [pathnameHook])

  const getNavItems = (): NavItem[] => {
    const baseItems = [
      {
        label: t('common.dashboard'),
        href: `/dashboard/${role}`,
        icon: <LayoutDashboard size={20} />,
      },
    ]

    const roleItems: Record<string, NavItem[]> = {
      admin: [
        ...baseItems,
        {
          label: t('admin.users'),
          href: `/dashboard/admin/users`,
          icon: <Users size={20} />,
        },
        {
          label: t('admin.groups'),
          href: `/dashboard/admin/groups`,
          icon: <BookOpen size={20} />,
        },
        {
          label: t('admin.analytics'),
          href: `/dashboard/admin/analytics`,
          icon: <BarChart3 size={20} />,
          badge: '↑12%',
        },
        {
          label: t('admin.payments'),
          href: `/dashboard/admin/payments`,
          icon: <FileText size={20} />,
        },
        {
          label: t('admin.aiGenerator'),
          href: `/dashboard/admin/ai-generator`,
          icon: <BookOpen size={20} />,
        },
        {
          label: t('common.settings'),
          href: `/dashboard/admin/settings`,
          icon: <Settings size={20} />,
        },
      ],
      student: [
        ...baseItems,
        {
          label: t('materials.title'),
          href: `/dashboard/student/materials`,
          icon: <FolderOpen size={20} />,
        },
        {
          label: t('student.lessons'),
          href: `/dashboard/student/lessons`,
          icon: <BookOpen size={20} />,
          badge: 3,
        },
        {
          label: t('student.games'),
          href: `/dashboard/student/games`,
          icon: <Trophy size={20} />,
        },
        {
          label: t('student.vocabulary'),
          href: `/dashboard/student/vocabulary`,
          icon: <FileText size={20} />,
        },
        {
          label: t('student.leaderboard'),
          href: `/dashboard/student/leaderboard`,
          icon: <BarChart3 size={20} />,
        },
        {
          label: t('student.homework'),
          href: `/dashboard/student/homework`,
          icon: <Calendar size={20} />,
        },
        {
          label: t('common.settings'),
          href: `/dashboard/student/settings`,
          icon: <Settings size={20} />,
        },
      ],
      teacher: [
        ...baseItems,
        {
          label: t('teacher.myGroups'),
          href: `/dashboard/teacher/groups`,
          icon: <Users size={20} />,
          badge: 2,
        },
        {
          label: t('student.lessons'),
          href: `/dashboard/teacher/lessons`,
          icon: <BookOpen size={20} />,
        },
        {
          label: t('teacher.attendance'),
          href: `/dashboard/teacher/attendance`,
          icon: <Calendar size={20} />,
        },
        {
          label: t('teacher.tests'),
          href: `/dashboard/teacher/tests`,
          icon: <FileText size={20} />,
        },
        {
          label: t('admin.analytics'),
          href: `/dashboard/teacher/analytics`,
          icon: <BarChart3 size={20} />,
        },
        {
          label: t('common.settings'),
          href: `/dashboard/teacher/settings`,
          icon: <Settings size={20} />,
        },
      ],
      support: [
        ...baseItems,
        {
          label: 'Buyurtmalar',
          href: `/dashboard/support/bookings`,
          icon: <Calendar size={20} />,
          badge: 5,
        },
        {
          label: 'Jadval',
          href: `/dashboard/support/schedule`,
          icon: <Calendar size={20} />,
        },
        {
          label: t('student.lessons'),
          href: `/dashboard/support/lessons`,
          icon: <BookOpen size={20} />,
        },
        {
          label: t('admin.analytics'),
          href: `/dashboard/support/analytics`,
          icon: <BarChart3 size={20} />,
        },
        {
          label: t('common.settings'),
          href: `/dashboard/support/settings`,
          icon: <Settings size={20} />,
        },
      ],
    }

    return roleItems[role] || baseItems
  }

  const navItems = getNavItems()

  return (
    <>
      {/* Mobile Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 md:hidden z-40"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed md:relative top-16 md:top-0 left-0 h-screen md:h-auto bg-surface border-r border-border w-64 transition-transform duration-300 z-40 md:z-auto ${
          isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        } overflow-y-auto`}
      >
        <div className="p-4 space-y-2">
          {/* Mobile Close Button */}
          <button
            onClick={onClose}
            className="md:hidden absolute top-4 right-4 p-2 hover:bg-surface-hover rounded-lg transition-colors text-text-primary"
          >
            <X size={20} />
          </button>

          {/* Navigation Items */}
          <div className="pt-4 md:pt-0 space-y-2">
            {navItems.map((item) => {
              const isActive = pathname === item.href
              return (
                <div key={item.label}>
                  <Link
                    href={item.href}
                    onClick={onClose}
                    className={`flex items-center justify-between px-4 py-3 rounded-lg transition-colors group ${
                      isActive
                        ? 'bg-primary/10 text-primary font-medium'
                        : 'text-text-primary hover:bg-surface-hover'
                    }`}
                  >
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <span className={isActive ? 'text-primary' : 'text-text-secondary group-hover:text-primary'}>
                        {item.icon}
                      </span>
                      <span className="truncate">{item.label}</span>
                    </div>
                    {item.badge && (
                      <span className="ml-2 px-2 py-1 rounded-full bg-accent text-white text-xs font-medium whitespace-nowrap">
                        {item.badge}
                      </span>
                    )}
                    {isActive && <ChevronRight size={16} className="ml-2 flex-shrink-0" />}
                  </Link>
                </div>
              )
            })}
          </div>

          {/* Footer Info */}
          <div className="mt-8 pt-4 border-t border-border text-xs text-text-secondary">
            <p>Diamond Education v1.0</p>
            <p className="mt-1">Premium Learning Platform</p>
          </div>
        </div>
      </aside>
    </>
  )
}
