import DashboardLayout from '@/components/DashboardLayout'
import StatCard from '@/components/StatCard'
import ProgressCard from '@/components/ProgressCard'
import { Calendar, Clock, CheckCircle, AlertCircle } from 'lucide-react'

export default function SupportDashboard() {
  return (
    <DashboardLayout role="support" userName="Support Staff">
      <div className="space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-4xl font-bold text-text-primary mb-2">Support Dashboard</h1>
          <p className="text-text-secondary">Manage lesson bookings and student support</p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard
            title="Bookings Today"
            value="12"
            subtitle="8 completed"
            icon={<Calendar className="w-6 h-6 text-accent" />}
            trend={{ value: 5, isPositive: true }}
            variant="accent"
          />
          <StatCard
            title="Pending Requests"
            value="5"
            subtitle="2 urgent"
            icon={<AlertCircle className="w-6 h-6 text-orange-500" />}
          />
          <StatCard
            title="Total Lessons"
            value="156"
            subtitle="This month"
            icon={<CheckCircle className="w-6 h-6 text-green-500" />}
          />
          <StatCard
            title="Avg Response Time"
            value="2.3 hrs"
            subtitle="↓ 0.5 hrs from last week"
            icon={<Clock className="w-6 h-6 text-primary" />}
            trend={{ value: 21, isPositive: true }}
            variant="primary"
          />
        </div>

        {/* Progress Cards */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1 space-y-6">
            <ProgressCard
              title="Bookings This Week"
              current={54}
              total={70}
              color="accent"
            />
            <ProgressCard
              title="Completion Rate"
              current={148}
              total={156}
              color="green"
            />
          </div>

          {/* Main Content Area */}
          <div className="lg:col-span-2 space-y-6">
            {/* Pending Bookings */}
            <div className="bg-surface border border-border rounded-lg p-6">
              <h2 className="text-lg font-semibold text-text-primary mb-4">Pending Requests (5)</h2>
              <div className="space-y-3">
                {[
                  { student: 'Ahmed Ali', time: '2 hrs ago', level: 'B1', priority: 'high' },
                  { student: 'Fatima Khan', time: '45 mins ago', level: 'A2', priority: 'medium' },
                  { student: 'Hassan Ali', time: '30 mins ago', level: 'B2', priority: 'high' },
                  { student: 'Aysha Hassan', time: '15 mins ago', level: 'A1', priority: 'low' },
                  { student: 'Omar Ibrahim', time: '5 mins ago', level: 'B1', priority: 'medium' },
                ].map((req, i) => (
                  <div key={i} className="p-4 border border-border rounded-lg hover:bg-surface-hover transition-colors">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <h3 className="font-medium text-text-primary">{req.student}</h3>
                        <div className="flex items-center gap-2 mt-1 text-sm text-text-secondary">
                          <Clock size={14} />
                          {req.time}
                          <span className="text-primary">Level {req.level}</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span
                          className={`px-3 py-1 rounded-full text-xs font-medium ${
                            req.priority === 'high'
                              ? 'bg-red-500/20 text-red-600'
                              : req.priority === 'medium'
                              ? 'bg-orange-500/20 text-orange-600'
                              : 'bg-green-500/20 text-green-600'
                          }`}
                        >
                          {req.priority}
                        </span>
                        <button className="px-3 py-1 rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors text-sm">
                          Respond
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Today's Schedule */}
            <div className="bg-surface border border-border rounded-lg p-6">
              <h2 className="text-lg font-semibold text-text-primary mb-4">Today&apos;s Schedule</h2>
              <div className="space-y-3">
                {[
                  { time: '10:00 AM', student: 'Group A - English Basics', duration: '1 hour', instructor: 'Fatima' },
                  { time: '11:15 AM', student: 'One-on-One - Ahmed Ali', duration: '45 min', instructor: 'Hassan' },
                  { time: '01:00 PM', student: 'Group B - Speaking Club', duration: '1.5 hours', instructor: 'Aysha' },
                  { time: '03:00 PM', student: 'Group C - Advanced English', duration: '1 hour', instructor: 'Omar' },
                ].map((slot, i) => (
                  <div key={i} className="flex items-center gap-4 p-3 hover:bg-surface-hover rounded-lg transition-colors">
                    <div className="flex-shrink-0">
                      <span className="font-semibold text-primary">{slot.time}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-text-primary truncate">{slot.student}</p>
                      <p className="text-sm text-text-secondary">{slot.duration} • Instructor: {slot.instructor}</p>
                    </div>
                    <button className="px-3 py-1 rounded-lg border border-border hover:bg-surface-hover transition-colors text-sm">
                      Details
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
