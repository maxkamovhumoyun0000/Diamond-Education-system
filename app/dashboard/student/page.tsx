'use client'

import { useState } from 'react'
import DashboardLayout from '@/components/DashboardLayout'
import StatCard from '@/components/StatCard'
import ProgressCard from '@/components/ProgressCard'
import { Flame, Zap, Trophy, Coins, ChevronRight, Star, Target, BookOpen } from 'lucide-react'
import { useSubject } from '@/lib/subject-context'
import { useLanguage } from '@/lib/i18n'

export default function StudentDashboard() {
  const [showCourseModal, setShowCourseModal] = useState(false)
  const [selectedCourse, setSelectedCourse] = useState<string | null>(null)
  const { subject, currentSubjectData } = useSubject()
  const { t } = useLanguage()

  const openCourse = (course: string) => {
    setSelectedCourse(course)
    setShowCourseModal(true)
  }

  // Subject-specific lesson data
  const lessonsBySubject = {
    english: [
      { name: 'English Grammar Basics', progress: 75, due: '2 days' },
      { name: 'Vocabulary Builder', progress: 60, due: '5 days' },
      { name: 'Speaking Practice', progress: 45, due: '3 days' },
    ],
    russian: [
      { name: 'Russian Alphabet Mastery', progress: 85, due: '1 day' },
      { name: 'Basic Conversations', progress: 50, due: '4 days' },
      { name: 'Grammar Fundamentals', progress: 30, due: '6 days' },
    ],
  }

  const recommendedBySubject = {
    english: ['Master Tenses', 'Advanced Vocabulary', 'Conversation Skills', 'Listening Practice'],
    russian: ['Cyrillic Writing', 'Common Phrases', 'Pronunciation Guide', 'Reading Comprehension'],
  }

  const lessons = lessonsBySubject[subject]
  const recommended = recommendedBySubject[subject]

  // Subject color themes
  const subjectTheme = subject === 'english' 
    ? { accent: 'text-blue-500', bg: 'bg-blue-500', bgLight: 'bg-blue-100', border: 'border-blue-200' }
    : { accent: 'text-red-500', bg: 'bg-red-500', bgLight: 'bg-red-100', border: 'border-red-200' }

  return (
    <DashboardLayout role="student" userName="Ahmed">
      <div className="space-y-8">
        {/* Header with D'Coins */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl sm:text-4xl font-bold text-text-primary mb-2">
              {t('dashboard.welcome')}, Ahmed!
            </h1>
            <p className="text-text-secondary flex items-center gap-2">
              <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${subjectTheme.bgLight} ${subjectTheme.accent}`}>
                <BookOpen size={12} />
                {t(`subject.${subject}`)}
              </span>
              Continue your learning journey
            </p>
          </div>
          <div className={`${subjectTheme.bgLight} border ${subjectTheme.border} rounded-lg px-6 py-4`}>
            <p className="text-sm text-text-secondary mb-1">D&apos;Coins Balance</p>
            <div className="flex items-center gap-2">
              <Coins size={28} className={subjectTheme.accent} />
              <span className={`text-3xl font-bold ${subjectTheme.accent}`}>
                {currentSubjectData.dcoins.toLocaleString()}
              </span>
            </div>
            <p className={`text-xs ${subjectTheme.accent} mt-1`}>+150 earned today</p>
          </div>
        </div>

        {/* Level Progress */}
        <div className={`${subjectTheme.bgLight} border ${subjectTheme.border} rounded-lg p-4`}>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Star className={subjectTheme.accent} size={20} />
              <span className="font-semibold text-text-primary">Level {currentSubjectData.level}</span>
            </div>
            <span className="text-sm text-text-secondary">
              {currentSubjectData.xp} / {currentSubjectData.xpToNextLevel} XP
            </span>
          </div>
          <div className="w-full h-2 bg-surface rounded-full overflow-hidden">
            <div
              className={`h-full ${subjectTheme.bg} rounded-full transition-all duration-500`}
              style={{ width: `${(currentSubjectData.xp / currentSubjectData.xpToNextLevel) * 100}%` }}
            />
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard
            title="Lessons Completed"
            value={currentSubjectData.lessonsCompleted.toString()}
            subtitle="8 this month"
            icon={<Zap className="w-6 h-6 text-accent" />}
            trend={{ value: 15, isPositive: true }}
            variant="accent"
          />
          <StatCard
            title="Total Points"
            value={currentSubjectData.xp.toLocaleString()}
            subtitle={`Level ${currentSubjectData.level}`}
            icon={<Trophy className="w-6 h-6 text-orange-500" />}
            trend={{ value: 5, isPositive: true }}
          />
          <StatCard
            title="Current Streak"
            value={`${currentSubjectData.streak} days`}
            subtitle="Keep it up!"
            icon={<Flame className="w-6 h-6 text-orange-500" />}
          />
          <StatCard
            title="Ranking"
            value={`#${currentSubjectData.rank}`}
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
              current={currentSubjectData.lessonsCompleted}
              total={50}
              color="accent"
            />
            <ProgressCard
              title="Vocabulary"
              current={currentSubjectData.vocabularyLearned}
              total={500}
              color="green"
            />
          </div>

          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Active Lessons */}
            <div className="bg-surface border border-border rounded-lg p-6">
              <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
                <Target size={20} className={subjectTheme.accent} />
                Active Lessons - {t(`subject.${subject}`)}
              </h2>
              <div className="space-y-3">
                {lessons.map((lesson, i) => (
                  <div key={i} className="p-4 border border-border rounded-lg hover:bg-surface-hover transition-colors">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-medium text-text-primary">{lesson.name}</h3>
                      <span className="text-sm text-text-secondary">Due in {lesson.due}</span>
                    </div>
                    <div className="w-full h-2 bg-surface-hover rounded-full overflow-hidden">
                      <div
                        className={`h-full ${subjectTheme.bg} rounded-full`}
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
                {recommended.map((course) => (
                  <button
                    key={course}
                    onClick={() => openCourse(course)}
                    className="p-4 border border-border rounded-lg hover:bg-surface-hover hover:border-primary transition-colors text-left active:scale-95 group"
                  >
                    <p className="font-medium text-text-primary group-hover:text-primary transition-colors">{course}</p>
                    <p className="text-xs text-text-secondary mt-1 flex items-center gap-1">Start learning <ChevronRight size={14} /></p>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Course Modal */}
        {showCourseModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-surface rounded-lg border border-border p-6 max-w-md w-full">
              <h2 className="text-2xl font-bold text-text-primary mb-4">{selectedCourse}</h2>
              <div className="space-y-4 mb-6">
                <p className="text-text-secondary">Learn the essential skills and concepts covered in this course.</p>
                <div className={`${subjectTheme.bgLight} rounded-lg p-4 space-y-2`}>
                  <p className="text-sm font-medium text-text-primary">Course Details:</p>
                  <ul className="text-sm text-text-secondary space-y-1">
                    <li>Duration: 4-6 weeks</li>
                    <li>Level: Intermediate</li>
                    <li>Lessons: 24</li>
                    <li>Reward: 500 D&apos;Coins</li>
                  </ul>
                </div>
              </div>
              <div className="flex gap-3">
                <button 
                  onClick={() => setShowCourseModal(false)}
                  className="flex-1 px-4 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors font-medium"
                >
                  Close
                </button>
                <button 
                  onClick={() => setShowCourseModal(false)}
                  className={`flex-1 px-4 py-2 rounded-lg ${subjectTheme.bg} text-white hover:opacity-90 transition-colors font-medium`}
                >
                  Enroll Now
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
