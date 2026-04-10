'use client'

import { useState } from 'react'
import { useLanguage } from '@/lib/i18n'
import DashboardLayout from '@/components/DashboardLayout'
import { 
  Calendar, 
  Clock, 
  Users, 
  TrendingUp,
  ChevronLeft,
  ChevronRight,
  Plus,
  X,
  Check,
  AlertCircle,
  Sparkles,
  Filter
} from 'lucide-react'
import type { SupportBooking, BookingStatus, TimeSlot, AttendanceStatus } from '@/types'

// Mock bookings data
const mockBookings: SupportBooking[] = [
  {
    id: '1',
    studentId: 'student-1',
    studentName: 'Alisher Karimov',
    date: '2026-04-10',
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
    studentId: 'student-2',
    studentName: 'Nodira Azimova',
    date: '2026-04-10',
    time: '14:30',
    branch: 'branch1',
    purpose: 'grammar',
    status: 'pending',
    dcoinCost: 0,
    createdAt: Date.now(),
    updatedAt: Date.now(),
  },
  {
    id: '3',
    studentId: 'student-3',
    studentName: 'Jasur Toshmatov',
    date: '2026-04-11',
    time: '10:00',
    branch: 'branch2',
    purpose: 'writing',
    status: 'approved',
    teacherName: 'Ms. Johnson',
    dcoinCost: 0,
    createdAt: Date.now(),
    updatedAt: Date.now(),
  },
  {
    id: '4',
    studentId: 'student-4',
    studentName: 'Malika Rahimova',
    date: '2026-04-09',
    time: '15:30',
    branch: 'branch1',
    purpose: 'listening',
    status: 'completed',
    teacherName: 'Mr. Brown',
    attendance: 'present',
    dcoinCost: 0,
    dcoinBonus: 2,
    createdAt: Date.now(),
    updatedAt: Date.now(),
  },
]

// Generate calendar dates
const generateCalendarDates = (year: number, month: number) => {
  const firstDay = new Date(year, month, 1)
  const lastDay = new Date(year, month + 1, 0)
  const daysInMonth = lastDay.getDate()
  const startingDay = firstDay.getDay()
  
  const dates = []
  // Add empty cells for days before the first day of the month
  for (let i = 0; i < startingDay; i++) {
    dates.push(null)
  }
  // Add all days of the month
  for (let i = 1; i <= daysInMonth; i++) {
    dates.push(new Date(year, month, i))
  }
  return dates
}

const statusColors: Record<BookingStatus, string> = {
  pending: 'bg-amber-500/10 text-amber-500 border-amber-500/20',
  approved: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
  completed: 'bg-green-500/10 text-green-500 border-green-500/20',
  cancelled: 'bg-red-500/10 text-red-500 border-red-500/20',
}

export default function SupportBookingDashboard() {
  const { t } = useLanguage()
  const [currentDate, setCurrentDate] = useState(new Date())
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [bookings, setBookings] = useState<SupportBooking[]>(mockBookings)
  const [showAttendanceModal, setShowAttendanceModal] = useState(false)
  const [showBonusModal, setShowBonusModal] = useState(false)
  const [selectedBooking, setSelectedBooking] = useState<SupportBooking | null>(null)
  const [bonusAmount, setBonusAmount] = useState(1)
  const [bonusReason, setBonusReason] = useState('')
  const [filterStatus, setFilterStatus] = useState<BookingStatus | 'all'>('all')
  const [filterBranch, setFilterBranch] = useState<'all' | 'branch1' | 'branch2'>('all')

  const calendarDates = generateCalendarDates(currentDate.getFullYear(), currentDate.getMonth())
  const today = new Date().toISOString().split('T')[0]

  // Stats
  const todayBookings = bookings.filter(b => b.date === today).length
  const upcomingBookings = bookings.filter(b => b.date >= today && b.status !== 'cancelled').length
  const thisMonthBookings = bookings.filter(b => {
    const bookingDate = new Date(b.date)
    return bookingDate.getMonth() === currentDate.getMonth() && 
           bookingDate.getFullYear() === currentDate.getFullYear()
  }).length
  const completedBookings = bookings.filter(b => b.status === 'completed')
  const presentCount = completedBookings.filter(b => b.attendance === 'present').length
  const attendanceRate = completedBookings.length > 0 
    ? Math.round((presentCount / completedBookings.length) * 100) 
    : 0

  // Filter bookings
  const filteredBookings = bookings.filter(b => {
    if (filterStatus !== 'all' && b.status !== filterStatus) return false
    if (filterBranch !== 'all' && b.branch !== filterBranch) return false
    if (selectedDate && b.date !== selectedDate) return false
    return true
  })

  const handleApprove = (bookingId: string) => {
    setBookings(prev => prev.map(b => 
      b.id === bookingId ? { ...b, status: 'approved' as BookingStatus, updatedAt: Date.now() } : b
    ))
  }

  const handleReject = (bookingId: string) => {
    setBookings(prev => prev.map(b => 
      b.id === bookingId ? { ...b, status: 'cancelled' as BookingStatus, updatedAt: Date.now() } : b
    ))
  }

  const handleMarkAttendance = (attendance: AttendanceStatus) => {
    if (selectedBooking) {
      setBookings(prev => prev.map(b => 
        b.id === selectedBooking.id 
          ? { 
              ...b, 
              status: 'completed' as BookingStatus, 
              attendance,
              dcoinBonus: attendance === 'present' ? 2 : 0,
              updatedAt: Date.now() 
            } 
          : b
      ))
      setShowAttendanceModal(false)
      setSelectedBooking(null)
    }
  }

  const handleGiveBonus = () => {
    if (selectedBooking && bonusAmount > 0) {
      setBookings(prev => prev.map(b => 
        b.id === selectedBooking.id 
          ? { 
              ...b, 
              dcoinBonus: (b.dcoinBonus || 0) + bonusAmount,
              bonusReason: bonusReason,
              updatedAt: Date.now() 
            } 
          : b
      ))
      setShowBonusModal(false)
      setSelectedBooking(null)
      setBonusAmount(1)
      setBonusReason('')
    }
  }

  const prevMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1))
  }

  const nextMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1))
  }

  const getBookingsForDate = (date: Date) => {
    const dateStr = date.toISOString().split('T')[0]
    return bookings.filter(b => b.date === dateStr)
  }

  return (
    <DashboardLayout role="support">
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-text-primary">{t('support.dashboard')}</h1>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-surface rounded-2xl border border-border p-6">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-xl bg-primary/10">
                <Calendar className="w-6 h-6 text-primary" />
              </div>
              <div>
                <p className="text-sm text-text-secondary">{t('support.todayBookings')}</p>
                <p className="text-2xl font-bold text-text-primary">{todayBookings}</p>
              </div>
            </div>
          </div>
          
          <div className="bg-surface rounded-2xl border border-border p-6">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-xl bg-blue-500/10">
                <Clock className="w-6 h-6 text-blue-500" />
              </div>
              <div>
                <p className="text-sm text-text-secondary">{t('support.upcomingBookings')}</p>
                <p className="text-2xl font-bold text-text-primary">{upcomingBookings}</p>
              </div>
            </div>
          </div>
          
          <div className="bg-surface rounded-2xl border border-border p-6">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-xl bg-green-500/10">
                <Users className="w-6 h-6 text-green-500" />
              </div>
              <div>
                <p className="text-sm text-text-secondary">{t('support.totalThisMonth')}</p>
                <p className="text-2xl font-bold text-text-primary">{thisMonthBookings}</p>
              </div>
            </div>
          </div>
          
          <div className="bg-surface rounded-2xl border border-border p-6">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-xl bg-amber-500/10">
                <TrendingUp className="w-6 h-6 text-amber-500" />
              </div>
              <div>
                <p className="text-sm text-text-secondary">{t('support.attendanceRate')}</p>
                <p className="text-2xl font-bold text-text-primary">{attendanceRate}%</p>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Calendar */}
          <div className="lg:col-span-1 bg-surface rounded-2xl border border-border p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-text-primary">
                {t('support.calendarManagement')}
              </h2>
              <div className="flex items-center gap-2">
                <button onClick={prevMonth} className="p-2 hover:bg-surface-hover rounded-lg transition-colors">
                  <ChevronLeft size={20} className="text-text-secondary" />
                </button>
                <span className="text-text-primary font-medium min-w-[120px] text-center">
                  {currentDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
                </span>
                <button onClick={nextMonth} className="p-2 hover:bg-surface-hover rounded-lg transition-colors">
                  <ChevronRight size={20} className="text-text-secondary" />
                </button>
              </div>
            </div>

            <div className="grid grid-cols-7 gap-1 mb-2">
              {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
                <div key={day} className="text-center text-xs font-medium text-text-secondary py-2">
                  {day}
                </div>
              ))}
            </div>

            <div className="grid grid-cols-7 gap-1">
              {calendarDates.map((date, index) => {
                if (!date) {
                  return <div key={`empty-${index}`} className="p-2" />
                }
                const dateStr = date.toISOString().split('T')[0]
                const dateBookings = getBookingsForDate(date)
                const isToday = dateStr === today
                const isSelected = dateStr === selectedDate
                const isWeekend = date.getDay() === 0 || date.getDay() === 6

                return (
                  <button
                    key={dateStr}
                    onClick={() => setSelectedDate(isSelected ? null : dateStr)}
                    className={`p-2 rounded-lg text-center transition-all relative ${
                      isSelected
                        ? 'bg-primary text-white'
                        : isToday
                        ? 'bg-primary/10 text-primary border border-primary'
                        : isWeekend
                        ? 'text-text-secondary'
                        : 'hover:bg-surface-hover text-text-primary'
                    }`}
                  >
                    <span className="text-sm">{date.getDate()}</span>
                    {dateBookings.length > 0 && (
                      <div className={`absolute bottom-1 left-1/2 -translate-x-1/2 w-1.5 h-1.5 rounded-full ${
                        isSelected ? 'bg-white' : 'bg-primary'
                      }`} />
                    )}
                  </button>
                )
              })}
            </div>

            {selectedDate && (
              <div className="mt-4 pt-4 border-t border-border">
                <p className="text-sm text-text-secondary mb-2">
                  {selectedDate}: {getBookingsForDate(new Date(selectedDate)).length} bronlar
                </p>
                <button
                  onClick={() => setSelectedDate(null)}
                  className="text-sm text-primary hover:underline"
                >
                  Barcha bronlarni ko&apos;rish
                </button>
              </div>
            )}
          </div>

          {/* Bookings List */}
          <div className="lg:col-span-2 bg-surface rounded-2xl border border-border p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-text-primary">{t('support.allBookings')}</h2>
              <div className="flex items-center gap-2">
                <select
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value as BookingStatus | 'all')}
                  className="px-3 py-2 bg-surface-hover border border-border rounded-lg text-sm text-text-primary"
                >
                  <option value="all">Barchasi</option>
                  <option value="pending">{t('booking.pending')}</option>
                  <option value="approved">{t('booking.approved')}</option>
                  <option value="completed">{t('booking.completed')}</option>
                  <option value="cancelled">{t('booking.cancelled')}</option>
                </select>
                <select
                  value={filterBranch}
                  onChange={(e) => setFilterBranch(e.target.value as 'all' | 'branch1' | 'branch2')}
                  className="px-3 py-2 bg-surface-hover border border-border rounded-lg text-sm text-text-primary"
                >
                  <option value="all">Barcha filiallar</option>
                  <option value="branch1">{t('booking.branch1')}</option>
                  <option value="branch2">{t('booking.branch2')}</option>
                </select>
              </div>
            </div>

            <div className="space-y-3 max-h-[500px] overflow-y-auto">
              {filteredBookings.length === 0 ? (
                <div className="text-center py-8 text-text-secondary">
                  Bronlar topilmadi
                </div>
              ) : (
                filteredBookings.map((booking) => (
                  <div
                    key={booking.id}
                    className="p-4 bg-surface-hover rounded-xl border border-border"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h3 className="font-semibold text-text-primary">{booking.studentName}</h3>
                        <p className="text-sm text-text-secondary">
                          {booking.date} | {booking.time} | {t(`booking.${booking.branch}`)}
                        </p>
                      </div>
                      <span className={`px-3 py-1 rounded-full text-xs font-medium border ${statusColors[booking.status]}`}>
                        {t(`booking.${booking.status}`)}
                      </span>
                    </div>

                    <div className="flex items-center gap-4 text-sm text-text-secondary mb-3">
                      <span>{t(`booking.${booking.purpose}`)}</span>
                      {booking.teacherName && <span>| {booking.teacherName}</span>}
                      {booking.dcoinBonus && booking.dcoinBonus > 0 && (
                        <span className="flex items-center gap-1 text-amber-500">
                          <Sparkles size={14} /> +{booking.dcoinBonus} D&apos;coin
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      {booking.status === 'pending' && (
                        <>
                          <button
                            onClick={() => handleApprove(booking.id)}
                            className="flex items-center gap-1 px-3 py-1.5 bg-green-500/10 text-green-500 rounded-lg text-sm hover:bg-green-500/20 transition-colors"
                          >
                            <Check size={14} /> Tasdiqlash
                          </button>
                          <button
                            onClick={() => handleReject(booking.id)}
                            className="flex items-center gap-1 px-3 py-1.5 bg-red-500/10 text-red-500 rounded-lg text-sm hover:bg-red-500/20 transition-colors"
                          >
                            <X size={14} /> Rad etish
                          </button>
                        </>
                      )}
                      {booking.status === 'approved' && (
                        <button
                          onClick={() => {
                            setSelectedBooking(booking)
                            setShowAttendanceModal(true)
                          }}
                          className="flex items-center gap-1 px-3 py-1.5 bg-primary/10 text-primary rounded-lg text-sm hover:bg-primary/20 transition-colors"
                        >
                          <AlertCircle size={14} /> {t('support.markAttendance')}
                        </button>
                      )}
                      {booking.status === 'completed' && (
                        <button
                          onClick={() => {
                            setSelectedBooking(booking)
                            setShowBonusModal(true)
                          }}
                          className="flex items-center gap-1 px-3 py-1.5 bg-amber-500/10 text-amber-500 rounded-lg text-sm hover:bg-amber-500/20 transition-colors"
                        >
                          <Sparkles size={14} /> {t('support.giveBonus')}
                        </button>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Attendance Modal */}
        {showAttendanceModal && selectedBooking && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-surface rounded-2xl p-6 max-w-md w-full">
              <h3 className="text-lg font-semibold text-text-primary mb-4">{t('support.markAttendance')}</h3>
              <p className="text-text-secondary mb-6">
                {selectedBooking.studentName} - {selectedBooking.date} {selectedBooking.time}
              </p>
              <div className="grid grid-cols-3 gap-3 mb-6">
                <button
                  onClick={() => handleMarkAttendance('present')}
                  className="flex flex-col items-center gap-2 p-4 rounded-xl bg-green-500/10 text-green-500 hover:bg-green-500/20 transition-colors"
                >
                  <Check size={24} />
                  <span className="text-sm font-medium">{t('support.present')}</span>
                </button>
                <button
                  onClick={() => handleMarkAttendance('late')}
                  className="flex flex-col items-center gap-2 p-4 rounded-xl bg-amber-500/10 text-amber-500 hover:bg-amber-500/20 transition-colors"
                >
                  <Clock size={24} />
                  <span className="text-sm font-medium">{t('support.late')}</span>
                </button>
                <button
                  onClick={() => handleMarkAttendance('absent')}
                  className="flex flex-col items-center gap-2 p-4 rounded-xl bg-red-500/10 text-red-500 hover:bg-red-500/20 transition-colors"
                >
                  <X size={24} />
                  <span className="text-sm font-medium">{t('support.absent')}</span>
                </button>
              </div>
              <button
                onClick={() => {
                  setShowAttendanceModal(false)
                  setSelectedBooking(null)
                }}
                className="w-full py-3 bg-surface-hover text-text-primary rounded-xl hover:bg-border transition-colors"
              >
                {t('common.cancel')}
              </button>
            </div>
          </div>
        )}

        {/* Bonus Modal */}
        {showBonusModal && selectedBooking && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-surface rounded-2xl p-6 max-w-md w-full">
              <h3 className="text-lg font-semibold text-text-primary mb-4">{t('support.giveBonus')}</h3>
              <p className="text-text-secondary mb-6">
                {selectedBooking.studentName}
              </p>
              
              <div className="mb-4">
                <label className="block text-sm text-text-secondary mb-2">D&apos;coin miqdori</label>
                <div className="flex items-center gap-2">
                  {[1, 2, 3, 5, 10].map(amount => (
                    <button
                      key={amount}
                      onClick={() => setBonusAmount(amount)}
                      className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                        bonusAmount === amount
                          ? 'bg-amber-500 text-white'
                          : 'bg-surface-hover text-text-primary hover:bg-amber-500/20'
                      }`}
                    >
                      +{amount}
                    </button>
                  ))}
                </div>
              </div>

              <div className="mb-6">
                <label className="block text-sm text-text-secondary mb-2">{t('support.bonusReason')}</label>
                <input
                  type="text"
                  value={bonusReason}
                  onChange={(e) => setBonusReason(e.target.value)}
                  placeholder="Masalan: Ajoyib natija"
                  className="w-full px-4 py-3 bg-surface-hover border border-border rounded-xl text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => {
                    setShowBonusModal(false)
                    setSelectedBooking(null)
                    setBonusAmount(1)
                    setBonusReason('')
                  }}
                  className="flex-1 py-3 bg-surface-hover text-text-primary rounded-xl hover:bg-border transition-colors"
                >
                  {t('common.cancel')}
                </button>
                <button
                  onClick={handleGiveBonus}
                  className="flex-1 py-3 bg-amber-500 text-white rounded-xl hover:bg-amber-600 transition-colors"
                >
                  {t('support.giveBonus')}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
