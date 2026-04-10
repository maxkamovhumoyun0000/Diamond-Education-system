'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth-context'

export default function LoginPage() {
  const router = useRouter()
  const { login, isAuthenticated, user } = useAuth()
  const [loginId, setLoginId] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Redirect if already authenticated
  if (isAuthenticated && user) {
    if (user.login_type === 3 || user.login_type === 2) {
      router.push('/dashboard')
    } else {
      router.push('/student')
    }
    return null
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsSubmitting(true)

    try {
      await login(loginId, password)
      // Redirect is handled in useAuth after successful login
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center diamond-gradient p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 mx-auto rounded-full gold-gradient flex items-center justify-center mb-4 shadow-lg">
            <svg
              className="w-8 h-8 text-[hsl(213,56%,24%)]"
              fill="currentColor"
              viewBox="0 0 24 24"
            >
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
            </svg>
          </div>
          <h1 className="text-2xl font-serif font-bold text-white">
            Diamond Education
          </h1>
          <p className="text-[hsl(43,65%,52%)] text-sm mt-1">
            Sign in to your account
          </p>
        </div>

        {/* Login Card */}
        <div className="card p-6 shadow-xl">
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm">
                {error}
              </div>
            )}

            <div>
              <label htmlFor="loginId" className="block text-sm font-medium mb-1.5">
                Login ID
              </label>
              <input
                id="loginId"
                type="text"
                value={loginId}
                onChange={(e) => setLoginId(e.target.value)}
                className="input"
                placeholder="Enter your login ID"
                required
                disabled={isSubmitting}
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium mb-1.5">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input"
                placeholder="Enter your password"
                required
                disabled={isSubmitting}
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary w-full"
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <span className="flex items-center gap-2">
                  <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Signing in...
                </span>
              ) : (
                'Sign In'
              )}
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-[hsl(var(--border))]">
            <p className="text-sm text-center text-[hsl(var(--muted-foreground))]">
              Need an account?{' '}
              <a href="/register" className="text-[hsl(var(--primary))] hover:underline font-medium">
                Register here
              </a>
            </p>
          </div>
        </div>

        {/* Telegram Link */}
        <div className="mt-6 text-center">
          <p className="text-white/60 text-sm">
            Or use our{' '}
            <a
              href="https://t.me/diamond_education_bot"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[hsl(43,65%,52%)] hover:underline"
            >
              Telegram Bot
            </a>
          </p>
        </div>
      </div>
    </div>
  )
}
