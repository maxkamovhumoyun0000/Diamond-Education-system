"use client";

import { createClient } from "@/lib/supabase/client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const supabase = createClient();
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const checkUser = async () => {
      const {
        data: { user },
      } = await supabase.auth.getUser();

      if (!user) {
        router.push("/auth/login");
      } else {
        setUser(user);
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
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="text-lg text-muted-foreground">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex">
      {/* Sidebar */}
      <div className="w-64 bg-primary text-primary-foreground p-6 hidden md:block">
        <h1 className="text-2xl font-bold mb-8">Diamond</h1>
        <nav className="space-y-4">
          <a
            href="/dashboard"
            className="block px-4 py-2 rounded hover:bg-primary-foreground hover:text-primary transition"
          >
            Dashboard
          </a>
          <a
            href="/dashboard/students"
            className="block px-4 py-2 rounded hover:bg-primary-foreground hover:text-primary transition"
          >
            Students
          </a>
          <a
            href="/dashboard/profiles"
            className="block px-4 py-2 rounded hover:bg-primary-foreground hover:text-primary transition"
          >
            User Profiles
          </a>
          <a
            href="/dashboard/articles"
            className="block px-4 py-2 rounded hover:bg-primary-foreground hover:text-primary transition"
          >
            Articles
          </a>
          <a
            href="/dashboard/dcoin"
            className="block px-4 py-2 rounded hover:bg-primary-foreground hover:text-primary transition"
          >
            D&apos;coin System
          </a>
          <a
            href="/dashboard/messages"
            className="block px-4 py-2 rounded hover:bg-primary-foreground hover:text-primary transition"
          >
            Messages
          </a>
          <a
            href="/dashboard/groups"
            className="block px-4 py-2 rounded hover:bg-primary-foreground hover:text-primary transition"
          >
            Groups
          </a>
        </nav>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Top Bar */}
        <div className="bg-background border-b border-muted px-6 py-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-foreground">Admin Panel</h2>
          <div className="flex items-center gap-4">
            <span className="text-muted-foreground text-sm">{user?.email}</span>
            <button
              onClick={handleSignOut}
              className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition"
            >
              Sign Out
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">{children}</div>
      </div>

      {/* Mobile Menu Button */}
      <button
        onClick={() => setMenuOpen(!menuOpen)}
        className="fixed bottom-4 right-4 md:hidden p-2 bg-primary text-primary-foreground rounded-lg z-50"
      >
        ☰
      </button>
    </div>
  );
}
