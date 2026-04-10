'use client'

import { useState } from 'react'
import DashboardLayout from '@/components/DashboardLayout'
import { Users, Calendar, BarChart3, Settings, Plus, Trash2, Edit2, Eye } from 'lucide-react'

export default function TeacherGroups() {
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [selectedGroup, setSelectedGroup] = useState<any>(null)
  const [groupName, setGroupName] = useState('')
  const [groupLevel, setGroupLevel] = useState('')
  const groups = [
    {
      id: 1,
      name: 'Advanced English Group A',
      level: 'B2',
      students: 15,
      schedule: 'Mon & Wed, 3:00 PM',
      progress: 82,
      avgScore: 87,
      description: 'For intermediate-advanced learners',
    },
    {
      id: 2,
      name: 'Grammar Basics',
      level: 'A2',
      students: 18,
      schedule: 'Tue & Thu, 2:00 PM',
      progress: 65,
      avgScore: 76,
      description: 'Foundation grammar course',
    },
    {
      id: 3,
      name: 'Speaking Club',
      level: 'B1',
      students: 12,
      schedule: 'Fri, 4:00 PM',
      progress: 75,
      avgScore: 82,
      description: 'Conversation and fluency practice',
    },
  ]

  return (
    <DashboardLayout role="teacher" userName="Fatima">
      <div className="space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-text-primary mb-2">My Groups</h1>
            <p className="text-text-secondary">Manage and monitor your classes ({groups.length})</p>
          </div>
          <button 
            onClick={() => setShowCreateModal(true)}
            className="px-6 py-2 rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors font-medium flex items-center gap-2 active:scale-95"
          >
            <Plus size={20} />
            Create Group
          </button>
        </div>

        {/* Groups Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {groups.map((group) => (
            <div key={group.id} className="bg-surface border border-border rounded-lg overflow-hidden hover:shadow-glass transition-all">
              {/* Header */}
              <div className="bg-gradient-to-r from-primary to-primary-dark p-6 text-white">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-xl font-semibold mb-2">{group.name}</h3>
                    <p className="text-white/80 text-sm">{group.description}</p>
                  </div>
                  <span className="px-3 py-1 rounded-full bg-white/20 text-white text-sm font-medium">
                    Level {group.level}
                  </span>
                </div>
              </div>

              {/* Content */}
              <div className="p-6 space-y-6">
                {/* Stats Grid */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 rounded-lg bg-surface-hover">
                    <p className="text-xs text-text-secondary mb-1">Students</p>
                    <p className="text-2xl font-bold text-text-primary flex items-center gap-1">
                      <Users size={18} className="text-primary" />
                      {group.students}
                    </p>
                  </div>
                  <div className="p-3 rounded-lg bg-surface-hover">
                    <p className="text-xs text-text-secondary mb-1">Avg Score</p>
                    <p className="text-2xl font-bold text-accent">{group.avgScore}%</p>
                  </div>
                </div>

                {/* Schedule */}
                <div className="p-3 rounded-lg bg-surface-hover">
                  <p className="text-xs text-text-secondary mb-1 flex items-center gap-1">
                    <Calendar size={14} />
                    Schedule
                  </p>
                  <p className="font-medium text-text-primary">{group.schedule}</p>
                </div>

                {/* Progress Bar */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-sm font-medium text-text-primary">Course Progress</p>
                    <span className="text-sm font-semibold text-primary">{group.progress}%</span>
                  </div>
                  <div className="w-full h-2 bg-surface-hover rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary transition-all"
                      style={{ width: `${group.progress}%` }}
                    />
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-2 pt-4 border-t border-border">
                  <button className="flex-1 py-2 px-3 rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors font-medium text-sm active:scale-95 flex items-center justify-center gap-1">
                    <Eye size={16} />
                    View Students
                  </button>
                  <button className="flex-1 py-2 px-3 rounded-lg border border-border hover:bg-surface-hover transition-colors font-medium text-sm flex items-center justify-center gap-1 active:scale-95">
                    <BarChart3 size={16} />
                    Analytics
                  </button>
                  <button 
                    onClick={() => {
                      setSelectedGroup(group)
                      setShowEditModal(true)
                    }}
                    className="py-2 px-3 rounded-lg border border-border hover:bg-surface-hover transition-colors active:scale-95"
                    title="Edit group"
                  >
                    <Edit2 size={16} className="text-text-secondary" />
                  </button>
                  <button 
                    onClick={() => {
                      setSelectedGroup(group)
                      setShowDeleteModal(true)
                    }}
                    className="py-2 px-3 rounded-lg border border-border hover:bg-red-100 transition-colors active:scale-95"
                    title="Delete group"
                  >
                    <Trash2 size={16} className="text-red-500" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Upcoming Classes */}
        <div className="bg-surface border border-border rounded-lg p-6">
          <h2 className="text-lg font-semibold text-text-primary mb-4">Upcoming Classes</h2>
          <div className="space-y-3">
            {[
              { group: 'Advanced English Group A', date: 'Today', time: '3:00 PM', students: 15 },
              { group: 'Grammar Basics', date: 'Tomorrow', time: '2:00 PM', students: 18 },
              { group: 'Speaking Club', date: 'Friday', time: '4:00 PM', students: 12 },
              { group: 'Advanced English Group A', date: 'Next Wed', time: '3:00 PM', students: 15 },
            ].map((cls, i) => (
              <div key={i} className="flex items-center justify-between p-4 hover:bg-surface-hover rounded-lg transition-colors border border-transparent hover:border-border">
                <div>
                  <p className="font-medium text-text-primary">{cls.group}</p>
                  <p className="text-sm text-text-secondary">{cls.date} at {cls.time}</p>
                </div>
                <span className="px-3 py-1 rounded-full bg-accent/10 text-accent text-sm font-medium">
                  {cls.students} students
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Create Group Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-surface rounded-lg border border-border p-6 max-w-md w-full">
              <h2 className="text-2xl font-bold text-text-primary mb-4">Create New Group</h2>
              <div className="space-y-4">
                <input 
                  type="text" 
                  placeholder="Group Name" 
                  value={groupName}
                  onChange={(e) => setGroupName(e.target.value)}
                  className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary" 
                />
                <select 
                  value={groupLevel}
                  onChange={(e) => setGroupLevel(e.target.value)}
                  className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="">Select Level</option>
                  <option value="A1">A1 - Beginner</option>
                  <option value="A2">A2 - Elementary</option>
                  <option value="B1">B1 - Intermediate</option>
                  <option value="B2">B2 - Upper Intermediate</option>
                  <option value="C1">C1 - Advanced</option>
                </select>
                <input 
                  type="text" 
                  placeholder="Schedule (e.g., Mon & Wed, 3:00 PM)" 
                  className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary" 
                />
                <textarea 
                  placeholder="Description" 
                  rows={3}
                  className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              <div className="flex gap-3 mt-6">
                <button 
                  onClick={() => {
                    setShowCreateModal(false)
                    setGroupName('')
                    setGroupLevel('')
                  }}
                  className="flex-1 px-4 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors font-medium"
                >
                  Cancel
                </button>
                <button 
                  onClick={() => {
                    setShowCreateModal(false)
                    setGroupName('')
                    setGroupLevel('')
                  }}
                  className="flex-1 px-4 py-2 rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors font-medium"
                >
                  Create Group
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Edit Group Modal */}
        {showEditModal && selectedGroup && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-surface rounded-lg border border-border p-6 max-w-md w-full">
              <h2 className="text-2xl font-bold text-text-primary mb-4">Edit Group</h2>
              <div className="space-y-4">
                <input 
                  type="text" 
                  defaultValue={selectedGroup.name}
                  placeholder="Group Name" 
                  className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary" 
                />
                <select 
                  defaultValue={selectedGroup.level}
                  className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="A1">A1 - Beginner</option>
                  <option value="A2">A2 - Elementary</option>
                  <option value="B1">B1 - Intermediate</option>
                  <option value="B2">B2 - Upper Intermediate</option>
                  <option value="C1">C1 - Advanced</option>
                </select>
                <input 
                  type="text" 
                  defaultValue={selectedGroup.schedule}
                  placeholder="Schedule" 
                  className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary" 
                />
                <textarea 
                  defaultValue={selectedGroup.description}
                  placeholder="Description" 
                  rows={3}
                  className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              <div className="flex gap-3 mt-6">
                <button 
                  onClick={() => {
                    setShowEditModal(false)
                    setSelectedGroup(null)
                  }}
                  className="flex-1 px-4 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors font-medium"
                >
                  Cancel
                </button>
                <button 
                  onClick={() => {
                    setShowEditModal(false)
                    setSelectedGroup(null)
                  }}
                  className="flex-1 px-4 py-2 rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors font-medium"
                >
                  Save Changes
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Delete Group Modal */}
        {showDeleteModal && selectedGroup && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-surface rounded-lg border border-border p-6 max-w-md w-full">
              <h2 className="text-2xl font-bold text-red-600 mb-2">Delete Group</h2>
              <p className="text-text-secondary mb-6">Are you sure you want to delete <span className="font-semibold">{selectedGroup.name}</span>? This action cannot be undone.</p>
              <div className="flex gap-3">
                <button 
                  onClick={() => {
                    setShowDeleteModal(false)
                    setSelectedGroup(null)
                  }}
                  className="flex-1 px-4 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors font-medium"
                >
                  Cancel
                </button>
                <button 
                  onClick={() => {
                    setShowDeleteModal(false)
                    setSelectedGroup(null)
                  }}
                  className="flex-1 px-4 py-2 rounded-lg bg-red-600 text-white hover:bg-red-700 transition-colors font-medium"
                >
                  Delete
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
