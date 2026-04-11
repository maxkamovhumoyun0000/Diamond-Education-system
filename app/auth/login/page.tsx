"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const supabase = createClient();

    try {
      const { error: signInError } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (signInError) {
        setError(signInError.message);
      } else {
        router.push("/dashboard");
        router.refresh();
      }
    } catch {
      setError("An unexpected error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#f8fafc] flex">
      {/* Left Side - Form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          <div className="flex items-center gap-3 mb-8">
            <Image
              src="/logo.jpg"
              alt="Diamond Education Logo"
              width={48}
              height={48}
              className="rounded-lg"
            />
            <div>
              <h1 className="text-xl font-bold text-[#2563eb]">Diamond</h1>
              <p className="text-xs text-gray-500">Education</p>
            </div>
          </div>

          <h2 className="text-2xl font-bold text-gray-900 mb-2">Kirish</h2>
          <p className="text-gray-500 mb-8">Hisobingizga kirish uchun ma&apos;lumotlaringizni kiriting</p>

          <form onSubmit={handleSignIn} className="space-y-5">
            {error && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">
                {error}
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb] focus:border-transparent"
                placeholder="you@example.com"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Parol
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb] focus:border-transparent"
                placeholder="Parolingizni kiriting"
                required
              />
            </div>

            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2">
                <input type="checkbox" className="rounded border-gray-300 text-[#2563eb] focus:ring-[#2563eb]" />
                <span className="text-sm text-gray-600">Meni eslab qol</span>
              </label>
              <Link href="/auth/forgot-password" className="text-sm text-[#2563eb] hover:underline">
                Parolni unutdingizmi?
              </Link>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full px-4 py-3 bg-[#2563eb] text-white rounded-lg hover:bg-[#1d4ed8] transition disabled:opacity-50 font-medium"
            >
              {loading ? "Kirilmoqda..." : "Kirish"}
            </button>
          </form>

          <p className="text-center text-gray-500 mt-6">
            Hisobingiz yo&apos;qmi?{" "}
            <Link href="/auth/sign-up" className="text-[#2563eb] hover:underline font-medium">
              Ro&apos;yxatdan o&apos;tish
            </Link>
          </p>
        </div>
      </div>

      {/* Right Side - Gradient */}
      <div className="hidden lg:flex flex-1 bg-gradient-to-br from-[#1a3a8f] to-[#0066ff] items-center justify-center p-8">
        <div className="text-center text-white">
          <Image
            src="/logo.jpg"
            alt="Diamond Education Logo"
            width={120}
            height={120}
            className="rounded-2xl shadow-2xl mx-auto mb-8"
          />
          <h2 className="text-3xl font-bold mb-4">Diamond Education</h2>
          <p className="text-white/80 max-w-md">
            Premium ta&apos;lim platformasi. O&apos;zingizning bilimlaringizni kengaytiring va yangi imkoniyatlarga ega bo&apos;ling.
          </p>
        </div>
      </div>
    </div>
  );
}
