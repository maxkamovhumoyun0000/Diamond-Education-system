import type { Metadata, Viewport } from 'next'
import './globals.css'
import { LanguageProvider } from '@/lib/i18n'

export const metadata: Metadata = {
  title: 'Diamond Education System',
  description: 'Premium online learning platform with role-based dashboards',
  icons: {
    icon: '/logo.jpg',
  },
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
  userScalable: true,
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#ffffff' },
    { media: '(prefers-color-scheme: dark)', color: '#1a1f35' },
  ],
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="uz" suppressHydrationWarning data-scroll-behavior="smooth">
      <body className="antialiased">
        <LanguageProvider>
          {children}
        </LanguageProvider>
      </body>
    </html>
  )
}
