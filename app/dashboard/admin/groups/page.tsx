'use client'

import { useState } from 'react'
import DashboardLayout from '@/components/DashboardLayout'
import { BookOpen, Users, Plus, Search, Edit2, Trash2, Archive } from 'lucide-react'

export default function AdminGroups() {
  const [searchQuery, setSearchQuery] = useState('')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [statusFilter, setStatusFilter] = useState('active')

  const groups = [
    { id: 1, name: 'English Fundamentals', instructor: 'Fatima Khan', students: 45, level: 'Beginner', status: 'Active', progress: 65 },
    { id: 2, name: 'Business English', instructor: 'Ahmed Hassan', students: 32, level: 'Intermediate', status: 'Active', progress: 78 },
    { id: 3, name: 'Speaking Mastery', instructor: 'Leila Ahmed', students: 28, level: 'Advanced', status: 'Active', progress: 85 },
    { id: 4, name: 'IELTS Preparation', instructor: 'Hassan Ibrahim', students: 52, level: 'Advanced', status: 'Active', progress: 72 },
    { id: 5, name: 'Writing Essentials', instructor: 'Maryam Ali', students: 18, level: 'Beginner', status: 'Inactive', progress: 45 },
    { id: 6, name: 'Listening Skills', instructor: 'Omar Ahmed', students: 35, level: 'Intermediate', status: 'Active', progress: 68 },
  ]

  const filteredGroups = groups.filter((group) => {
    const matchesSearch = group.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
                         group.instructor.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesStatus = statusFilter === 'all' || group.status === statusFilter
    return matchesSearch && matchesStatus
  })

  return (
    <DashboardLayout role="admin" userName="Admin">
      <div className="space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-text-primary mb-2">Group Management</h1>
            <p className="text-text-secondary">Create and manage learning groups/courses</p>
          </div>
          <button 
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors font-medium active:scale-95"
          >
            <Plus size={20} />
            New Group
          </button>
        </div>

        {/* Search and Filters */}
        <div className="space-y-4">
          <div className="flex gap-4 flex-col sm:flex-row">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary" size={20} />
              <input
                type="text"
                placeholder="Search by name or instructor..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-border rounded-lg bg-surface text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
          </div>
          <div className="flex gap-2 flex-wrap">
            {['active', 'inactive', 'all'].map((status) => (
              <button
                key={status}
                onClick={() => setStatusFilter(status)}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  statusFilter === status
                    ? 'bg-primary text-white'
                    : 'border border-border hover:bg-surface-hover'
                }`}
              >
                {status === 'all' ? 'All Groups' : status === 'active' ? 'Active' : 'Inactive'}
              </button>
            ))}
          </div>
        </div>

        {/* Groups Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredGroups.map((group) => (
            <div key={group.id} className="bg-surface border border-border rounded-lg p-6 hover:shadow-lg transition-shadow">
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-text-primary">{group.name}</h3>
                  <p className="text-sm text-text-secondary">by {group.instructor}</p>
                </div>
                <span
                  className={`px-3 py-1 rounded-full text-xs font-medium ${
                    group.status === 'Active'
                      ? 'bg-green-500/10 text-green-600'
                      : 'bg-gray-500/10 text-gray-600'
                  }`}
                >
                  {group.status}
                </span>
              </div>

              <div className="space-y-3 mb-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-text-secondary flex items-center gap-2">
                    <Users size={16} />
                    {group.students} Students
                  </span>
                  <span className="text-xs font-semibold text-primary">{group.level}</span>
                </div>
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-text-secondary">Progress</span>
                    <span className="text-xs font-semibold text-text-primary">{group.progress}%</span>
                  </div>
                  <div className="h-2 bg-surface-hover rounded-full overflow-hidden">
                    <div
                      className="h-full bg-accent"
                      style={{ width: `${group.progress}%` }}
                    />
                  </div>
                </div>
              </div>

              <div className="flex gap-2">
                <button className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors text-sm font-medium">
                  <Edit2 size={16} />
                  Edit
                </button>
                <button className="p-2 rounded-lg border border-border hover:bg-red-100 transition-colors">
                  <Trash2 size={16} className="text-red-500" />
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Create Group Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-surface rounded-lg border border-border p-6 max-w-md w-full">
              <h2 className="text-2xl font-bold text-text-primary mb-4">Create New Group</h2>
              <div className="space-y-4">
                <input type="text" placeholder="Group Name" className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary" />
                <textarea placeholder="Description" rows={3} className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary" />
                <select className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-primary">
                  <option>Select Instructor</option>
                  <option>Fatima Khan</option>
                  <option>Ahmed Hassan</option>
                  <option>Leila Ahmed</option>
                </select>
                <select className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-primary">
                  <option>Select Level</option>
                  <option>Beginner</option>
                  <option>Intermediate</option>
                  <option>Advanced</option>
                </select>
                <input type="number" placeholder="Max Students" className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary" />
              </div>
              <div className="flex gap-3 mt-6">
                <button 
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 px-4 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors font-medium"
                >
                  Cancel
                </button>
                <button 
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 px-4 py-2 rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors font-medium"
                >
                  Create Group
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Statistics */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-surface border border-border rounded-lg p-4">
            <p className="text-sm text-text-secondary mb-2">Total Groups</p>
            <p className="text-3xl font-bold text-primary">{groups.length}</p>
          </div>
          <div className="bg-surface border border-border rounded-lg p-4">
            <p className="text-sm text-text-secondary mb-2">Active Groups</p>
            <p className="text-3xl font-bold text-green-500">{groups.filter(g => g.status === 'Active').length}</p>
          </div>
          <div className="bg-surface border border-border rounded-lg p-4">
            <p className="text-sm text-text-secondary mb-2">Total Students</p>
            <p className="text-3xl font-bold text-accent">{groups.reduce((sum, g) => sum + g.students, 0)}</p>
          </div>
          <div className="bg-surface border border-border rounded-lg p-4">
            <p className="text-sm text-text-secondary mb-2">Avg. Progress</p>
            <p className="text-3xl font-bold text-orange-500">{Math.round(groups.reduce((sum, g) => sum + g.progress, 0) / groups.length)}%</p>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
