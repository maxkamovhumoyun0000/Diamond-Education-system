'use client'

import { useState } from 'react'
import DashboardLayout from '@/components/DashboardLayout'
import { useLanguage } from '@/lib/i18n'
import { mockArticles, mockTeacherPermissions, articleCategories, Article, ArticleCategory, TeacherPermission } from '@/lib/articles'
import { 
  Plus, 
  Search, 
  Filter, 
  Eye, 
  Edit, 
  Trash2, 
  FileText, 
  Users, 
  CheckCircle, 
  XCircle,
  Clock,
  MoreVertical,
  Settings,
  BookOpen
} from 'lucide-react'
import Link from 'next/link'

type Tab = 'articles' | 'permissions'

export default function AdminArticlesPage() {
  const { t } = useLanguage()
  const [activeTab, setActiveTab] = useState<Tab>('articles')
  const [searchQuery, setSearchQuery] = useState('')
  const [categoryFilter, setCategoryFilter] = useState<ArticleCategory | 'all'>('all')
  const [statusFilter, setStatusFilter] = useState<'all' | 'draft' | 'published'>('all')
  const [articles, setArticles] = useState<Article[]>(mockArticles)
  const [permissions, setPermissions] = useState<TeacherPermission[]>(mockTeacherPermissions)
  const [showDeleteModal, setShowDeleteModal] = useState<string | null>(null)

  // Filter articles
  const filteredArticles = articles.filter(article => {
    const matchesSearch = article.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         article.excerpt.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesCategory = categoryFilter === 'all' || article.category === categoryFilter
    const matchesStatus = statusFilter === 'all' || article.status === statusFilter
    return matchesSearch && matchesCategory && matchesStatus
  })

  // Stats
  const totalArticles = articles.length
  const publishedArticles = articles.filter(a => a.status === 'published').length
  const totalViews = articles.reduce((sum, a) => sum + a.views, 0)
  const teachersWithPermission = permissions.filter(p => p.canCreateArticles).length

  const handleDelete = (id: string) => {
    setArticles(articles.filter(a => a.id !== id))
    setShowDeleteModal(null)
  }

  const togglePermission = (teacherId: string) => {
    setPermissions(permissions.map(p => 
      p.teacherId === teacherId 
        ? { ...p, canCreateArticles: !p.canCreateArticles }
        : p
    ))
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('uz-UZ', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  return (
    <DashboardLayout role="admin" userName="Admin">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-text-primary">{t('articles.title')}</h1>
            <p className="text-text-secondary">Manage articles and teacher permissions</p>
          </div>
          <Link
            href="/dashboard/admin/articles/create"
            className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors"
          >
            <Plus size={20} />
            {t('articles.create')}
          </Link>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-surface border border-border rounded-lg p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary/10 rounded-lg">
                <FileText size={20} className="text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold text-text-primary">{totalArticles}</p>
                <p className="text-sm text-text-secondary">Total Articles</p>
              </div>
            </div>
          </div>
          <div className="bg-surface border border-border rounded-lg p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-100 rounded-lg">
                <CheckCircle size={20} className="text-green-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-text-primary">{publishedArticles}</p>
                <p className="text-sm text-text-secondary">Published</p>
              </div>
            </div>
          </div>
          <div className="bg-surface border border-border rounded-lg p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-accent/10 rounded-lg">
                <Eye size={20} className="text-accent" />
              </div>
              <div>
                <p className="text-2xl font-bold text-text-primary">{totalViews.toLocaleString()}</p>
                <p className="text-sm text-text-secondary">Total Views</p>
              </div>
            </div>
          </div>
          <div className="bg-surface border border-border rounded-lg p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-orange-100 rounded-lg">
                <Users size={20} className="text-orange-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-text-primary">{teachersWithPermission}</p>
                <p className="text-sm text-text-secondary">Teachers w/ Permission</p>
              </div>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="border-b border-border">
          <div className="flex gap-4">
            <button
              onClick={() => setActiveTab('articles')}
              className={`pb-3 px-1 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'articles'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-text-secondary hover:text-text-primary'
              }`}
            >
              <span className="flex items-center gap-2">
                <BookOpen size={16} />
                {t('articles.allArticles')}
              </span>
            </button>
            <button
              onClick={() => setActiveTab('permissions')}
              className={`pb-3 px-1 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'permissions'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-text-secondary hover:text-text-primary'
              }`}
            >
              <span className="flex items-center gap-2">
                <Settings size={16} />
                {t('articles.permissions')}
              </span>
            </button>
          </div>
        </div>

        {/* Articles Tab */}
        {activeTab === 'articles' && (
          <div className="space-y-4">
            {/* Filters */}
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
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as 'all' | 'draft' | 'published')}
                className="px-4 py-2 bg-surface border border-border rounded-lg focus:ring-2 focus:ring-primary focus:border-primary text-text-primary"
              >
                <option value="all">All Status</option>
                <option value="published">{t('articles.published')}</option>
                <option value="draft">{t('articles.draft')}</option>
              </select>
            </div>

            {/* Articles List */}
            <div className="bg-surface border border-border rounded-lg overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-surface-hover">
                    <tr>
                      <th className="text-left px-4 py-3 text-sm font-medium text-text-secondary">Title</th>
                      <th className="text-left px-4 py-3 text-sm font-medium text-text-secondary hidden md:table-cell">Category</th>
                      <th className="text-left px-4 py-3 text-sm font-medium text-text-secondary hidden lg:table-cell">Author</th>
                      <th className="text-left px-4 py-3 text-sm font-medium text-text-secondary">Status</th>
                      <th className="text-left px-4 py-3 text-sm font-medium text-text-secondary hidden sm:table-cell">Views</th>
                      <th className="text-left px-4 py-3 text-sm font-medium text-text-secondary hidden lg:table-cell">Date</th>
                      <th className="text-right px-4 py-3 text-sm font-medium text-text-secondary">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {filteredArticles.map((article) => (
                      <tr key={article.id} className="hover:bg-surface-hover transition-colors">
                        <td className="px-4 py-4">
                          <div>
                            <p className="font-medium text-text-primary line-clamp-1">{article.title}</p>
                            <p className="text-sm text-text-secondary line-clamp-1">{article.excerpt}</p>
                          </div>
                        </td>
                        <td className="px-4 py-4 hidden md:table-cell">
                          <span className="px-2 py-1 bg-surface-hover rounded text-xs text-text-secondary capitalize">
                            {t(`articles.categories.${article.category}`)}
                          </span>
                        </td>
                        <td className="px-4 py-4 hidden lg:table-cell">
                          <p className="text-sm text-text-primary">{article.authorName}</p>
                          <p className="text-xs text-text-secondary capitalize">{article.authorRole}</p>
                        </td>
                        <td className="px-4 py-4">
                          <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium ${
                            article.status === 'published' 
                              ? 'bg-green-100 text-green-700' 
                              : 'bg-yellow-100 text-yellow-700'
                          }`}>
                            {article.status === 'published' ? <CheckCircle size={12} /> : <Clock size={12} />}
                            {t(`articles.${article.status}`)}
                          </span>
                        </td>
                        <td className="px-4 py-4 hidden sm:table-cell">
                          <span className="text-sm text-text-secondary">{article.views.toLocaleString()}</span>
                        </td>
                        <td className="px-4 py-4 hidden lg:table-cell">
                          <span className="text-sm text-text-secondary">{formatDate(article.createdAt)}</span>
                        </td>
                        <td className="px-4 py-4">
                          <div className="flex items-center justify-end gap-2">
                            <Link
                              href={`/articles/${article.slug}`}
                              className="p-2 hover:bg-surface-hover rounded-lg transition-colors text-text-secondary hover:text-primary"
                              title="View"
                            >
                              <Eye size={16} />
                            </Link>
                            <Link
                              href={`/dashboard/admin/articles/edit/${article.id}`}
                              className="p-2 hover:bg-surface-hover rounded-lg transition-colors text-text-secondary hover:text-primary"
                              title="Edit"
                            >
                              <Edit size={16} />
                            </Link>
                            <button
                              onClick={() => setShowDeleteModal(article.id)}
                              className="p-2 hover:bg-red-50 rounded-lg transition-colors text-text-secondary hover:text-red-600"
                              title="Delete"
                            >
                              <Trash2 size={16} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              
              {filteredArticles.length === 0 && (
                <div className="p-8 text-center">
                  <FileText size={48} className="mx-auto text-text-secondary mb-4" />
                  <p className="text-text-secondary">{t('articles.noArticles')}</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Permissions Tab */}
        {activeTab === 'permissions' && (
          <div className="space-y-4">
            <div className="bg-surface border border-border rounded-lg p-4 mb-4">
              <h3 className="font-medium text-text-primary mb-2">{t('articles.managePermissions')}</h3>
              <p className="text-sm text-text-secondary">
                Control which teachers can create and publish articles on the platform.
              </p>
            </div>

            <div className="bg-surface border border-border rounded-lg overflow-hidden">
              <table className="w-full">
                <thead className="bg-surface-hover">
                  <tr>
                    <th className="text-left px-4 py-3 text-sm font-medium text-text-secondary">Teacher</th>
                    <th className="text-left px-4 py-3 text-sm font-medium text-text-secondary hidden sm:table-cell">Articles Created</th>
                    <th className="text-left px-4 py-3 text-sm font-medium text-text-secondary">{t('articles.allowCreate')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {permissions.map((teacher) => (
                    <tr key={teacher.teacherId} className="hover:bg-surface-hover transition-colors">
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 bg-primary/10 rounded-full flex items-center justify-center">
                            <span className="text-primary font-medium">
                              {teacher.teacherName.split(' ').map(n => n[0]).join('')}
                            </span>
                          </div>
                          <p className="font-medium text-text-primary">{teacher.teacherName}</p>
                        </div>
                      </td>
                      <td className="px-4 py-4 hidden sm:table-cell">
                        <span className="text-text-secondary">{teacher.articlesCreated}</span>
                      </td>
                      <td className="px-4 py-4">
                        <button
                          onClick={() => togglePermission(teacher.teacherId)}
                          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                            teacher.canCreateArticles ? 'bg-primary' : 'bg-gray-300'
                          }`}
                        >
                          <span
                            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                              teacher.canCreateArticles ? 'translate-x-6' : 'translate-x-1'
                            }`}
                          />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Delete Confirmation Modal */}
        {showDeleteModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-surface rounded-lg border border-border p-6 max-w-md w-full">
              <h2 className="text-xl font-bold text-text-primary mb-4">{t('articles.delete')}</h2>
              <p className="text-text-secondary mb-6">
                Are you sure you want to delete this article? This action cannot be undone.
              </p>
              <div className="flex gap-3">
                <button 
                  onClick={() => setShowDeleteModal(null)}
                  className="flex-1 px-4 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors font-medium"
                >
                  {t('common.cancel')}
                </button>
                <button 
                  onClick={() => handleDelete(showDeleteModal)}
                  className="flex-1 px-4 py-2 rounded-lg bg-red-600 text-white hover:bg-red-700 transition-colors font-medium"
                >
                  {t('common.delete')}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
