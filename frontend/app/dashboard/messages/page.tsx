'use client'

import { useEffect, useState } from 'react'
import { messagesApi, Message, usersApi, User } from '@/lib/api'

export default function MessagesPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [activeFolder, setActiveFolder] = useState<'inbox' | 'sent'>('inbox')
  const [showComposeModal, setShowComposeModal] = useState(false)
  const [selectedMessage, setSelectedMessage] = useState<Message | null>(null)
  const [composeData, setComposeData] = useState({
    recipient_id: '',
    subject: '',
    content: '',
  })
  const [isSending, setIsSending] = useState(false)

  useEffect(() => {
    fetchMessages()
    fetchUsers()
  }, [activeFolder])

  const fetchMessages = async () => {
    try {
      setIsLoading(true)
      const data = await messagesApi.list(activeFolder)
      setMessages(data.messages || [])
    } catch (err) {
      console.error('Failed to load messages:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const fetchUsers = async () => {
    try {
      const data = await usersApi.list({ limit: 200 })
      setUsers(data.users || [])
    } catch (err) {
      console.error('Failed to load users:', err)
    }
  }

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!composeData.recipient_id || !composeData.subject || !composeData.content) return

    try {
      setIsSending(true)
      await messagesApi.send({
        recipient_id: parseInt(composeData.recipient_id),
        subject: composeData.subject,
        content: composeData.content,
      })
      setShowComposeModal(false)
      setComposeData({ recipient_id: '', subject: '', content: '' })
      if (activeFolder === 'sent') fetchMessages()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to send message')
    } finally {
      setIsSending(false)
    }
  }

  const handleMarkRead = async (id: number) => {
    try {
      await messagesApi.markRead(id)
      fetchMessages()
    } catch (err) {
      console.error('Failed to mark as read:', err)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this message?')) return
    try {
      await messagesApi.delete(id)
      fetchMessages()
      setSelectedMessage(null)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete message')
    }
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const days = Math.floor(diff / (1000 * 60 * 60 * 24))
    
    if (days === 0) {
      return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
    } else if (days === 1) {
      return 'Yesterday'
    } else if (days < 7) {
      return date.toLocaleDateString('en-US', { weekday: 'short' })
    }
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-serif font-bold">Messages</h1>
          <p className="text-[hsl(var(--muted-foreground))]">
            Communicate with students and teachers
          </p>
        </div>
        <button onClick={() => setShowComposeModal(true)} className="btn btn-primary">
          <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
          Compose
        </button>
      </div>

      {/* Folder Tabs */}
      <div className="flex gap-2 border-b border-[hsl(var(--border))]">
        <button
          onClick={() => setActiveFolder('inbox')}
          className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
            activeFolder === 'inbox'
              ? 'border-[hsl(var(--primary))] text-[hsl(var(--primary))]'
              : 'border-transparent text-[hsl(var(--muted-foreground))] hover:text-foreground'
          }`}
        >
          Inbox
        </button>
        <button
          onClick={() => setActiveFolder('sent')}
          className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
            activeFolder === 'sent'
              ? 'border-[hsl(var(--primary))] text-[hsl(var(--primary))]'
              : 'border-transparent text-[hsl(var(--muted-foreground))] hover:text-foreground'
          }`}
        >
          Sent
        </button>
      </div>

      {/* Messages List */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 border-3 border-[hsl(var(--primary))]/30 border-t-[hsl(var(--primary))] rounded-full animate-spin" />
        </div>
      ) : messages.length === 0 ? (
        <div className="card p-12 text-center">
          <svg className="w-12 h-12 mx-auto text-[hsl(var(--muted-foreground))] mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
          <p className="text-[hsl(var(--muted-foreground))]">
            {activeFolder === 'inbox' ? 'Your inbox is empty' : 'No sent messages'}
          </p>
        </div>
      ) : (
        <div className="card divide-y divide-[hsl(var(--border))]">
          {messages.map((message) => (
            <div
              key={message.id}
              onClick={() => {
                setSelectedMessage(message)
                if (!message.is_read && activeFolder === 'inbox') {
                  handleMarkRead(message.id)
                }
              }}
              className={`p-4 cursor-pointer hover:bg-[hsl(var(--muted))/0.5] transition-colors ${
                !message.is_read && activeFolder === 'inbox' ? 'bg-[hsl(var(--primary))]/5' : ''
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    {!message.is_read && activeFolder === 'inbox' && (
                      <div className="w-2 h-2 rounded-full bg-[hsl(var(--primary))]" />
                    )}
                    <p className={`font-medium truncate ${!message.is_read && activeFolder === 'inbox' ? 'text-[hsl(var(--primary))]' : ''}`}>
                      {activeFolder === 'inbox'
                        ? `${message.sender_name} ${message.sender_last_name}`
                        : `${message.recipient_name} ${message.recipient_last_name}`}
                    </p>
                  </div>
                  <p className="text-sm font-medium truncate">{message.subject}</p>
                  <p className="text-sm text-[hsl(var(--muted-foreground))] truncate">{message.content}</p>
                </div>
                <span className="text-xs text-[hsl(var(--muted-foreground))] whitespace-nowrap">
                  {formatDate(message.created_at)}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Compose Modal */}
      {showComposeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="card p-6 w-full max-w-lg animate-fadeIn">
            <h2 className="text-xl font-semibold mb-4">New Message</h2>
            <form onSubmit={handleSend} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1.5">To</label>
                <select
                  value={composeData.recipient_id}
                  onChange={(e) => setComposeData({ ...composeData, recipient_id: e.target.value })}
                  className="input"
                  required
                >
                  <option value="">Select recipient</option>
                  {users.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.first_name} {u.last_name} ({u.login_id})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">Subject</label>
                <input
                  type="text"
                  value={composeData.subject}
                  onChange={(e) => setComposeData({ ...composeData, subject: e.target.value })}
                  className="input"
                  placeholder="Message subject"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">Message</label>
                <textarea
                  value={composeData.content}
                  onChange={(e) => setComposeData({ ...composeData, content: e.target.value })}
                  className="input h-32 resize-none"
                  placeholder="Write your message..."
                  required
                />
              </div>
              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowComposeModal(false)}
                  className="btn btn-outline flex-1"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSending}
                  className="btn btn-primary flex-1"
                >
                  {isSending ? 'Sending...' : 'Send Message'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* View Message Modal */}
      {selectedMessage && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="card p-6 w-full max-w-lg animate-fadeIn">
            <div className="flex items-start justify-between mb-4">
              <div>
                <p className="text-sm text-[hsl(var(--muted-foreground))]">
                  {activeFolder === 'inbox' ? 'From' : 'To'}:{' '}
                  <span className="font-medium text-foreground">
                    {activeFolder === 'inbox'
                      ? `${selectedMessage.sender_name} ${selectedMessage.sender_last_name}`
                      : `${selectedMessage.recipient_name} ${selectedMessage.recipient_last_name}`}
                  </span>
                </p>
                <h2 className="text-lg font-semibold mt-1">{selectedMessage.subject}</h2>
              </div>
              <button
                onClick={() => setSelectedMessage(null)}
                className="btn btn-ghost h-8 w-8 p-0"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="border-t border-[hsl(var(--border))] pt-4 mb-4">
              <p className="whitespace-pre-wrap">{selectedMessage.content}</p>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-[hsl(var(--muted-foreground))]">
                {new Date(selectedMessage.created_at).toLocaleString()}
              </span>
              <button
                onClick={() => handleDelete(selectedMessage.id)}
                className="btn btn-ghost text-red-500 text-xs h-8 px-3"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
