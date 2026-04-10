'use client'

import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { authApi, User, getAuthToken, setAuthToken } from './api'

interface AuthContextType {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (login_id: string, password: string) => Promise<void>
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const refreshUser = async () => {
    try {
      const token = getAuthToken()
      if (!token) {
        setUser(null)
        return
      }
      const userData = await authApi.me()
      setUser(userData)
    } catch (error) {
      setUser(null)
      setAuthToken(null)
    }
  }

  useEffect(() => {
    const initAuth = async () => {
      await refreshUser()
      setIsLoading(false)
    }
    initAuth()
  }, [])

  const login = async (login_id: string, password: string) => {
    const response = await authApi.login(login_id, password)
    setUser(response.user)
  }

  const logout = async () => {
    try {
      await authApi.logout()
    } finally {
      setUser(null)
    }
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

// Helper function to get user role name
export function getUserRole(login_type: number): string {
  switch (login_type) {
    case 1:
      return 'Student'
    case 2:
      return 'Teacher'
    case 3:
      return 'Admin'
    case 4:
      return 'Support Teacher'
    default:
      return 'Unknown'
  }
}

// Check if user is admin or teacher
export function isAdmin(user: User | null): boolean {
  return user?.login_type === 3
}

export function isTeacher(user: User | null): boolean {
  return user?.login_type === 2
}

export function isStudent(user: User | null): boolean {
  return user?.login_type === 1
}

export function canManageContent(user: User | null): boolean {
  return user?.login_type === 2 || user?.login_type === 3
}
