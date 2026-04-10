import DashboardLayout from '@/components/DashboardLayout'
import { Calendar, AlertCircle, CheckCircle, Clock, Download, Upload } from 'lucide-react'

export default function StudentHomework() {
  const assignments = [
    {
      id: 1,
      title: 'Essay: My Future Plans',
      description: 'Write a 300-word essay about your future career goals',
      subject: 'Writing',
      dueDate: '2024-03-20',
      status: 'pending',
      submittedDate: null,
      score: null,
      instructions: 'Use past, present, and future tenses appropriately',
    },
    {
      id: 2,
      title: 'Grammar Exercise Set 5',
      description: 'Complete 50 grammar questions on tenses and modals',
      subject: 'Grammar',
      dueDate: '2024-03-18',
      status: 'submitted',
      submittedDate: '2024-03-15',
      score: 92,
      instructions: 'Choose the correct answer for each sentence',
    },
    {
      id: 3,
      title: 'Listening Comprehension',
      description: 'Listen to the audio and answer comprehension questions',
      subject: 'Listening',
      dueDate: '2024-03-15',
      status: 'completed',
      submittedDate: '2024-03-13',
      score: 88,
      instructions: 'Watch the video and answer 10 questions',
    },
    {
      id: 4,
      title: 'Vocabulary Task: Business Terms',
      description: 'Learn and use 20 new business vocabulary words',
      subject: 'Vocabulary',
      dueDate: '2024-03-22',
      status: 'pending',
      submittedDate: null,
      score: null,
      instructions: 'Create sentences using each word in context',
    },
    {
      id: 5,
      title: 'Speaking Practice Recording',
      description: 'Record a 3-minute speech on your favorite hobby',
      subject: 'Speaking',
      dueDate: '2024-03-25',
      status: 'pending',
      submittedDate: null,
      score: null,
      instructions: 'Use linking words and maintain good pronunciation',
    },
    {
      id: 6,
      title: 'Reading Comprehension',
      description: 'Read the article and answer analytical questions',
      subject: 'Reading',
      dueDate: '2024-03-10',
      status: 'completed',
      submittedDate: '2024-03-09',
      score: 95,
      instructions: 'Answer questions about the main ideas and details',
    },
  ]

  const getDaysUntilDue = (date: string) => {
    const due = new Date(date)
    const today = new Date()
    const diff = Math.ceil((due.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
    return diff
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-500/10 text-green-600 border-green-500/20'
      case 'submitted':
        return 'bg-blue-500/10 text-blue-600 border-blue-500/20'
      case 'pending':
        return 'bg-orange-500/10 text-orange-600 border-orange-500/20'
      default:
        return 'bg-gray-500/10 text-gray-600 border-gray-500/20'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle size={20} />
      case 'submitted':
        return <Upload size={20} />
      case 'pending':
        return <AlertCircle size={20} />
      default:
        return null
    }
  }

  return (
    <DashboardLayout role="student" userName="Ahmed">
      <div className="space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-4xl font-bold text-text-primary mb-2">My Homework</h1>
          <p className="text-text-secondary">Track and submit your assignments</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[
            { label: 'Total Assigned', value: assignments.length, color: 'text-primary' },
            { label: 'Completed', value: assignments.filter(a => a.status === 'completed').length, color: 'text-green-500' },
            { label: 'Submitted', value: assignments.filter(a => a.status === 'submitted').length, color: 'text-blue-500' },
            { label: 'Pending', value: assignments.filter(a => a.status === 'pending').length, color: 'text-orange-500' },
          ].map((stat) => (
            <div key={stat.label} className="bg-surface border border-border rounded-lg p-4">
              <p className="text-sm text-text-secondary mb-1">{stat.label}</p>
              <p className={`text-3xl font-bold ${stat.color}`}>{stat.value}</p>
            </div>
          ))}
        </div>

        {/* Assignments List */}
        <div className="space-y-4">
          <h2 className="text-2xl font-semibold text-text-primary">Your Assignments</h2>
          <div className="space-y-4">
            {assignments
              .sort((a, b) => new Date(a.dueDate).getTime() - new Date(b.dueDate).getTime())
              .map((assignment) => {
                const daysLeft = getDaysUntilDue(assignment.dueDate)
                const isOverdue = daysLeft < 0 && assignment.status === 'pending'

                return (
                  <div
                    key={assignment.id}
                    className={`rounded-lg border p-6 transition-all ${
                      assignment.status === 'completed'
                        ? 'bg-green-500/5 border-green-500/20 hover:border-green-500/50'
                        : 'bg-surface border-border hover:shadow-glass hover:border-primary'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full border text-sm font-medium ${getStatusColor(assignment.status)}`}>
                            {getStatusIcon(assignment.status)}
                            {assignment.status.charAt(0).toUpperCase() + assignment.status.slice(1)}
                          </span>
                          <span className="px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-medium">
                            {assignment.subject}
                          </span>
                        </div>
                        <h3 className="text-xl font-semibold text-text-primary mb-2">{assignment.title}</h3>
                        <p className="text-text-secondary mb-3">{assignment.description}</p>
                        <p className="text-sm text-text-secondary italic">📝 {assignment.instructions}</p>
                      </div>

                      {/* Right Column */}
                      <div className="flex flex-col items-end gap-3 flex-shrink-0">
                        {/* Due Date */}
                        <div className="text-right">
                          <p className="text-xs text-text-secondary mb-1">Due Date</p>
                          <p className="font-semibold text-text-primary">{assignment.dueDate}</p>
                          {assignment.status === 'pending' && (
                            <p className={`text-xs font-medium mt-1 ${isOverdue ? 'text-red-600' : 'text-orange-600'}`}>
                              {isOverdue ? `${Math.abs(daysLeft)} days overdue` : `${daysLeft} days left`}
                            </p>
                          )}
                        </div>

                        {/* Score */}
                        {assignment.score !== null && (
                          <div className="text-right">
                            <p className="text-xs text-text-secondary mb-1">Your Score</p>
                            <p className={`text-2xl font-bold ${assignment.score >= 80 ? 'text-green-500' : assignment.score >= 60 ? 'text-orange-500' : 'text-red-500'}`}>
                              {assignment.score}%
                            </p>
                          </div>
                        )}

                        {/* Actions */}
                        {assignment.status === 'pending' && (
                          <button className="px-4 py-2 rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors font-medium text-sm">
                            Submit
                          </button>
                        )}
                        {(assignment.status === 'submitted' || assignment.status === 'completed') && (
                          <button className="px-4 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors font-medium text-sm flex items-center gap-2">
                            <Download size={16} />
                            Download
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
          </div>
        </div>

        {/* Info Box */}
        <div className="p-4 rounded-lg bg-accent/10 border border-accent/20">
          <p className="text-sm text-text-primary">
            <span className="font-semibold">Tip:</span> Submit assignments before the due date for the best grades. Late submissions may have point deductions.
          </p>
        </div>
      </div>
    </DashboardLayout>
  )
}
