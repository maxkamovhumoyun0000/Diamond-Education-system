'use client'

import { useState } from 'react'
import DashboardLayout from '@/components/DashboardLayout'
import StatCard from '@/components/StatCard'
import ProgressCard from '@/components/ProgressCard'
import { Users, BookOpen, Star, Calendar, ChevronRight, Eye } from 'lucide-react'

export default function TeacherDashboard() {
  const [showGroupModal, setShowGroupModal] = useState(false)
  const [selectedGroup, setSelectedGroup] = useState<any>(null)

  const viewGroup = (group: any) => {
    setSelectedGroup(group)
    setShowGroupModal(true)
  }

  return (
    <DashboardLayout role="teacher" userName="Fatima">
      <div className="space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-4xl font-bold text-text-primary mb-2">Teacher Dashboard</h1>
          <p className="text-text-secondary">Manage your groups and track student progress</p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard
            title="Active Groups"
            value="3"
            subtitle="45 students total"
            icon={<Users className="w-6 h-6 text-primary" />}
            trend={{ value: 0, isPositive: true }}
            variant="primary"
          />
          <StatCard
            title="Total Students"
            value="45"
            subtitle="↑ 2 new this week"
            icon={<Users className="w-6 h-6 text-accent" />}
            trend={{ value: 4, isPositive: true }}
            variant="accent"
          />
          <StatCard
            title="Lessons Created"
            value="28"
            subtitle="2 this week"
            icon={<BookOpen className="w-6 h-6 text-green-500" />}
            trend={{ value: 7, isPositive: true }}
          />
          <StatCard
            title="Average Rating"
            value="4.8"
            subtitle="From 45 reviews"
            icon={<Star className="w-6 h-6 text-orange-500" />}
          />
        </div>

        {/* Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1 space-y-6">
            <ProgressCard
              title="Student Attendance"
              current={42}
              total={45}
              color="primary"
            />
            <ProgressCard
              title="Lessons Graded"
              current={25}
              total={28}
              color="accent"
            />
          </div>

          {/* Main Content Area */}
          <div className="lg:col-span-2 space-y-6">
            {/* My Groups */}
            <div className="bg-surface border border-border rounded-lg p-6">
              <h2 className="text-lg font-semibold text-text-primary mb-4">My Groups</h2>
              <div className="space-y-3">
                {[
                  { id: 1, name: 'Advanced English', students: 15, level: 'B2', meeting: 'Mon, 3 PM' },
                  { id: 2, name: 'Grammar Basics', students: 18, level: 'A2', meeting: 'Wed, 2 PM' },
                  { id: 3, name: 'Speaking Club', students: 12, level: 'B1', meeting: 'Fri, 4 PM' },
                ].map((group) => (
                  <div key={group.id} className="p-4 border border-border rounded-lg hover:bg-surface-hover transition-colors group">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h3 className="font-medium text-text-primary group-hover:text-primary transition-colors">{group.name}</h3>
                        <div className="flex items-center gap-4 mt-2 text-sm text-text-secondary">
                          <span className="flex items-center gap-1">
                            <Users size={16} />
                            {group.students} students
                          </span>
                          <span>Level {group.level}</span>
                          <span className="flex items-center gap-1">
                            <Calendar size={16} />
                            {group.meeting}
                          </span>
                        </div>
                      </div>
                      <button 
                        onClick={() => viewGroup(group)}
                        className="px-3 py-1 rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors text-sm font-medium active:scale-95 flex items-center gap-1"
                      >
                        <Eye size={14} />
                        View
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Upcoming Schedule */}
            <div className="bg-surface border border-border rounded-lg p-6">
              <h2 className="text-lg font-semibold text-text-primary mb-4">Upcoming Classes</h2>
              <div className="space-y-3">
                {[
                  { group: 'Advanced English', date: 'Today', time: '3:00 PM', students: 15 },
                  { group: 'Grammar Basics', date: 'Tomorrow', time: '2:00 PM', students: 18 },
                  { group: 'Speaking Club', date: 'Fri', time: '4:00 PM', students: 12 },
                ].map((cls, i) => (
                  <div key={i} className="flex items-center justify-between p-3 hover:bg-surface-hover rounded-lg transition-colors">
                    <div>
                      <p className="font-medium text-text-primary">{cls.group}</p>
                      <p className="text-sm text-text-secondary">{cls.date} at {cls.time}</p>
                    </div>
                    <span className="text-sm bg-primary/10 text-primary px-3 py-1 rounded-full font-medium">
                      {cls.students} students
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Group Modal */}
        {showGroupModal && selectedGroup && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-surface rounded-lg border border-border p-6 max-w-md w-full">
              <h2 className="text-2xl font-bold text-text-primary mb-2">{selectedGroup.name}</h2>
              <p className="text-text-secondary text-sm mb-6">Level {selectedGroup.level}</p>
              
              <div className="bg-accent/10 rounded-lg p-4 space-y-3 mb-6">
                <div className="flex items-center justify-between">
                  <p className="text-sm text-text-secondary">Total Students</p>
                  <p className="font-medium text-text-primary text-lg flex items-center gap-1"><Users size={16} className="text-primary" /> {selectedGroup.students}</p>
                </div>
                <div className="flex items-center justify-between">
                  <p className="text-sm text-text-secondary">Meeting Time</p>
                  <p className="font-medium text-text-primary">{selectedGroup.meeting}</p>
                </div>
                <div className="flex items-center justify-between">
                  <p className="text-sm text-text-secondary">Upcoming Classes</p>
                  <p className="font-medium text-primary">3 this week</p>
                </div>
              </div>

              <div className="flex gap-3">
                <button 
                  onClick={() => {
                    setShowGroupModal(false)
                    setSelectedGroup(null)
                  }}
                  className="flex-1 px-4 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors font-medium"
                >
                  Close
                </button>
                <button 
                  onClick={() => {
                    setShowGroupModal(false)
                    setSelectedGroup(null)
                  }}
                  className="flex-1 px-4 py-2 rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors font-medium"
                >
                  Manage Group
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
