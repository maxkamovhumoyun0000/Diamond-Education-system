import DashboardLayout from '@/components/DashboardLayout'
import StatCard from '@/components/StatCard'
import ProgressCard from '@/components/ProgressCard'
import { Flame, Zap, Trophy, Coins } from 'lucide-react'

export default function StudentDashboard() {
  return (
    <DashboardLayout role="student" userName="Ahmed">
      <div className="space-y-8">
        {/* Header with D'Coins */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-text-primary mb-2">Welcome back, Ahmed!</h1>
            <p className="text-text-secondary">Continue your learning journey</p>
          </div>
          <div className="bg-accent/10 border border-accent/20 rounded-lg px-6 py-4">
            <p className="text-sm text-text-secondary mb-1">D&apos;Coins Balance</p>
            <div className="flex items-center gap-2">
              <Coins size={28} className="text-accent" />
              <span className="text-3xl font-bold text-accent">1,250</span>
            </div>
            <p className="text-xs text-accent mt-1">+150 earned today</p>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard
            title="Lessons Completed"
            value="42"
            subtitle="8 this month"
            icon={<Zap className="w-6 h-6 text-accent" />}
            trend={{ value: 15, isPositive: true }}
            variant="accent"
          />
          <StatCard
            title="Total Points"
            value="8,450"
            subtitle="Level 12"
            icon={<Trophy className="w-6 h-6 text-orange-500" />}
            trend={{ value: 5, isPositive: true }}
          />
          <StatCard
            title="Current Streak"
            value="7 days"
            subtitle="Keep it up!"
            icon={<Flame className="w-6 h-6 text-orange-500" />}
          />
          <StatCard
            title="Ranking"
            value="#23"
            subtitle="in your group"
            icon={<Trophy className="w-6 h-6 text-orange-500" />}
          />
        </div>

        {/* Learning Progress */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1 space-y-6">
            <ProgressCard
              title="Daily Goal"
              current={45}
              total={100}
              color="primary"
            />
            <ProgressCard
              title="Course Progress"
              current={18}
              total={25}
              color="accent"
            />
            <ProgressCard
              title="Vocabulary"
              current={320}
              total={500}
              color="green"
            />
          </div>

          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Active Lessons */}
            <div className="bg-surface border border-border rounded-lg p-6">
              <h2 className="text-lg font-semibold text-text-primary mb-4">Active Lessons</h2>
              <div className="space-y-3">
                {[
                  { name: 'English Grammar Basics', progress: 75, due: '2 days' },
                  { name: 'Vocabulary Builder', progress: 60, due: '5 days' },
                  { name: 'Speaking Practice', progress: 45, due: '3 days' },
                ].map((lesson, i) => (
                  <div key={i} className="p-4 border border-border rounded-lg hover:bg-surface-hover transition-colors">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-medium text-text-primary">{lesson.name}</h3>
                      <span className="text-sm text-text-secondary">Due in {lesson.due}</span>
                    </div>
                    <div className="w-full h-2 bg-surface-hover rounded-full overflow-hidden">
                      <div
                        className="h-full bg-accent rounded-full"
                        style={{ width: `${lesson.progress}%` }}
                      />
                    </div>
                    <p className="text-xs text-text-secondary mt-2">{lesson.progress}% complete</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Recommended Content */}
            <div className="bg-surface border border-border rounded-lg p-6">
              <h2 className="text-lg font-semibold text-text-primary mb-4">Recommended For You</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {['Master Tenses', 'Advanced Vocabulary', 'Conversation Skills', 'Listening Practice'].map((course) => (
                  <button
                    key={course}
                    className="p-4 border border-border rounded-lg hover:bg-surface-hover hover:border-primary transition-colors text-left"
                  >
                    <p className="font-medium text-text-primary">{course}</p>
                    <p className="text-xs text-text-secondary mt-1">Start learning →</p>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
