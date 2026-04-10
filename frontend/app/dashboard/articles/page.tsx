'use client'

import { useEffect, useState } from 'react'
import { articlesApi, Article } from '@/lib/api'

export default function ArticlesPage() {
  const [articles, setArticles] = useState<Article[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [showAddModal, setShowAddModal] = useState(false)
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null)
  const [formData, setFormData] = useState({
    title: '',
    content: '',
    subject: 'English',
    level: '',
    visible_to_teachers: true,
    visible_to_support_teachers: false,
    visible_to_students: false,
    is_published: false,
  })
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    fetchArticles()
  }, [])

  const fetchArticles = async () => {
    try {
      setIsLoading(true)
      const data = await articlesApi.list()
      setArticles(data.articles || [])
    } catch (err) {
      console.error('Failed to load articles:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.title.trim() || !formData.content.trim()) return

    try {
      setIsSubmitting(true)
      await articlesApi.create(formData)
      setShowAddModal(false)
      setFormData({
        title: '',
        content: '',
        subject: 'English',
        level: '',
        visible_to_teachers: true,
        visible_to_support_teachers: false,
        visible_to_students: false,
        is_published: false,
      })
      fetchArticles()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to create article')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleTogglePublish = async (id: number) => {
    try {
      await articlesApi.togglePublish(id)
      fetchArticles()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to toggle publish')
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this article?')) return
    try {
      await articlesApi.delete(id)
      fetchArticles()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete article')
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-serif font-bold">Articles</h1>
          <p className="text-[hsl(var(--muted-foreground))]">
            Create and manage educational content
          </p>
        </div>
        <button onClick={() => setShowAddModal(true)} className="btn btn-primary">
          <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          New Article
        </button>
      </div>

      {/* Articles List */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 border-3 border-[hsl(var(--primary))]/30 border-t-[hsl(var(--primary))] rounded-full animate-spin" />
        </div>
      ) : articles.length === 0 ? (
        <div className="card p-12 text-center">
          <svg className="w-12 h-12 mx-auto text-[hsl(var(--muted-foreground))] mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <p className="text-[hsl(var(--muted-foreground))] mb-4">No articles yet</p>
          <button onClick={() => setShowAddModal(true)} className="btn btn-primary">
            Create First Article
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {articles.map((article) => (
            <div key={article.id} className="card p-6">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`badge ${article.subject === 'English' ? 'badge-primary' : 'badge-secondary'}`}>
                      {article.subject}
                    </span>
                    {article.level && (
                      <span className="badge badge-outline">{article.level}</span>
                    )}
                    {article.is_published ? (
                      <span className="badge badge-success">Published</span>
                    ) : (
                      <span className="badge badge-outline">Draft</span>
                    )}
                  </div>
                  <h3 
                    className="font-semibold text-lg cursor-pointer hover:text-[hsl(var(--primary))] transition-colors"
                    onClick={() => setSelectedArticle(article)}
                  >
                    {article.title}
                  </h3>
                  <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1 line-clamp-2">
                    {article.content.substring(0, 200)}...
                  </p>
                  <div className="flex items-center gap-4 mt-3 text-xs text-[hsl(var(--muted-foreground))]">
                    {article.visible_to_teachers && <span>Teachers</span>}
                    {article.visible_to_support_teachers && <span>Support Teachers</span>}
                    {article.visible_to_students && <span>Students</span>}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleTogglePublish(article.id)}
                    className="btn btn-ghost text-xs h-8 px-3"
                  >
                    {article.is_published ? 'Unpublish' : 'Publish'}
                  </button>
                  <button
                    onClick={() => handleDelete(article.id)}
                    className="btn btn-ghost text-xs h-8 px-3 text-red-500"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add/Edit Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="card p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto animate-fadeIn">
            <h2 className="text-xl font-semibold mb-4">Create New Article</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1.5">Title</label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="input"
                  placeholder="Enter article title"
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
                  <label className="block text-sm font-medium mb-1.5">Level</label>
                  <select
                    value={formData.level}
                    onChange={(e) => setFormData({ ...formData, level: e.target.value })}
                    className="input"
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
              <div>
                <label className="block text-sm font-medium mb-1.5">Content</label>
                <textarea
                  value={formData.content}
                  onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                  className="input h-48 resize-none"
                  placeholder="Write your article content here..."
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Visibility</label>
                <div className="flex flex-wrap gap-4">
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={formData.visible_to_teachers}
                      onChange={(e) => setFormData({ ...formData, visible_to_teachers: e.target.checked })}
                      className="w-4 h-4"
                    />
                    <span className="text-sm">Teachers</span>
                  </label>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={formData.visible_to_support_teachers}
                      onChange={(e) => setFormData({ ...formData, visible_to_support_teachers: e.target.checked })}
                      className="w-4 h-4"
                    />
                    <span className="text-sm">Support Teachers</span>
                  </label>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={formData.visible_to_students}
                      onChange={(e) => setFormData({ ...formData, visible_to_students: e.target.checked })}
                      className="w-4 h-4"
                    />
                    <span className="text-sm">Students</span>
                  </label>
                </div>
              </div>
              <label className="flex items-center gap-2 pt-2">
                <input
                  type="checkbox"
                  checked={formData.is_published}
                  onChange={(e) => setFormData({ ...formData, is_published: e.target.checked })}
                  className="w-4 h-4"
                />
                <span className="text-sm font-medium">Publish immediately</span>
              </label>
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
                  {isSubmitting ? 'Creating...' : 'Create Article'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* View Article Modal */}
      {selectedArticle && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="card p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto animate-fadeIn">
            <div className="flex items-start justify-between mb-4">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <span className={`badge ${selectedArticle.subject === 'English' ? 'badge-primary' : 'badge-secondary'}`}>
                    {selectedArticle.subject}
                  </span>
                  {selectedArticle.level && (
                    <span className="badge badge-outline">{selectedArticle.level}</span>
                  )}
                </div>
                <h2 className="text-xl font-semibold">{selectedArticle.title}</h2>
              </div>
              <button
                onClick={() => setSelectedArticle(null)}
                className="btn btn-ghost h-8 w-8 p-0"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="prose max-w-none">
              <p className="whitespace-pre-wrap">{selectedArticle.content}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
