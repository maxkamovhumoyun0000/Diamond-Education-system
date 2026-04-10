'use client'

import { useState } from 'react'
import DashboardLayout from '@/components/DashboardLayout'
import StatCard from '@/components/StatCard'
import ProgressCard from '@/components/ProgressCard'
import { Users, BookOpen, TrendingUp, DollarSign, AlertCircle, CheckCircle, XCircle } from 'lucide-react'

export default function AdminDashboard() {
  const [showUserModal, setShowUserModal] = useState(false)
  const [showCourseModal, setShowCourseModal] = useState(false)
  const [filteredView, setFilteredView] = useState('all')

  const recentUsers = [
    { id: 1, name: 'User 1', email: 'user1@diamond.edu', role: 'Student' },
    { id: 2, name: 'User 2', email: 'user2@diamond.edu', role: 'Teacher' },
    { id: 3, name: 'User 3', email: 'user3@diamond.edu', role: 'Student' },
    { id: 4, name: 'User 4', email: 'user4@diamond.edu', role: 'Support' },
    { id: 5, name: 'User 5', email: 'user5@diamond.edu', role: 'Student' },
  ]

  const alerts = [
    { id: 1, type: 'warning', title: '3 Inactive Courses', message: 'Some courses have no activity', icon: AlertCircle },
    { id: 2, type: 'success', title: 'System Status', message: 'All systems operational', icon: CheckCircle },
    { id: 3, type: 'error', title: 'Payment Issue', message: '2 payment failures detected', icon: XCircle },
  ]

  return (
    <DashboardLayout role="admin" userName="Admin">
      <div className="space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-4xl font-bold text-text-primary mb-2">Admin Dashboard</h1>
          <p className="text-text-secondary">Welcome back! Here&apos;s your system overview.</p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard
            title="Total Users"
            value="1,248"
            subtitle="↑ 12% from last month"
            icon={<Users className="w-6 h-6 text-primary" />}
            trend={{ value: 12, isPositive: true }}
            variant="primary"
          />
          <StatCard
            title="Active Students"
            value="892"
            subtitle="↑ 8% from last month"
            icon={<BookOpen className="w-6 h-6 text-accent" />}
            trend={{ value: 8, isPositive: true }}
            variant="accent"
          />
          <StatCard
            title="Total Courses"
            value="156"
            subtitle="4 new this month"
            icon={<TrendingUp className="w-6 h-6 text-green-500" />}
            trend={{ value: 2, isPositive: true }}
          />
          <StatCard
            title="Total Revenue"
            value="$45,230"
            subtitle="↑ 23% from last month"
            icon={<DollarSign className="w-6 h-6 text-orange-500" />}
            trend={{ value: 23, isPositive: true }}
          />
        </div>

        {/* Alerts Section */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {alerts.map((alert) => {
            const IconComponent = alert.icon
            const bgColor = alert.type === 'warning' ? 'bg-yellow-50' : alert.type === 'success' ? 'bg-green-50' : 'bg-red-50'
            const textColor = alert.type === 'warning' ? 'text-yellow-700' : alert.type === 'success' ? 'text-green-700' : 'text-red-700'
            const iconColor = alert.type === 'warning' ? 'text-yellow-500' : alert.type === 'success' ? 'text-green-500' : 'text-red-500'

            return (
              <div key={alert.id} className={`${bgColor} p-4 rounded-lg border border-gray-200`}>
                <div className="flex items-start gap-3">
                  <IconComponent className={`w-5 h-5 ${iconColor} mt-0.5 flex-shrink-0`} />
                  <div>
                    <h3 className={`font-semibold ${textColor} text-sm`}>{alert.title}</h3>
                    <p className={`text-xs mt-1 ${textColor} opacity-75`}>{alert.message}</p>
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {/* Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Progress Cards */}
          <div className="lg:col-span-1 space-y-6">
            <ProgressCard
              title="Course Completion"
              current={156}
              total={200}
              color="primary"
            />
            <ProgressCard
              title="Student Satisfaction"
              current={92}
              total={100}
              color="green"
            />
          </div>

          {/* Main Content Area */}
          <div className="lg:col-span-2 space-y-6">
            {/* Recent Users Table */}
            <div className="bg-surface border border-border rounded-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-text-primary">Recent Users</h2>
                <a href="/dashboard/admin/users" className="text-sm text-primary hover:underline">View All</a>
              </div>
              <div className="space-y-3">
                {recentUsers.map((user) => (
                  <div key={user.id} className="flex items-center justify-between p-3 hover:bg-surface-hover rounded-lg transition-colors">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center">
                        <Users size={20} className="text-primary" />
                      </div>
                      <div>
                        <p className="font-medium text-text-primary">{user.name}</p>
                        <p className="text-xs text-text-secondary">{user.email}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-text-secondary">{user.role}</span>
                      <button className="text-text-secondary hover:text-primary transition-colors">
                        →
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Quick Actions */}
            <div className="bg-surface border border-border rounded-lg p-6">
              <h2 className="text-lg font-semibold text-text-primary mb-4">Quick Actions</h2>
              <div className="grid grid-cols-2 gap-3">
                <button 
                  onClick={() => setShowUserModal(true)}
                  className="px-4 py-2 rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors font-medium active:scale-95"
                >
                  Add User
                </button>
                <button 
                  onClick={() => setShowCourseModal(true)}
                  className="px-4 py-2 rounded-lg bg-accent text-white hover:opacity-90 transition-colors font-medium active:scale-95"
                >
                  Create Course
                </button>
                <a href="/dashboard/admin/analytics" className="px-4 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors font-medium text-center">
                  View Reports
                </a>
                <button className="px-4 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors font-medium active:scale-95">
                  Settings
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Add User Modal */}
        {showUserModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-surface rounded-lg border border-border p-6 max-w-md w-full">
              <h2 className="text-2xl font-bold text-text-primary mb-4">Add New User</h2>
              <div className="space-y-4">
                <input type="text" placeholder="Full Name" className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary" />
                <input type="email" placeholder="Email Address" className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary" />
                <select className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-primary">
                  <option>Select Role</option>
                  <option>Student</option>
                  <option>Teacher</option>
                  <option>Support</option>
                  <option>Admin</option>
                </select>
                <input type="password" placeholder="Temporary Password" className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary" />
              </div>
              <div className="flex gap-3 mt-6">
                <button 
                  onClick={() => setShowUserModal(false)}
                  className="flex-1 px-4 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors font-medium"
                >
                  Cancel
                </button>
                <button 
                  onClick={() => setShowUserModal(false)}
                  className="flex-1 px-4 py-2 rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors font-medium"
                >
                  Create User
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Create Course Modal */}
        {showCourseModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-surface rounded-lg border border-border p-6 max-w-md w-full">
              <h2 className="text-2xl font-bold text-text-primary mb-4">Create New Course</h2>
              <div className="space-y-4">
                <input type="text" placeholder="Course Name" className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary" />
                <textarea placeholder="Course Description" rows={3} className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary" />
                <select className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-primary">
                  <option>Select Instructor</option>
                  <option>Teacher 1</option>
                  <option>Teacher 2</option>
                </select>
                <input type="number" placeholder="Price ($)" className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary" />
              </div>
              <div className="flex gap-3 mt-6">
                <button 
                  onClick={() => setShowCourseModal(false)}
                  className="flex-1 px-4 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors font-medium"
                >
                  Cancel
                </button>
                <button 
                  onClick={() => setShowCourseModal(false)}
                  className="flex-1 px-4 py-2 rounded-lg bg-accent text-white hover:opacity-90 transition-colors font-medium"
                >
                  Create Course
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
