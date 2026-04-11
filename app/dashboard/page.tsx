import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import Link from "next/link";

export default async function DashboardPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) {
    redirect("/auth/login");
  }

  return (
    <div>
      <h1 className="text-3xl font-bold text-foreground mb-8">Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Stats Cards */}
        <div className="bg-background rounded-xl p-6 shadow-sm border border-border">
          <h3 className="text-muted-foreground text-sm font-medium">Total Students</h3>
          <p className="text-3xl font-bold text-primary mt-2">--</p>
        </div>

        <div className="bg-background rounded-xl p-6 shadow-sm border border-border">
          <h3 className="text-muted-foreground text-sm font-medium">Active Groups</h3>
          <p className="text-3xl font-bold text-primary mt-2">--</p>
        </div>

        <div className="bg-background rounded-xl p-6 shadow-sm border border-border">
          <h3 className="text-muted-foreground text-sm font-medium">Published Articles</h3>
          <p className="text-3xl font-bold text-primary mt-2">--</p>
        </div>

        <div className="bg-background rounded-xl p-6 shadow-sm border border-border">
          <h3 className="text-muted-foreground text-sm font-medium">D&apos;coin Transactions</h3>
          <p className="text-3xl font-bold text-primary mt-2">--</p>
        </div>
      </div>

      <div className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Quick Actions */}
        <div className="bg-background rounded-xl p-6 shadow-sm border border-border">
          <h2 className="text-xl font-bold text-foreground mb-4">Quick Actions</h2>
          <div className="space-y-3">
            <Link
              href="/dashboard/students"
              className="block px-4 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-accent transition text-center font-medium"
            >
              Add New Student
            </Link>
            <Link
              href="/dashboard/articles"
              className="block px-4 py-3 bg-secondary text-secondary-foreground rounded-lg hover:opacity-90 transition text-center font-medium"
            >
              Create Article
            </Link>
            <Link
              href="/dashboard/groups"
              className="block px-4 py-3 border-2 border-primary text-primary rounded-lg hover:bg-primary hover:text-primary-foreground transition text-center font-medium"
            >
              Create Group
            </Link>
          </div>
        </div>

        {/* System Info */}
        <div className="bg-background rounded-xl p-6 shadow-sm border border-border">
          <h2 className="text-xl font-bold text-foreground mb-4">System Information</h2>
          <div className="space-y-4">
            <div className="flex justify-between items-center py-2 border-b border-border">
              <span className="text-muted-foreground">User</span>
              <span className="text-foreground font-medium">{user.email}</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-border">
              <span className="text-muted-foreground">Role</span>
              <span className="text-foreground font-medium">
                {user.user_metadata?.role || "User"}
              </span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-muted-foreground">Status</span>
              <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm font-medium">
                Active
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
