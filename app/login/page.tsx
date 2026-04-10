'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import Navbar from '@/components/Navbar'
import { Eye, EyeOff, Mail, Lock } from 'lucide-react'

export default function LoginPage() {
  const router = useRouter()
  const [showPassword, setShowPassword] = useState(false)
  const [role, setRole] = useState<'student' | 'teacher' | 'admin' | 'support'>('student')
  const [formData, setFormData] = useState({
    email: '',
    password: '',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }))
    setError('')
  }

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      // Simulate login - in production, this would call an API
      await new Promise(resolve => setTimeout(resolve, 1000))

      // Demo credentials
      const demoUsers: Record<string, { password: string; name: string }> = {
        'admin@diamond.edu': { password: 'admin123', name: 'Admin' },
        'student@diamond.edu': { password: 'student123', name: 'Ahmed' },
        'teacher@diamond.edu': { password: 'teacher123', name: 'Fatima' },
        'support@diamond.edu': { password: 'support123', name: 'Support Staff' },
      }

      const user = demoUsers[formData.email]
      if (user && user.password === formData.password) {
        // Store session (in production, use secure cookies)
        localStorage.setItem('userRole', role)
        localStorage.setItem('userName', user.name)
        localStorage.setItem('userEmail', formData.email)
        
        router.push(`/dashboard/${role}`)
      } else {
        setError('Invalid email or password. Try admin@diamond.edu / admin123')
      }
    } catch (err) {
      setError('An error occurred. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-surface">
      <Navbar />

      <div className="flex items-center justify-center min-h-[calc(100vh-64px)] px-4 py-12">
        <div className="w-full max-w-md">
          {/* Logo */}
          <div className="flex justify-center mb-8">
            <div className="relative w-16 h-16 rounded-full overflow-hidden bg-primary flex items-center justify-center">
              <Image
                src="/logo.jpg"
                alt="Diamond Education"
                width={64}
                height={64}
                className="object-cover"
              />
            </div>
          </div>

          {/* Card */}
          <div className="bg-surface border border-border rounded-2xl p-8 shadow-lg">
            <div className="text-center mb-8">
              <h1 className="text-3xl font-bold text-text-primary mb-2">Welcome Back</h1>
              <p className="text-text-secondary">Sign in to your Diamond account</p>
            </div>

            {/* Role Selection */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-text-primary mb-3">
                Select Your Role
              </label>
              <div className="grid grid-cols-2 gap-3">
                {(['student', 'teacher', 'admin', 'support'] as const).map((r) => (
                  <button
                    key={r}
                    onClick={() => setRole(r)}
                    className={`py-2 px-3 rounded-lg font-medium transition-all capitalize ${
                      role === r
                        ? 'bg-primary text-white'
                        : 'bg-surface-hover text-text-primary hover:border-primary border border-border'
                    }`}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </div>

            {/* Form */}
            <form onSubmit={handleLogin} className="space-y-4">
              {/* Email Field */}
              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary" size={20} />
                  <input
                    type="email"
                    name="email"
                    placeholder="admin@diamond.edu"
                    value={formData.email}
                    onChange={handleInputChange}
                    className="w-full pl-10 pr-4 py-3 border border-border rounded-lg bg-surface-hover text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary transition-all"
                    required
                  />
                </div>
              </div>

              {/* Password Field */}
              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary" size={20} />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    name="password"
                    placeholder="••••••••"
                    value={formData.password}
                    onChange={handleInputChange}
                    className="w-full pl-10 pr-10 py-3 border border-border rounded-lg bg-surface-hover text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary transition-all"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-text-secondary hover:text-text-primary transition-colors"
                  >
                    {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                  </button>
                </div>
              </div>

              {/* Error Message */}
              {error && (
                <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-600 text-sm">
                  {error}
                </div>
              )}

              {/* Demo Credentials */}
              <div className="p-3 rounded-lg bg-accent/10 border border-accent/20 text-accent text-sm">
                <p className="font-medium mb-1">Demo Credentials:</p>
                <p>Admin: admin@diamond.edu / admin123</p>
                <p>Student: student@diamond.edu / student123</p>
                <p>Teacher: teacher@diamond.edu / teacher123</p>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 px-4 rounded-lg bg-primary text-white font-semibold hover:bg-primary-dark transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Signing in...' : 'Sign In'}
              </button>
            </form>

            {/* Footer */}
            <div className="mt-6 text-center text-sm text-text-secondary">
              <p>
                Don&apos;t have an account?{' '}
                <Link href="#" className="text-primary hover:underline font-medium">
                  Sign up
                </Link>
              </p>
            </div>
          </div>

          {/* Back to Home */}
          <div className="mt-6 text-center">
            <Link
              href="/"
              className="text-primary hover:underline font-medium text-sm"
            >
              ← Back to home
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
