import DashboardLayout from '@/components/DashboardLayout'
import { Users, Calendar, BarChart3, Settings } from 'lucide-react'

export default function TeacherGroups() {
  const groups = [
    {
      id: 1,
      name: 'Advanced English Group A',
      level: 'B2',
      students: 15,
      schedule: 'Mon & Wed, 3:00 PM',
      progress: 82,
      avgScore: 87,
      description: 'For intermediate-advanced learners',
    },
    {
      id: 2,
      name: 'Grammar Basics',
      level: 'A2',
      students: 18,
      schedule: 'Tue & Thu, 2:00 PM',
      progress: 65,
      avgScore: 76,
      description: 'Foundation grammar course',
    },
    {
      id: 3,
      name: 'Speaking Club',
      level: 'B1',
      students: 12,
      schedule: 'Fri, 4:00 PM',
      progress: 75,
      avgScore: 82,
      description: 'Conversation and fluency practice',
    },
  ]

  return (
    <DashboardLayout role="teacher" userName="Fatima">
      <div className="space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-text-primary mb-2">My Groups</h1>
            <p className="text-text-secondary">Manage and monitor your classes</p>
          </div>
          <button className="px-6 py-2 rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors font-medium">
            Create Group
          </button>
        </div>

        {/* Groups Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {groups.map((group) => (
            <div key={group.id} className="bg-surface border border-border rounded-lg overflow-hidden hover:shadow-glass transition-all">
              {/* Header */}
              <div className="bg-gradient-to-r from-primary to-primary-dark p-6 text-white">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-xl font-semibold mb-2">{group.name}</h3>
                    <p className="text-white/80 text-sm">{group.description}</p>
                  </div>
                  <span className="px-3 py-1 rounded-full bg-white/20 text-white text-sm font-medium">
                    Level {group.level}
                  </span>
                </div>
              </div>

              {/* Content */}
              <div className="p-6 space-y-6">
                {/* Stats Grid */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 rounded-lg bg-surface-hover">
                    <p className="text-xs text-text-secondary mb-1">Students</p>
                    <p className="text-2xl font-bold text-text-primary flex items-center gap-1">
                      <Users size={18} className="text-primary" />
                      {group.students}
                    </p>
                  </div>
                  <div className="p-3 rounded-lg bg-surface-hover">
                    <p className="text-xs text-text-secondary mb-1">Avg Score</p>
                    <p className="text-2xl font-bold text-accent">{group.avgScore}%</p>
                  </div>
                </div>

                {/* Schedule */}
                <div className="p-3 rounded-lg bg-surface-hover">
                  <p className="text-xs text-text-secondary mb-1 flex items-center gap-1">
                    <Calendar size={14} />
                    Schedule
                  </p>
                  <p className="font-medium text-text-primary">{group.schedule}</p>
                </div>

                {/* Progress Bar */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-sm font-medium text-text-primary">Course Progress</p>
                    <span className="text-sm font-semibold text-primary">{group.progress}%</span>
                  </div>
                  <div className="w-full h-2 bg-surface-hover rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary transition-all"
                      style={{ width: `${group.progress}%` }}
                    />
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-2 pt-4 border-t border-border">
                  <button className="flex-1 py-2 px-3 rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors font-medium text-sm">
                    View Students
                  </button>
                  <button className="flex-1 py-2 px-3 rounded-lg border border-border hover:bg-surface-hover transition-colors font-medium text-sm flex items-center justify-center gap-1">
                    <BarChart3 size={16} />
                    Analytics
                  </button>
                  <button className="py-2 px-3 rounded-lg border border-border hover:bg-surface-hover transition-colors">
                    <Settings size={16} className="text-text-secondary" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Upcoming Classes */}
        <div className="bg-surface border border-border rounded-lg p-6">
          <h2 className="text-lg font-semibold text-text-primary mb-4">Upcoming Classes</h2>
          <div className="space-y-3">
            {[
              { group: 'Advanced English Group A', date: 'Today', time: '3:00 PM', students: 15 },
              { group: 'Grammar Basics', date: 'Tomorrow', time: '2:00 PM', students: 18 },
              { group: 'Speaking Club', date: 'Friday', time: '4:00 PM', students: 12 },
              { group: 'Advanced English Group A', date: 'Next Wed', time: '3:00 PM', students: 15 },
            ].map((cls, i) => (
              <div key={i} className="flex items-center justify-between p-4 hover:bg-surface-hover rounded-lg transition-colors border border-transparent hover:border-border">
                <div>
                  <p className="font-medium text-text-primary">{cls.group}</p>
                  <p className="text-sm text-text-secondary">{cls.date} at {cls.time}</p>
                </div>
                <span className="px-3 py-1 rounded-full bg-accent/10 text-accent text-sm font-medium">
                  {cls.students} students
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
