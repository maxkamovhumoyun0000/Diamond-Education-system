import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import Link from "next/link";

export default async function DashboardPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) {
    redirect("/auth/login");
  }

  const stats = [
    {
      label: "Total Users",
      value: "1,248",
      change: "12% from last month",
      changeType: "up",
      changeValue: "12%",
      icon: "users",
      bgColor: "bg-[#e0f2fe]",
      iconColor: "text-[#2563eb]"
    },
    {
      label: "Active Students",
      value: "892",
      change: "8% from last month",
      changeType: "up",
      changeValue: "8%",
      icon: "book",
      bgColor: "bg-[#e0f7fa]",
      iconColor: "text-[#06b6d4]"
    },
    {
      label: "Total Courses",
      value: "156",
      change: "4 new this month",
      changeType: "up",
      changeValue: "2%",
      icon: "courses",
      bgColor: "bg-white",
      iconColor: "text-[#22c55e]"
    },
    {
      label: "Total Revenue",
      value: "$45,230",
      change: "23% from last month",
      changeType: "up",
      changeValue: "23%",
      icon: "dollar",
      bgColor: "bg-white",
      iconColor: "text-[#2563eb]"
    },
  ];

  const alerts = [
    { type: "warning", icon: "clock", title: "3 Inactive Courses", description: "Some courses have no activity" },
    { type: "success", icon: "check", title: "System Status", description: "All systems operational" },
    { type: "error", icon: "alert", title: "Payment Issue", description: "2 payment failures detected" },
  ];

  const recentUsers = [
    { name: "User 1", email: "user1@diamond.edu", role: "Student" },
    { name: "User 2", email: "user2@diamond.edu", role: "Teacher" },
    { name: "User 3", email: "user3@diamond.edu", role: "Student" },
    { name: "User 4", email: "user4@diamond.edu", role: "Support" },
    { name: "User 5", email: "user5@diamond.edu", role: "Student" },
  ];

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Admin Dashboard</h1>
        <p className="text-gray-500">Welcome back! Here&apos;s your system overview.</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {stats.map((stat, index) => (
          <div key={index} className={`${stat.bgColor} rounded-xl p-5 border border-gray-100`}>
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-gray-500">{stat.label}</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">{stat.value}</p>
                <p className="text-xs text-gray-400 mt-1">{stat.change}</p>
              </div>
              <div className={`p-2 rounded-lg ${stat.iconColor}`}>
                {stat.icon === "users" && (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                  </svg>
                )}
                {stat.icon === "book" && (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                  </svg>
                )}
                {stat.icon === "courses" && (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                )}
                {stat.icon === "dollar" && (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                )}
              </div>
            </div>
            {stat.changeType === "up" && (
              <div className="flex items-center gap-1 mt-3">
                <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
                </svg>
                <span className="text-green-500 text-sm font-medium">{stat.changeValue}</span>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Alerts */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {alerts.map((alert, index) => (
          <div
            key={index}
            className={`rounded-xl p-4 border ${
              alert.type === "warning" ? "bg-amber-50 border-amber-100" :
              alert.type === "success" ? "bg-green-50 border-green-100" :
              "bg-red-50 border-red-100"
            }`}
          >
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-full ${
                alert.type === "warning" ? "bg-amber-100 text-amber-600" :
                alert.type === "success" ? "bg-green-100 text-green-600" :
                "bg-red-100 text-red-600"
              }`}>
                {alert.icon === "clock" && (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                )}
                {alert.icon === "check" && (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                )}
                {alert.icon === "alert" && (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                )}
              </div>
              <div>
                <p className={`font-medium ${
                  alert.type === "warning" ? "text-amber-700" :
                  alert.type === "success" ? "text-green-700" :
                  "text-red-700"
                }`}>{alert.title}</p>
                <p className={`text-sm ${
                  alert.type === "warning" ? "text-amber-600" :
                  alert.type === "success" ? "text-green-600" :
                  "text-red-600"
                }`}>{alert.description}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Course Completion */}
        <div className="bg-white rounded-xl p-6 border border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Course Completion</h2>
          <div className="mb-4">
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold text-gray-900">156</span>
              <span className="text-gray-400">of 200</span>
            </div>
            <div className="w-full h-3 bg-gray-100 rounded-full mt-3 overflow-hidden">
              <div className="h-full bg-[#2563eb] rounded-full" style={{ width: "78%" }}></div>
            </div>
            <p className="text-right text-sm text-gray-500 mt-2">78%</p>
          </div>

          <h2 className="text-lg font-semibold text-gray-900 mb-4 mt-6">Student Satisfaction</h2>
          <div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold text-gray-900">92</span>
              <span className="text-gray-400">of 100</span>
            </div>
            <div className="w-full h-3 bg-gray-100 rounded-full mt-3 overflow-hidden">
              <div className="h-full bg-green-500 rounded-full" style={{ width: "92%" }}></div>
            </div>
            <p className="text-right text-sm text-gray-500 mt-2">92%</p>
          </div>
        </div>

        {/* Recent Users */}
        <div className="bg-white rounded-xl p-6 border border-gray-100">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Recent Users</h2>
            <Link href="/dashboard/users" className="text-[#2563eb] text-sm font-medium hover:underline">
              View All
            </Link>
          </div>
          <div className="space-y-3">
            {recentUsers.map((u, index) => (
              <div key={index} className="flex items-center justify-between py-2">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-[#2563eb] flex items-center justify-center text-white font-medium">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">{u.name}</p>
                    <p className="text-sm text-gray-500">{u.email}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-500">{u.role}</span>
                  <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-xl p-6 border border-gray-100 mt-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Link
            href="/dashboard/users"
            className="flex items-center justify-center gap-2 px-4 py-3 bg-[#2563eb] text-white rounded-lg hover:bg-[#1d4ed8] transition font-medium"
          >
            Add User
          </Link>
          <Link
            href="/dashboard/groups"
            className="flex items-center justify-center gap-2 px-4 py-3 bg-[#2563eb] text-white rounded-lg hover:bg-[#1d4ed8] transition font-medium"
          >
            Create Course
          </Link>
          <Link
            href="/dashboard/analytics"
            className="flex items-center justify-center gap-2 px-4 py-3 border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 transition font-medium"
          >
            View Reports
          </Link>
          <Link
            href="/dashboard/settings"
            className="flex items-center justify-center gap-2 px-4 py-3 border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 transition font-medium"
          >
            Settings
          </Link>
        </div>
      </div>
    </div>
  );
}
