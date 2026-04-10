'use client'

import { useState } from 'react'
import DashboardLayout from '@/components/DashboardLayout'
import { Plus, Edit2, Trash2, Eye, BarChart3 } from 'lucide-react'

export default function TeacherTests() {
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [selectedTest, setSelectedTest] = useState<any>(null)
  const [testName, setTestName] = useState('')
  const [testType, setTestType] = useState('')

  const tests = [
    { id: 1, name: 'Midterm Exam - Unit 1-3', group: 'Advanced English', date: '2026-04-15', totalQuestions: 50, avgScore: 78 },
    { id: 2, name: 'Grammar Quiz 1', group: 'Grammar Basics', date: '2026-04-12', totalQuestions: 20, avgScore: 85 },
    { id: 3, name: 'Speaking Assessment', group: 'Speaking Club', date: '2026-04-18', totalQuestions: 10, avgScore: 82 },
    { id: 4, name: 'Vocabulary Test', group: 'Advanced English', date: '2026-04-20', totalQuestions: 30, avgScore: 88 },
  ]

  return (
    <DashboardLayout role="teacher" userName="Fatima">
      <div className="space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-text-primary mb-2">Tests & Exams</h1>
            <p className="text-text-secondary">Create and manage student assessments</p>
          </div>
          <button 
            onClick={() => setShowCreateModal(true)}
            className="px-6 py-2 rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors font-medium flex items-center gap-2 active:scale-95"
          >
            <Plus size={20} />
            Create Test
          </button>
        </div>

        {/* Tests List */}
        <div className="space-y-4">
          {tests.map((test) => (
            <div key={test.id} className="bg-surface border border-border rounded-lg p-6 hover:shadow-glass transition-all">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-text-primary mb-2">{test.name}</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <p className="text-text-secondary">Group</p>
                      <p className="font-medium text-text-primary">{test.group}</p>
                    </div>
                    <div>
                      <p className="text-text-secondary">Date</p>
                      <p className="font-medium text-text-primary">{test.date}</p>
                    </div>
                    <div>
                      <p className="text-text-secondary">Questions</p>
                      <p className="font-medium text-text-primary">{test.totalQuestions}</p>
                    </div>
                    <div>
                      <p className="text-text-secondary">Avg Score</p>
                      <p className="font-medium text-primary">{test.avgScore}%</p>
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center gap-2 ml-4">
                  <button className="p-2 rounded-lg border border-border hover:bg-surface-hover transition-colors active:scale-95">
                    <Eye size={18} className="text-text-secondary" />
                  </button>
                  <button className="p-2 rounded-lg border border-border hover:bg-surface-hover transition-colors active:scale-95">
                    <BarChart3 size={18} className="text-text-secondary" />
                  </button>
                  <button 
                    onClick={() => {
                      setSelectedTest(test)
                      setShowEditModal(true)
                    }}
                    className="p-2 rounded-lg border border-border hover:bg-surface-hover transition-colors active:scale-95"
                  >
                    <Edit2 size={18} className="text-text-secondary" />
                  </button>
                  <button 
                    onClick={() => {
                      setSelectedTest(test)
                      setShowDeleteModal(true)
                    }}
                    className="p-2 rounded-lg border border-border hover:bg-red-100 transition-colors active:scale-95"
                  >
                    <Trash2 size={18} className="text-red-500" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Create Test Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-surface rounded-lg border border-border p-6 max-w-md w-full max-h-96 overflow-y-auto">
              <h2 className="text-2xl font-bold text-text-primary mb-4">Create New Test</h2>
              <div className="space-y-4">
                <input 
                  type="text" 
                  placeholder="Test Name" 
                  value={testName}
                  onChange={(e) => setTestName(e.target.value)}
                  className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary" 
                />
                <select 
                  className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="">Select Group</option>
                  <option value="Advanced English">Advanced English</option>
                  <option value="Grammar Basics">Grammar Basics</option>
                  <option value="Speaking Club">Speaking Club</option>
                </select>
                <select 
                  value={testType}
                  onChange={(e) => setTestType(e.target.value)}
                  className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="">Select Type</option>
                  <option value="quiz">Quiz</option>
                  <option value="midterm">Midterm Exam</option>
                  <option value="final">Final Exam</option>
                  <option value="assessment">Assessment</option>
                </select>
                <input 
                  type="date" 
                  className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-primary" 
                />
                <input 
                  type="number" 
                  placeholder="Number of Questions" 
                  className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary" 
                />
              </div>
              <div className="flex gap-3 mt-6">
                <button 
                  onClick={() => {
                    setShowCreateModal(false)
                    setTestName('')
                    setTestType('')
                  }}
                  className="flex-1 px-4 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors font-medium"
                >
                  Cancel
                </button>
                <button 
                  onClick={() => {
                    setShowCreateModal(false)
                    setTestName('')
                    setTestType('')
                  }}
                  className="flex-1 px-4 py-2 rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors font-medium"
                >
                  Create Test
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Edit Test Modal */}
        {showEditModal && selectedTest && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-surface rounded-lg border border-border p-6 max-w-md w-full">
              <h2 className="text-2xl font-bold text-text-primary mb-4">Edit Test</h2>
              <div className="space-y-4">
                <input 
                  type="text" 
                  defaultValue={selectedTest.name}
                  placeholder="Test Name" 
                  className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary" 
                />
                <select 
                  defaultValue={selectedTest.group}
                  className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="Advanced English">Advanced English</option>
                  <option value="Grammar Basics">Grammar Basics</option>
                  <option value="Speaking Club">Speaking Club</option>
                </select>
                <input 
                  type="date" 
                  defaultValue={selectedTest.date}
                  className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-primary" 
                />
              </div>
              <div className="flex gap-3 mt-6">
                <button 
                  onClick={() => {
                    setShowEditModal(false)
                    setSelectedTest(null)
                  }}
                  className="flex-1 px-4 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors font-medium"
                >
                  Cancel
                </button>
                <button 
                  onClick={() => {
                    setShowEditModal(false)
                    setSelectedTest(null)
                  }}
                  className="flex-1 px-4 py-2 rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors font-medium"
                >
                  Save Changes
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Delete Test Modal */}
        {showDeleteModal && selectedTest && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-surface rounded-lg border border-border p-6 max-w-md w-full">
              <h2 className="text-2xl font-bold text-red-600 mb-2">Delete Test</h2>
              <p className="text-text-secondary mb-6">Are you sure you want to delete <span className="font-semibold">{selectedTest.name}</span>? This action cannot be undone.</p>
              <div className="flex gap-3">
                <button 
                  onClick={() => {
                    setShowDeleteModal(false)
                    setSelectedTest(null)
                  }}
                  className="flex-1 px-4 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors font-medium"
                >
                  Cancel
                </button>
                <button 
                  onClick={() => {
                    setShowDeleteModal(false)
                    setSelectedTest(null)
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
