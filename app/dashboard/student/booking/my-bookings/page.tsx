'use client'

import { useState, useMemo } from 'react'
import Link from 'next/link'
import { useLanguage } from '@/lib/i18n'
import DashboardLayout from '@/components/DashboardLayout'
import { 
  Calendar, 
  Clock, 
  MapPin, 
  Target,
  Plus,
  ChevronRight,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Sparkles
} from 'lucide-react'
import type { SupportBooking, BookingStatus } from '@/types'

// Mock data
const mockBookings: SupportBooking[] = [
  {
    id: '1',
    studentId: 'student-1',
    studentName: 'Test Student',
    date: '2026-04-12',
    time: '14:00',
    branch: 'branch1',
    purpose: 'speaking',
    status: 'approved',
    teacherName: 'Mr. Smith',
    dcoinCost: 0,
    createdAt: Date.now(),
    updatedAt: Date.now(),
  },
  {
    id: '2',
    studentId: 'student-1',
    studentName: 'Test Student',
    date: '2026-04-15',
    time: '10:00',
    branch: 'branch2',
    purpose: 'grammar',
    status: 'pending',
    dcoinCost: 0,
    createdAt: Date.now(),
    updatedAt: Date.now(),
  },
  {
    id: '3',
    studentId: 'student-1',
    studentName: 'Test Student',
    date: '2026-04-05',
    time: '15:30',
    branch: 'branch1',
    purpose: 'writing',
    status: 'completed',
    teacherName: 'Ms. Johnson',
    attendance: 'present',
    dcoinCost: 0,
    dcoinBonus: 2,
    createdAt: Date.now(),
    updatedAt: Date.now(),
  },
]

const statusConfig: Record<BookingStatus, { color: string; bgColor: string; icon: React.ReactNode }> = {
  pending: { color: 'text-amber-500', bgColor: 'bg-amber-500/10', icon: <AlertCircle size={16} /> },
  approved: { color: 'text-blue-500', bgColor: 'bg-blue-500/10', icon: <CheckCircle2 size={16} /> },
  completed: { color: 'text-green-500', bgColor: 'bg-green-500/10', icon: <CheckCircle2 size={16} /> },
  cancelled: { color: 'text-red-500', bgColor: 'bg-red-500/10', icon: <XCircle size={16} /> },
}

export default function MyBookingsPage() {
  const { t } = useLanguage()
  const [activeTab, setActiveTab] = useState<'upcoming' | 'past'>('upcoming')
  const [bookings] = useState<SupportBooking[]>(mockBookings)

  const today = useMemo(() => {
    const d = new Date()
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  }, [])
  const upcomingBookings = bookings.filter(b => b.date >= today && b.status !== 'cancelled')
  const pastBookings = bookings.filter(b => b.date < today || b.status === 'completed')

  const displayBookings = activeTab === 'upcoming' ? upcomingBookings : pastBookings

  return (
    <DashboardLayout role="student">
      <div className="max-w-4xl mx-auto p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-text-primary">{t('booking.myBookings')}</h1>
          <Link
            href="/dashboard/student/booking"
            className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-xl hover:bg-primary-dark transition-colors"
          >
            <Plus size={20} />
            {t('booking.bookLesson')}
          </Link>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 p-1 bg-surface-hover rounded-xl">
          <button
            onClick={() => setActiveTab('upcoming')}
            className={`flex-1 py-3 px-4 rounded-lg font-medium transition-all ${
              activeTab === 'upcoming'
                ? 'bg-primary text-white'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            {t('booking.upcoming')} ({upcomingBookings.length})
          </button>
          <button
            onClick={() => setActiveTab('past')}
            className={`flex-1 py-3 px-4 rounded-lg font-medium transition-all ${
              activeTab === 'past'
                ? 'bg-primary text-white'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            {t('booking.past')} ({pastBookings.length})
          </button>
        </div>

        {/* Bookings List */}
        {displayBookings.length === 0 ? (
          <div className="text-center py-16 bg-surface rounded-2xl border border-border">
            <Calendar className="w-16 h-16 text-text-secondary mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-text-primary mb-2">{t('booking.noBookings')}</h3>
            <p className="text-text-secondary mb-6">
              {activeTab === 'upcoming' 
                ? "Hali bronlar yo'q. Yangi dars bron qiling!"
                : "O'tgan bronlar mavjud emas"
              }
            </p>
            {activeTab === 'upcoming' && (
              <Link
                href="/dashboard/student/booking"
                className="inline-flex items-center gap-2 px-6 py-3 bg-primary text-white rounded-xl hover:bg-primary-dark transition-colors"
              >
                <Plus size={20} />
                {t('booking.bookLesson')}
              </Link>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            {displayBookings.map((booking) => {
              const status = statusConfig[booking.status]
              return (
                <div
                  key={booking.id}
                  className="bg-surface rounded-2xl border border-border p-6 hover:border-primary/30 transition-colors"
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg ${status.bgColor} ${status.color}`}>
                        {status.icon}
                      </div>
                      <div>
                        <span className={`text-sm font-medium ${status.color}`}>
                          {t(`booking.${booking.status}`)}
                        </span>
                        {booking.dcoinBonus && booking.dcoinBonus > 0 && (
                          <div className="flex items-center gap-1 text-amber-500 text-sm mt-1">
                            <Sparkles size={14} />
                            +{booking.dcoinBonus} D&apos;coin
                          </div>
                        )}
                      </div>
                    </div>
                    
                    {booking.status === 'pending' && (
                      <div className="flex gap-2">
                        <button className="px-3 py-1 text-sm text-primary bg-primary/10 rounded-lg hover:bg-primary/20 transition-colors">
                          {t('booking.reschedule')}
                        </button>
                        <button className="px-3 py-1 text-sm text-red-500 bg-red-500/10 rounded-lg hover:bg-red-500/20 transition-colors">
                          {t('booking.cancel')}
                        </button>
                      </div>
                    )}
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                    <div className="flex items-center gap-2">
                      <Calendar className="w-4 h-4 text-text-secondary" />
                      <span className="text-text-primary font-medium">{booking.date}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Clock className="w-4 h-4 text-text-secondary" />
                      <span className="text-text-primary font-medium">{booking.time}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <MapPin className="w-4 h-4 text-text-secondary" />
                      <span className="text-text-primary">{t(`booking.${booking.branch}`)}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Target className="w-4 h-4 text-text-secondary" />
                      <span className="text-text-primary">{t(`booking.${booking.purpose}`)}</span>
                    </div>
                  </div>

                  {booking.teacherName && (
                    <div className="mt-4 pt-4 border-t border-border flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
                          <span className="text-primary font-semibold text-sm">
                            {booking.teacherName.charAt(0)}
                          </span>
                        </div>
                        <div>
                          <p className="text-sm text-text-secondary">{t('booking.teacher')}</p>
                          <p className="font-medium text-text-primary">{booking.teacherName}</p>
                        </div>
                      </div>
                      <ChevronRight className="w-5 h-5 text-text-secondary" />
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
