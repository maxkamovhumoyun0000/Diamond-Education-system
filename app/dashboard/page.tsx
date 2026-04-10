import { createClient } from "@/lib/supabase/server";

export default async function DashboardPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">Not authenticated</p>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-4xl font-bold text-primary mb-8">Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Stats Cards */}
        <div className="bg-background border border-muted rounded-lg p-6">
          <h3 className="text-muted-foreground text-sm font-medium">Total Students</h3>
          <p className="text-3xl font-bold text-primary mt-2">--</p>
        </div>

        <div className="bg-background border border-muted rounded-lg p-6">
          <h3 className="text-muted-foreground text-sm font-medium">Active Groups</h3>
          <p className="text-3xl font-bold text-secondary mt-2">--</p>
        </div>

        <div className="bg-background border border-muted rounded-lg p-6">
          <h3 className="text-muted-foreground text-sm font-medium">Published Articles</h3>
          <p className="text-3xl font-bold text-accent mt-2">--</p>
        </div>

        <div className="bg-background border border-muted rounded-lg p-6">
          <h3 className="text-muted-foreground text-sm font-medium">D&apos;coin Transactions</h3>
          <p className="text-3xl font-bold text-primary mt-2">--</p>
        </div>
      </div>

      <div className="mt-12 grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Quick Actions */}
        <div className="bg-background border border-muted rounded-lg p-6">
          <h2 className="text-xl font-bold text-foreground mb-4">Quick Actions</h2>
          <div className="space-y-2">
            <a
              href="/dashboard/students"
              className="block px-4 py-3 bg-primary text-primary-foreground rounded hover:opacity-90 transition text-center"
            >
              Add New Student
            </a>
            <a
              href="/dashboard/articles"
              className="block px-4 py-3 bg-secondary text-secondary-foreground rounded hover:opacity-90 transition text-center"
            >
              Create Article
            </a>
            <a
              href="/dashboard/groups"
              className="block px-4 py-3 bg-accent text-accent-foreground rounded hover:opacity-90 transition text-center"
            >
              Create Group
            </a>
          </div>
        </div>

        {/* System Info */}
        <div className="bg-background border border-muted rounded-lg p-6">
          <h2 className="text-xl font-bold text-foreground mb-4">System Information</h2>
          <div className="space-y-3 text-sm">
            <div>
              <span className="text-muted-foreground">User:</span>
              <span className="ml-2 text-foreground">{user.email}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Role:</span>
              <span className="ml-2 text-foreground">
                {user.user_metadata?.role || "User"}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground">Status:</span>
              <span className="ml-2 text-green-600">Active</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
