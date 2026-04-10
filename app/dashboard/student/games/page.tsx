import DashboardLayout from '@/components/DashboardLayout'
import { Play, RotateCcw, Trophy, Clock } from 'lucide-react'

export default function StudentGames() {
  const games = [
    {
      id: 1,
      name: 'Word Master',
      description: 'Build vocabulary through interactive word puzzles',
      icon: '🎮',
      difficulty: 'Easy',
      timePerGame: '10 min',
      highScore: 2450,
      played: 45,
      reward: '+150 D\'Coins',
      color: 'bg-blue-500',
    },
    {
      id: 2,
      name: 'Sentence Builder',
      description: 'Construct correct sentences from scrambled words',
      icon: '🔤',
      difficulty: 'Medium',
      timePerGame: '15 min',
      highScore: 1850,
      played: 32,
      reward: '+200 D\'Coins',
      color: 'bg-purple-500',
    },
    {
      id: 3,
      name: 'Listening Challenge',
      description: 'Test your listening comprehension skills',
      icon: '🎧',
      difficulty: 'Medium',
      timePerGame: '20 min',
      highScore: 1650,
      played: 28,
      reward: '+250 D\'Coins',
      color: 'bg-green-500',
    },
    {
      id: 4,
      name: 'Vocabulary Match',
      description: 'Match words with their correct definitions',
      icon: '🎯',
      difficulty: 'Easy',
      timePerGame: '8 min',
      highScore: 3100,
      played: 67,
      reward: '+100 D\'Coins',
      color: 'bg-pink-500',
    },
    {
      id: 5,
      name: 'Grammar Quest',
      description: 'Complete grammar challenges to level up',
      icon: '⚔️',
      difficulty: 'Hard',
      timePerGame: '25 min',
      highScore: 1200,
      played: 15,
      reward: '+300 D\'Coins',
      color: 'bg-orange-500',
    },
    {
      id: 6,
      name: 'Speaking Simulator',
      description: 'Practice speaking with AI-powered conversations',
      icon: '🎤',
      difficulty: 'Hard',
      timePerGame: '30 min',
      highScore: 950,
      played: 12,
      reward: '+350 D\'Coins',
      color: 'bg-red-500',
    },
  ]

  const leaderboardData = [
    { rank: 1, player: 'Ahmed Ali', score: 45230, games: 156 },
    { rank: 2, player: 'Fatima Khan', score: 43120, games: 148 },
    { rank: 3, player: 'Hassan Ahmed', score: 41050, games: 142 },
    { rank: 4, player: 'You', score: 38450, games: 127, isCurrent: true },
    { rank: 5, player: 'Omar Ibrahim', score: 37200, games: 135 },
  ]

  return (
    <DashboardLayout role="student" userName="Ahmed">
      <div className="space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-text-primary mb-2">Learning Games</h1>
            <p className="text-text-secondary">Have fun while improving your English skills</p>
          </div>
          <div className="bg-accent/10 border border-accent/20 rounded-lg px-6 py-4">
            <p className="text-sm text-text-secondary">Total Games Played</p>
            <p className="text-3xl font-bold text-accent">127</p>
          </div>
        </div>

        {/* Games Grid */}
        <div>
          <h2 className="text-2xl font-semibold text-text-primary mb-4">Available Games</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {games.map((game) => (
              <div
                key={game.id}
                className="rounded-lg border border-border bg-surface hover:shadow-glass hover:border-primary transition-all overflow-hidden group"
              >
                {/* Game Header */}
                <div className={`${game.color} h-24 flex items-center justify-center text-6xl group-hover:scale-110 transition-transform`}>
                  {game.icon}
                </div>

                {/* Game Content */}
                <div className="p-6 space-y-4">
                  <div>
                    <h3 className="text-lg font-semibold text-text-primary mb-1">{game.name}</h3>
                    <p className="text-sm text-text-secondary">{game.description}</p>
                  </div>

                  {/* Game Stats */}
                  <div className="grid grid-cols-2 gap-3 py-3 border-y border-border">
                    <div>
                      <p className="text-xs text-text-secondary">Difficulty</p>
                      <p className="font-medium text-text-primary text-sm">{game.difficulty}</p>
                    </div>
                    <div>
                      <p className="text-xs text-text-secondary">Duration</p>
                      <p className="font-medium text-text-primary text-sm flex items-center gap-1">
                        <Clock size={14} />
                        {game.timePerGame}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-text-secondary">High Score</p>
                      <p className="font-medium text-primary text-sm">{game.highScore.toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-xs text-text-secondary">Times Played</p>
                      <p className="font-medium text-text-primary text-sm">{game.played}</p>
                    </div>
                  </div>

                  {/* Reward */}
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-accent bg-accent/10 px-3 py-1 rounded-full">
                      {game.reward}
                    </span>
                  </div>

                  {/* Play Button */}
                  <button className="w-full py-2 px-4 rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors font-medium flex items-center justify-center gap-2">
                    <Play size={16} />
                    Play Now
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Leaderboard */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-surface border border-border rounded-lg p-6">
            <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
              <Trophy size={20} className="text-orange-500" />
              Global Leaderboard
            </h2>
            <div className="space-y-3">
              {leaderboardData.map((entry) => (
                <div
                  key={entry.rank}
                  className={`flex items-center justify-between p-4 rounded-lg transition-colors ${
                    entry.isCurrent
                      ? 'bg-primary/10 border border-primary/20'
                      : 'hover:bg-surface-hover'
                  }`}
                >
                  <div className="flex items-center gap-4">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${
                      entry.rank === 1 ? 'bg-orange-500 text-white' :
                      entry.rank === 2 ? 'bg-gray-400 text-white' :
                      entry.rank === 3 ? 'bg-orange-600 text-white' :
                      'bg-surface-hover text-text-primary'
                    }`}>
                      {entry.rank}
                    </div>
                    <div>
                      <p className={`font-medium ${entry.isCurrent ? 'text-primary' : 'text-text-primary'}`}>
                        {entry.player}
                      </p>
                      <p className="text-xs text-text-secondary">{entry.games} games played</p>
                    </div>
                  </div>
                  <span className="text-lg font-bold text-primary">{entry.score.toLocaleString()}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Achievements */}
          <div className="bg-surface border border-border rounded-lg p-6">
            <h2 className="text-lg font-semibold text-text-primary mb-4">Achievements</h2>
            <div className="space-y-3">
              {[
                { icon: '🌟', name: 'First Win', unlocked: true },
                { icon: '🔥', name: '7-Day Streak', unlocked: true },
                { icon: '🏆', name: 'Top 10 Score', unlocked: false },
                { icon: '💎', name: 'Complete All Games', unlocked: false },
                { icon: '⭐', name: '1000+ Points', unlocked: true },
              ].map((ach, i) => (
                <div key={i} className={`p-3 rounded-lg flex items-center gap-3 ${
                  ach.unlocked ? 'bg-primary/10 border border-primary/20' : 'bg-surface-hover border border-border opacity-50'
                }`}>
                  <span className="text-xl">{ach.icon}</span>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-text-primary">{ach.name}</p>
                    {!ach.unlocked && <p className="text-xs text-text-secondary">Locked</p>}
                  </div>
                  {ach.unlocked && <span className="text-xs bg-green-500/20 text-green-600 px-2 py-1 rounded">✓</span>}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
