'use client'

import { useState, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import { useLanguage } from '@/lib/i18n'
import DashboardLayout from '@/components/DashboardLayout'
import { 
  Calendar, 
  Clock, 
  MapPin, 
  Target, 
  ChevronLeft, 
  ChevronRight,
  Sparkles,
  CheckCircle2,
  BookOpen
} from 'lucide-react'
import type { BookingPurpose, Branch, TimeSlot } from '@/types'

const purposes: { key: BookingPurpose; icon: React.ReactNode }[] = [
  { key: 'speaking', icon: <span className="text-lg">🗣️</span> },
  { key: 'grammar', icon: <span className="text-lg">📝</span> },
  { key: 'writing', icon: <span className="text-lg">✍️</span> },
  { key: 'reading', icon: <span className="text-lg">📖</span> },
  { key: 'listening', icon: <span className="text-lg">🎧</span> },
  { key: 'general', icon: <span className="text-lg">📚</span> },
]

// Generate next 14 days - moved inside component with useMemo

// Generate time slots
const generateTimeSlots = (): TimeSlot[] => {
  const slots: TimeSlot[] = []
  const times = ['09:00', '09:30', '10:00', '10:30', '11:00', '14:00', '14:30', '15:00', '15:30', '16:00', '16:30', '17:00']
  times.forEach((time, index) => {
    slots.push({
      id: `slot-${index}`,
      time,
      available: Math.random() > 0.3,
      blocked: Math.random() > 0.9,
    })
  })
  return slots
}

export default function StudentBookingPage() {
  const { t } = useLanguage()
  const router = useRouter()
  
  const dates = useMemo(() => {
    const result = []
    const today = new Date()
    for (let i = 0; i < 14; i++) {
      const date = new Date(today)
      date.setDate(today.getDate() + i)
      result.push({
        date: `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`,
        dayName: date.toLocaleDateString('en-US', { weekday: 'short' }),
        dayNumber: date.getDate(),
        month: date.toLocaleDateString('en-US', { month: 'short' }),
        isToday: i === 0,
        isWeekend: date.getDay() === 0 || date.getDay() === 6,
      })
    }
    return result
  }, [])
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [selectedTime, setSelectedTime] = useState<string | null>(null)
  const [selectedBranch, setSelectedBranch] = useState<Branch>('branch1')
  const [selectedPurpose, setSelectedPurpose] = useState<BookingPurpose | null>(null)
  const [timeSlots, setTimeSlots] = useState<TimeSlot[]>([])
  const [showConfirmation, setShowConfirmation] = useState(false)
  const [bookingComplete, setBookingComplete] = useState(false)
  const [dateScrollIndex, setDateScrollIndex] = useState(0)

  const handleDateSelect = (date: string) => {
    setSelectedDate(date)
    setSelectedTime(null)
    setTimeSlots(generateTimeSlots())
  }

  const handleBooking = () => {
    if (selectedDate && selectedTime && selectedPurpose) {
      setShowConfirmation(true)
    }
  }

  const confirmBooking = () => {
    setBookingComplete(true)
    setTimeout(() => {
      router.push('/dashboard/student/booking/my-bookings')
    }, 2000)
  }

  const visibleDates = dates.slice(dateScrollIndex, dateScrollIndex + 7)

  if (bookingComplete) {
    return (
      <DashboardLayout role="student">
        <div className="min-h-[80vh] flex items-center justify-center">
          <div className="text-center p-8 bg-surface rounded-2xl border border-border max-w-md mx-auto">
            <div className="w-20 h-20 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
              <CheckCircle2 className="w-10 h-10 text-green-500" />
            </div>
            <h2 className="text-2xl font-bold text-text-primary mb-2">{t('booking.success')}</h2>
            <p className="text-text-secondary mb-4">
              {selectedDate} - {selectedTime}
            </p>
            <p className="text-sm text-text-secondary">+2 D&apos;coin {t('booking.pending')}</p>
          </div>
        </div>
      </DashboardLayout>
    )
  }

  if (showConfirmation) {
    return (
      <DashboardLayout role="student">
        <div className="max-w-2xl mx-auto p-6">
          <button
            onClick={() => setShowConfirmation(false)}
            className="flex items-center gap-2 text-text-secondary hover:text-text-primary mb-6 transition-colors"
          >
            <ChevronLeft size={20} />
            {t('common.back')}
          </button>

          <div className="bg-surface rounded-2xl border border-border p-8">
            <h2 className="text-2xl font-bold text-text-primary mb-6">{t('booking.confirmation')}</h2>
            
            <div className="space-y-4 mb-8">
              <div className="flex items-center gap-4 p-4 bg-surface-hover rounded-xl">
                <Calendar className="w-6 h-6 text-primary" />
                <div>
                  <p className="text-sm text-text-secondary">{t('booking.selectDate')}</p>
                  <p className="font-semibold text-text-primary">{selectedDate}</p>
                </div>
              </div>
              
              <div className="flex items-center gap-4 p-4 bg-surface-hover rounded-xl">
                <Clock className="w-6 h-6 text-primary" />
                <div>
                  <p className="text-sm text-text-secondary">{t('booking.selectTime')}</p>
                  <p className="font-semibold text-text-primary">{selectedTime} ({t('booking.duration')})</p>
                </div>
              </div>
              
              <div className="flex items-center gap-4 p-4 bg-surface-hover rounded-xl">
                <MapPin className="w-6 h-6 text-primary" />
                <div>
                  <p className="text-sm text-text-secondary">{t('booking.selectBranch')}</p>
                  <p className="font-semibold text-text-primary">{t(`booking.${selectedBranch}`)}</p>
                </div>
              </div>
              
              <div className="flex items-center gap-4 p-4 bg-surface-hover rounded-xl">
                <Target className="w-6 h-6 text-primary" />
                <div>
                  <p className="text-sm text-text-secondary">{t('booking.selectPurpose')}</p>
                  <p className="font-semibold text-text-primary">{t(`booking.${selectedPurpose}`)}</p>
                </div>
              </div>

              <div className="flex items-center gap-4 p-4 bg-amber-500/10 rounded-xl border border-amber-500/20">
                <Sparkles className="w-6 h-6 text-amber-500" />
                <div>
                  <p className="text-sm text-text-secondary">{t('booking.dcoinCost')}</p>
                  <p className="font-semibold text-amber-500">0 D&apos;coin (Bepul)</p>
                </div>
              </div>
            </div>

            <button
              onClick={confirmBooking}
              className="w-full py-4 bg-primary text-white font-semibold rounded-xl hover:bg-primary-dark transition-colors"
            >
              {t('booking.confirmBooking')}
            </button>
          </div>
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout role="student">
      <div className="max-w-4xl mx-auto p-6 space-y-8">
        {/* Hero Section */}
        <div className="relative bg-gradient-to-r from-primary to-primary-dark rounded-2xl p-8 text-white overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full -translate-y-1/2 translate-x-1/2" />
          <div className="absolute bottom-0 left-0 w-32 h-32 bg-white/5 rounded-full translate-y-1/2 -translate-x-1/2" />
          <div className="relative z-10">
            <div className="flex items-center gap-3 mb-4">
              <BookOpen className="w-8 h-8" />
              <span className="text-white/80 text-sm font-medium">Support Lesson</span>
            </div>
            <h1 className="text-3xl font-bold mb-2">{t('booking.heroTitle')}</h1>
            <p className="text-white/80 text-lg">{t('booking.heroSubtitle')}</p>
          </div>
        </div>

        {/* Branch Selection */}
        <div className="bg-surface rounded-2xl border border-border p-6">
          <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
            <MapPin size={20} className="text-primary" />
            {t('booking.selectBranch')}
          </h3>
          <div className="flex gap-4">
            {(['branch1', 'branch2'] as Branch[]).map((branch) => (
              <button
                key={branch}
                onClick={() => setSelectedBranch(branch)}
                className={`flex-1 py-4 px-6 rounded-xl font-medium transition-all ${
                  selectedBranch === branch
                    ? 'bg-primary text-white'
                    : 'bg-surface-hover text-text-primary hover:border-primary border border-border'
                }`}
              >
                {t(`booking.${branch}`)}
              </button>
            ))}
          </div>
        </div>

        {/* Date Selection */}
        <div className="bg-surface rounded-2xl border border-border p-6">
          <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
            <Calendar size={20} className="text-primary" />
            {t('booking.selectDate')}
          </h3>
          
          <div className="flex items-center gap-2">
            <button
              onClick={() => setDateScrollIndex(Math.max(0, dateScrollIndex - 1))}
              disabled={dateScrollIndex === 0}
              className="p-2 rounded-lg bg-surface-hover text-text-primary disabled:opacity-50 disabled:cursor-not-allowed hover:bg-primary hover:text-white transition-colors"
            >
              <ChevronLeft size={20} />
            </button>
            
            <div className="flex-1 grid grid-cols-7 gap-2">
              {visibleDates.map((day) => (
                <button
                  key={day.date}
                  onClick={() => !day.isWeekend && handleDateSelect(day.date)}
                  disabled={day.isWeekend}
                  className={`p-3 rounded-xl text-center transition-all ${
                    day.isWeekend
                      ? 'bg-surface-hover text-text-secondary opacity-50 cursor-not-allowed'
                      : selectedDate === day.date
                      ? 'bg-primary text-white'
                      : day.isToday
                      ? 'bg-primary/10 text-primary border-2 border-primary'
                      : 'bg-surface-hover text-text-primary hover:bg-primary/10'
                  }`}
                >
                  <p className="text-xs font-medium mb-1">{day.dayName}</p>
                  <p className="text-lg font-bold">{day.dayNumber}</p>
                  <p className="text-xs opacity-80">{day.month}</p>
                </button>
              ))}
            </div>
            
            <button
              onClick={() => setDateScrollIndex(Math.min(dates.length - 7, dateScrollIndex + 1))}
              disabled={dateScrollIndex >= dates.length - 7}
              className="p-2 rounded-lg bg-surface-hover text-text-primary disabled:opacity-50 disabled:cursor-not-allowed hover:bg-primary hover:text-white transition-colors"
            >
              <ChevronRight size={20} />
            </button>
          </div>
        </div>

        {/* Time Slots */}
        {selectedDate && (
          <div className="bg-surface rounded-2xl border border-border p-6">
            <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
              <Clock size={20} className="text-primary" />
              {t('booking.selectTime')}
            </h3>
            
            <div className="grid grid-cols-4 sm:grid-cols-6 gap-3">
              {timeSlots.map((slot) => (
                <button
                  key={slot.id}
                  onClick={() => slot.available && !slot.blocked && setSelectedTime(slot.time)}
                  disabled={!slot.available || slot.blocked}
                  className={`py-3 px-4 rounded-xl font-medium transition-all ${
                    slot.blocked
                      ? 'bg-red-500/10 text-red-500 cursor-not-allowed'
                      : !slot.available
                      ? 'bg-surface-hover text-text-secondary opacity-50 cursor-not-allowed'
                      : selectedTime === slot.time
                      ? 'bg-primary text-white'
                      : 'bg-green-500/10 text-green-600 hover:bg-green-500/20 border border-green-500/20'
                  }`}
                >
                  {slot.time}
                </button>
              ))}
            </div>
            
            <div className="flex items-center gap-6 mt-4 text-sm">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-green-500" />
                <span className="text-text-secondary">{t('booking.available')}</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-red-500" />
                <span className="text-text-secondary">{t('booking.blocked')}</span>
              </div>
            </div>
          </div>
        )}

        {/* Purpose Selection */}
        {selectedTime && (
          <div className="bg-surface rounded-2xl border border-border p-6">
            <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
              <Target size={20} className="text-primary" />
              {t('booking.selectPurpose')}
            </h3>
            
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {purposes.map((purpose) => (
                <button
                  key={purpose.key}
                  onClick={() => setSelectedPurpose(purpose.key)}
                  className={`p-4 rounded-xl font-medium transition-all flex items-center gap-3 ${
                    selectedPurpose === purpose.key
                      ? 'bg-primary text-white'
                      : 'bg-surface-hover text-text-primary hover:border-primary border border-border'
                  }`}
                >
                  {purpose.icon}
                  {t(`booking.${purpose.key}`)}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Book Button */}
        {selectedPurpose && (
          <button
            onClick={handleBooking}
            className="w-full py-4 bg-primary text-white font-semibold rounded-xl hover:bg-primary-dark transition-colors text-lg"
          >
            {t('booking.bookLesson')}
          </button>
        )}
      </div>
    </DashboardLayout>
  )
}
