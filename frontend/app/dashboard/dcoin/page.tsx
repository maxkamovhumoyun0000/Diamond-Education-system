'use client'

import { useEffect, useState } from 'react'
import { dcoinApi, DCoinTransaction, LeaderboardEntry, studentsApi, User } from '@/lib/api'

export default function DCoinPage() {
  const [transactions, setTransactions] = useState<DCoinTransaction[]>([])
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([])
  const [students, setStudents] = useState<User[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'transactions' | 'leaderboard'>('transactions')
  const [showAwardModal, setShowAwardModal] = useState(false)
  const [selectedStudent, setSelectedStudent] = useState<number | null>(null)
  const [awardAmount, setAwardAmount] = useState('')
  const [awardReason, setAwardReason] = useState('')
  const [awardType, setAwardType] = useState<'reward' | 'deduction'>('reward')
  const [isAwarding, setIsAwarding] = useState(false)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      setIsLoading(true)
      const [txData, leaderData, studentsData] = await Promise.all([
        dcoinApi.getTransactions({ limit: 100 }),
        dcoinApi.getLeaderboard({ limit: 50 }),
        studentsApi.list({ limit: 200 }),
      ])
      setTransactions(txData.transactions || [])
      setLeaderboard(leaderData.leaderboard || [])
      setStudents(studentsData.students || [])
    } catch (err) {
      console.error('Failed to load data:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleAward = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedStudent || !awardAmount || !awardReason) return

    try {
      setIsAwarding(true)
      await dcoinApi.createTransaction({
        student_id: selectedStudent,
        amount: parseInt(awardAmount),
        transaction_type: awardType,
        reason: awardReason,
      })
      setShowAwardModal(false)
      setSelectedStudent(null)
      setAwardAmount('')
      setAwardReason('')
      setAwardType('reward')
      fetchData()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to create transaction')
    } finally {
      setIsAwarding(false)
    }
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-serif font-bold">{"D'Coin Management"}</h1>
          <p className="text-[hsl(var(--muted-foreground))]">
            Reward students and track transactions
          </p>
        </div>
        <button onClick={() => setShowAwardModal(true)} className="btn btn-secondary">
          <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Award D'Coin
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-[hsl(var(--border))]">
        <button
          onClick={() => setActiveTab('transactions')}
          className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
            activeTab === 'transactions'
              ? 'border-[hsl(var(--primary))] text-[hsl(var(--primary))]'
              : 'border-transparent text-[hsl(var(--muted-foreground))] hover:text-foreground'
          }`}
        >
          Transactions
        </button>
        <button
          onClick={() => setActiveTab('leaderboard')}
          className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
            activeTab === 'leaderboard'
              ? 'border-[hsl(var(--primary))] text-[hsl(var(--primary))]'
              : 'border-transparent text-[hsl(var(--muted-foreground))] hover:text-foreground'
          }`}
        >
          Leaderboard
        </button>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 border-3 border-[hsl(var(--primary))]/30 border-t-[hsl(var(--primary))] rounded-full animate-spin" />
        </div>
      ) : activeTab === 'transactions' ? (
        <div className="card overflow-hidden">
          <table className="table">
            <thead>
              <tr>
                <th>Student</th>
                <th>Amount</th>
                <th>Type</th>
                <th>Reason</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {transactions.length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-center py-8 text-[hsl(var(--muted-foreground))]">
                    No transactions yet
                  </td>
                </tr>
              ) : (
                transactions.map((tx) => (
                  <tr key={tx.id}>
                    <td>
                      <p className="font-medium">{tx.first_name} {tx.last_name}</p>
                      <p className="text-xs text-[hsl(var(--muted-foreground))]">{tx.login_id}</p>
                    </td>
                    <td>
                      <span className={`font-semibold ${tx.amount > 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {tx.amount > 0 ? '+' : ''}{tx.amount}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${
                        tx.transaction_type === 'reward' ? 'badge-success' :
                        tx.transaction_type === 'bonus' ? 'badge-secondary' :
                        tx.transaction_type === 'deduction' ? 'badge-destructive' :
                        'badge-outline'
                      }`}>
                        {tx.transaction_type}
                      </span>
                    </td>
                    <td className="max-w-[200px] truncate">{tx.reason}</td>
                    <td className="text-sm text-[hsl(var(--muted-foreground))]">
                      {formatDate(tx.created_at)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="table">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Student</th>
                <th>Subject</th>
                <th>Level</th>
                <th>{"D'Coins"}</th>
              </tr>
            </thead>
            <tbody>
              {leaderboard.length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-center py-8 text-[hsl(var(--muted-foreground))]">
                    No leaderboard data yet
                  </td>
                </tr>
              ) : (
                leaderboard.map((entry, index) => (
                  <tr key={entry.id}>
                    <td>
                      {index < 3 ? (
                        <span className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-white ${
                          index === 0 ? 'bg-yellow-500' :
                          index === 1 ? 'bg-gray-400' :
                          'bg-amber-600'
                        }`}>
                          {index + 1}
                        </span>
                      ) : (
                        <span className="text-[hsl(var(--muted-foreground))]">{index + 1}</span>
                      )}
                    </td>
                    <td>
                      <p className="font-medium">{entry.first_name} {entry.last_name}</p>
                      <p className="text-xs text-[hsl(var(--muted-foreground))]">{entry.login_id}</p>
                    </td>
                    <td>
                      <span className={`badge ${entry.subject === 'English' ? 'badge-primary' : 'badge-secondary'}`}>
                        {entry.subject}
                      </span>
                    </td>
                    <td>{entry.level || '-'}</td>
                    <td>
                      <span className="font-bold text-[hsl(var(--secondary))]">
                        {entry.total_dcoins}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Award Modal */}
      {showAwardModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="card p-6 w-full max-w-md animate-fadeIn">
            <h2 className="text-xl font-semibold mb-4">{"Award D'Coin"}</h2>
            <form onSubmit={handleAward} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1.5">Student</label>
                <select
                  value={selectedStudent || ''}
                  onChange={(e) => setSelectedStudent(parseInt(e.target.value))}
                  className="input"
                  required
                >
                  <option value="">Select a student</option>
                  {students.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.first_name} {s.last_name} ({s.login_id})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">Type</label>
                <div className="flex gap-4">
                  <label className="flex items-center gap-2">
                    <input
                      type="radio"
                      name="awardType"
                      checked={awardType === 'reward'}
                      onChange={() => setAwardType('reward')}
                      className="w-4 h-4"
                    />
                    <span>Reward</span>
                  </label>
                  <label className="flex items-center gap-2">
                    <input
                      type="radio"
                      name="awardType"
                      checked={awardType === 'deduction'}
                      onChange={() => setAwardType('deduction')}
                      className="w-4 h-4"
                    />
                    <span>Deduction</span>
                  </label>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">Amount</label>
                <input
                  type="number"
                  value={awardAmount}
                  onChange={(e) => setAwardAmount(e.target.value)}
                  className="input"
                  placeholder="Enter amount"
                  min="1"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">Reason</label>
                <textarea
                  value={awardReason}
                  onChange={(e) => setAwardReason(e.target.value)}
                  className="input h-20 resize-none"
                  placeholder="Enter reason for this transaction"
                  required
                />
              </div>
              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowAwardModal(false)}
                  className="btn btn-outline flex-1"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isAwarding}
                  className="btn btn-primary flex-1"
                >
                  {isAwarding ? 'Processing...' : 'Confirm'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
