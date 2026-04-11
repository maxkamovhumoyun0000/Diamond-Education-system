import { createClient } from "@/lib/supabase/server";
import Link from "next/link";
import Image from "next/image";

export default async function Home() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (user) {
    return (
      <div className="min-h-screen bg-background">
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center">
            <div className="flex justify-center mb-6">
              <Image
                src="/logo.jpg"
                alt="Diamond Education Logo"
                width={120}
                height={120}
                className="rounded-2xl shadow-lg"
              />
            </div>
            <h1 className="text-4xl font-bold text-primary mb-4">Diamond Education</h1>
            <p className="text-lg text-muted-foreground mb-8">Admin Control Panel</p>
            <p className="text-foreground mb-8">Welcome, {user.email}</p>
            <Link
              href="/dashboard"
              className="inline-block px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-accent transition"
            >
              Go to Dashboard
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#1a3a8f] to-[#0066ff] flex items-center justify-center p-4">
      <div className="bg-background rounded-2xl shadow-2xl p-8 max-w-md w-full">
        <div className="flex justify-center mb-6">
          <Image
            src="/logo.jpg"
            alt="Diamond Education Logo"
            width={100}
            height={100}
            className="rounded-xl shadow-md"
          />
        </div>
        <h1 className="text-3xl font-bold text-primary text-center mb-2">Diamond Education</h1>
        <p className="text-muted-foreground text-center mb-6">Admin Control Panel</p>
        <p className="text-foreground text-center mb-8">Please log in to continue</p>
        <div className="space-y-4">
          <Link
            href="/auth/login"
            className="block w-full text-center px-4 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-accent transition font-medium"
          >
            Sign In
          </Link>
          <Link
            href="/auth/sign-up"
            className="block w-full text-center px-4 py-3 border-2 border-primary text-primary rounded-lg hover:bg-primary hover:text-primary-foreground transition font-medium"
          >
            Create Account
          </Link>
        </div>
      </div>
    </div>
  );
}
