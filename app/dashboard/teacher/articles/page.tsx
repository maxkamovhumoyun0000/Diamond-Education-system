'use client'

import { useState } from 'react'
import DashboardLayout from '@/components/DashboardLayout'
import { useLanguage } from '@/lib/i18n'
import { mockArticles, articleCategories, Article, ArticleCategory } from '@/lib/articles'
import { 
  Plus, 
  Search, 
  Eye, 
  Edit, 
  Trash2, 
  FileText, 
  CheckCircle, 
  Clock,
  AlertCircle
} from 'lucide-react'
import Link from 'next/link'

export default function TeacherArticlesPage() {
  const { t } = useLanguage()
  const [searchQuery, setSearchQuery] = useState('')
  const [categoryFilter, setCategoryFilter] = useState<ArticleCategory | 'all'>('all')
  
  // Simulate current teacher - in real app this would come from auth
  const currentTeacherId = 'teacher1'
  const hasPermission = true // In real app, check from permissions
  
  // Filter to only show this teacher's articles
  const myArticles = mockArticles.filter(a => a.authorId === currentTeacherId)
  
  const filteredArticles = myArticles.filter(article => {
    const matchesSearch = article.title.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesCategory = categoryFilter === 'all' || article.category === categoryFilter
    return matchesSearch && matchesCategory
  })

  const publishedCount = myArticles.filter(a => a.status === 'published').length
  const draftCount = myArticles.filter(a => a.status === 'draft').length
  const totalViews = myArticles.reduce((sum, a) => sum + a.views, 0)

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('uz-UZ', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  if (!hasPermission) {
    return (
      <DashboardLayout role="teacher" userName="Sarah Teacher">
        <div className="flex flex-col items-center justify-center min-h-[400px] text-center">
          <AlertCircle size={64} className="text-text-secondary mb-4" />
          <h1 className="text-2xl font-bold text-text-primary mb-2">Access Restricted</h1>
          <p className="text-text-secondary max-w-md">
            You don&apos;t have permission to create articles. Please contact an administrator to request access.
          </p>
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout role="teacher" userName="Sarah Teacher">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-text-primary">{t('articles.myArticles')}</h1>
            <p className="text-text-secondary">Create and manage your educational articles</p>
          </div>
          <Link
            href="/dashboard/teacher/articles/create"
            className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors"
          >
            <Plus size={20} />
            {t('articles.create')}
          </Link>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-surface border border-border rounded-lg p-4 text-center">
            <p className="text-2xl font-bold text-text-primary">{myArticles.length}</p>
            <p className="text-sm text-text-secondary">Total Articles</p>
          </div>
          <div className="bg-surface border border-border rounded-lg p-4 text-center">
            <p className="text-2xl font-bold text-green-600">{publishedCount}</p>
            <p className="text-sm text-text-secondary">Published</p>
          </div>
          <div className="bg-surface border border-border rounded-lg p-4 text-center">
            <p className="text-2xl font-bold text-accent">{totalViews.toLocaleString()}</p>
            <p className="text-sm text-text-secondary">Total Views</p>
          </div>
        </div>

        {/* Search & Filter */}
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1">
            <Search size={20} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary" />
            <input
              type="text"
              placeholder={t('articles.searchPlaceholder')}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-surface border border-border rounded-lg focus:ring-2 focus:ring-primary focus:border-primary text-text-primary"
            />
          </div>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value as ArticleCategory | 'all')}
            className="px-4 py-2 bg-surface border border-border rounded-lg focus:ring-2 focus:ring-primary focus:border-primary text-text-primary"
          >
            <option value="all">All Categories</option>
            {articleCategories.map(cat => (
              <option key={cat} value={cat}>{t(`articles.categories.${cat}`)}</option>
            ))}
          </select>
        </div>

        {/* Articles List */}
        {filteredArticles.length > 0 ? (
          <div className="space-y-4">
            {filteredArticles.map((article) => (
              <div
                key={article.id}
                className="bg-surface border border-border rounded-lg p-6 hover:border-primary/50 transition-colors"
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium ${
                        article.status === 'published' 
                          ? 'bg-green-100 text-green-700' 
                          : 'bg-yellow-100 text-yellow-700'
                      }`}>
                        {article.status === 'published' ? <CheckCircle size={12} /> : <Clock size={12} />}
                        {t(`articles.${article.status}`)}
                      </span>
                      <span className="px-2 py-1 bg-surface-hover rounded text-xs text-text-secondary">
                        {t(`articles.categories.${article.category}`)}
                      </span>
                    </div>
                    <h3 className="text-lg font-semibold text-text-primary mb-1">{article.title}</h3>
                    <p className="text-sm text-text-secondary line-clamp-2 mb-3">{article.excerpt}</p>
                    <div className="flex items-center gap-4 text-xs text-text-secondary">
                      <span className="flex items-center gap-1">
                        <Eye size={14} />
                        {article.views} views
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock size={14} />
                        {article.readTime} min read
                      </span>
                      <span>{formatDate(article.createdAt)}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Link
                      href={`/articles/${article.slug}`}
                      className="p-2 hover:bg-surface-hover rounded-lg transition-colors text-text-secondary hover:text-primary"
                      title="View"
                    >
                      <Eye size={18} />
                    </Link>
                    <Link
                      href={`/dashboard/teacher/articles/edit/${article.id}`}
                      className="p-2 hover:bg-surface-hover rounded-lg transition-colors text-text-secondary hover:text-primary"
                      title="Edit"
                    >
                      <Edit size={18} />
                    </Link>
                    <button
                      className="p-2 hover:bg-red-50 rounded-lg transition-colors text-text-secondary hover:text-red-600"
                      title="Delete"
                    >
                      <Trash2 size={18} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-16 bg-surface border border-border rounded-lg">
            <FileText size={48} className="mx-auto text-text-secondary mb-4" />
            <h3 className="text-lg font-semibold text-text-primary mb-2">No articles yet</h3>
            <p className="text-text-secondary mb-6">Start creating educational content for your students.</p>
            <Link
              href="/dashboard/teacher/articles/create"
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors"
            >
              <Plus size={18} />
              Create Your First Article
            </Link>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
