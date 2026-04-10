'use client'

import { useEffect, useState } from 'react'
import { studentsApi, usersApi, User } from '@/lib/api'

export default function StudentsPage() {
  const [students, setStudents] = useState<User[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const [subjectFilter, setSubjectFilter] = useState('')
  const [levelFilter, setLevelFilter] = useState('')

  useEffect(() => {
    fetchStudents()
  }, [subjectFilter, levelFilter])

  const fetchStudents = async () => {
    try {
      setIsLoading(true)
      const data = await studentsApi.list({
        subject: subjectFilter || undefined,
        level: levelFilter || undefined,
        limit: 100,
      })
      setStudents(data.students || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load students')
    } finally {
      setIsLoading(false)
    }
  }

  const handleToggleAccess = async (studentId: number) => {
    try {
      await usersApi.toggleAccess(studentId)
      fetchStudents()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to toggle access')
    }
  }

  const filteredStudents = students.filter((student) => {
    if (!searchTerm) return true
    const search = searchTerm.toLowerCase()
    return (
      student.first_name?.toLowerCase().includes(search) ||
      student.last_name?.toLowerCase().includes(search) ||
      student.login_id?.toLowerCase().includes(search) ||
      student.phone?.includes(search)
    )
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-serif font-bold">Students</h1>
          <p className="text-[hsl(var(--muted-foreground))]">
            Manage your students and their access
          </p>
        </div>
        <button className="btn btn-primary">
          <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Add Student
        </button>
      </div>

      {/* Filters */}
      <div className="card p-4">
        <div className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-[200px]">
            <input
              type="text"
              placeholder="Search students..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="input"
            />
          </div>
          <select
            value={subjectFilter}
            onChange={(e) => setSubjectFilter(e.target.value)}
            className="input w-auto"
          >
            <option value="">All Subjects</option>
            <option value="English">English</option>
            <option value="Russian">Russian</option>
          </select>
          <select
            value={levelFilter}
            onChange={(e) => setLevelFilter(e.target.value)}
            className="input w-auto"
          >
            <option value="">All Levels</option>
            <option value="Starter">Starter</option>
            <option value="Elementary">Elementary</option>
            <option value="Pre-Intermediate">Pre-Intermediate</option>
            <option value="Intermediate">Intermediate</option>
            <option value="Upper-Intermediate">Upper-Intermediate</option>
            <option value="Advanced">Advanced</option>
          </select>
        </div>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 border-3 border-[hsl(var(--primary))]/30 border-t-[hsl(var(--primary))] rounded-full animate-spin" />
        </div>
      ) : error ? (
        <div className="card p-6 text-center text-red-600">{error}</div>
      ) : (
        <div className="card overflow-hidden">
          <table className="table">
            <thead>
              <tr>
                <th>Student</th>
                <th>Login ID</th>
                <th>Subject</th>
                <th>Level</th>
                <th>Phone</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredStudents.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-8 text-[hsl(var(--muted-foreground))]">
                    No students found
                  </td>
                </tr>
              ) : (
                filteredStudents.map((student) => (
                  <tr key={student.id}>
                    <td>
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-[hsl(var(--primary))]/10 flex items-center justify-center text-[hsl(var(--primary))] font-medium text-sm">
                          {student.first_name?.charAt(0) || '?'}
                        </div>
                        <div>
                          <p className="font-medium">
                            {student.first_name} {student.last_name}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="font-mono text-sm">{student.login_id}</td>
                    <td>
                      <span className={`badge ${student.subject === 'English' ? 'badge-primary' : 'badge-secondary'}`}>
                        {student.subject}
                      </span>
                    </td>
                    <td>{student.level || '-'}</td>
                    <td>{student.phone || '-'}</td>
                    <td>
                      <span className={`badge ${student.access_enabled ? 'badge-success' : 'badge-outline'}`}>
                        {student.access_enabled ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleToggleAccess(student.id)}
                          className="btn btn-ghost text-xs h-8 px-2"
                          title={student.access_enabled ? 'Disable access' : 'Enable access'}
                        >
                          {student.access_enabled ? 'Disable' : 'Enable'}
                        </button>
                        <button className="btn btn-ghost text-xs h-8 px-2">
                          Edit
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card p-4 text-center">
          <p className="text-2xl font-bold">{filteredStudents.length}</p>
          <p className="text-sm text-[hsl(var(--muted-foreground))]">Total Students</p>
        </div>
        <div className="card p-4 text-center">
          <p className="text-2xl font-bold text-green-600">
            {filteredStudents.filter((s) => s.access_enabled).length}
          </p>
          <p className="text-sm text-[hsl(var(--muted-foreground))]">Active</p>
        </div>
        <div className="card p-4 text-center">
          <p className="text-2xl font-bold">
            {filteredStudents.filter((s) => s.subject === 'English').length}
          </p>
          <p className="text-sm text-[hsl(var(--muted-foreground))]">English</p>
        </div>
        <div className="card p-4 text-center">
          <p className="text-2xl font-bold">
            {filteredStudents.filter((s) => s.subject === 'Russian').length}
          </p>
          <p className="text-sm text-[hsl(var(--muted-foreground))]">Russian</p>
        </div>
      </div>
    </div>
  )
}
