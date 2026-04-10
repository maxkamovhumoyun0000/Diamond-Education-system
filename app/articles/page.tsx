import Link from 'next/link'
import Image from 'next/image'
import Navbar from '@/components/Navbar'
import { Clock, User, ArrowRight, Search } from 'lucide-react'

export default function ArticlesPage() {
  const articles = [
    {
      id: 1,
      title: '10 Tips to Improve Your English Speaking Skills',
      excerpt: 'Learn practical techniques to enhance your fluency and confidence in English conversations.',
      category: 'Speaking',
      author: 'Sarah Johnson',
      date: 'Mar 15, 2024',
      readTime: '8 min',
      image: 'https://images.unsplash.com/photo-1516321318423-f06c6aaf7051?w=400&h=300&fit=crop',
    },
    {
      id: 2,
      title: 'Mastering English Grammar: A Beginner\'s Guide',
      excerpt: 'Essential grammar rules and exercises to build a strong foundation in English.',
      category: 'Grammar',
      author: 'Ahmed Ali',
      date: 'Mar 10, 2024',
      readTime: '12 min',
      image: 'https://images.unsplash.com/photo-1456521228898-75bf8f4e0f8f?w=400&h=300&fit=crop',
    },
    {
      id: 3,
      title: 'Vocabulary Building: From Beginner to Advanced',
      excerpt: 'Effective strategies to expand your English vocabulary and use words naturally.',
      category: 'Vocabulary',
      author: 'Fatima Khan',
      date: 'Mar 5, 2024',
      readTime: '10 min',
      image: 'https://images.unsplash.com/photo-1506126613408-eca07ce68773?w=400&h=300&fit=crop',
    },
    {
      id: 4,
      title: 'Understanding English Idioms and Expressions',
      excerpt: 'Learn common idioms and phrases that native speakers use in everyday conversation.',
      category: 'Idioms',
      author: 'Hassan Ahmed',
      date: 'Feb 28, 2024',
      readTime: '9 min',
      image: 'https://images.unsplash.com/photo-1516979187457-637abb4f9353?w=400&h=300&fit=crop',
    },
    {
      id: 5,
      title: 'Listening Comprehension: Techniques and Practice',
      excerpt: 'Improve your ability to understand spoken English through proven methods.',
      category: 'Listening',
      author: 'Aysha Hassan',
      date: 'Feb 20, 2024',
      readTime: '11 min',
      image: 'https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=400&h=300&fit=crop',
    },
    {
      id: 6,
      title: 'Business English: Communication in Professional Settings',
      excerpt: 'Specialized English skills for successful communication in the workplace.',
      category: 'Business',
      author: 'Omar Ibrahim',
      date: 'Feb 15, 2024',
      readTime: '13 min',
      image: 'https://images.unsplash.com/photo-1552664730-d307ca884978?w=400&h=300&fit=crop',
    },
  ]

  const categories = ['All', 'Speaking', 'Grammar', 'Vocabulary', 'Idioms', 'Listening', 'Business']

  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      {/* Hero Section */}
      <section className="bg-gradient-to-r from-primary to-primary-dark text-white py-16 md:py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 className="text-4xl md:text-5xl font-bold mb-4">Learning Resources</h1>
          <p className="text-xl text-white/80 max-w-2xl">
            Read our latest articles, tips, and guides to improve your English skills
          </p>
        </div>
      </section>

      {/* Main Content */}
      <section className="py-12 md:py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Search and Filter */}
          <div className="mb-12 space-y-6">
            <div className="relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-text-secondary" size={20} />
              <input
                type="text"
                placeholder="Search articles..."
                className="w-full pl-12 pr-4 py-3 border border-border rounded-lg bg-surface text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            {/* Category Filter */}
            <div className="flex flex-wrap gap-3">
              {categories.map((cat) => (
                <button
                  key={cat}
                  className={`px-4 py-2 rounded-full font-medium transition-colors ${
                    cat === 'All'
                      ? 'bg-primary text-white'
                      : 'bg-surface border border-border text-text-primary hover:border-primary'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>

          {/* Articles Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {articles.map((article) => (
              <Link
                key={article.id}
                href={`/articles/${article.id}`}
                className="group bg-surface border border-border rounded-xl overflow-hidden hover:shadow-glass transition-all duration-300 hover:border-primary"
              >
                {/* Image */}
                <div className="relative h-48 overflow-hidden bg-surface-hover">
                  <img
                    src={article.image}
                    alt={article.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent" />
                  <span className="absolute top-3 right-3 px-3 py-1 rounded-full bg-primary text-white text-xs font-medium">
                    {article.category}
                  </span>
                </div>

                {/* Content */}
                <div className="p-6 space-y-4">
                  <h2 className="text-lg font-semibold text-text-primary group-hover:text-primary transition-colors">
                    {article.title}
                  </h2>
                  <p className="text-text-secondary text-sm line-clamp-2">{article.excerpt}</p>

                  {/* Meta */}
                  <div className="flex items-center justify-between text-xs text-text-secondary pt-4 border-t border-border">
                    <div className="flex items-center gap-2">
                      <User size={14} />
                      <span>{article.author}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Clock size={14} />
                      <span>{article.readTime}</span>
                    </div>
                  </div>

                  {/* Footer */}
                  <div className="flex items-center justify-between pt-2">
                    <span className="text-xs text-text-secondary">{article.date}</span>
                    <ArrowRight size={16} className="text-primary group-hover:translate-x-1 transition-transform" />
                  </div>
                </div>
              </Link>
            ))}
          </div>

          {/* Load More */}
          <div className="mt-12 text-center">
            <button className="px-8 py-3 rounded-lg border border-primary text-primary hover:bg-primary/5 font-medium transition-colors">
              Load More Articles
            </button>
          </div>
        </div>
      </section>

      {/* Newsletter Section */}
      <section className="bg-surface border-y border-border py-12 md:py-16">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 text-center">
          <h2 className="text-2xl md:text-3xl font-bold text-text-primary mb-4">
            Subscribe to Our Newsletter
          </h2>
          <p className="text-text-secondary mb-6">
            Get weekly tips and resources to improve your English skills
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
