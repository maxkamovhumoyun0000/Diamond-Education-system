import { createClient } from "@/lib/supabase/server";
import Link from "next/link";
import Image from "next/image";
import { redirect } from "next/navigation";

export default async function Home() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (user) {
    redirect("/dashboard");
  }

  const articles = [
    { id: 1, title: "10 Tips to Improve Your English Speaking Skills", category: "Speaking", author: "Sarah Johnson", readTime: "8 min", date: "Mar 15, 2024" },
    { id: 2, title: "Mastering English Grammar: A Beginner's Guide", category: "Grammar", author: "Ahmed Ali", readTime: "12 min", date: "Mar 10, 2024" },
    { id: 3, title: "Vocabulary Building: From Beginner to Advanced", category: "Vocabulary", author: "Fatima Khan", readTime: "10 min", date: "Mar 5, 2024" },
  ];

  return (
    <div className="min-h-screen bg-[#f8fafc]">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Image
              src="/logo.jpg"
              alt="Diamond Education Logo"
              width={40}
              height={40}
              className="rounded-lg"
            />
            <div>
              <h1 className="text-lg font-bold text-[#2563eb]">Diamond</h1>
              <p className="text-xs text-gray-500">Education</p>
            </div>
          </div>
          <nav className="flex items-center gap-6">
            <Link href="/articles" className="text-gray-600 hover:text-[#2563eb] text-sm font-medium">
              Maqolalar
            </Link>
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
              </svg>
              <span>O&apos;zbekcha</span>
            </div>
            <Link
              href="/auth/login"
              className="px-4 py-2 bg-[#2563eb] text-white rounded-lg hover:bg-[#1d4ed8] transition text-sm font-medium"
            >
              Kirish
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <section className="bg-gradient-to-br from-[#1a3a8f] to-[#0066ff] text-white py-20">
        <div className="max-w-7xl mx-auto px-4">
          <h1 className="text-4xl font-bold mb-4">Learning Resources</h1>
          <p className="text-white/80 text-lg">Read our latest articles, tips, and guides to improve your English skills</p>
        </div>
      </section>

      {/* Search and Filter */}
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="relative mb-6">
          <svg className="w-5 h-5 text-gray-400 absolute left-4 top-1/2 -translate-y-1/2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            placeholder="Search articles..."
            className="w-full pl-12 pr-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb] focus:border-transparent bg-white"
          />
        </div>

        {/* Category Tabs */}
        <div className="flex flex-wrap gap-2 mb-8">
          {["All", "Speaking", "Grammar", "Vocabulary", "Idioms", "Listening", "Business"].map((cat, index) => (
            <button
              key={cat}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
                index === 0
                  ? "bg-[#2563eb] text-white"
                  : "bg-white border border-gray-200 text-gray-600 hover:bg-gray-50"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Articles Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {articles.map((article) => (
            <div key={article.id} className="bg-white rounded-xl overflow-hidden border border-gray-100 hover:shadow-lg transition">
              <div className="h-48 bg-gradient-to-br from-gray-100 to-gray-200 relative">
                <span className="absolute top-4 right-4 px-3 py-1 bg-[#2563eb] text-white text-xs font-medium rounded-full">
                  {article.category}
                </span>
              </div>
              <div className="p-5">
                <h3 className="font-semibold text-gray-900 mb-2 line-clamp-2">{article.title}</h3>
                <p className="text-sm text-gray-500 mb-4 line-clamp-2">
                  Learn practical techniques to enhance your fluency and confidence in English conversations.
                </p>
                <div className="flex items-center justify-between text-sm text-gray-400 pt-4 border-t border-gray-100">
                  <div className="flex items-center gap-2">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                    <span>{article.author}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>{article.readTime}</span>
                  </div>
                </div>
                <div className="flex items-center justify-between mt-4">
                  <span className="text-xs text-gray-400">{article.date}</span>
                  <Link href={`/articles/${article.id}`} className="text-[#2563eb] hover:underline text-sm font-medium flex items-center gap-1">
                    Read more
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
