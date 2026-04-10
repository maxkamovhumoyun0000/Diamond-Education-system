export type ArticleCategory = 'grammar' | 'vocabulary' | 'motivation' | 'tips' | 'culture' | 'news' | 'general'
export type ArticleVisibility = 'all' | 'students' | 'teachers'
export type ArticleStatus = 'draft' | 'published'

export interface Article {
  id: string
  title: string
  slug: string
  excerpt: string
  content: string
  category: ArticleCategory
  visibility: ArticleVisibility
  status: ArticleStatus
  featuredImage?: string
  tags: string[]
  authorId: string
  authorName: string
  authorRole: 'admin' | 'teacher'
  views: number
  readTime: number // in minutes
  metaTitle?: string
  metaDescription?: string
  createdAt: string
  updatedAt: string
  publishedAt?: string
}

export interface TeacherPermission {
  teacherId: string
  teacherName: string
  canCreateArticles: boolean
  articlesCreated: number
}

// Mock data for articles
export const mockArticles: Article[] = [
  {
    id: '1',
    title: 'Mastering English Tenses: A Complete Guide',
    slug: 'mastering-english-tenses',
    excerpt: 'Learn all 12 English tenses with clear explanations and practical examples.',
    content: `<h2>Introduction to English Tenses</h2>
<p>English has 12 main tenses that help us express when actions happen. Understanding these tenses is crucial for effective communication.</p>
<h3>Present Simple</h3>
<p>We use the present simple for habits, routines, and general truths.</p>
<ul>
<li>I study English every day.</li>
<li>She works at Diamond Education.</li>
</ul>
<h3>Present Continuous</h3>
<p>We use the present continuous for actions happening now.</p>
<ul>
<li>I am learning grammar right now.</li>
<li>They are studying for their test.</li>
</ul>`,
    category: 'grammar',
    visibility: 'all',
    status: 'published',
    featuredImage: '/articles/tenses.jpg',
    tags: ['grammar', 'tenses', 'beginner'],
    authorId: 'admin1',
    authorName: 'Admin User',
    authorRole: 'admin',
    views: 1250,
    readTime: 8,
    metaTitle: 'Master English Tenses - Complete Guide | Diamond Education',
    metaDescription: 'Learn all 12 English tenses with clear explanations and examples. Perfect for beginners and intermediate learners.',
    createdAt: '2024-01-15T10:00:00Z',
    updatedAt: '2024-01-20T14:30:00Z',
    publishedAt: '2024-01-15T12:00:00Z',
  },
  {
    id: '2',
    title: '100 Most Common English Words You Need to Know',
    slug: '100-common-english-words',
    excerpt: 'Build your vocabulary with the most frequently used English words.',
    content: `<h2>Essential Vocabulary</h2>
<p>These 100 words make up about 50% of all written English material. Learn them well!</p>
<h3>Top 20 Words</h3>
<ol>
<li>the</li>
<li>be</li>
<li>to</li>
<li>of</li>
<li>and</li>
</ol>`,
    category: 'vocabulary',
    visibility: 'all',
    status: 'published',
    tags: ['vocabulary', 'beginner', 'essentials'],
    authorId: 'teacher1',
    authorName: 'Sarah Teacher',
    authorRole: 'teacher',
    views: 890,
    readTime: 5,
    createdAt: '2024-01-10T09:00:00Z',
    updatedAt: '2024-01-10T09:00:00Z',
    publishedAt: '2024-01-10T09:00:00Z',
  },
  {
    id: '3',
    title: 'Stay Motivated: Tips for Language Learning Success',
    slug: 'stay-motivated-language-learning',
    excerpt: 'Discover proven strategies to stay motivated on your language learning journey.',
    content: `<h2>Why Motivation Matters</h2>
<p>Learning a new language is a marathon, not a sprint. Here's how to keep going.</p>`,
    category: 'motivation',
    visibility: 'students',
    status: 'published',
    tags: ['motivation', 'tips', 'learning'],
    authorId: 'admin1',
    authorName: 'Admin User',
    authorRole: 'admin',
    views: 567,
    readTime: 4,
    createdAt: '2024-01-08T15:00:00Z',
    updatedAt: '2024-01-08T15:00:00Z',
    publishedAt: '2024-01-08T15:00:00Z',
  },
  {
    id: '4',
    title: 'Draft: Advanced Grammar Concepts',
    slug: 'advanced-grammar-concepts',
    excerpt: 'Deep dive into complex grammar structures.',
    content: `<h2>Work in Progress</h2><p>This article is still being written.</p>`,
    category: 'grammar',
    visibility: 'all',
    status: 'draft',
    tags: ['grammar', 'advanced'],
    authorId: 'admin1',
    authorName: 'Admin User',
    authorRole: 'admin',
    views: 0,
    readTime: 10,
    createdAt: '2024-01-20T10:00:00Z',
    updatedAt: '2024-01-20T10:00:00Z',
  },
]

// Mock teacher permissions
export const mockTeacherPermissions: TeacherPermission[] = [
  { teacherId: 'teacher1', teacherName: 'Sarah Teacher', canCreateArticles: true, articlesCreated: 5 },
  { teacherId: 'teacher2', teacherName: 'John Smith', canCreateArticles: false, articlesCreated: 0 },
  { teacherId: 'teacher3', teacherName: 'Maria Garcia', canCreateArticles: true, articlesCreated: 3 },
]

export const articleCategories: ArticleCategory[] = ['grammar', 'vocabulary', 'motivation', 'tips', 'culture', 'news', 'general']
