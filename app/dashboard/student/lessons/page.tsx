import DashboardLayout from '@/components/DashboardLayout'
import { CheckCircle, Clock, Play } from 'lucide-react'

export default function StudentLessons() {
  const lessons = [
    {
      id: 1,
      title: 'Present Simple Tense',
      module: 'Fundamentals',
      progress: 100,
      status: 'completed',
      duration: '45 min',
      date: '2024-03-15',
    },
    {
      id: 2,
      title: 'Present Continuous',
      module: 'Fundamentals',
      progress: 75,
      status: 'in-progress',
      duration: '45 min',
      date: 'Today',
    },
    {
      id: 3,
      title: 'Past Simple & Past Continuous',
      module: 'Fundamentals',
      progress: 45,
      status: 'in-progress',
      duration: '60 min',
      date: 'Tomorrow',
    },
    {
      id: 4,
      title: 'Perfect Tenses Overview',
      module: 'Intermediate',
      progress: 0,
      status: 'locked',
      duration: '60 min',
      date: 'Next week',
    },
    {
      id: 5,
      title: 'Advanced Sentence Structures',
      module: 'Advanced',
      progress: 0,
      status: 'locked',
      duration: '75 min',
      date: 'TBD',
    },
    {
      id: 6,
      title: 'Business Communication',
      module: 'Special',
      progress: 0,
      status: 'locked',
      duration: '90 min',
      date: 'TBD',
    },
  ]

  return (
    <DashboardLayout role="student" userName="Ahmed">
      <div className="space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-4xl font-bold text-text-primary mb-2">My Lessons</h1>
          <p className="text-text-secondary">Continue learning and track your progress</p>
        </div>

        {/* Lessons Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {lessons.map((lesson) => (
            <div
              key={lesson.id}
              className={`rounded-lg border p-6 transition-all ${
                lesson.status === 'locked'
                  ? 'bg-surface-hover border-border opacity-60'
                  : 'bg-surface border-border hover:shadow-glass hover:border-primary'
              }`}
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs font-medium px-2 py-1 rounded-full bg-primary/10 text-primary">
                      {lesson.module}
                    </span>
                  </div>
                  <h3 className="text-lg font-semibold text-text-primary">{lesson.title}</h3>
                </div>
                {lesson.status === 'completed' && (
                  <CheckCircle className="text-green-500 flex-shrink-0" size={24} />
                )}
              </div>

              {/* Duration and Date */}
              <div className="flex items-center gap-4 mb-4 text-sm text-text-secondary">
                <span className="flex items-center gap-1">
                  <Clock size={16} />
                  {lesson.duration}
                </span>
                <span>{lesson.date}</span>
              </div>

              {/* Progress Bar */}
              {lesson.status !== 'locked' && (
                <div className="mb-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-text-secondary">Progress</span>
                    <span className="text-xs font-medium text-primary">{lesson.progress}%</span>
                  </div>
                  <div className="w-full h-2 bg-surface-hover rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary transition-all"
                      style={{ width: `${lesson.progress}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Action Button */}
              <div className="pt-4 border-t border-border">
                <button
                  className={`w-full py-2 px-4 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 ${
                    lesson.status === 'locked'
                      ? 'bg-surface text-text-secondary cursor-not-allowed'
                      : lesson.status === 'completed'
                      ? 'bg-green-500/10 text-green-600 hover:bg-green-500/20'
                      : 'bg-primary text-white hover:bg-primary-dark'
                  }`}
                  disabled={lesson.status === 'locked'}
                >
                  {lesson.status === 'locked' && 'Locked'}
                  {lesson.status === 'completed' && 'Review'}
                  {lesson.status === 'in-progress' && (
                    <>
                      <Play size={16} />
                      Continue
                    </>
                  )}
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Info Box */}
        <div className="p-6 rounded-lg bg-accent/10 border border-accent/20">
          <h3 className="font-semibold text-text-primary mb-2">💡 Tip</h3>
          <p className="text-text-secondary text-sm">
            Complete lessons in order to unlock advanced content. Each lesson takes 45-90 minutes to complete.
          </p>
        </div>
      </div>
    </DashboardLayout>
  )
}
