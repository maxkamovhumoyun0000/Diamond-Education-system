"use client";

import { useState } from "react";

export default function AnalyticsPage() {
  const [timeRange, setTimeRange] = useState("Last 30 Days");

  const stats = [
    { label: "User Growth", value: "12%", change: "vs last month", bgColor: "bg-[#e0f2fe]", icon: "users", iconColor: "text-[#2563eb]" },
    { label: "Course Engagement", value: "78%", change: "Completion rate", bgColor: "bg-[#e0f7fa]", icon: "book", iconColor: "text-[#06b6d4]" },
    { label: "Revenue Growth", value: "23%", change: "vs last month", bgColor: "bg-white", icon: "dollar", iconColor: "text-green-500" },
    { label: "Active Sessions", value: "234", change: "Right now", bgColor: "bg-white", icon: "chart", iconColor: "text-[#2563eb]" },
  ];

  const revenueBreakdown = [
    { label: "Subscriptions", value: "$28,500", width: "100%" },
    { label: "One-time Courses", value: "$8,750", width: "30%" },
    { label: "Paid Lessons", value: "$4,375", width: "15%" },
    { label: "Premium Features", value: "$2,185", width: "8%" },
  ];

  const topCourses = [
    { rank: 1, name: "English Fundamentals", enrolled: "245 enrolled", rating: 4.8 },
    { rank: 2, name: "Business English", enrolled: "189 enrolled", rating: 4.7 },
    { rank: 3, name: "Speaking Mastery", enrolled: "167 enrolled", rating: 4.9 },
    { rank: 4, name: "IELTS Preparation", enrolled: "156 enrolled", rating: 4.6 },
  ];

  const userDistribution = [
    { label: "Students", count: 892, color: "bg-[#2563eb]" },
    { label: "Teachers", count: 234, color: "bg-[#06b6d4]" },
    { label: "Support Staff", count: 45, color: "bg-green-500" },
    { label: "Admins", count: 12, color: "bg-orange-500" },
  ];

  const engagementStats = [
    { label: "Daily Active Users", value: "234", change: "5%" },
    { label: "Weekly Active Users", value: "892", change: "8%" },
    { label: "Monthly Active Users", value: "1,248", change: "12%" },
    { label: "Lesson Completion Rate", value: "78%", change: "3%" },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analytics & Reports</h1>
          <p className="text-gray-500">System-wide performance metrics and insights</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            className="px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb] bg-white"
          >
            <option>Last 7 Days</option>
            <option>Last 30 Days</option>
            <option>Last 90 Days</option>
            <option>Last Year</option>
          </select>
          <button className="flex items-center gap-2 px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 transition">
            <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Export
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {stats.map((stat, index) => (
          <div key={index} className={`${stat.bgColor} rounded-xl p-5 border border-gray-100`}>
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-gray-500">{stat.label}</p>
                <div className="flex items-baseline gap-1 mt-1">
                  <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
                  </svg>
                  <span className="text-2xl font-bold text-gray-900">{stat.value}</span>
                </div>
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
                {stat.icon === "dollar" && (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                )}
                {stat.icon === "chart" && (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                  </svg>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* User Growth Trend */}
        <div className="bg-white rounded-xl p-6 border border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">User Growth Trend</h2>
          <div className="h-48 flex items-end justify-between gap-2 px-4">
            {[40, 55, 45, 60, 75, 65, 80, 70, 85, 90, 95, 100].map((height, i) => (
              <div key={i} className="flex-1">
                <div 
                  className="bg-[#2563eb] rounded-t-sm transition-all hover:bg-[#1d4ed8]"
                  style={{ height: `${height}%` }}
                ></div>
              </div>
            ))}
          </div>
          <p className="text-center text-sm text-gray-500 mt-4">Monthly Users (Jan-Dec)</p>
        </div>

        {/* Revenue Breakdown */}
        <div className="bg-white rounded-xl p-6 border border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Revenue Breakdown</h2>
          <div className="space-y-4">
            {revenueBreakdown.map((item, index) => (
              <div key={index}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-600">{item.label}</span>
                  <span className="font-medium text-[#2563eb]">{item.value}</span>
                </div>
                <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-[#06b6d4] rounded-full"
                    style={{ width: item.width }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Top Performing Courses */}
      <div className="bg-white rounded-xl p-6 border border-gray-100 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Top Performing Courses</h2>
        <div className="space-y-4">
          {topCourses.map((course) => (
            <div key={course.rank} className="flex items-center justify-between py-2">
              <div className="flex items-center gap-4">
                <span className="w-8 h-8 rounded-full bg-[#2563eb] text-white flex items-center justify-center text-sm font-medium">
                  {course.rank}
                </span>
                <div>
                  <p className="font-medium text-gray-900">{course.name}</p>
                  <p className="text-sm text-gray-500">{course.enrolled}</p>
                </div>
              </div>
              <div className="flex items-center gap-1 text-amber-500">
                <svg className="w-4 h-4 fill-current" viewBox="0 0 20 20">
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                </svg>
                <span className="text-sm font-medium text-gray-700">{course.rating}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* User Distribution */}
        <div className="bg-white rounded-xl p-6 border border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">User Distribution</h2>
          <div className="space-y-4">
            {userDistribution.map((item, index) => (
              <div key={index} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className={`w-3 h-3 rounded-full ${item.color}`}></span>
                  <span className="text-gray-600">{item.label}</span>
                </div>
                <span className="font-medium text-gray-900">{item.count}</span>
              </div>
            ))}
          </div>
          <div className="mt-6 flex gap-1">
            {userDistribution.map((item, index) => (
              <div
                key={index}
                className={`h-3 ${item.color} first:rounded-l-full last:rounded-r-full`}
                style={{ width: `${(item.count / 1183) * 100}%` }}
              ></div>
            ))}
          </div>
        </div>

        {/* Engagement Rate */}
        <div className="bg-white rounded-xl p-6 border border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Engagement Rate</h2>
          <div className="space-y-4">
            {engagementStats.map((stat, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div>
                  <p className="text-gray-600">{stat.label}</p>
                  <p className="text-xs text-gray-400 flex items-center gap-1 mt-1">
                    <svg className="w-3 h-3 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
                    </svg>
                    {stat.change}
                  </p>
                </div>
                <span className="text-xl font-bold text-[#2563eb]">{stat.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
