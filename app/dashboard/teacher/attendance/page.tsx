'use client'

import { useState } from 'react'
import DashboardLayout from '@/components/DashboardLayout'
import { Calendar, Download, Filter, CheckCircle, XCircle } from 'lucide-react'

export default function TeacherAttendance() {
  const [selectedGroup, setSelectedGroup] = useState('all')
  const [selectedDate, setSelectedDate] = useState('')
  const [attendance, setAttendance] = useState({
    1: true, 2: true, 3: false, 4: true, 5: true, 6: false, 7: true, 8: true, 9: true, 10: true,
    11: true, 12: false, 13: true, 14: true, 15: true
  })

  const toggleAttendance = (studentId: number) => {
    setAttendance(prev => ({
      ...prev,
      [studentId]: !prev[studentId]
    }))
  }

  const students = [
    { id: 1, name: 'Ahmed Ali', group: 'Advanced English' },
    { id: 2, name: 'Fatima Khan', group: 'Advanced English' },
    { id: 3, name: 'Hassan Ali', group: 'Grammar Basics' },
    { id: 4, name: 'Aysha Hassan', group: 'Advanced English' },
    { id: 5, name: 'Omar Ibrahim', group: 'Speaking Club' },
    { id: 6, name: 'Leila Ahmed', group: 'Grammar Basics' },
    { id: 7, name: 'Karim Yousuf', group: 'Speaking Club' },
    { id: 8, name: 'Noor Khalid', group: 'Advanced English' },
    { id: 9, name: 'Huda Said', group: 'Grammar Basics' },
    { id: 10, name: 'Zainab Ibrahim', group: 'Speaking Club' },
    { id: 11, name: 'Samir Ahmed', group: 'Advanced English' },
    { id: 12, name: 'Rania Hassan', group: 'Grammar Basics' },
    { id: 13, name: 'Tariq Ali', group: 'Speaking Club' },
    { id: 14, name: 'Layla Khan', group: 'Advanced English' },
    { id: 15, name: 'Amara Khalil', group: 'Grammar Basics' },
  ]

  const groups = ['Advanced English', 'Grammar Basics', 'Speaking Club']
  const presentCount = Object.values(attendance).filter(Boolean).length
  const absentCount = Object.values(attendance).filter(a => !a).length

  return (
    <DashboardLayout role="teacher" userName="Fatima">
      <div className="space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-text-primary mb-2">Attendance</h1>
            <p className="text-text-secondary">Mark and track student attendance</p>
          </div>
          <button className="px-6 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors font-medium flex items-center gap-2 active:scale-95">
            <Download size={20} />
            Export Report
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-surface border border-border rounded-lg p-4">
            <p className="text-text-secondary text-sm mb-2">Present</p>
            <p className="text-3xl font-bold text-green-600">{presentCount}</p>
          </div>
          <div className="bg-surface border border-border rounded-lg p-4">
            <p className="text-text-secondary text-sm mb-2">Absent</p>
            <p className="text-3xl font-bold text-red-600">{absentCount}</p>
          </div>
          <div className="bg-surface border border-border rounded-lg p-4">
            <p className="text-text-secondary text-sm mb-2">Attendance Rate</p>
            <p className="text-3xl font-bold text-primary">{Math.round((presentCount / 15) * 100)}%</p>
          </div>
        </div>

        {/* Filters */}
        <div className="flex gap-4 flex-col sm:flex-row">
          <input 
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="px-4 py-2 rounded-lg border border-border bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
          />
          <select 
            value={selectedGroup}
            onChange={(e) => setSelectedGroup(e.target.value)}
            className="px-4 py-2 rounded-lg border border-border bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="all">All Groups</option>
            {groups.map(g => <option key={g} value={g}>{g}</option>)}
          </select>
        </div>

        {/* Attendance Table */}
        <div className="bg-surface border border-border rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-surface-hover border-b border-border">
                <tr>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-text-primary">Student Name</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-text-primary">Group</th>
                  <th className="px-6 py-4 text-center text-sm font-semibold text-text-primary">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {students
                  .filter(s => selectedGroup === 'all' || s.group === selectedGroup)
                  .map((student) => (
                    <tr key={student.id} className="hover:bg-surface-hover transition-colors">
                      <td className="px-6 py-4 font-medium text-text-primary">{student.name}</td>
                      <td className="px-6 py-4 text-text-secondary text-sm">{student.group}</td>
                      <td className="px-6 py-4 text-center">
                        <button 
                          onClick={() => toggleAttendance(student.id)}
                          className="inline-flex items-center gap-2 px-3 py-1 rounded-full transition-colors active:scale-95"
                          style={{
                            backgroundColor: attendance[student.id] ? 'rgb(34, 197, 94, 0.1)' : 'rgb(239, 68, 68, 0.1)'
                          }}
                        >
                          {attendance[student.id] ? (
                            <>
                              <CheckCircle size={16} className="text-green-600" />
                              <span className="text-xs font-medium text-green-600">Present</span>
                            </>
                          ) : (
                            <>
                              <XCircle size={16} className="text-red-600" />
                              <span className="text-xs font-medium text-red-600">Absent</span>
                            </>
                          )}
                        </button>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Save Button */}
        <div className="flex justify-end gap-3">
          <button className="px-6 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors font-medium active:scale-95">
            Cancel
          </button>
          <button className="px-6 py-2 rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors font-medium active:scale-95">
            Save Attendance
          </button>
        </div>
      </div>
    </DashboardLayout>
  )
}
