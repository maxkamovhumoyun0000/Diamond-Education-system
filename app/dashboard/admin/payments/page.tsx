'use client'

import { useState } from 'react'
import DashboardLayout from '@/components/DashboardLayout'
import StatCard from '@/components/StatCard'
import { DollarSign, CreditCard, TrendingUp, AlertCircle, CheckCircle, Clock } from 'lucide-react'

export default function AdminPayments() {
  const [filterStatus, setFilterStatus] = useState('all')

  const payments = [
    { id: 1, user: 'Ahmed Ali', amount: '$49.99', course: 'English Course', status: 'Completed', date: '2024-03-20', method: 'Credit Card' },
    { id: 2, user: 'Fatima Khan', amount: '$99.99', course: 'Premium Bundle', status: 'Completed', date: '2024-03-19', method: 'PayPal' },
    { id: 3, user: 'Hassan Ahmed', amount: '$29.99', course: 'Speaking Class', status: 'Pending', date: '2024-03-18', method: 'Credit Card' },
    { id: 4, user: 'Aysha Hassan', amount: '$149.99', course: 'IELTS Prep', status: 'Completed', date: '2024-03-17', method: 'Bank Transfer' },
    { id: 5, user: 'Omar Ibrahim', amount: '$39.99', course: 'Writing Course', status: 'Failed', date: '2024-03-16', method: 'Credit Card' },
  ]

  const filteredPayments = payments.filter(p => filterStatus === 'all' || p.status === filterStatus)

  return (
    <DashboardLayout role="admin" userName="Admin">
      <div className="space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-text-primary mb-2">Payment Management</h1>
            <p className="text-text-secondary">Track all transactions and payment status</p>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard
            title="Total Revenue"
            value="$12,450"
            subtitle="↑ 15% from last month"
            icon={<DollarSign className="w-6 h-6 text-primary" />}
            trend={{ value: 15, isPositive: true }}
            variant="primary"
          />
          <StatCard
            title="Completed"
            value="248"
            subtitle="Successful transactions"
            icon={<CheckCircle className="w-6 h-6 text-green-500" />}
          />
          <StatCard
            title="Pending"
            value="12"
            subtitle="Awaiting confirmation"
            icon={<Clock className="w-6 h-6 text-orange-500" />}
          />
          <StatCard
            title="Failed"
            value="5"
            subtitle="Require attention"
            icon={<AlertCircle className="w-6 h-6 text-red-500" />}
          />
        </div>

        {/* Payment Methods */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { name: 'Credit Card', count: 145, color: 'bg-blue-500' },
            { name: 'PayPal', count: 98, color: 'bg-accent' },
            { name: 'Bank Transfer', count: 52, color: 'bg-green-500' },
            { name: 'Other', count: 15, color: 'bg-gray-500' },
          ].map((method) => (
            <div key={method.name} className="bg-surface border border-border rounded-lg p-4">
              <div className="flex items-center gap-3 mb-3">
                <div className={`w-3 h-3 rounded-full ${method.color}`} />
                <span className="text-sm font-medium text-text-primary">{method.name}</span>
              </div>
              <p className="text-2xl font-bold text-text-primary">{method.count}</p>
              <p className="text-xs text-text-secondary mt-1">transactions</p>
            </div>
          ))}
        </div>

        {/* Filters */}
        <div className="flex gap-2 flex-wrap">
          {['all', 'Completed', 'Pending', 'Failed'].map((status) => (
            <button
              key={status}
              onClick={() => setFilterStatus(status)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                filterStatus === status
                  ? 'bg-primary text-white'
                  : 'border border-border hover:bg-surface-hover'
              }`}
            >
              {status === 'all' ? 'All Payments' : status}
            </button>
          ))}
        </div>

        {/* Payments Table */}
        <div className="rounded-lg border border-border overflow-hidden bg-surface">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-surface-hover border-b border-border">
                <tr>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-text-primary">User</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-text-primary">Course</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-text-primary">Amount</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-text-primary">Method</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-text-primary">Status</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-text-primary">Date</th>
                  <th className="px-6 py-4 text-center text-sm font-semibold text-text-primary">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredPayments.map((payment) => (
                  <tr key={payment.id} className="hover:bg-surface-hover transition-colors">
                    <td className="px-6 py-4">
                      <span className="font-medium text-text-primary">{payment.user}</span>
                    </td>
                    <td className="px-6 py-4 text-sm text-text-secondary">{payment.course}</td>
                    <td className="px-6 py-4 font-semibold text-text-primary">{payment.amount}</td>
                    <td className="px-6 py-4 text-sm text-text-secondary">{payment.method}</td>
                    <td className="px-6 py-4">
                      <span
                        className={`px-3 py-1 rounded-full text-xs font-medium ${
                          payment.status === 'Completed'
                            ? 'bg-green-500/10 text-green-600'
                            : payment.status === 'Pending'
                            ? 'bg-orange-500/10 text-orange-600'
                            : 'bg-red-500/10 text-red-600'
                        }`}
                      >
                        {payment.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-text-secondary">{payment.date}</td>
                    <td className="px-6 py-4 text-center">
                      <button className="px-3 py-1 rounded-lg text-xs font-medium border border-border hover:bg-surface-hover transition-colors">
                        View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Summary */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-surface border border-border rounded-lg p-6">
            <h3 className="text-lg font-semibold text-text-primary mb-4">Daily Revenue</h3>
            <p className="text-3xl font-bold text-primary mb-2">$2,450</p>
            <p className="text-sm text-text-secondary">Last 24 hours</p>
          </div>
          <div className="bg-surface border border-border rounded-lg p-6">
            <h3 className="text-lg font-semibold text-text-primary mb-4">Monthly Average</h3>
            <p className="text-3xl font-bold text-accent mb-2">$3,820</p>
            <p className="text-sm text-text-secondary">Per day average</p>
          </div>
          <div className="bg-surface border border-border rounded-lg p-6">
            <h3 className="text-lg font-semibold text-text-primary mb-4">Conversion Rate</h3>
            <p className="text-3xl font-bold text-green-500 mb-2">8.2%</p>
            <p className="text-sm text-text-secondary">From visits to purchases</p>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
