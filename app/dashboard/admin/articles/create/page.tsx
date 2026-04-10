'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import DashboardLayout from '@/components/DashboardLayout'
import { useLanguage } from '@/lib/i18n'
import { ArticleCategory, ArticleVisibility, articleCategories } from '@/lib/articles'
import { 
  ArrowLeft, 
  Save, 
  Eye, 
  Image as ImageIcon, 
  Bold, 
  Italic, 
  List, 
  ListOrdered,
  Heading1,
  Heading2,
  Link as LinkIcon,
  Quote,
  Code
} from 'lucide-react'
import Link from 'next/link'

export default function CreateArticlePage() {
  const { t } = useLanguage()
  const router = useRouter()
  
  const [title, setTitle] = useState('')
  const [excerpt, setExcerpt] = useState('')
  const [content, setContent] = useState('')
  const [category, setCategory] = useState<ArticleCategory>('general')
  const [visibility, setVisibility] = useState<ArticleVisibility>('all')
  const [tags, setTags] = useState('')
  const [featuredImage, setFeaturedImage] = useState('')
  const [metaTitle, setMetaTitle] = useState('')
  const [metaDescription, setMetaDescription] = useState('')
  const [showPreview, setShowPreview] = useState(false)
  const [isSaving, setIsSaving] = useState(false)

  // Simple text formatting functions
  const insertFormat = (format: string) => {
    const textarea = document.getElementById('content-editor') as HTMLTextAreaElement
    if (!textarea) return

    const start = textarea.selectionStart
    const end = textarea.selectionEnd
    const selectedText = content.substring(start, end)
    let newText = ''

    switch (format) {
      case 'bold':
        newText = `<strong>${selectedText || 'bold text'}</strong>`
        break
      case 'italic':
        newText = `<em>${selectedText || 'italic text'}</em>`
        break
      case 'h1':
        newText = `<h2>${selectedText || 'Heading'}</h2>`
        break
      case 'h2':
        newText = `<h3>${selectedText || 'Subheading'}</h3>`
        break
      case 'ul':
        newText = `<ul>\n<li>${selectedText || 'List item'}</li>\n</ul>`
        break
      case 'ol':
        newText = `<ol>\n<li>${selectedText || 'List item'}</li>\n</ol>`
        break
      case 'quote':
        newText = `<blockquote>${selectedText || 'Quote'}</blockquote>`
        break
      case 'code':
        newText = `<code>${selectedText || 'code'}</code>`
        break
      case 'link':
        newText = `<a href="url">${selectedText || 'link text'}</a>`
        break
      default:
        newText = selectedText
    }

    const newContent = content.substring(0, start) + newText + content.substring(end)
    setContent(newContent)
  }

  const handleSave = async (status: 'draft' | 'published') => {
    setIsSaving(true)
    
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    // In real implementation, this would save to database
    console.log('Saving article:', {
      title,
      excerpt,
      content,
      category,
      visibility,
      tags: tags.split(',').map(t => t.trim()),
      featuredImage,
      metaTitle,
      metaDescription,
      status,
    })
    
    setIsSaving(false)
    router.push('/dashboard/admin/articles')
  }

  const calculateReadTime = () => {
    const wordsPerMinute = 200
    const words = content.replace(/<[^>]*>/g, '').split(/\s+/).length
    return Math.max(1, Math.ceil(words / wordsPerMinute))
  }

  return (
    <DashboardLayout role="admin" userName="Admin">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <Link
              href="/dashboard/admin/articles"
              className="p-2 hover:bg-surface-hover rounded-lg transition-colors text-text-secondary hover:text-text-primary"
            >
              <ArrowLeft size={20} />
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-text-primary">{t('articles.create')}</h1>
              <p className="text-text-secondary">Create a new article for the platform</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowPreview(!showPreview)}
              className="flex items-center gap-2 px-4 py-2 border border-border rounded-lg hover:bg-surface-hover transition-colors text-text-primary"
            >
              <Eye size={18} />
              {showPreview ? 'Edit' : 'Preview'}
            </button>
            <button
              onClick={() => handleSave('draft')}
              disabled={isSaving || !title}
              className="flex items-center gap-2 px-4 py-2 border border-border rounded-lg hover:bg-surface-hover transition-colors text-text-primary disabled:opacity-50"
            >
              <Save size={18} />
              {t('articles.draft')}
            </button>
            <button
              onClick={() => handleSave('published')}
              disabled={isSaving || !title || !content}
              className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors disabled:opacity-50"
            >
              {t('articles.publish')}
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {showPreview ? (
              // Preview Mode
              <div className="bg-surface border border-border rounded-lg p-6">
                <h2 className="text-2xl font-bold text-text-primary mb-2">{title || 'Untitled Article'}</h2>
                <p className="text-text-secondary mb-4">{excerpt}</p>
                <div className="flex items-center gap-4 text-sm text-text-secondary mb-6 pb-4 border-b border-border">
                  <span>{t(`articles.categories.${category}`)}</span>
                  <span>{calculateReadTime()} {t('articles.minutes')}</span>
                </div>
                <div 
                  className="prose prose-sm max-w-none text-text-primary"
                  dangerouslySetInnerHTML={{ __html: content || '<p>No content yet</p>' }}
                />
              </div>
            ) : (
              // Edit Mode
              <>
                {/* Title */}
                <div className="bg-surface border border-border rounded-lg p-6">
                  <label className="block text-sm font-medium text-text-primary mb-2">
                    {t('articles.articleTitle')} *
                  </label>
                  <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="Enter article title..."
                    className="w-full px-4 py-3 bg-background border border-border rounded-lg focus:ring-2 focus:ring-primary focus:border-primary text-text-primary text-lg"
                  />
                </div>

                {/* Excerpt */}
                <div className="bg-surface border border-border rounded-lg p-6">
                  <label className="block text-sm font-medium text-text-primary mb-2">
                    {t('articles.excerpt')}
                  </label>
                  <textarea
                    value={excerpt}
                    onChange={(e) => setExcerpt(e.target.value)}
                    placeholder="Brief description of the article..."
                    rows={2}
                    className="w-full px-4 py-3 bg-background border border-border rounded-lg focus:ring-2 focus:ring-primary focus:border-primary text-text-primary resize-none"
                  />
                </div>

                {/* Content Editor */}
                <div className="bg-surface border border-border rounded-lg p-6">
                  <label className="block text-sm font-medium text-text-primary mb-2">
                    {t('articles.content')} *
                  </label>
                  
                  {/* Toolbar */}
                  <div className="flex flex-wrap gap-1 p-2 bg-surface-hover rounded-lg mb-3">
                    <button
                      type="button"
                      onClick={() => insertFormat('h1')}
                      className="p-2 hover:bg-surface rounded transition-colors text-text-secondary hover:text-text-primary"
                      title="Heading 1"
                    >
                      <Heading1 size={18} />
                    </button>
                    <button
                      type="button"
                      onClick={() => insertFormat('h2')}
                      className="p-2 hover:bg-surface rounded transition-colors text-text-secondary hover:text-text-primary"
                      title="Heading 2"
                    >
                      <Heading2 size={18} />
                    </button>
                    <div className="w-px bg-border mx-1" />
                    <button
                      type="button"
                      onClick={() => insertFormat('bold')}
                      className="p-2 hover:bg-surface rounded transition-colors text-text-secondary hover:text-text-primary"
                      title="Bold"
                    >
                      <Bold size={18} />
                    </button>
                    <button
                      type="button"
                      onClick={() => insertFormat('italic')}
                      className="p-2 hover:bg-surface rounded transition-colors text-text-secondary hover:text-text-primary"
                      title="Italic"
                    >
                      <Italic size={18} />
                    </button>
                    <div className="w-px bg-border mx-1" />
                    <button
                      type="button"
                      onClick={() => insertFormat('ul')}
                      className="p-2 hover:bg-surface rounded transition-colors text-text-secondary hover:text-text-primary"
                      title="Bullet List"
                    >
                      <List size={18} />
                    </button>
                    <button
                      type="button"
                      onClick={() => insertFormat('ol')}
                      className="p-2 hover:bg-surface rounded transition-colors text-text-secondary hover:text-text-primary"
                      title="Numbered List"
                    >
                      <ListOrdered size={18} />
                    </button>
                    <div className="w-px bg-border mx-1" />
                    <button
                      type="button"
                      onClick={() => insertFormat('quote')}
                      className="p-2 hover:bg-surface rounded transition-colors text-text-secondary hover:text-text-primary"
                      title="Quote"
                    >
                      <Quote size={18} />
                    </button>
                    <button
                      type="button"
                      onClick={() => insertFormat('code')}
                      className="p-2 hover:bg-surface rounded transition-colors text-text-secondary hover:text-text-primary"
                      title="Code"
                    >
                      <Code size={18} />
                    </button>
                    <button
                      type="button"
                      onClick={() => insertFormat('link')}
                      className="p-2 hover:bg-surface rounded transition-colors text-text-secondary hover:text-text-primary"
                      title="Link"
                    >
                      <LinkIcon size={18} />
                    </button>
                  </div>

                  <textarea
                    id="content-editor"
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    placeholder="Write your article content here... (HTML supported)"
                    rows={15}
                    className="w-full px-4 py-3 bg-background border border-border rounded-lg focus:ring-2 focus:ring-primary focus:border-primary text-text-primary font-mono text-sm resize-y"
                  />
                  
                  <p className="mt-2 text-xs text-text-secondary">
                    Estimated read time: {calculateReadTime()} {t('articles.minutes')}
                  </p>
                </div>
              </>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Category & Visibility */}
            <div className="bg-surface border border-border rounded-lg p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  {t('articles.category')}
                </label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value as ArticleCategory)}
                  className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:ring-2 focus:ring-primary focus:border-primary text-text-primary"
                >
                  {articleCategories.map(cat => (
                    <option key={cat} value={cat}>{t(`articles.categories.${cat}`)}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  {t('articles.visibility')}
                </label>
                <select
                  value={visibility}
                  onChange={(e) => setVisibility(e.target.value as ArticleVisibility)}
                  className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:ring-2 focus:ring-primary focus:border-primary text-text-primary"
                >
                  <option value="all">{t('articles.visibilityAll')}</option>
                  <option value="students">{t('articles.visibilityStudents')}</option>
                  <option value="teachers">{t('articles.visibilityTeachers')}</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  {t('articles.tags')}
                </label>
                <input
                  type="text"
                  value={tags}
                  onChange={(e) => setTags(e.target.value)}
                  placeholder="grammar, beginner, tips"
                  className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:ring-2 focus:ring-primary focus:border-primary text-text-primary"
                />
                <p className="mt-1 text-xs text-text-secondary">Separate with commas</p>
              </div>
            </div>

            {/* Featured Image */}
            <div className="bg-surface border border-border rounded-lg p-6">
              <label className="block text-sm font-medium text-text-primary mb-2">
                {t('articles.featuredImage')}
              </label>
              {featuredImage ? (
                <div className="relative">
                  <img
                    src={featuredImage}
                    alt="Featured"
                    className="w-full h-40 object-cover rounded-lg"
                  />
                  <button
                    onClick={() => setFeaturedImage('')}
                    className="absolute top-2 right-2 p-1 bg-red-500 text-white rounded-full hover:bg-red-600"
                  >
                    ×
                  </button>
                </div>
              ) : (
                <div className="border-2 border-dashed border-border rounded-lg p-8 text-center">
                  <ImageIcon size={32} className="mx-auto text-text-secondary mb-2" />
                  <p className="text-sm text-text-secondary mb-2">Click or drag to upload</p>
                  <input
                    type="text"
                    placeholder="Or enter image URL..."
                    onChange={(e) => setFeaturedImage(e.target.value)}
                    className="w-full px-3 py-2 bg-background border border-border rounded text-sm text-text-primary"
                  />
                </div>
              )}
            </div>

            {/* SEO */}
            <div className="bg-surface border border-border rounded-lg p-6 space-y-4">
              <h3 className="font-medium text-text-primary">SEO Settings</h3>
              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  {t('articles.metaTitle')}
                </label>
                <input
                  type="text"
                  value={metaTitle}
                  onChange={(e) => setMetaTitle(e.target.value)}
                  placeholder={title || 'Article title'}
                  className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:ring-2 focus:ring-primary focus:border-primary text-text-primary text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  {t('articles.metaDescription')}
                </label>
                <textarea
                  value={metaDescription}
                  onChange={(e) => setMetaDescription(e.target.value)}
                  placeholder={excerpt || 'Brief description for search engines...'}
                  rows={3}
                  className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:ring-2 focus:ring-primary focus:border-primary text-text-primary text-sm resize-none"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
