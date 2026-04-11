"use client";

import { useState } from "react";

interface Group {
  id: number;
  name: string;
  instructor: string;
  level: string;
  maxStudents: number;
  currentStudents: number;
  status: "Active" | "Inactive";
}

export default function GroupsPage() {
  const [showModal, setShowModal] = useState(false);
  const [activeTab, setActiveTab] = useState("Active");
  const [searchQuery, setSearchQuery] = useState("");

  const groups: Group[] = [
    { id: 1, name: "Business English", instructor: "Mr. Smith", level: "B2", maxStudents: 20, currentStudents: 18, status: "Active" },
    { id: 2, name: "Grammar Basics", instructor: "Ms. Johnson", level: "A1", maxStudents: 15, currentStudents: 12, status: "Active" },
    { id: 3, name: "Speaking Club", instructor: "Mr. Brown", level: "B1", maxStudents: 10, currentStudents: 10, status: "Active" },
    { id: 4, name: "IELTS Prep", instructor: "Ms. Davis", level: "C1", maxStudents: 12, currentStudents: 8, status: "Active" },
    { id: 5, name: "Kids English", instructor: "Ms. Wilson", level: "A1", maxStudents: 10, currentStudents: 6, status: "Active" },
    { id: 6, name: "Writing Course", instructor: "Mr. Taylor", level: "B2", maxStudents: 15, currentStudents: 0, status: "Inactive" },
  ];

  const stats = [
    { label: "Total Groups", value: "6", color: "text-[#2563eb]" },
    { label: "Active Groups", value: "5", color: "text-[#2563eb]" },
    { label: "Total Students", value: "210", color: "text-[#06b6d4]" },
    { label: "Avg. Progress", value: "69%", color: "text-green-500" },
  ];

  const filteredGroups = groups.filter(group => {
    const matchesSearch = group.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      group.instructor.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesTab = activeTab === "All Groups" || group.status === activeTab;
    return matchesSearch && matchesTab;
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Group Management</h1>
          <p className="text-gray-500">Create and manage learning groups/courses</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-[#2563eb] text-white rounded-lg hover:bg-[#1d4ed8] transition font-medium"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New Group
        </button>
      </div>

      {/* Search */}
      <div className="relative mb-6">
        <svg className="w-5 h-5 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input
          type="text"
          placeholder="Search by name or instructor..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb] focus:border-transparent"
        />
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        {["Active", "Inactive", "All Groups"].map((tab) => (
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

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {stats.map((stat, index) => (
          <div key={index} className="bg-white rounded-xl p-4 border border-gray-100">
            <p className="text-sm text-gray-500">{stat.label}</p>
            <p className={`text-2xl font-bold ${stat.color} mt-1`}>{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Groups Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredGroups.map((group) => (
          <div key={group.id} className="bg-white rounded-xl p-5 border border-gray-100 hover:shadow-md transition">
            <div className="flex items-start justify-between mb-3">
              <div>
                <h3 className="font-semibold text-gray-900">{group.name}</h3>
                <p className="text-sm text-gray-500">Instructor: {group.instructor}</p>
              </div>
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                group.status === "Active" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"
              }`}>
                {group.status}
              </span>
            </div>
            <div className="flex items-center gap-4 text-sm text-gray-500 mb-4">
              <div className="flex items-center gap-1">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                </svg>
                <span>{group.currentStudents}/{group.maxStudents}</span>
              </div>
              <span className="px-2 py-0.5 bg-blue-50 text-blue-600 rounded text-xs font-medium">
                Level {group.level}
              </span>
            </div>
            <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
              <div 
                className="h-full bg-[#06b6d4] rounded-full transition-all"
                style={{ width: `${(group.currentStudents / group.maxStudents) * 100}%` }}
              ></div>
            </div>
            <div className="flex justify-between mt-4">
              <button className="text-[#2563eb] text-sm font-medium hover:underline">Edit</button>
              <button className="text-[#2563eb] text-sm font-medium hover:underline">View Details</button>
            </div>
          </div>
        ))}
      </div>

      {/* Create Group Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/50" onClick={() => setShowModal(false)} />
          <div className="relative bg-white rounded-xl p-6 w-full max-w-md shadow-xl">
            <h2 className="text-xl font-bold text-gray-900 mb-6">Create New Group</h2>
            <form className="space-y-4">
              <div>
                <input
                  type="text"
                  placeholder="Group Name"
                  className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb]"
                />
              </div>
              <div>
                <textarea
                  placeholder="Description"
                  rows={3}
                  className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb] resize-none"
                ></textarea>
              </div>
              <div>
                <select className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb] text-gray-500">
                  <option>Select Instructor</option>
                  <option>Mr. Smith</option>
                  <option>Ms. Johnson</option>
                  <option>Mr. Brown</option>
                </select>
              </div>
              <div>
                <select className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb] text-gray-500">
                  <option>Select Level</option>
                  <option>A1</option>
                  <option>A2</option>
                  <option>B1</option>
                  <option>B2</option>
                  <option>C1</option>
                  <option>C2</option>
                </select>
              </div>
              <div>
                <input
                  type="number"
                  placeholder="Max Students"
                  className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb]"
                />
              </div>
              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="flex-1 px-4 py-3 border border-gray-200 rounded-lg text-gray-700 hover:bg-gray-50 transition font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-3 bg-[#2563eb] text-white rounded-lg hover:bg-[#1d4ed8] transition font-medium"
                >
                  Create Group
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
