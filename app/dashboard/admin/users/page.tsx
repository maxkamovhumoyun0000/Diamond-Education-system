import DashboardLayout from '@/components/DashboardLayout'
import { Search, MoreVertical, UserPlus, Filter } from 'lucide-react'

export default function AdminUsers() {
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

  return (
    <DashboardLayout role="admin" userName="Admin">
      <div className="space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-text-primary mb-2">User Management</h1>
            <p className="text-text-secondary">Manage all system users and their roles</p>
          </div>
          <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors font-medium">
            <UserPlus size={20} />
            Add User
          </button>
        </div>

        {/* Filters and Search */}
        <div className="space-y-4">
          <div className="flex gap-4 flex-col sm:flex-row">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary" size={20} />
              <input
                type="text"
                placeholder="Search by name or email..."
                className="w-full pl-10 pr-4 py-2 border border-border rounded-lg bg-surface text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <button className="flex items-center gap-2 px-4 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors">
              <Filter size={20} />
              Filter
            </button>
          </div>
        </div>

        {/* Users Table */}
        <div className="rounded-lg border border-border overflow-hidden bg-surface">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-surface-hover border-b border-border">
                <tr>
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
                {users.map((user) => (
                  <tr key={user.id} className="hover:bg-surface-hover transition-colors">
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
                      <span
                        className={`px-3 py-1 rounded-full text-xs font-medium ${
                          user.status === 'Active'
                            ? 'bg-green-500/10 text-green-600'
                            : 'bg-gray-500/10 text-gray-600'
                        }`}
                      >
                        {user.status}
                      </span>
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
                      <button className="p-2 hover:bg-surface-hover rounded-lg transition-colors inline-flex items-center justify-center">
                        <MoreVertical size={16} className="text-text-secondary" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between">
          <p className="text-sm text-text-secondary">Showing 1 to 6 of 248 users</p>
          <div className="flex gap-2">
            <button className="px-3 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors text-sm">
              Previous
            </button>
            <button className="px-3 py-2 rounded-lg bg-primary text-white transition-colors text-sm">
              1
            </button>
            <button className="px-3 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors text-sm">
              2
            </button>
            <button className="px-3 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors text-sm">
              3
            </button>
            <button className="px-3 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors text-sm">
              Next
            </button>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
