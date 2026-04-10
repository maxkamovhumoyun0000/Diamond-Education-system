'use client'

import { useState } from 'react'
import Navbar from './Navbar'
import Sidebar from './Sidebar'

interface DashboardLayoutProps {
  children: React.ReactNode
  role: 'admin' | 'student' | 'teacher' | 'support'
  userName?: string
}

export default function DashboardLayout({
  children,
  role,
  userName = 'User',
}: DashboardLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const handleLogout = () => {
    // TODO: Implement actual logout
    console.log('Logout clicked')
  }

  return (
    <div className="flex flex-col min-h-screen bg-background">
      <Navbar
        userRole={role}
        userName={userName}
        onLogout={handleLogout}
        onMenuToggle={setSidebarOpen}
      />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar role={role} isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
