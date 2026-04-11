"use client";

import { useState } from "react";

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("General");

  const tabs = [
    { id: "General", icon: "settings" },
    { id: "Notifications", icon: "bell" },
    { id: "Security", icon: "lock" },
    { id: "User Management", icon: "users" },
    { id: "Analytics", icon: "chart" },
  ];

  const getIcon = (icon: string) => {
    switch (icon) {
      case "settings":
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        );
      case "bell":
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
          </svg>
        );
      case "lock":
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
          </svg>
        );
      case "users":
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
          </svg>
        );
      case "chart":
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        );
      default:
        return null;
    }
  };

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">System Settings</h1>
        <p className="text-gray-500">Configure system-wide settings and preferences</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-6 border-b border-gray-200 mb-6">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 pb-3 border-b-2 transition ${
              activeTab === tab.id
                ? "border-[#2563eb] text-[#2563eb]"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {getIcon(tab.icon)}
            <span className="text-sm font-medium">{tab.id}</span>
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="bg-white rounded-xl p-6 border border-gray-100">
        {activeTab === "General" && (
          <div>
            <h2 className="text-lg font-semibold text-gray-900 mb-6">Basic Information</h2>
            <div className="space-y-6 max-w-xl">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Site Name</label>
                <input
                  type="text"
                  defaultValue="Diamond Education"
                  className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb]"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Site URL</label>
                <input
                  type="text"
                  defaultValue="https://diamond-education.com"
                  className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb]"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Admin Email</label>
                <input
                  type="email"
                  defaultValue="admin@diamond.edu"
                  className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb]"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Timezone</label>
                <select className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb]">
                  <option>UTC+3</option>
                  <option>UTC+5</option>
                  <option>UTC+8</option>
                </select>
              </div>
              <button className="px-6 py-3 bg-[#2563eb] text-white rounded-lg hover:bg-[#1d4ed8] transition font-medium">
                Save Changes
              </button>
            </div>
          </div>
        )}

        {activeTab === "Notifications" && (
          <div>
            <h2 className="text-lg font-semibold text-gray-900 mb-6">Notification Preferences</h2>
            <div className="space-y-4 max-w-xl">
              {[
                { label: "Email notifications for new users", enabled: true },
                { label: "Email notifications for payments", enabled: true },
                { label: "Push notifications", enabled: false },
                { label: "Weekly reports", enabled: true },
                { label: "System alerts", enabled: true },
              ].map((item, index) => (
                <div key={index} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <span className="text-gray-700">{item.label}</span>
                  <button
                    className={`w-12 h-6 rounded-full transition ${
                      item.enabled ? "bg-[#2563eb]" : "bg-gray-300"
                    }`}
                  >
                    <span
                      className={`block w-5 h-5 bg-white rounded-full shadow transform transition ${
                        item.enabled ? "translate-x-6" : "translate-x-0.5"
                      }`}
                    ></span>
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === "Security" && (
          <div>
            <h2 className="text-lg font-semibold text-gray-900 mb-6">Security Settings</h2>
            <div className="space-y-6 max-w-xl">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Current Password</label>
                <input
                  type="password"
                  className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb]"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">New Password</label>
                <input
                  type="password"
                  className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb]"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Confirm New Password</label>
                <input
                  type="password"
                  className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb]"
                />
              </div>
              <button className="px-6 py-3 bg-[#2563eb] text-white rounded-lg hover:bg-[#1d4ed8] transition font-medium">
                Update Password
              </button>
            </div>
          </div>
        )}

        {activeTab === "User Management" && (
          <div>
            <h2 className="text-lg font-semibold text-gray-900 mb-6">User Management Settings</h2>
            <div className="space-y-4 max-w-xl">
              <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <div>
                  <p className="font-medium text-gray-900">Allow user registration</p>
                  <p className="text-sm text-gray-500">New users can create accounts</p>
                </div>
                <button className="w-12 h-6 rounded-full bg-[#2563eb] transition">
                  <span className="block w-5 h-5 bg-white rounded-full shadow transform translate-x-6"></span>
                </button>
              </div>
              <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <div>
                  <p className="font-medium text-gray-900">Email verification required</p>
                  <p className="text-sm text-gray-500">Users must verify email before access</p>
                </div>
                <button className="w-12 h-6 rounded-full bg-[#2563eb] transition">
                  <span className="block w-5 h-5 bg-white rounded-full shadow transform translate-x-6"></span>
                </button>
              </div>
              <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <div>
                  <p className="font-medium text-gray-900">Two-factor authentication</p>
                  <p className="text-sm text-gray-500">Require 2FA for admin accounts</p>
                </div>
                <button className="w-12 h-6 rounded-full bg-gray-300 transition">
                  <span className="block w-5 h-5 bg-white rounded-full shadow transform translate-x-0.5"></span>
                </button>
              </div>
            </div>
          </div>
        )}

        {activeTab === "Analytics" && (
          <div>
            <h2 className="text-lg font-semibold text-gray-900 mb-6">Analytics Settings</h2>
            <div className="space-y-4 max-w-xl">
              <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <div>
                  <p className="font-medium text-gray-900">Track user activity</p>
                  <p className="text-sm text-gray-500">Monitor user engagement and behavior</p>
                </div>
                <button className="w-12 h-6 rounded-full bg-[#2563eb] transition">
                  <span className="block w-5 h-5 bg-white rounded-full shadow transform translate-x-6"></span>
                </button>
              </div>
              <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <div>
                  <p className="font-medium text-gray-900">Revenue tracking</p>
                  <p className="text-sm text-gray-500">Track payments and revenue metrics</p>
                </div>
                <button className="w-12 h-6 rounded-full bg-[#2563eb] transition">
                  <span className="block w-5 h-5 bg-white rounded-full shadow transform translate-x-6"></span>
                </button>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Data retention period</label>
                <select className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb]">
                  <option>30 days</option>
                  <option>90 days</option>
                  <option>1 year</option>
                  <option>Forever</option>
                </select>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
