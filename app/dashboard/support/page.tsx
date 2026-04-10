'use client'

import { useState } from 'react'
import DashboardLayout from '@/components/DashboardLayout'
import StatCard from '@/components/StatCard'
import ProgressCard from '@/components/ProgressCard'
import { Calendar, Clock, CheckCircle, AlertCircle, Reply, Trash2, Eye } from 'lucide-react'

export default function SupportDashboard() {
  const [showRequestModal, setShowRequestModal] = useState(false)
  const [selectedRequest, setSelectedRequest] = useState<any>(null)
  const [responseText, setResponseText] = useState('')
  const [filterPriority, setFilterPriority] = useState('all')
  return (
    <DashboardLayout role="support" userName="Support Staff">
      <div className="space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-text-primary mb-2">Support Dashboard</h1>
            <p className="text-text-secondary">Manage lesson bookings and student support</p>
          </div>
          <div className="flex gap-2">
            <select 
              value={filterPriority}
              onChange={(e) => setFilterPriority(e.target.value)}
              className="px-4 py-2 rounded-lg border border-border bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="all">All Priorities</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>
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
              <h2 className="text-lg font-semibold text-text-primary mb-4">Pending Requests</h2>
              <div className="space-y-3">
                {[
                  { id: 1, student: 'Ahmed Ali', time: '2 hrs ago', level: 'B1', priority: 'high' },
                  { id: 2, student: 'Fatima Khan', time: '45 mins ago', level: 'A2', priority: 'medium' },
                  { id: 3, student: 'Hassan Ali', time: '30 mins ago', level: 'B2', priority: 'high' },
                  { id: 4, student: 'Aysha Hassan', time: '15 mins ago', level: 'A1', priority: 'low' },
                  { id: 5, student: 'Omar Ibrahim', time: '5 mins ago', level: 'B1', priority: 'medium' },
                ]
                .filter(req => filterPriority === 'all' || req.priority === filterPriority)
                .map((req) => (
                  <div key={req.id} className="p-4 border border-border rounded-lg hover:bg-surface-hover transition-colors">
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
                        <button 
                          onClick={() => {
                            setSelectedRequest(req)
                            setShowRequestModal(true)
                          }}
                          className="px-3 py-1 rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors text-sm font-medium active:scale-95 flex items-center gap-1"
                        >
                          <Reply size={14} />
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
                    <button className="px-3 py-1 rounded-lg border border-border hover:bg-surface-hover transition-colors text-sm font-medium active:scale-95 flex items-center gap-1">
                      <Eye size={14} />
                      Details
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Response Modal */}
        {showRequestModal && selectedRequest && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-surface rounded-lg border border-border p-6 max-w-md w-full">
              <h2 className="text-2xl font-bold text-text-primary mb-2">Respond to {selectedRequest.student}</h2>
              <p className="text-text-secondary text-sm mb-4">Level: {selectedRequest.level} • Priority: {selectedRequest.priority}</p>
              <div className="space-y-4">
                <textarea 
                  placeholder="Type your response..."
                  value={responseText}
                  onChange={(e) => setResponseText(e.target.value)}
                  rows={5}
                  className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              <div className="flex gap-3 mt-6">
                <button 
                  onClick={() => {
                    setShowRequestModal(false)
                    setSelectedRequest(null)
                    setResponseText('')
                  }}
                  className="flex-1 px-4 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors font-medium"
                >
                  Cancel
                </button>
                <button 
                  onClick={() => {
                    setShowRequestModal(false)
                    setSelectedRequest(null)
                    setResponseText('')
                  }}
                  className="flex-1 px-4 py-2 rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors font-medium flex items-center justify-center gap-2"
                >
                  <Reply size={16} />
                  Send Response
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
