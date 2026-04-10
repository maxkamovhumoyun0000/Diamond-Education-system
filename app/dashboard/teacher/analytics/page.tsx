'use client'

import { useState } from 'react'
import DashboardLayout from '@/components/DashboardLayout'
import StatCard from '@/components/StatCard'
import { BarChart3, TrendingUp, Users, Award, Download, Filter } from 'lucide-react'

export default function TeacherAnalytics() {
  const [timeRange, setTimeRange] = useState('30days')
  const [selectedGroup, setSelectedGroup] = useState('all')

  return (
    <DashboardLayout role="teacher" userName="Fatima">
      <div className="space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-text-primary mb-2">Analytics</h1>
            <p className="text-text-secondary">Track student performance and classroom metrics</p>
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
            <button className="px-6 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors font-medium flex items-center gap-2 active:scale-95">
              <Download size={20} />
              Export
            </button>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard
            title="Avg Student Score"
            value="82%"
            subtitle="↑ 5% from last period"
            icon={<Award className="w-6 h-6 text-primary" />}
            trend={{ value: 5, isPositive: true }}
            variant="primary"
          />
          <StatCard
            title="Total Students"
            value="45"
            subtitle="3 groups"
            icon={<Users className="w-6 h-6 text-accent" />}
            trend={{ value: 0, isPositive: true }}
            variant="accent"
          />
          <StatCard
            title="Attendance Rate"
            value="94%"
            subtitle="↑ 2% improvement"
            icon={<TrendingUp className="w-6 h-6 text-green-500" />}
            trend={{ value: 2, isPositive: true }}
          />
          <StatCard
            title="Lessons Completed"
            value="28"
            subtitle="2 this week"
            icon={<BarChart3 className="w-6 h-6 text-orange-500" />}
            trend={{ value: 7, isPositive: true }}
          />
        </div>

        {/* Group Filter */}
        <div className="flex gap-2">
          <button 
            onClick={() => setSelectedGroup('all')}
            className={`px-6 py-2 rounded-lg font-medium transition-colors active:scale-95 ${
              selectedGroup === 'all'
                ? 'bg-primary text-white'
                : 'border border-border hover:bg-surface-hover'
            }`}
          >
            All Groups
          </button>
          <button 
            onClick={() => setSelectedGroup('advanced')}
            className={`px-6 py-2 rounded-lg font-medium transition-colors active:scale-95 ${
              selectedGroup === 'advanced'
                ? 'bg-primary text-white'
                : 'border border-border hover:bg-surface-hover'
            }`}
          >
            Advanced English
          </button>
          <button 
            onClick={() => setSelectedGroup('grammar')}
            className={`px-6 py-2 rounded-lg font-medium transition-colors active:scale-95 ${
              selectedGroup === 'grammar'
                ? 'bg-primary text-white'
                : 'border border-border hover:bg-surface-hover'
            }`}
          >
            Grammar Basics
          </button>
          <button 
            onClick={() => setSelectedGroup('speaking')}
            className={`px-6 py-2 rounded-lg font-medium transition-colors active:scale-95 ${
              selectedGroup === 'speaking'
                ? 'bg-primary text-white'
                : 'border border-border hover:bg-surface-hover'
            }`}
          >
            Speaking Club
          </button>
        </div>

        {/* Performance Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Student Progress */}
          <div className="bg-surface border border-border rounded-lg p-6">
            <h2 className="text-lg font-semibold text-text-primary mb-6">Student Progress Distribution</h2>
            <div className="space-y-4">
              {[
                { label: 'Excellent (90-100%)', count: 12, color: 'bg-green-500', width: '80%' },
                { label: 'Good (80-89%)', count: 18, color: 'bg-accent', width: '60%' },
                { label: 'Average (70-79%)', count: 10, color: 'bg-yellow-500', width: '35%' },
                { label: 'Needs Improvement (<70%)', count: 5, color: 'bg-red-500', width: '17%' },
              ].map((item, i) => (
                <div key={i}>
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-sm text-text-primary font-medium">{item.label}</p>
                    <span className="text-sm font-semibold text-text-primary">{item.count}</span>
                  </div>
                  <div className="w-full h-3 bg-surface-hover rounded-full overflow-hidden">
                    <div className={`h-full ${item.color} transition-all`} style={{ width: item.width }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Assignment Submission */}
          <div className="bg-surface border border-border rounded-lg p-6">
            <h2 className="text-lg font-semibold text-text-primary mb-6">Assignment Submission Rate</h2>
            <div className="space-y-6">
              {[
                { assignment: 'Assignment 1', submitted: 42, total: 45, percentage: 93 },
                { assignment: 'Assignment 2', submitted: 40, total: 45, percentage: 89 },
                { assignment: 'Assignment 3', submitted: 38, total: 45, percentage: 84 },
                { assignment: 'Assignment 4', submitted: 35, total: 45, percentage: 78 },
              ].map((item, i) => (
                <div key={i}>
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-sm text-text-primary font-medium">{item.assignment}</p>
                    <span className="text-sm font-semibold text-primary">{item.percentage}%</span>
                  </div>
                  <div className="w-full h-2 bg-surface-hover rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-primary transition-all" 
                      style={{ width: `${item.percentage}%` }} 
                    />
                  </div>
                  <p className="text-xs text-text-secondary mt-1">{item.submitted} of {item.total} submitted</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Top Performers */}
        <div className="bg-surface border border-border rounded-lg p-6">
          <h2 className="text-lg font-semibold text-text-primary mb-4">Top Performers</h2>
          <div className="space-y-3">
            {[
              { rank: 1, name: 'Ahmed Ali', score: 95, improvement: '↑ 8%' },
              { rank: 2, name: 'Fatima Khan', score: 93, improvement: '↑ 5%' },
              { rank: 3, name: 'Hassan Ali', score: 91, improvement: '↑ 3%' },
              { rank: 4, name: 'Aysha Hassan', score: 89, improvement: '↑ 6%' },
              { rank: 5, name: 'Omar Ibrahim', score: 87, improvement: '↑ 2%' },
            ].map((student) => (
              <div key={student.rank} className="flex items-center justify-between p-3 border border-border rounded-lg hover:bg-surface-hover transition-colors">
                <div className="flex items-center gap-4">
                  <span className="text-lg font-bold text-primary">{student.rank}</span>
                  <span className="font-medium text-text-primary">{student.name}</span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-sm text-green-600">{student.improvement}</span>
                  <span className="text-lg font-bold text-text-primary">{student.score}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
