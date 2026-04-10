"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function StudentLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, isLoading, isAuthenticated, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [user, isLoading, isAuthenticated, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center diamond-gradient">
        <div className="w-8 h-8 border-3 border-white/30 border-t-white rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return null;
  }

  const handleLogout = async () => {
    await logout();
    router.push("/login");
  };

  return (
    <div className="min-h-screen bg-[hsl(var(--background))]">
      {/* Top Navigation */}
      <nav className="diamond-gradient text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex justify-between items-center h-16">
            <Link href="/student" className="flex items-center gap-2 font-serif font-bold text-xl">
              <div className="w-8 h-8 rounded gold-gradient flex items-center justify-center">
                <svg className="w-4 h-4 text-[hsl(213,56%,24%)]" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
                </svg>
              </div>
              Diamond Education
            </Link>
            <div className="flex items-center gap-6">
              <Link href="/student" className="hover:text-[hsl(43,65%,52%)] transition">
                Dashboard
              </Link>
              <button
                onClick={handleLogout}
                className="hover:text-[hsl(43,65%,52%)] transition"
              >
                Chiqish
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        {children}
      </main>
    </div>
  );
}
