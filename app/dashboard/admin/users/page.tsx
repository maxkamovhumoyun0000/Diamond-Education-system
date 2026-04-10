'use client'

import { useState } from 'react'
import DashboardLayout from '@/components/DashboardLayout'
import { Search, MoreVertical, UserPlus, Filter, Trash2, Edit2, CheckCircle, XCircle } from 'lucide-react'

export default function AdminUsers() {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedUsers, setSelectedUsers] = useState<number[]>([])
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [userToDelete, setUserToDelete] = useState<number | null>(null)
  const [filterRole, setFilterRole] = useState('all')
  const [showEditModal, setShowEditModal] = useState(false)
  const [editingUser, setEditingUser] = useState<any>(null)

  const users = [
    {
      id: 1,
      name: 'Ahmed Ali',
      email: 'ahmed@diamond.edu',
      role: 'Student',
      status: 'Active',
      joinDate: '2024-01-15',
      progress: 65,
    },
    {
      id: 2,
      name: 'Fatima Khan',
      email: 'fatima@diamond.edu',
      role: 'Teacher',
      status: 'Active',
      joinDate: '2024-01-20',
      progress: 92,
    },
    {
      id: 3,
      name: 'Hassan Ahmed',
      email: 'hassan@diamond.edu',
      role: 'Student',
      status: 'Active',
      joinDate: '2024-02-01',
      progress: 45,
    },
    {
      id: 4,
      name: 'Aysha Hassan',
      email: 'aysha@diamond.edu',
      role: 'Teacher',
      status: 'Inactive',
      joinDate: '2024-02-10',
      progress: 78,
    },
    {
      id: 5,
      name: 'Omar Ibrahim',
      email: 'omar@diamond.edu',
      role: 'Student',
      status: 'Active',
      joinDate: '2024-02-15',
      progress: 82,
    },
    {
      id: 6,
      name: 'Leila Ahmed',
      email: 'leila@diamond.edu',
      role: 'Support',
      status: 'Active',
      joinDate: '2024-03-01',
      progress: 100,
    },
  ]

  const filteredUsers = users.filter((user) => {
    const matchesSearch = user.name.toLowerCase().includes(searchQuery.toLowerCase()) || user.email.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesRole = filterRole === 'all' || user.role === filterRole
    return matchesSearch && matchesRole
  })

  const toggleSelectUser = (id: number) => {
    setSelectedUsers(prev => prev.includes(id) ? prev.filter(uid => uid !== id) : [...prev, id])
  }

  const toggleSelectAll = () => {
    if (selectedUsers.length === filteredUsers.length) {
      setSelectedUsers([])
    } else {
      setSelectedUsers(filteredUsers.map(u => u.id))
    }
  }

  const handleDeleteUser = (id: number) => {
    setUserToDelete(id)
    setShowDeleteModal(true)
  }

  const handleEditUser = (user: any) => {
    setEditingUser(user)
    setShowEditModal(true)
  }

  return (
    <DashboardLayout role="admin" userName="Admin">
      <div className="space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-text-primary mb-2">User Management</h1>
            <p className="text-text-secondary">Manage all system users and their roles ({filteredUsers.length})</p>
          </div>
          <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors font-medium active:scale-95">
            <UserPlus size={20} />
            Add User
          </button>
        </div>

        {/* Bulk Actions */}
        {selectedUsers.length > 0 && (
          <div className="bg-primary/10 border border-primary/30 rounded-lg p-4 flex items-center justify-between">
            <span className="text-sm font-medium text-text-primary">{selectedUsers.length} user(s) selected</span>
            <div className="flex gap-2">
              <button className="px-3 py-2 rounded-lg border border-primary hover:bg-primary/5 transition-colors text-sm font-medium">
                Activate
              </button>
              <button className="px-3 py-2 rounded-lg border border-primary hover:bg-primary/5 transition-colors text-sm font-medium">
                Deactivate
              </button>
              <button 
                onClick={() => {
                  setShowDeleteModal(true)
                  setUserToDelete(null)
                }}
                className="px-3 py-2 rounded-lg border border-red-500 text-red-600 hover:bg-red-50 transition-colors text-sm font-medium"
              >
                Delete Selected
              </button>
            </div>
          </div>
        )}

        {/* Filters and Search */}
        <div className="space-y-4">
          <div className="flex gap-4 flex-col sm:flex-row">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary" size={20} />
              <input
                type="text"
                placeholder="Search by name or email..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-border rounded-lg bg-surface text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <select 
              value={filterRole}
              onChange={(e) => setFilterRole(e.target.value)}
              className="px-4 py-2 rounded-lg border border-border bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="all">All Roles</option>
              <option value="Student">Student</option>
              <option value="Teacher">Teacher</option>
              <option value="Support">Support</option>
            </select>
          </div>
        </div>

        {/* Users Table */}
        <div className="rounded-lg border border-border overflow-hidden bg-surface">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-surface-hover border-b border-border">
                <tr>
                  <th className="px-6 py-4 text-left">
                    <input 
                      type="checkbox"
                      checked={selectedUsers.length === filteredUsers.length && filteredUsers.length > 0}
                      onChange={toggleSelectAll}
                      className="w-4 h-4 rounded border-border cursor-pointer"
                    />
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-text-primary">Name</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-text-primary">Email</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-text-primary">Role</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-text-primary">Status</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-text-primary">Progress</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-text-primary">Join Date</th>
                  <th className="px-6 py-4 text-center text-sm font-semibold text-text-primary">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredUsers.map((user) => (
                  <tr key={user.id} className="hover:bg-surface-hover transition-colors">
                    <td className="px-6 py-4">
                      <input 
                        type="checkbox"
                        checked={selectedUsers.includes(user.id)}
                        onChange={() => toggleSelectUser(user.id)}
                        className="w-4 h-4 rounded border-border cursor-pointer"
                      />
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center text-primary font-semibold">
                          {user.name.charAt(0)}
                        </div>
                        <span className="font-medium text-text-primary">{user.name}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-text-secondary text-sm">{user.email}</td>
                    <td className="px-6 py-4">
                      <span className="px-3 py-1 rounded-full text-xs font-medium bg-primary/10 text-primary">
                        {user.role}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        {user.status === 'Active' ? (
                          <>
                            <CheckCircle size={16} className="text-green-500" />
                            <span className="text-xs font-medium text-green-600">Active</span>
                          </>
                        ) : (
                          <>
                            <XCircle size={16} className="text-gray-500" />
                            <span className="text-xs font-medium text-gray-600">Inactive</span>
                          </>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="w-24">
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-2 bg-surface-hover rounded-full overflow-hidden">
                            <div
                              className="h-full bg-accent"
                              style={{ width: `${user.progress}%` }}
                            />
                          </div>
                          <span className="text-xs text-text-secondary">{user.progress}%</span>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-text-secondary">{user.joinDate}</td>
                    <td className="px-6 py-4 text-center">
                      <div className="flex items-center justify-center gap-2">
                        <button 
                          onClick={() => handleEditUser(user)}
                          className="p-2 hover:bg-surface-hover rounded-lg transition-colors inline-flex items-center justify-center"
                          title="Edit user"
                        >
                          <Edit2 size={16} className="text-text-secondary" />
                        </button>
                        <button 
                          onClick={() => handleDeleteUser(user.id)}
                          className="p-2 hover:bg-red-100 rounded-lg transition-colors inline-flex items-center justify-center"
                          title="Delete user"
                        >
                          <Trash2 size={16} className="text-red-500" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between">
          <p className="text-sm text-text-secondary">Showing {filteredUsers.length} of {users.length} users</p>
          <div className="flex gap-2">
            <button className="px-3 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors text-sm active:scale-95">
              Previous
            </button>
            <button className="px-3 py-2 rounded-lg bg-primary text-white transition-colors text-sm active:scale-95">
              1
            </button>
            <button className="px-3 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors text-sm active:scale-95">
              2
            </button>
            <button className="px-3 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors text-sm active:scale-95">
              3
            </button>
            <button className="px-3 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors text-sm active:scale-95">
              Next
            </button>
          </div>
        </div>
      </div>

      {/* Delete Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-surface rounded-lg border border-border p-6 max-w-sm w-full">
            <h2 className="text-2xl font-bold text-text-primary mb-2">Delete User(s)</h2>
            <p className="text-text-secondary mb-6">
              Are you sure you want to delete {userToDelete ? '1' : selectedUsers.length} user(s)? This action cannot be undone.
            </p>
            <div className="flex gap-3">
              <button 
                onClick={() => {
                  setShowDeleteModal(false)
                  setUserToDelete(null)
                }}
                className="flex-1 px-4 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors font-medium"
              >
                Cancel
              </button>
              <button 
                onClick={() => {
                  setShowDeleteModal(false)
                  setSelectedUsers([])
                  setUserToDelete(null)
                }}
                className="flex-1 px-4 py-2 rounded-lg bg-red-600 text-white hover:bg-red-700 transition-colors font-medium"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit User Modal */}
      {showEditModal && editingUser && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-surface rounded-lg border border-border p-6 max-w-md w-full">
            <h2 className="text-2xl font-bold text-text-primary mb-4">Edit User</h2>
            <div className="space-y-4">
              <input type="text" defaultValue={editingUser.name} placeholder="Full Name" className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary" />
              <input type="email" defaultValue={editingUser.email} placeholder="Email Address" className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary" />
              <select defaultValue={editingUser.role} className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-primary">
                <option>Student</option>
                <option>Teacher</option>
                <option>Support</option>
                <option>Admin</option>
              </select>
              <select defaultValue={editingUser.status} className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-primary">
                <option>Active</option>
                <option>Inactive</option>
              </select>
            </div>
            <div className="flex gap-3 mt-6">
              <button 
                onClick={() => {
                  setShowEditModal(false)
                  setEditingUser(null)
                }}
                className="flex-1 px-4 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors font-medium"
              >
                Cancel
              </button>
              <button 
                onClick={() => {
                  setShowEditModal(false)
                  setEditingUser(null)
                }}
                className="flex-1 px-4 py-2 rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors font-medium"
              >
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}
    </DashboardLayout>
  )
}
