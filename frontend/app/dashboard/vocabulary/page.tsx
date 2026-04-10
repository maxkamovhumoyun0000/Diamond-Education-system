'use client'

import { useEffect, useState } from 'react'
import { vocabularyApi, VocabularyWord } from '@/lib/api'

export default function VocabularyPage() {
  const [words, setWords] = useState<VocabularyWord[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [subjectFilter, setSubjectFilter] = useState('')
  const [levelFilter, setLevelFilter] = useState('')
  const [showAddModal, setShowAddModal] = useState(false)
  const [formData, setFormData] = useState({
    word: '',
    subject: 'English',
    language: 'en',
    level: '',
    translation_uz: '',
    translation_ru: '',
    definition: '',
    example: '',
  })
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    fetchWords()
  }, [subjectFilter, levelFilter])

  const fetchWords = async () => {
    try {
      setIsLoading(true)
      const data = await vocabularyApi.list({
        subject: subjectFilter || undefined,
        level: levelFilter || undefined,
        search: searchTerm || undefined,
        limit: 100,
      })
      setWords(data.words || [])
    } catch (err) {
      console.error('Failed to load vocabulary:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSearch = () => {
    fetchWords()
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.word.trim()) return

    try {
      setIsSubmitting(true)
      await vocabularyApi.add(formData)
      setShowAddModal(false)
      setFormData({
        word: '',
        subject: 'English',
        language: 'en',
        level: '',
        translation_uz: '',
        translation_ru: '',
        definition: '',
        example: '',
      })
      fetchWords()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to add word')
    } finally {
      setIsSubmitting(false)
    }
  }

  const filteredWords = searchTerm 
    ? words.filter((w) => 
        w.word.toLowerCase().includes(searchTerm.toLowerCase()) ||
        w.translation_uz?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        w.translation_ru?.toLowerCase().includes(searchTerm.toLowerCase())
      )
    : words

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-serif font-bold">Vocabulary</h1>
          <p className="text-[hsl(var(--muted-foreground))]">
            Manage vocabulary words for all levels
          </p>
        </div>
        <button onClick={() => setShowAddModal(true)} className="btn btn-primary">
          <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Add Word
        </button>
      </div>

      {/* Filters */}
      <div className="card p-4">
        <div className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-[200px]">
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Search words..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                className="input flex-1"
              />
              <button onClick={handleSearch} className="btn btn-outline">
                Search
              </button>
            </div>
          </div>
          <select
            value={subjectFilter}
            onChange={(e) => setSubjectFilter(e.target.value)}
            className="input w-auto"
          >
            <option value="">All Subjects</option>
            <option value="English">English</option>
            <option value="Russian">Russian</option>
          </select>
          <select
            value={levelFilter}
            onChange={(e) => setLevelFilter(e.target.value)}
            className="input w-auto"
          >
            <option value="">All Levels</option>
            <option value="Starter">Starter</option>
            <option value="Elementary">Elementary</option>
            <option value="Pre-Intermediate">Pre-Intermediate</option>
            <option value="Intermediate">Intermediate</option>
            <option value="Upper-Intermediate">Upper-Intermediate</option>
            <option value="Advanced">Advanced</option>
          </select>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card p-4 text-center">
          <p className="text-2xl font-bold">{words.length}</p>
          <p className="text-sm text-[hsl(var(--muted-foreground))]">Total Words</p>
        </div>
        <div className="card p-4 text-center">
          <p className="text-2xl font-bold">{words.filter((w) => w.subject === 'English').length}</p>
          <p className="text-sm text-[hsl(var(--muted-foreground))]">English</p>
        </div>
        <div className="card p-4 text-center">
          <p className="text-2xl font-bold">{words.filter((w) => w.subject === 'Russian').length}</p>
          <p className="text-sm text-[hsl(var(--muted-foreground))]">Russian</p>
        </div>
        <div className="card p-4 text-center">
          <p className="text-2xl font-bold">{filteredWords.length}</p>
          <p className="text-sm text-[hsl(var(--muted-foreground))]">Filtered</p>
        </div>
      </div>

      {/* Words Grid */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 border-3 border-[hsl(var(--primary))]/30 border-t-[hsl(var(--primary))] rounded-full animate-spin" />
        </div>
      ) : filteredWords.length === 0 ? (
        <div className="card p-12 text-center">
          <svg className="w-12 h-12 mx-auto text-[hsl(var(--muted-foreground))] mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
          </svg>
          <p className="text-[hsl(var(--muted-foreground))]">No vocabulary words found</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredWords.map((word) => (
            <div key={word.id} className="card p-4">
              <div className="flex items-start justify-between mb-2">
                <h3 className="font-semibold text-lg">{word.word}</h3>
                <span className={`badge text-xs ${word.subject === 'English' ? 'badge-primary' : 'badge-secondary'}`}>
                  {word.language.toUpperCase()}
                </span>
              </div>
              {word.level && (
                <span className="badge badge-outline text-xs mb-2">{word.level}</span>
              )}
              <div className="space-y-1 text-sm">
                {word.translation_uz && (
                  <p><span className="text-[hsl(var(--muted-foreground))]">UZ:</span> {word.translation_uz}</p>
                )}
                {word.translation_ru && (
                  <p><span className="text-[hsl(var(--muted-foreground))]">RU:</span> {word.translation_ru}</p>
                )}
                {word.definition && (
                  <p className="text-[hsl(var(--muted-foreground))] italic">{word.definition}</p>
                )}
                {word.example && (
                  <p className="text-[hsl(var(--primary))] text-xs mt-2">
                    Example: {word.example}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add Word Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="card p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto animate-fadeIn">
            <h2 className="text-xl font-semibold mb-4">Add New Word</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1.5">Word</label>
                <input
                  type="text"
                  value={formData.word}
                  onChange={(e) => setFormData({ ...formData, word: e.target.value })}
                  className="input"
                  placeholder="Enter word"
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1.5">Subject</label>
                  <select
                    value={formData.subject}
                    onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                    className="input"
                  >
                    <option value="English">English</option>
                    <option value="Russian">Russian</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1.5">Language</label>
                  <select
                    value={formData.language}
                    onChange={(e) => setFormData({ ...formData, language: e.target.value })}
                    className="input"
                  >
                    <option value="en">English</option>
                    <option value="ru">Russian</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">Level</label>
                <select
                  value={formData.level}
                  onChange={(e) => setFormData({ ...formData, level: e.target.value })}
                  className="input"
                >
                  <option value="">No specific level</option>
                  <option value="Starter">Starter</option>
                  <option value="Elementary">Elementary</option>
                  <option value="Pre-Intermediate">Pre-Intermediate</option>
                  <option value="Intermediate">Intermediate</option>
                  <option value="Upper-Intermediate">Upper-Intermediate</option>
                  <option value="Advanced">Advanced</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">Translation (Uzbek)</label>
                <input
                  type="text"
                  value={formData.translation_uz}
                  onChange={(e) => setFormData({ ...formData, translation_uz: e.target.value })}
                  className="input"
                  placeholder="Uzbek translation"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">Translation (Russian)</label>
                <input
                  type="text"
                  value={formData.translation_ru}
                  onChange={(e) => setFormData({ ...formData, translation_ru: e.target.value })}
                  className="input"
                  placeholder="Russian translation"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">Definition</label>
                <textarea
                  value={formData.definition}
                  onChange={(e) => setFormData({ ...formData, definition: e.target.value })}
                  className="input h-20 resize-none"
                  placeholder="Word definition"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">Example</label>
                <textarea
                  value={formData.example}
                  onChange={(e) => setFormData({ ...formData, example: e.target.value })}
                  className="input h-20 resize-none"
                  placeholder="Example sentence"
                />
              </div>
              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="btn btn-outline flex-1"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="btn btn-primary flex-1"
                >
                  {isSubmitting ? 'Adding...' : 'Add Word'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
