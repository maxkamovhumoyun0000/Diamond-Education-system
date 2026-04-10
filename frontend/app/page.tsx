'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth-context'
import { healthApi } from '@/lib/api'

export default function HomePage() {
  const router = useRouter()
  const { user, isLoading, isAuthenticated } = useAuth()
  const [backendStatus, setBackendStatus] = useState<string>('checking...')

  useEffect(() => {
    healthApi.check()
      .then((data) => setBackendStatus(data.status))
      .catch(() => setBackendStatus('offline'))
  }, [])

  useEffect(() => {
    if (!isLoading) {
      if (isAuthenticated) {
        // Redirect based on role
        if (user?.login_type === 3 || user?.login_type === 2) {
          router.push('/dashboard')
        } else {
          router.push('/student')
        }
      } else {
        router.push('/login')
      }
    }
  }, [isLoading, isAuthenticated, user, router])

  return (
    <div className="min-h-screen flex items-center justify-center diamond-gradient">
      <div className="text-center">
        {/* Logo */}
        <div className="mb-8">
          <div className="w-20 h-20 mx-auto rounded-full gold-gradient flex items-center justify-center mb-4 shadow-lg">
            <svg
              className="w-10 h-10 text-[hsl(213,56%,24%)]"
              fill="currentColor"
              viewBox="0 0 24 24"
            >
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
            </svg>
          </div>
          <h1 className="text-3xl font-serif font-bold text-white mb-2">
            Diamond Education
          </h1>
          <p className="text-[hsl(43,65%,52%)]">
            Premium Language Learning
          </p>
        </div>

        {/* Loading State */}
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-3 border-white/30 border-t-white rounded-full animate-spin" />
          <p className="text-white/80 text-sm">
            {isLoading ? 'Loading...' : 'Redirecting...'}
          </p>
        </div>

        {/* Backend Status */}
        <div className="mt-8 text-xs text-white/50">
          Backend: {backendStatus === 'ok' ? (
            <span className="text-green-400">Online</span>
          ) : backendStatus === 'offline' ? (
            <span className="text-red-400">Offline</span>
          ) : (
            <span className="text-yellow-400">{backendStatus}</span>
          )}
        </div>
      </div>
    </div>
  )
}
