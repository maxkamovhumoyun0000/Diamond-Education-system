'use client'

import Link from 'next/link'
import Navbar from '@/components/Navbar'
import DiamondAIChat from '@/components/DiamondAIChat'
import { Clock, User, ArrowRight, Search, Eye, BookOpen } from 'lucide-react'
import { useState } from 'react'
import { useLanguage } from '@/lib/i18n'
import { mockArticles, articleCategories, ArticleCategory } from '@/lib/articles'

export default function ArticlesPage() {
  const { t } = useLanguage()
  const [searchQuery, setSearchQuery] = useState('')
  const [categoryFilter, setCategoryFilter] = useState<ArticleCategory | 'all'>('all')

  // Only show published articles
  const publishedArticles = mockArticles.filter(a => a.status === 'published')

  // Filter articles
  const filteredArticles = publishedArticles.filter(article => {
    const matchesSearch = article.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         article.excerpt.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesCategory = categoryFilter === 'all' || article.category === categoryFilter
    return matchesSearch && matchesCategory
  })

  // Featured article (most views)
  const featuredArticle = [...publishedArticles].sort((a, b) => b.views - a.views)[0]

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('uz-UZ', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-surface">
      <Navbar />
      <DiamondAIChat userRole="student" />

      {/* Hero Section */}
      <section className="bg-gradient-to-r from-primary to-primary-dark text-white py-16 md:py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 className="text-4xl md:text-5xl font-bold mb-4">{t('articles.title')}</h1>
          <p className="text-xl text-white/80 max-w-2xl">
            Read our latest articles, tips, and guides to improve your language skills
          </p>
        </div>
      </section>

      {/* Featured Article */}
      {featuredArticle && (
        <section className="py-8">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <Link 
              href={`/articles/${featuredArticle.slug}`}
              className="block group"
            >
              <div className="relative bg-gradient-to-br from-accent/20 to-primary/20 border border-accent/30 rounded-2xl overflow-hidden">
                <div className="p-8 md:p-12">
                  <span className="inline-block px-3 py-1 bg-accent text-white rounded-full text-sm font-medium mb-4">
                    Featured Article
                  </span>
                  <h2 className="text-2xl md:text-3xl font-bold text-text-primary mb-4 group-hover:text-primary transition-colors">
                    {featuredArticle.title}
                  </h2>
                  <p className="text-text-secondary mb-6 max-w-2xl line-clamp-2">
                    {featuredArticle.excerpt}
                  </p>
                  <div className="flex flex-wrap items-center gap-4 text-sm text-text-secondary">
                    <span className="flex items-center gap-1">
                      <User size={14} />
                      {featuredArticle.authorName}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock size={14} />
                      {featuredArticle.readTime} {t('articles.minutes')}
                    </span>
                    <span className="flex items-center gap-1">
                      <Eye size={14} />
                      {featuredArticle.views.toLocaleString()} {t('articles.views')}
                    </span>
                    <span className="ml-auto flex items-center gap-1 text-primary font-medium">
                      Read Article <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
                    </span>
                  </div>
                </div>
              </div>
            </Link>
          </div>
        </section>
      )}

      {/* Main Content */}
      <section className="py-8 md:py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Search and Filter */}
          <div className="mb-8 space-y-6">
            <div className="relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-text-secondary" size={20} />
              <input
                type="text"
                placeholder={t('articles.searchPlaceholder')}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-12 pr-4 py-3 border border-border rounded-lg bg-surface text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            {/* Category Filter */}
            <div className="flex flex-wrap gap-3">
              <button
                onClick={() => setCategoryFilter('all')}
                className={`px-4 py-2 rounded-full font-medium transition-colors ${
                  categoryFilter === 'all'
                    ? 'bg-primary text-white'
                    : 'bg-surface border border-border text-text-primary hover:border-primary'
                }`}
              >
                All
              </button>
              {articleCategories.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setCategoryFilter(cat)}
                  className={`px-4 py-2 rounded-full font-medium transition-colors ${
                    categoryFilter === cat
                      ? 'bg-primary text-white'
                      : 'bg-surface border border-border text-text-primary hover:border-primary'
                  }`}
                >
                  {t(`articles.categories.${cat}`)}
                </button>
              ))}
            </div>
          </div>

          {/* Articles Grid */}
          {filteredArticles.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredArticles.map((article) => (
                <Link
                  key={article.id}
                  href={`/articles/${article.slug}`}
                  className="group bg-surface border border-border rounded-xl overflow-hidden hover:shadow-lg transition-all duration-300 hover:border-primary"
                >
                  {/* Image */}
                  <div className="relative h-48 overflow-hidden bg-gradient-to-br from-surface-hover to-surface flex items-center justify-center">
                    {article.featuredImage ? (
                      <img
                        src={article.featuredImage}
                        alt={article.title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                      />
                    ) : (
                      <BookOpen size={48} className="text-text-secondary" />
                    )}
                    <div className="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent" />
                    <span className="absolute top-3 right-3 px-3 py-1 rounded-full bg-primary text-white text-xs font-medium">
                      {t(`articles.categories.${article.category}`)}
                    </span>
                  </div>

                  {/* Content */}
                  <div className="p-6 space-y-4">
                    <h2 className="text-lg font-semibold text-text-primary group-hover:text-primary transition-colors line-clamp-2">
                      {article.title}
                    </h2>
                    <p className="text-text-secondary text-sm line-clamp-2">{article.excerpt}</p>

                    {/* Meta */}
                    <div className="flex items-center justify-between text-xs text-text-secondary pt-4 border-t border-border">
                      <div className="flex items-center gap-2">
                        <User size={14} />
                        <span>{article.authorName}</span>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className="flex items-center gap-1">
                          <Clock size={14} />
                          {article.readTime} min
                        </span>
                        <span className="flex items-center gap-1">
                          <Eye size={14} />
                          {article.views}
                        </span>
                      </div>
                    </div>

                    {/* Footer */}
                    <div className="flex items-center justify-between pt-2">
                      <span className="text-xs text-text-secondary">{formatDate(article.createdAt)}</span>
                      <ArrowRight size={16} className="text-primary group-hover:translate-x-1 transition-transform" />
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="text-center py-16">
              <BookOpen size={64} className="mx-auto text-text-secondary mb-4" />
              <h3 className="text-xl font-semibold text-text-primary mb-2">{t('articles.noArticles')}</h3>
              <p className="text-text-secondary">Try adjusting your search or filter criteria.</p>
            </div>
          )}
        </div>
      </section>

      {/* Newsletter Section */}
      <section className="bg-surface border-y border-border py-12 md:py-16">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 text-center">
          <h2 className="text-2xl md:text-3xl font-bold text-text-primary mb-4">
            Subscribe to Our Newsletter
          </h2>
          <p className="text-text-secondary mb-6">
            Get weekly tips and resources to improve your language skills
          </p>
          <div className="flex flex-col sm:flex-row gap-3">
            <input
              type="email"
              placeholder="Enter your email"
              className="flex-1 px-4 py-3 border border-border rounded-lg bg-background text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary"
            />
            <button className="px-6 py-3 rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors font-medium">
              Subscribe
            </button>
          </div>
        </div>
      </section>
    </div>
  )
}
