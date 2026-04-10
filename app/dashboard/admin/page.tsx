import DashboardLayout from '@/components/DashboardLayout'
import StatCard from '@/components/StatCard'
import ProgressCard from '@/components/ProgressCard'
import { Users, BookOpen, TrendingUp, DollarSign } from 'lucide-react'

export default function AdminDashboard() {
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
              <h2 className="text-lg font-semibold text-text-primary mb-4">Recent Users</h2>
              <div className="space-y-3">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div key={i} className="flex items-center justify-between p-3 hover:bg-surface-hover rounded-lg transition-colors">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center">
                        <Users size={20} className="text-primary" />
                      </div>
                      <div>
                        <p className="font-medium text-text-primary">User {i}</p>
                        <p className="text-xs text-text-secondary">user{i}@diamond.edu</p>
                      </div>
                    </div>
                    <span className="text-sm text-text-secondary">Student</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Quick Actions */}
            <div className="bg-surface border border-border rounded-lg p-6">
              <h2 className="text-lg font-semibold text-text-primary mb-4">Quick Actions</h2>
              <div className="grid grid-cols-2 gap-3">
                <button className="px-4 py-2 rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors font-medium">
                  Add User
                </button>
                <button className="px-4 py-2 rounded-lg bg-accent text-white hover:opacity-90 transition-colors font-medium">
                  Create Course
                </button>
                <button className="px-4 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors font-medium">
                  View Reports
                </button>
                <button className="px-4 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors font-medium">
                  Settings
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
