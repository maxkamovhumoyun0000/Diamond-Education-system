'use client'

import Image from 'next/image'
import Link from 'next/link'
import { Menu, X, LogOut, User } from 'lucide-react'
import { useState } from 'react'

interface NavbarProps {
  userRole?: string
  userName?: string
  onLogout?: () => void
  onMenuToggle?: (open: boolean) => void
}

export default function Navbar({
  userRole,
  userName,
  onLogout,
  onMenuToggle,
}: NavbarProps) {
  const [isMenuOpen, setIsMenuOpen] = useState(false)

  const toggleMenu = () => {
    setIsMenuOpen(!isMenuOpen)
    onMenuToggle?.(!isMenuOpen)
  }

  return (
    <nav className="sticky top-0 z-50 bg-surface border-b border-border shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-3 flex-shrink-0 hover:opacity-80 transition-opacity">
            <div className="relative w-10 h-10 rounded-full overflow-hidden bg-primary flex items-center justify-center">
              <Image
                src="/logo.jpg"
                alt="Diamond Education"
                width={40}
                height={40}
                className="object-cover"
              />
            </div>
            <div className="hidden sm:block">
              <h1 className="text-lg font-bold text-primary">Diamond</h1>
              <p className="text-xs text-text-secondary">Education</p>
            </div>
          </Link>

          {/* Desktop Menu */}
          <div className="hidden md:flex items-center gap-8">
            <Link
              href="/articles"
              className="text-text-primary hover:text-primary transition-colors font-medium text-sm"
            >
              Articles
            </Link>
            {userRole && (
              <>
                <Link
                  href={`/dashboard/${userRole}`}
                  className="text-text-primary hover:text-primary transition-colors font-medium text-sm"
                >
                  Dashboard
                </Link>
                <div className="flex items-center gap-4 pl-4 border-l border-border">
                  <div className="text-right">
                    <p className="text-sm font-medium text-text-primary">{userName}</p>
                    <p className="text-xs text-text-secondary capitalize">{userRole}</p>
                  </div>
                  <button
                    onClick={onLogout}
                    className="p-2 hover:bg-surface-hover rounded-lg transition-colors text-text-secondary hover:text-primary"
                    title="Logout"
                  >
                    <LogOut size={20} />
                  </button>
                </div>
              </>
            )}
            {!userRole && (
              <Link
                href="/login"
                className="px-4 py-2 rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors font-medium"
              >
                Login
              </Link>
            )}
          </div>

          {/* Mobile Menu Button */}
          <button
            onClick={toggleMenu}
            className="md:hidden p-2 hover:bg-surface-hover rounded-lg transition-colors text-text-primary"
          >
            {isMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>

        {/* Mobile Menu */}
        {isMenuOpen && (
          <div className="md:hidden border-t border-border py-4 space-y-3">
            <Link
              href="/articles"
              className="block px-4 py-2 text-text-primary hover:bg-surface-hover rounded-lg transition-colors"
            >
              Articles
            </Link>
            {userRole ? (
              <>
                <Link
                  href={`/dashboard/${userRole}`}
                  className="block px-4 py-2 text-text-primary hover:bg-surface-hover rounded-lg transition-colors"
                >
                  Dashboard
                </Link>
                <div className="px-4 py-3 border-t border-border flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-text-primary">{userName}</p>
                    <p className="text-xs text-text-secondary capitalize">{userRole}</p>
                  </div>
                  <button
                    onClick={onLogout}
                    className="p-2 hover:bg-surface-hover rounded-lg transition-colors text-text-secondary hover:text-primary"
                  >
                    <LogOut size={20} />
                  </button>
                </div>
              </>
            ) : (
              <Link
                href="/login"
                className="block px-4 py-2 rounded-lg bg-primary text-white text-center hover:bg-primary-dark transition-colors font-medium"
              >
                Login
              </Link>
            )}
          </div>
        )}
      </div>
    </nav>
  )
}
