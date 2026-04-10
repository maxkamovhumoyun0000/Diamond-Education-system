'use client'

import { useState } from 'react'
import DashboardLayout from '@/components/DashboardLayout'
import StatCard from '@/components/StatCard'
import { TrendingUp, Users, BookOpen, DollarSign, Calendar, Download, Filter } from 'lucide-react'

export default function AdminAnalytics() {
  const [timeRange, setTimeRange] = useState('30days')
  const [showExportModal, setShowExportModal] = useState(false)

  return (
    <DashboardLayout role="admin" userName="Admin">
      <div className="space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-text-primary mb-2">Analytics & Reports</h1>
            <p className="text-text-secondary">System-wide performance metrics and insights</p>
          </div>
          <div className="flex gap-2">
            <select 
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
              className="px-4 py-2 rounded-lg border border-border bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="7days">Last 7 Days</option>
              <option value="30days">Last 30 Days</option>
              <option value="90days">Last 90 Days</option>
              <option value="year">Last Year</option>
            </select>
            <button 
              onClick={() => setShowExportModal(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors font-medium"
            >
              <Download size={20} />
              Export
            </button>
          </div>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard
            title="User Growth"
            value="↑ 12%"
            subtitle="vs last month"
            icon={<Users className="w-6 h-6 text-primary" />}
            variant="primary"
          />
          <StatCard
            title="Course Engagement"
            value="78%"
            subtitle="Completion rate"
            icon={<BookOpen className="w-6 h-6 text-accent" />}
            variant="accent"
          />
          <StatCard
            title="Revenue Growth"
            value="↑ 23%"
            subtitle="vs last month"
            icon={<DollarSign className="w-6 h-6 text-green-500" />}
          />
          <StatCard
            title="Active Sessions"
            value="234"
            subtitle="Right now"
            icon={<TrendingUp className="w-6 h-6 text-orange-500" />}
          />
        </div>

        {/* Charts Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* User Growth Chart */}
          <div className="bg-surface border border-border rounded-lg p-6">
            <h2 className="text-lg font-semibold text-text-primary mb-4">User Growth Trend</h2>
            <div className="h-64 flex items-end justify-around gap-2">
              {[45, 52, 48, 65, 72, 88, 95, 105, 118, 125, 142, 158].map((val, i) => (
                <div key={i} className="flex-1 flex flex-col items-center">
                  <div
                    className="w-full rounded-t-lg bg-primary transition-all hover:bg-primary-dark cursor-pointer"
                    style={{ height: `${(val / 158) * 100}%` }}
                  />
                </div>
              ))}
            </div>
            <div className="mt-4 text-xs text-text-secondary text-center">Monthly Users (Jan-Dec)</div>
          </div>

          {/* Revenue Chart */}
          <div className="bg-surface border border-border rounded-lg p-6">
            <h2 className="text-lg font-semibold text-text-primary mb-4">Revenue Breakdown</h2>
            <div className="space-y-4">
              {[
                { label: 'Subscriptions', value: 65, amount: '$28,500' },
                { label: 'One-time Courses', value: 20, amount: '$8,750' },
                { label: 'Paid Lessons', value: 10, amount: '$4,375' },
                { label: 'Premium Features', value: 5, amount: '$2,185' },
              ].map((item) => (
                <div key={item.label}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-text-primary font-medium">{item.label}</span>
                    <span className="text-sm font-semibold text-primary">{item.amount}</span>
                  </div>
                  <div className="w-full h-2 bg-surface-hover rounded-full overflow-hidden">
                    <div
                      className="h-full bg-accent"
                      style={{ width: `${item.value}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Top Courses */}
        <div className="bg-surface border border-border rounded-lg p-6">
          <h2 className="text-lg font-semibold text-text-primary mb-4">Top Performing Courses</h2>
          <div className="space-y-3">
            {[
              { rank: 1, name: 'English Fundamentals', students: 245, rating: 4.8 },
              { rank: 2, name: 'Business English', students: 189, rating: 4.7 },
              { rank: 3, name: 'Speaking Mastery', students: 167, rating: 4.9 },
              { rank: 4, name: 'IELTS Preparation', students: 156, rating: 4.6 },
            ].map((course) => (
              <div key={course.rank} className="flex items-center justify-between p-4 hover:bg-surface-hover rounded-lg transition-colors">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center font-bold text-primary">
                    {course.rank}
                  </div>
                  <div>
                    <p className="font-medium text-text-primary">{course.name}</p>
                    <p className="text-xs text-text-secondary">{course.students} enrolled</p>
                  </div>
                </div>
                <span className="text-sm font-semibold text-primary">★ {course.rating}</span>
              </div>
            ))}
          </div>
        </div>

        {/* User Demographics */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-surface border border-border rounded-lg p-6">
            <h2 className="text-lg font-semibold text-text-primary mb-4">User Distribution</h2>
            <div className="space-y-3">
              {[
                { label: 'Students', value: 892, color: 'bg-primary' },
                { label: 'Teachers', value: 234, color: 'bg-accent' },
                { label: 'Support Staff', value: 45, color: 'bg-green-500' },
                { label: 'Admins', value: 12, color: 'bg-orange-500' },
              ].map((item) => (
                <div key={item.label}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-text-primary font-medium flex items-center gap-2">
                      <span className={`w-3 h-3 rounded-full ${item.color}`} />
                      {item.label}
                    </span>
                    <span className="text-sm font-semibold text-text-primary">{item.value}</span>
                  </div>
                  <div className="w-full h-2 bg-surface-hover rounded-full overflow-hidden">
                    <div className={`h-full ${item.color}`} style={{ width: '100%' }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-surface border border-border rounded-lg p-6">
            <h2 className="text-lg font-semibold text-text-primary mb-4">Engagement Rate</h2>
            <div className="space-y-4">
              {[
                { metric: 'Daily Active Users', value: '234', trend: '↑ 5%' },
                { metric: 'Weekly Active Users', value: '892', trend: '↑ 8%' },
                { metric: 'Monthly Active Users', value: '1,248', trend: '↑ 12%' },
                { metric: 'Lesson Completion Rate', value: '78%', trend: '↑ 3%' },
              ].map((item) => (
                <div key={item.metric} className="flex items-center justify-between p-3 border border-border rounded-lg">
                  <div>
                    <p className="text-sm text-text-primary font-medium">{item.metric}</p>
                    <p className="text-xs text-text-secondary">{item.trend}</p>
                  </div>
                  <span className="text-lg font-bold text-primary">{item.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Export Modal */}
        {showExportModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-surface rounded-lg border border-border p-6 max-w-md w-full">
              <h2 className="text-2xl font-bold text-text-primary mb-4">Export Data</h2>
              <p className="text-text-secondary mb-6">Select format and data to export:</p>
              <div className="space-y-3 mb-6">
                <label className="flex items-center gap-3 p-3 border border-border rounded-lg hover:bg-surface-hover cursor-pointer">
                  <input type="radio" name="format" value="csv" defaultChecked className="w-4 h-4" />
                  <span className="text-text-primary font-medium">CSV Format</span>
                </label>
                <label className="flex items-center gap-3 p-3 border border-border rounded-lg hover:bg-surface-hover cursor-pointer">
                  <input type="radio" name="format" value="pdf" className="w-4 h-4" />
                  <span className="text-text-primary font-medium">PDF Report</span>
                </label>
                <label className="flex items-center gap-3 p-3 border border-border rounded-lg hover:bg-surface-hover cursor-pointer">
                  <input type="radio" name="format" value="excel" className="w-4 h-4" />
                  <span className="text-text-primary font-medium">Excel Spreadsheet</span>
                </label>
              </div>
              <div className="space-y-2 mb-6">
                <label className="flex items-center gap-3 p-2 hover:bg-surface-hover rounded cursor-pointer">
                  <input type="checkbox" defaultChecked className="w-4 h-4" />
                  <span className="text-sm text-text-primary">User Data</span>
                </label>
                <label className="flex items-center gap-3 p-2 hover:bg-surface-hover rounded cursor-pointer">
                  <input type="checkbox" defaultChecked className="w-4 h-4" />
                  <span className="text-sm text-text-primary">Course Data</span>
                </label>
                <label className="flex items-center gap-3 p-2 hover:bg-surface-hover rounded cursor-pointer">
                  <input type="checkbox" defaultChecked className="w-4 h-4" />
                  <span className="text-sm text-text-primary">Revenue Data</span>
                </label>
              </div>
              <div className="flex gap-3">
                <button 
                  onClick={() => setShowExportModal(false)}
                  className="flex-1 px-4 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors font-medium"
                >
                  Cancel
                </button>
                <button 
                  onClick={() => setShowExportModal(false)}
                  className="flex-1 px-4 py-2 rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors font-medium flex items-center justify-center gap-2"
                >
                  <Download size={18} />
                  Export
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
