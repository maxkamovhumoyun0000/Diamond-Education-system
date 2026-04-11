import { createClient } from "@/lib/supabase/server";
import Link from "next/link";

export default async function Home() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (user) {
    return (
      <div className="min-h-screen bg-background">
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center">
            <h1 className="text-4xl font-bold text-primary mb-4">Diamond Education</h1>
            <p className="text-lg text-muted-foreground mb-8">Admin Control Panel</p>
            <p className="text-foreground mb-8">Welcome, {user.email}</p>
            <Link
              href="/dashboard"
              className="inline-block px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition"
            >
              Go to Dashboard
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary to-accent flex items-center justify-center p-4">
      <div className="bg-background rounded-lg shadow-lg p-8 max-w-md w-full">
        <h1 className="text-3xl font-bold text-primary mb-2">Diamond Education</h1>
        <p className="text-muted-foreground mb-6">Admin Control Panel</p>
        <p className="text-foreground mb-8">Please log in to continue</p>
        <div className="space-y-4">
          <Link
            href="/auth/login"
            className="block w-full text-center px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition"
          >
            Sign In
          </Link>
          <Link
            href="/auth/sign-up"
            className="block w-full text-center px-4 py-2 border-2 border-primary text-primary rounded-lg hover:bg-primary hover:text-primary-foreground transition"
          >
            Create Account
          </Link>
        </div>
      </div>
    </div>
  );
}
