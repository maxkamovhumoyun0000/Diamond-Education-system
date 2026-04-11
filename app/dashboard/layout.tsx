"use client";

import { createClient } from "@/lib/supabase/client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const supabase = createClient();
  const [user, setUser] = useState<{ email?: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const checkUser = async () => {
      const { data } = await supabase.auth.getUser();

      if (!data?.user) {
        router.push("/auth/login");
      } else {
        setUser(data.user);
      }
      setLoading(false);
    };

    checkUser();
  }, [supabase, router]);

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    router.push("/");
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-[#1a3a8f] to-[#0066ff]">
        <div className="text-lg text-white">Loading...</div>
      </div>
    );
  }

  const navItems = [
    { href: "/dashboard", label: "Dashboard" },
    { href: "/dashboard/students", label: "Students" },
    { href: "/dashboard/profiles", label: "User Profiles" },
    { href: "/dashboard/articles", label: "Articles" },
    { href: "/dashboard/dcoin", label: "D'coin System" },
    { href: "/dashboard/messages", label: "Messages" },
    { href: "/dashboard/groups", label: "Groups" },
  ];

  return (
    <div className="min-h-screen bg-muted flex">
      {/* Sidebar */}
      <div className="w-64 bg-gradient-to-b from-[#1a3a8f] to-[#0044cc] text-white p-6 hidden md:flex flex-col">
        <div className="flex items-center gap-3 mb-8">
          <Image
            src="/logo.jpg"
            alt="Diamond Education Logo"
            width={48}
            height={48}
            className="rounded-lg"
          />
          <h1 className="text-xl font-bold">Diamond</h1>
        </div>
        <nav className="space-y-2 flex-1">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="block px-4 py-3 rounded-lg hover:bg-white/10 transition font-medium"
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="pt-4 border-t border-white/20">
          <button
            onClick={handleSignOut}
            className="w-full px-4 py-3 bg-white/10 hover:bg-white/20 rounded-lg transition font-medium text-left"
          >
            Sign Out
          </button>
        </div>
      </div>

      {/* Mobile Sidebar */}
      {menuOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div 
            className="absolute inset-0 bg-black/50"
            onClick={() => setMenuOpen(false)}
          />
          <div className="absolute left-0 top-0 bottom-0 w-64 bg-gradient-to-b from-[#1a3a8f] to-[#0044cc] text-white p-6 flex flex-col">
            <div className="flex items-center gap-3 mb-8">
              <Image
                src="/logo.jpg"
                alt="Diamond Education Logo"
                width={48}
                height={48}
                className="rounded-lg"
              />
              <h1 className="text-xl font-bold">Diamond</h1>
            </div>
            <nav className="space-y-2 flex-1">
              {navItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setMenuOpen(false)}
                  className="block px-4 py-3 rounded-lg hover:bg-white/10 transition font-medium"
                >
                  {item.label}
                </Link>
              ))}
            </nav>
            <div className="pt-4 border-t border-white/20">
              <button
                onClick={handleSignOut}
                className="w-full px-4 py-3 bg-white/10 hover:bg-white/20 rounded-lg transition font-medium text-left"
              >
                Sign Out
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Top Bar */}
        <div className="bg-background border-b border-border px-6 py-4 flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setMenuOpen(true)}
              className="md:hidden p-2 hover:bg-muted rounded-lg transition"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <h2 className="text-lg font-semibold text-foreground">Admin Panel</h2>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-muted-foreground text-sm hidden sm:block">{user?.email}</span>
            <button
              onClick={handleSignOut}
              className="px-4 py-2 bg-destructive text-destructive-foreground rounded-lg hover:opacity-90 transition text-sm font-medium"
            >
              Sign Out
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">{children}</div>
      </div>
    </div>
  );
}
