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
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && (!user || user.role !== "student")) {
      router.push("/login");
    }
  }, [user, loading, router]);

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
  }

  if (!user || user.role !== "student") {
    return null;
  }

  return (
    <div className="min-h-screen bg-background">
      <nav className="bg-primary text-primary-foreground shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <Link href="/student" className="text-2xl font-bold">
              Diamond Education
            </Link>
            <div className="flex gap-6">
              <Link href="/student" className="hover:text-secondary transition">
                Dashboard
              </Link>
              <Link href="/student/arena" className="hover:text-secondary transition">
                Arena
              </Link>
              <Link href="/student/tests" className="hover:text-secondary transition">
                Tests
              </Link>
              <Link href="/student/leaderboard" className="hover:text-secondary transition">
                Leaderboard
              </Link>
              <button
                onClick={async () => {
                  const res = await fetch("/api/auth/logout", { method: "POST" });
                  if (res.ok) router.push("/login");
                }}
                className="hover:text-secondary transition"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto px-4 py-8">{children}</main>
    </div>
  );
}
