"use client";

import { useState } from "react";
import Link from "next/link";

interface User {
  id: number;
  name: string;
  email: string;
  role: "O'quvchi" | "O'qituvchi" | "Yordam";
  subject: string;
  status: "Faol" | "Nofaol";
  progress: number;
}

export default function UsersPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [filterRole, setFilterRole] = useState("Foydalanuvchilar");
  const [showAddModal, setShowAddModal] = useState(false);

  const users: User[] = [
    { id: 1, name: "Ahmed Ali", email: "ahmed@diamond.edu", role: "O'quvchi", subject: "Ingliz tili", status: "Faol", progress: 65 },
    { id: 2, name: "Fatima Khan", email: "fatima@diamond.edu", role: "O'qituvchi", subject: "Ingliz tili", status: "Faol", progress: 92 },
    { id: 3, name: "Hassan Ahmed", email: "hassan@diamond.edu", role: "O'quvchi", subject: "Rus tili", status: "Faol", progress: 45 },
    { id: 4, name: "Aysha Hassan", email: "aysha@diamond.edu", role: "O'qituvchi", subject: "Rus tili", status: "Nofaol", progress: 78 },
    { id: 5, name: "Omar Ibrahim", email: "omar@diamond.edu", role: "O'quvchi", subject: "Ingliz tili", status: "Faol", progress: 82 },
    { id: 6, name: "Leila Ahmed", email: "leila@diamond.edu", role: "Yordam", subject: "Ingliz tili", status: "Faol", progress: 100 },
  ];

  const filteredUsers = users.filter(user => 
    user.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    user.email.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case "O'quvchi": return "bg-blue-100 text-blue-700";
      case "O'qituvchi": return "bg-purple-100 text-purple-700";
      case "Yordam": return "bg-gray-100 text-gray-700";
      default: return "bg-gray-100 text-gray-700";
    }
  };

  const getSubjectBadgeColor = (subject: string) => {
    switch (subject) {
      case "Ingliz tili": return "bg-blue-50 text-blue-600";
      case "Rus tili": return "bg-red-50 text-red-600";
      default: return "bg-gray-50 text-gray-600";
    }
  };

  const getInitials = (name: string) => {
    return name.split(' ').map(n => n[0]).join('').toUpperCase();
  };

  const getAvatarColor = (index: number) => {
    const colors = ["bg-blue-500", "bg-purple-500", "bg-green-500", "bg-orange-500", "bg-pink-500", "bg-cyan-500"];
    return colors[index % colors.length];
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Foydalanuvchilarni boshqarish</h1>
          <p className="text-gray-500">Jami foydalanuvchilar: {users.length}</p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-[#2563eb] text-white rounded-lg hover:bg-[#1d4ed8] transition font-medium"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
          </svg>
          Foydalanuvchi qo&apos;shish
        </button>
      </div>

      {/* Search and Filter */}
      <div className="flex items-center gap-4 mb-6">
        <div className="relative flex-1">
          <svg className="w-5 h-5 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            placeholder="Qidirish..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb] focus:border-transparent"
          />
        </div>
        <select
          value={filterRole}
          onChange={(e) => setFilterRole(e.target.value)}
          className="px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb] focus:border-transparent"
        >
          <option>Foydalanuvchilar</option>
          <option>O&apos;quvchilar</option>
          <option>O&apos;qituvchilar</option>
          <option>Yordam</option>
        </select>
      </div>

      {/* Users Table */}
      <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-100">
            <tr>
              <th className="text-left px-6 py-4 text-sm font-medium text-gray-500">
                <input type="checkbox" className="rounded border-gray-300" />
              </th>
              <th className="text-left px-6 py-4 text-sm font-medium text-gray-500">Ism</th>
              <th className="text-left px-6 py-4 text-sm font-medium text-gray-500">Email</th>
              <th className="text-left px-6 py-4 text-sm font-medium text-gray-500">Rolni tanlang</th>
              <th className="text-left px-6 py-4 text-sm font-medium text-gray-500">Fan tanlang</th>
              <th className="text-left px-6 py-4 text-sm font-medium text-gray-500">Status</th>
              <th className="text-left px-6 py-4 text-sm font-medium text-gray-500">Progress</th>
              <th className="text-left px-6 py-4 text-sm font-medium text-gray-500">Tahrirlash</th>
            </tr>
          </thead>
          <tbody>
            {filteredUsers.map((user, index) => (
              <tr key={user.id} className="border-b border-gray-50 hover:bg-gray-50 transition">
                <td className="px-6 py-4">
                  <input type="checkbox" className="rounded border-gray-300" />
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-full ${getAvatarColor(index)} flex items-center justify-center text-white text-sm font-medium`}>
                      {getInitials(user.name)}
                    </div>
                    <span className="font-medium text-gray-900">{user.name}</span>
                  </div>
                </td>
                <td className="px-6 py-4 text-gray-600">{user.email}</td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getRoleBadgeColor(user.role)}`}>
                    {user.role}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${getSubjectBadgeColor(user.subject)}`}>
                    {user.subject}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${user.status === "Faol" ? "bg-green-500" : "bg-gray-400"}`}></span>
                    <span className={user.status === "Faol" ? "text-green-600" : "text-gray-500"}>{user.status}</span>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-2">
                    <div className="w-20 h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-[#06b6d4] rounded-full" 
                        style={{ width: `${user.progress}%` }}
                      ></div>
                    </div>
                    <span className="text-sm text-gray-600">{user.progress}%</span>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-2">
                    <button className="p-1 text-gray-400 hover:text-[#2563eb] transition">
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                      </svg>
                    </button>
                    <button className="p-1 text-gray-400 hover:text-red-500 transition">
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* Pagination */}
        <div className="px-6 py-4 border-t border-gray-100 flex items-center justify-between">
          <span className="text-sm text-gray-500">{filteredUsers.length} / {users.length}</span>
          <div className="flex items-center gap-2">
            <button className="px-3 py-1 border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-50 transition">
              Orqaga
            </button>
            <button className="px-3 py-1 bg-[#2563eb] text-white rounded-lg">1</button>
            <button className="px-3 py-1 border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-50 transition">2</button>
            <button className="px-3 py-1 border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-50 transition">
              Keyingi
            </button>
          </div>
        </div>
      </div>

      {/* Add User Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50" onClick={() => setShowAddModal(false)} />
          <div className="relative bg-white rounded-xl p-6 w-full max-w-md shadow-xl">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Yangi foydalanuvchi</h2>
            <form className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Ism</label>
                <input
                  type="text"
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb]"
                  placeholder="Ism kiriting"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <input
                  type="email"
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb]"
                  placeholder="email@diamond.edu"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Rol</label>
                <select className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb]">
                  <option>O&apos;quvchi</option>
                  <option>O&apos;qituvchi</option>
                  <option>Yordam</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Fan</label>
                <select className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb]">
                  <option>Ingliz tili</option>
                  <option>Rus tili</option>
                </select>
              </div>
              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="flex-1 px-4 py-2 border border-gray-200 rounded-lg text-gray-700 hover:bg-gray-50 transition"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-[#2563eb] text-white rounded-lg hover:bg-[#1d4ed8] transition"
                >
                  Qo&apos;shish
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
