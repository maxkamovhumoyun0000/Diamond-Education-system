import DashboardLayout from '@/components/DashboardLayout'
import { Trophy, Target, Zap, TrendingUp } from 'lucide-react'

export default function StudentLeaderboard() {
  const leaderboard = [
    { rank: 1, name: 'Ahmed Ali', points: 45230, streak: 28, level: 15, avatar: '🧑‍🎓' },
    { rank: 2, name: 'Fatima Khan', points: 43120, streak: 21, level: 14, avatar: '👩‍🎓' },
    { rank: 3, name: 'Hassan Ahmed', points: 41050, streak: 19, level: 13, avatar: '👨‍🎓' },
    { rank: 4, name: 'You (Aysha)', points: 38450, streak: 15, level: 12, avatar: '👩‍💼', isCurrent: true },
    { rank: 5, name: 'Omar Ibrahim', points: 37200, streak: 14, level: 11, avatar: '👨‍💼' },
    { rank: 6, name: 'Leila Ahmed', points: 35800, streak: 12, level: 11, avatar: '👩‍🎓' },
    { rank: 7, name: 'Karim Hassan', points: 34100, streak: 10, level: 10, avatar: '👨‍🎓' },
    { rank: 8, name: 'Sara Mohamed', points: 32950, streak: 9, level: 9, avatar: '👩‍💻' },
  ]

  return (
    <DashboardLayout role="student" userName="Ahmed">
      <div className="space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-4xl font-bold text-text-primary mb-2">Leaderboard</h1>
          <p className="text-text-secondary">See how you rank among all learners</p>
        </div>

        {/* Your Stats */}
        <div className="bg-gradient-to-r from-primary to-primary-dark text-white rounded-lg p-8 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-white/80 text-sm mb-2">Your Current Rank</p>
              <div className="flex items-end gap-3">
                <p className="text-6xl font-bold">#4</p>
                <p className="text-lg mb-2">out of 1,248 learners</p>
              </div>
            </div>
            <div className="text-6xl">🏅</div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-6 border-t border-white/20">
            <div>
              <p className="text-white/80 text-sm mb-1">Total Points</p>
              <p className="text-3xl font-bold">38,450</p>
              <p className="text-sm text-white/60 mt-1">+450 this week</p>
            </div>
            <div>
              <p className="text-white/80 text-sm mb-1">Current Streak</p>
              <p className="text-3xl font-bold">15 days</p>
              <p className="text-sm text-white/60 mt-1">Keep it going! 🔥</p>
            </div>
            <div>
              <p className="text-white/80 text-sm mb-1">Current Level</p>
              <p className="text-3xl font-bold">12</p>
              <p className="text-sm text-white/60 mt-1">Expert Learner</p>
            </div>
          </div>
        </div>

        {/* Top Performers */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {leaderboard.slice(0, 3).map((user) => (
            <div
              key={user.rank}
              className={`rounded-lg border p-6 text-center ${
                user.rank === 1
                  ? 'bg-gradient-to-br from-orange-500/10 to-orange-500/5 border-orange-500/20'
                  : user.rank === 2
                  ? 'bg-gradient-to-br from-gray-400/10 to-gray-400/5 border-gray-400/20'
                  : 'bg-gradient-to-br from-orange-600/10 to-orange-600/5 border-orange-600/20'
              }`}
            >
              <div className="text-5xl mb-3">{user.avatar}</div>
              <div className={`text-2xl font-bold mb-1 ${
                user.rank === 1 ? 'text-orange-500' :
                user.rank === 2 ? 'text-gray-400' :
                'text-orange-600'
              }`}>
                #{user.rank}
              </div>
              <h3 className="font-semibold text-text-primary mb-3">{user.name}</h3>
              <div className="space-y-2 text-sm">
                <p className="text-text-secondary">{user.points.toLocaleString()} points</p>
                <p className="text-text-secondary">Level {user.level}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Full Leaderboard */}
        <div className="bg-surface border border-border rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-surface-hover border-b border-border">
                <tr>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-text-primary">Rank</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-text-primary">Student</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-text-primary">Points</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-text-primary">Level</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-text-primary">Streak</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-text-primary">Change</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {leaderboard.map((user) => (
                  <tr
                    key={user.rank}
                    className={`transition-colors ${
                      user.isCurrent ? 'bg-primary/10' : 'hover:bg-surface-hover'
                    }`}
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        {user.rank <= 3 ? (
                          <span className="text-xl">
                            {user.rank === 1 ? '🥇' : user.rank === 2 ? '🥈' : '🥉'}
                          </span>
                        ) : (
                          <span className="font-bold text-text-primary w-6">{user.rank}</span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <span className="text-2xl">{user.avatar}</span>
                        <span className={`font-medium ${user.isCurrent ? 'text-primary' : 'text-text-primary'}`}>
                          {user.name}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 font-semibold text-text-primary">
                      {user.points.toLocaleString()}
                    </td>
                    <td className="px-6 py-4">
                      <span className="px-3 py-1 rounded-full bg-primary/10 text-primary text-sm font-medium">
                        Lvl {user.level}
                      </span>
                    </td>
                    <td className="px-6 py-4 flex items-center gap-1 text-text-primary">
                      <span className="text-orange-500">🔥</span>
                      {user.streak} days
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-green-500 font-medium text-sm">↑ 1</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Badges Section */}
        <div>
          <h2 className="text-2xl font-semibold text-text-primary mb-4">Your Badges</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-4">
            {[
              { emoji: '🌟', name: 'Beginner', earned: true },
              { emoji: '⚡', name: 'Lightning Fast', earned: true },
              { emoji: '🎯', name: 'Precision', earned: true },
              { emoji: '🔥', name: '7-Day Streak', earned: true },
              { emoji: '🏆', name: 'Top Achiever', earned: false },
              { emoji: '👑', name: 'Champion', earned: false },
            ].map((badge) => (
              <div
                key={badge.name}
                className={`p-4 rounded-lg text-center ${
                  badge.earned
                    ? 'bg-primary/10 border border-primary/20'
                    : 'bg-surface-hover border border-border opacity-50'
                }`}
              >
                <div className="text-3xl mb-2">{badge.emoji}</div>
                <p className="text-sm font-medium text-text-primary">{badge.name}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
