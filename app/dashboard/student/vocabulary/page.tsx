import DashboardLayout from '@/components/DashboardLayout'
import ProgressCard from '@/components/ProgressCard'
import { BookOpen, Volume2, RefreshCw } from 'lucide-react'

export default function StudentVocabulary() {
  const words = [
    { word: 'Persevere', pronunciation: '/pərˈsɪvər/', meaning: 'Continue despite difficulty', example: 'She persevered through challenges', learned: true },
    { word: 'Ephemeral', pronunciation: '/ɪˈfɛm(ə)rəl/', meaning: 'Lasting a very short time', example: 'Beauty is ephemeral', learned: true },
    { word: 'Serendipity', pronunciation: '/ˌsɛrənˈdɪpɪti/', meaning: 'Luck in finding good things by chance', example: 'Meeting was pure serendipity', learned: true },
    { word: 'Eloquent', pronunciation: '/ˈɛlə(k)wənt/', meaning: 'Fluent and persuasive speaking', example: 'An eloquent speech', learned: false },
    { word: 'Benevolent', pronunciation: '/bəˈnɛvələnt/', meaning: 'Kind and generous', example: 'A benevolent leader', learned: false },
    { word: 'Ubiquitous', pronunciation: '/juːˈbɪkwɪtəs/', meaning: 'Present, appearing everywhere', example: 'Smart phones are ubiquitous', learned: false },
  ]

  const categories = [
    { name: 'Business', words: 245, learned: 189 },
    { name: 'Academic', words: 312, learned: 267 },
    { name: 'Daily Life', words: 456, learned: 423 },
    { name: 'Idioms & Phrases', words: 234, learned: 145 },
  ]

  return (
    <DashboardLayout role="student" userName="Ahmed">
      <div className="space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-4xl font-bold text-text-primary mb-2">Vocabulary Bank</h1>
          <p className="text-text-secondary">Build and review your vocabulary collection</p>
        </div>

        {/* Overall Progress */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <ProgressCard
            title="Total Words"
            current={320}
            total={500}
            color="primary"
            icon={<BookOpen size={20} />}
          />
          <ProgressCard
            title="Words Learned"
            current={267}
            total={320}
            color="accent"
          />
          <ProgressCard
            title="Review Queue"
            current={53}
            total={320}
            color="green"
          />
        </div>

        {/* Categories */}
        <div>
          <h2 className="text-2xl font-semibold text-text-primary mb-4">Categories</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {categories.map((cat) => (
              <button
                key={cat.name}
                className="p-4 rounded-lg bg-surface border border-border hover:border-primary hover:shadow-glass transition-all text-left group"
              >
                <p className="font-semibold text-text-primary group-hover:text-primary transition-colors">{cat.name}</p>
                <p className="text-sm text-text-secondary mt-2">{cat.learned}/{cat.words} words</p>
                <div className="w-full h-2 bg-surface-hover rounded-full overflow-hidden mt-3">
                  <div
                    className="h-full bg-primary"
                    style={{ width: `${(cat.learned / cat.words) * 100}%` }}
                  />
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Words List */}
        <div>
          <h2 className="text-2xl font-semibold text-text-primary mb-4">Recent Words</h2>
          <div className="space-y-3">
            {words.map((w) => (
              <div
                key={w.word}
                className={`p-6 rounded-lg border transition-all cursor-pointer group ${
                  w.learned
                    ? 'bg-green-500/5 border-green-500/20 hover:border-green-500/50'
                    : 'bg-surface border-border hover:border-primary'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-xl font-semibold text-text-primary">{w.word}</h3>
                      <button className="p-2 rounded-lg hover:bg-surface-hover transition-colors text-text-secondary hover:text-primary">
                        <Volume2 size={18} />
                      </button>
                    </div>
                    <p className="text-sm text-text-secondary mb-3">{w.pronunciation}</p>
                    <div className="space-y-2">
                      <div>
                        <p className="text-xs text-text-secondary font-medium mb-1">Definition:</p>
                        <p className="text-sm text-text-primary">{w.meaning}</p>
                      </div>
                      <div>
                        <p className="text-xs text-text-secondary font-medium mb-1">Example:</p>
                        <p className="text-sm text-text-primary italic">&quot;{w.example}&quot;</p>
                      </div>
                    </div>
                  </div>
                  <div className="ml-4 flex flex-col gap-2">
                    {w.learned ? (
                      <span className="px-3 py-1 rounded-full bg-green-500/20 text-green-600 text-xs font-medium">
                        Learned ✓
                      </span>
                    ) : (
                      <button className="px-3 py-1 rounded-lg bg-primary text-white text-xs font-medium hover:bg-primary-dark transition-colors">
                        Learn
                      </button>
                    )}
                    <button className="p-2 rounded-lg hover:bg-surface-hover transition-colors text-text-secondary hover:text-primary">
                      <RefreshCw size={16} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3 flex-wrap">
          <button className="px-6 py-3 rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors font-medium">
            Add New Word
          </button>
          <button className="px-6 py-3 rounded-lg border border-border hover:bg-surface-hover transition-colors font-medium">
            Quiz Mode
          </button>
          <button className="px-6 py-3 rounded-lg border border-border hover:bg-surface-hover transition-colors font-medium">
            Flashcards
          </button>
        </div>
      </div>
    </DashboardLayout>
  )
}
