'use client'

import { use } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import Navbar from '@/components/Navbar'
import DiamondAIChat from '@/components/DiamondAIChat'
import { useLanguage } from '@/lib/i18n'
import { mockArticles } from '@/lib/articles'
import { Clock, User, Eye, ArrowLeft, Share2, BookOpen, Calendar, Tag } from 'lucide-react'

interface ArticlePageProps {
  params: Promise<{ slug: string }>
}

export default function ArticlePage({ params }: ArticlePageProps) {
  const { slug } = use(params)
  const { t } = useLanguage()
  const router = useRouter()

  const article = mockArticles.find(a => a.slug === slug)

  if (!article) {
    return (
      <div className="min-h-screen bg-background">
        <Navbar />
        <div className="max-w-4xl mx-auto px-4 py-16 text-center">
          <BookOpen size={64} className="mx-auto text-text-secondary mb-4" />
          <h1 className="text-2xl font-bold text-text-primary mb-2">Article Not Found</h1>
          <p className="text-text-secondary mb-6">The article you&apos;re looking for doesn&apos;t exist.</p>
          <Link
            href="/articles"
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors"
          >
            <ArrowLeft size={18} />
            Back to Articles
          </Link>
        </div>
      </div>
    )
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('uz-UZ', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  }

  const handleShare = async () => {
    if (navigator.share) {
      await navigator.share({
        title: article.title,
        text: article.excerpt,
        url: window.location.href,
      })
    } else {
      navigator.clipboard.writeText(window.location.href)
      alert('Link copied to clipboard!')
    }
  }

  // Get related articles (same category, excluding current)
  const relatedArticles = mockArticles
    .filter(a => a.category === article.category && a.id !== article.id && a.status === 'published')
    .slice(0, 3)

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <DiamondAIChat userRole="student" />

      {/* Article Header */}
      <header className="bg-gradient-to-br from-primary/5 to-accent/5 border-b border-border">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Back Button */}
          <button
            onClick={() => router.back()}
            className="flex items-center gap-2 text-text-secondary hover:text-primary transition-colors mb-6"
          >
            <ArrowLeft size={18} />
            {t('common.back')}
          </button>

          {/* Category */}
          <span className="inline-block px-3 py-1 bg-primary/10 text-primary rounded-full text-sm font-medium mb-4">
            {t(`articles.categories.${article.category}`)}
          </span>

          {/* Title */}
          <h1 className="text-3xl md:text-4xl font-bold text-text-primary mb-4 text-balance">
            {article.title}
          </h1>

          {/* Excerpt */}
          <p className="text-lg text-text-secondary mb-6">
            {article.excerpt}
          </p>

          {/* Meta Info */}
          <div className="flex flex-wrap items-center gap-4 text-sm text-text-secondary">
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 bg-primary/10 rounded-full flex items-center justify-center">
                <span className="text-primary font-medium">
                  {article.authorName.split(' ').map(n => n[0]).join('')}
                </span>
              </div>
              <div>
                <p className="font-medium text-text-primary">{article.authorName}</p>
                <p className="text-xs capitalize">{article.authorRole}</p>
              </div>
            </div>
            <span className="hidden sm:block w-px h-6 bg-border" />
            <span className="flex items-center gap-1">
              <Calendar size={16} />
              {formatDate(article.publishedAt || article.createdAt)}
            </span>
            <span className="flex items-center gap-1">
              <Clock size={16} />
              {article.readTime} {t('articles.minutes')}
            </span>
            <span className="flex items-center gap-1">
              <Eye size={16} />
              {article.views.toLocaleString()} {t('articles.views')}
            </span>
            <button
              onClick={handleShare}
              className="ml-auto flex items-center gap-1 px-3 py-1.5 bg-surface border border-border rounded-lg hover:bg-surface-hover transition-colors"
            >
              <Share2 size={16} />
              Share
            </button>
          </div>
        </div>
      </header>

      {/* Featured Image */}
      {article.featuredImage && (
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 -mt-4">
          <img
            src={article.featuredImage}
            alt={article.title}
            className="w-full h-64 md:h-96 object-cover rounded-xl shadow-lg"
          />
        </div>
      )}

      {/* Article Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <article 
          className="prose prose-lg max-w-none
            prose-headings:text-text-primary prose-headings:font-bold
            prose-h2:text-2xl prose-h2:mt-8 prose-h2:mb-4
            prose-h3:text-xl prose-h3:mt-6 prose-h3:mb-3
            prose-p:text-text-secondary prose-p:leading-relaxed
            prose-a:text-primary prose-a:no-underline hover:prose-a:underline
            prose-strong:text-text-primary
            prose-ul:text-text-secondary prose-ol:text-text-secondary
            prose-li:my-1
            prose-blockquote:border-l-4 prose-blockquote:border-primary prose-blockquote:bg-surface prose-blockquote:py-2 prose-blockquote:px-4 prose-blockquote:rounded-r-lg prose-blockquote:text-text-secondary prose-blockquote:not-italic
            prose-code:bg-surface prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-accent prose-code:font-mono prose-code:text-sm
          "
          dangerouslySetInnerHTML={{ __html: article.content }}
        />

        {/* Tags */}
        {article.tags.length > 0 && (
          <div className="mt-8 pt-6 border-t border-border">
            <div className="flex items-center gap-2 flex-wrap">
              <Tag size={18} className="text-text-secondary" />
              {article.tags.map(tag => (
                <span
                  key={tag}
                  className="px-3 py-1 bg-surface-hover rounded-full text-sm text-text-secondary"
                >
                  #{tag}
                </span>
              ))}
            </div>
          </div>
        )}
      </main>

      {/* Related Articles */}
      {relatedArticles.length > 0 && (
        <section className="bg-surface border-t border-border py-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="text-2xl font-bold text-text-primary mb-6">Related Articles</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {relatedArticles.map((related) => (
                <Link
                  key={related.id}
                  href={`/articles/${related.slug}`}
                  className="group bg-background border border-border rounded-xl p-6 hover:border-primary transition-colors"
                >
                  <span className="text-xs text-primary font-medium">
                    {t(`articles.categories.${related.category}`)}
                  </span>
                  <h3 className="text-lg font-semibold text-text-primary mt-2 mb-2 line-clamp-2 group-hover:text-primary transition-colors">
                    {related.title}
                  </h3>
                  <p className="text-sm text-text-secondary line-clamp-2">
                    {related.excerpt}
                  </p>
                  <div className="flex items-center gap-3 mt-4 text-xs text-text-secondary">
                    <span className="flex items-center gap-1">
                      <Clock size={12} />
                      {related.readTime} min
                    </span>
                    <span className="flex items-center gap-1">
                      <Eye size={12} />
                      {related.views}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* CTA */}
      <section className="py-12">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-2xl font-bold text-text-primary mb-4">Ready to Start Learning?</h2>
          <p className="text-text-secondary mb-6">
            Join Diamond Education and get access to all our courses and resources.
          </p>
          <div className="flex items-center justify-center gap-4">
            <Link
              href="/articles"
              className="px-6 py-3 border border-border rounded-lg hover:bg-surface-hover transition-colors font-medium text-text-primary"
            >
              Browse Articles
            </Link>
            <Link
              href="/login"
              className="px-6 py-3 bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors font-medium"
            >
              Get Started
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}
