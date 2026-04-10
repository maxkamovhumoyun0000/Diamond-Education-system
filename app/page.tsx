'use client'

import Link from 'next/link'
import Image from 'next/image'
import Navbar from '@/components/Navbar'
import DiamondAIChat from '@/components/DiamondAIChat'
import { ArrowRight, Sparkles, Users, BookOpen, Trophy } from 'lucide-react'

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-surface">
      <Navbar />
      <DiamondAIChat userRole="student" />

      {/* Hero Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 md:py-32">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          {/* Left Content */}
          <div className="space-y-8">
            <div className="space-y-4">
              <h1 className="text-5xl md:text-6xl font-bold text-text-primary leading-tight">
                Learn Brilliantly with <span className="text-primary">Diamond</span>
              </h1>
              <p className="text-xl text-text-secondary leading-relaxed">
                Experience a premium online learning platform designed for excellence. Master English, build confidence, and unlock your potential with our world-class educators.
              </p>
            </div>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row gap-4">
              <Link
                href="/login"
                className="inline-flex items-center justify-center px-8 py-3 rounded-lg bg-primary text-white font-semibold hover:bg-primary-dark transition-colors"
              >
                Get Started
                <ArrowRight className="ml-2" size={20} />
              </Link>
              <Link
                href="/articles"
                className="inline-flex items-center justify-center px-8 py-3 rounded-lg border-2 border-primary text-primary font-semibold hover:bg-primary/5 transition-colors"
              >
                Learn More
              </Link>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-3 gap-4 pt-8 border-t border-border">
              <div>
                <p className="text-3xl font-bold text-primary">1.2K+</p>
                <p className="text-sm text-text-secondary">Active Students</p>
              </div>
              <div>
                <p className="text-3xl font-bold text-accent">156+</p>
                <p className="text-sm text-text-secondary">Courses</p>
              </div>
              <div>
                <p className="text-3xl font-bold text-green-500">4.8★</p>
                <p className="text-sm text-text-secondary">Avg Rating</p>
              </div>
            </div>
          </div>

          {/* Right Image */}
          <div className="flex items-center justify-center">
            <div className="relative w-full max-w-md aspect-square rounded-2xl overflow-hidden bg-gradient-to-br from-primary to-primary-dark p-8 flex items-center justify-center">
              <Image
                src="/logo.jpg"
                alt="Diamond Logo"
                width={300}
                height={300}
                className="object-contain drop-shadow-lg"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="bg-surface border-t border-border py-20 md:py-32">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-5xl font-bold text-text-primary mb-4">Why Choose Diamond?</h2>
            <p className="text-xl text-text-secondary">Everything you need for exceptional learning outcomes</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {[
              {
                icon: <Users className="w-8 h-8" />,
                title: 'Expert Teachers',
                description: 'Learn from certified, experienced English educators worldwide',
              },
              {
                icon: <BookOpen className="w-8 h-8" />,
                title: 'Rich Curriculum',
                description: 'Comprehensive courses from basics to advanced proficiency',
              },
              {
                icon: <Trophy className="w-8 h-8" />,
                title: 'Gamification',
                description: 'Earn D\'Coins, climb leaderboards, and unlock achievements',
              },
              {
                icon: <Sparkles className="w-8 h-8" />,
                title: 'AI-Powered',
                description: 'Smart learning recommendations tailored to your progress',
              },
            ].map((feature, i) => (
              <div
                key={i}
                className="p-8 rounded-xl border border-border bg-surface hover:shadow-glass transition-all duration-300 group"
              >
                <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center text-primary group-hover:bg-primary group-hover:text-white transition-colors mb-4">
                  {feature.icon}
                </div>
                <h3 className="text-lg font-semibold text-text-primary mb-2">{feature.title}</h3>
                <p className="text-text-secondary">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* User Roles Section */}
      <section className="py-20 md:py-32">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-5xl font-bold text-text-primary mb-4">For Everyone</h2>
            <p className="text-xl text-text-secondary">Tailored experiences for different user roles</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              {
                role: 'Students',
                description: 'Interactive lessons, track progress, earn rewards, play games, and connect with peers',
              },
              {
                role: 'Teachers',
                description: 'Create groups, manage students, track attendance, create tests, analyze progress',
              },
              {
                role: 'Administrators',
                description: 'Manage users, monitor analytics, handle payments, create content, generate reports',
              },
              {
                role: 'Support Staff',
                description: 'Schedule lessons, manage bookings, handle inquiries, coordinate with teachers',
              },
            ].map((item, i) => (
              <div
                key={i}
                className="p-6 rounded-xl border border-border bg-surface hover:border-primary transition-all duration-300"
              >
                <h3 className="text-xl font-semibold text-text-primary mb-3">{item.role}</h3>
                <p className="text-text-secondary text-sm leading-relaxed">{item.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="bg-primary text-white py-16 md:py-24">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-4xl md:text-5xl font-bold mb-6">Ready to Start Learning?</h2>
          <p className="text-lg text-white/80 mb-8 max-w-2xl mx-auto">
            Join thousands of successful learners who have transformed their English skills with Diamond Education.
          </p>
          <Link
            href="/login"
            className="inline-flex items-center justify-center px-8 py-3 rounded-lg bg-white text-primary font-semibold hover:bg-gray-100 transition-colors"
          >
            Start Your Journey
            <ArrowRight className="ml-2" size={20} />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-surface border-t border-border py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center">
                  <Image src="/logo.jpg" alt="Diamond" width={20} height={20} />
                </div>
                <span className="font-bold text-text-primary">Diamond</span>
              </div>
              <p className="text-sm text-text-secondary">Premium online learning platform</p>
            </div>
            <div>
              <h4 className="font-semibold text-text-primary mb-4">Product</h4>
              <ul className="space-y-2 text-sm text-text-secondary">
                <li><Link href="#" className="hover:text-primary transition-colors">Features</Link></li>
                <li><Link href="#" className="hover:text-primary transition-colors">Pricing</Link></li>
                <li><Link href="#" className="hover:text-primary transition-colors">Security</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-text-primary mb-4">Company</h4>
              <ul className="space-y-2 text-sm text-text-secondary">
                <li><Link href="#" className="hover:text-primary transition-colors">About</Link></li>
                <li><Link href="#" className="hover:text-primary transition-colors">Blog</Link></li>
                <li><Link href="#" className="hover:text-primary transition-colors">Contact</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-text-primary mb-4">Legal</h4>
              <ul className="space-y-2 text-sm text-text-secondary">
                <li><Link href="#" className="hover:text-primary transition-colors">Privacy</Link></li>
                <li><Link href="#" className="hover:text-primary transition-colors">Terms</Link></li>
                <li><Link href="#" className="hover:text-primary transition-colors">Cookies</Link></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-border pt-8 text-center text-sm text-text-secondary">
            <p>&copy; 2024 Diamond Education System. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
