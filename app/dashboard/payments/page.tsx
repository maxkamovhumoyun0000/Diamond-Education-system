"use client";

import { useState } from "react";

export default function PaymentsPage() {
  const [activeTab, setActiveTab] = useState("All Payments");

  const stats = [
    { label: "Total Revenue", value: "$12,450", change: "15% from last month", changeType: "up", bgColor: "bg-[#e0f2fe]", icon: "dollar" },
    { label: "Completed", value: "248", description: "Successful transactions", bgColor: "bg-[#e0f7fa]", icon: "check" },
    { label: "Pending", value: "12", description: "Awaiting confirmation", bgColor: "bg-white", icon: "clock" },
    { label: "Failed", value: "5", description: "Require attention", bgColor: "bg-white", icon: "alert" },
  ];

  const paymentMethods = [
    { method: "Credit Card", count: 145, color: "bg-[#2563eb]" },
    { method: "PayPal", count: 98, color: "bg-[#06b6d4]" },
    { method: "Bank Transfer", count: 52, color: "bg-green-500" },
    { method: "Other", count: 15, color: "bg-orange-500" },
  ];

  const transactions = [
    { user: "Ahmed Ali", course: "English Course", amount: "$49.99", method: "Credit Card", status: "Completed", date: "2024-03-20" },
    { user: "Fatima Khan", course: "Premium Bundle", amount: "$99.99", method: "PayPal", status: "Completed", date: "2024-03-19" },
    { user: "Hassan Ahmed", course: "Speaking Class", amount: "$29.99", method: "Credit Card", status: "Pending", date: "2024-03-18" },
    { user: "Aysha Hassan", course: "IELTS Prep", amount: "$149.99", method: "Bank Transfer", status: "Completed", date: "2024-03-17" },
    { user: "Omar Ibrahim", course: "Writing Course", amount: "$39.99", method: "Credit Card", status: "Failed", date: "2024-03-16" },
  ];

  const bottomStats = [
    { label: "Daily Revenue", value: "$2,450", description: "Last 24 hours", color: "text-[#2563eb]" },
    { label: "Monthly Average", value: "$3,820", description: "Per day average", color: "text-[#06b6d4]" },
    { label: "Conversion Rate", value: "8.2%", description: "From visits to purchases", color: "text-green-500" },
  ];

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Payment Management</h1>
        <p className="text-gray-500">Track all transactions and payment status</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {stats.map((stat, index) => (
          <div key={index} className={`${stat.bgColor} rounded-xl p-5 border border-gray-100`}>
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-gray-500">{stat.label}</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">{stat.value}</p>
                <p className="text-xs text-gray-400 mt-1">{stat.change || stat.description}</p>
              </div>
              <div className={`p-2 rounded-lg ${
                stat.icon === "dollar" ? "text-[#2563eb]" :
                stat.icon === "check" ? "text-green-500" :
                stat.icon === "clock" ? "text-amber-500" :
                "text-red-500"
              }`}>
                {stat.icon === "dollar" && (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                )}
                {stat.icon === "check" && (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                )}
                {stat.icon === "clock" && (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                )}
                {stat.icon === "alert" && (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                )}
              </div>
            </div>
            {stat.changeType === "up" && (
              <div className="flex items-center gap-1 mt-3">
                <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
                </svg>
                <span className="text-green-500 text-sm font-medium">15%</span>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Payment Methods */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {paymentMethods.map((pm, index) => (
          <div key={index} className="bg-white rounded-xl p-4 border border-gray-100">
            <div className="flex items-center gap-2 mb-2">
              <span className={`w-3 h-3 rounded-full ${pm.color}`}></span>
              <span className="text-sm text-gray-500">{pm.method}</span>
            </div>
            <p className="text-2xl font-bold text-gray-900">{pm.count}</p>
            <p className="text-xs text-gray-400">transactions</p>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        {["All Payments", "Completed", "Pending", "Failed"].map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
              activeTab === tab
                ? "bg-[#2563eb] text-white"
                : "bg-white border border-gray-200 text-gray-600 hover:bg-gray-50"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Transactions Table */}
      <div className="bg-white rounded-xl border border-gray-100 overflow-hidden mb-6">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-100">
            <tr>
              <th className="text-left px-6 py-4 text-sm font-medium text-gray-500">User</th>
              <th className="text-left px-6 py-4 text-sm font-medium text-gray-500">Course</th>
              <th className="text-left px-6 py-4 text-sm font-medium text-gray-500">Amount</th>
              <th className="text-left px-6 py-4 text-sm font-medium text-gray-500">Method</th>
              <th className="text-left px-6 py-4 text-sm font-medium text-gray-500">Status</th>
              <th className="text-left px-6 py-4 text-sm font-medium text-gray-500">Date</th>
              <th className="text-left px-6 py-4 text-sm font-medium text-gray-500">Action</th>
            </tr>
          </thead>
          <tbody>
            {transactions.map((tx, index) => (
              <tr key={index} className="border-b border-gray-50 hover:bg-gray-50 transition">
                <td className="px-6 py-4 font-medium text-gray-900">{tx.user}</td>
                <td className="px-6 py-4 text-gray-500">{tx.course}</td>
                <td className="px-6 py-4 font-medium text-gray-900">{tx.amount}</td>
                <td className="px-6 py-4 text-gray-500">{tx.method}</td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    tx.status === "Completed" ? "bg-green-100 text-green-700" :
                    tx.status === "Pending" ? "bg-amber-100 text-amber-700" :
                    "bg-red-100 text-red-700"
                  }`}>
                    {tx.status}
                  </span>
                </td>
                <td className="px-6 py-4 text-gray-500">{tx.date}</td>
                <td className="px-6 py-4">
                  <button className="text-[#2563eb] text-sm font-medium hover:underline">View</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Bottom Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {bottomStats.map((stat, index) => (
          <div key={index} className="bg-white rounded-xl p-5 border border-gray-100">
            <p className="text-sm text-gray-500">{stat.label}</p>
            <p className={`text-2xl font-bold ${stat.color} mt-1`}>{stat.value}</p>
            <p className="text-xs text-gray-400 mt-1">{stat.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
