'use client'

import { useState, useRef, useEffect } from 'react'
import { Send, MessageCircle, X, Minimize2, Maximize2 } from 'lucide-react'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
}

interface DiamondAIChatProps {
  userRole: 'student' | 'teacher' | 'admin' | 'support'
}

const initialMessages: Message[] = [
  {
    id: '1',
    role: 'assistant',
    content: 'Hello! I\'m Diamond AI, your personal learning assistant. How can I help you today?',
    timestamp: 0,
  },
]

export default function DiamondAIChat({ userRole }: DiamondAIChatProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [isMinimized, setIsMinimized] = useState(false)
  const [messages, setMessages] = useState<Message[]>(initialMessages)
  const [inputValue, setInputValue] = useState('')
  const [loading, setLoading] = useState(false)
  const [messageCount, setMessageCount] = useState(0)
  const [showLimitWarning, setShowLimitWarning] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const STUDENT_MESSAGE_LIMIT = 3
  const isStudent = userRole === 'student'
  const isLimitReached = isStudent && messageCount >= STUDENT_MESSAGE_LIMIT

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const generateAIResponse = (userMessage: string): string => {
    const responses: Record<string, string[]> = {
      hello: [
        'Hello! How can I assist you with your learning today?',
        'Hi there! What would you like to learn about?',
        'Hello! I\'m here to help. What\'s on your mind?',
      ],
      homework: [
        'I can help you with your homework! What subject are you working on?',
        'Tell me about your assignment and I\'ll provide guidance.',
        'Let\'s break down your homework together. What\'s the topic?',
      ],
      vocabulary: [
        'Great! Learning vocabulary is essential. What words would you like to learn?',
        'I can teach you new vocabulary words and their usage. What interests you?',
        'Let\'s expand your vocabulary! Any specific topic?',
      ],
      lesson: [
        'Which lesson would you like help with?',
        'I can explain any lesson concept to you. What would you like to understand better?',
        'Tell me which lesson you\'re studying and I\'ll help clarify it.',
      ],
      grammar: [
        'Grammar is important! What grammar rule would you like to understand?',
        'Let me help you with grammar. What\'s confusing you?',
        'I\'d be happy to explain grammar rules. What do you need help with?',
      ],
      test: [
        'Would you like to practice for an upcoming test? I can quiz you!',
        'Let\'s prepare for your test! What subject should we focus on?',
        'I can help you study for your test. What topics do you need to cover?',
      ],
    }

    const lowerMessage = userMessage.toLowerCase()
    
    for (const [keyword, responseList] of Object.entries(responses)) {
      if (lowerMessage.includes(keyword)) {
        return responseList[Math.floor(Math.random() * responseList.length)]
      }
    }

    const defaultResponses = [
      'That\'s interesting! Can you tell me more about what you need help with?',
      'I understand. How can I assist you further?',
      'Thank you for sharing. Would you like tips on this topic?',
      'Great question! Let me provide you with some helpful information on that.',
      'I\'m here to help! Can you be more specific about your question?',
    ]

    return defaultResponses[Math.floor(Math.random() * defaultResponses.length)]
  }

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return

    // Check student limit
    if (isLimitReached) {
      setShowLimitWarning(true)
      setTimeout(() => setShowLimitWarning(false), 4000)
      return
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue,
      timestamp: Date.now(),
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setLoading(true)

    // Update message count for students
    if (isStudent) {
      setMessageCount(prev => prev + 1)
    }

    // Simulate AI response delay
    setTimeout(() => {
      const aiResponse: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: generateAIResponse(inputValue),
        timestamp: Date.now(),
      }
      setMessages(prev => [...prev, aiResponse])
      setLoading(false)
    }, 800)
  }

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-40 p-4 rounded-full bg-primary text-white shadow-lg hover:shadow-xl hover:scale-110 transition-all active:scale-95"
        title="Open Diamond AI Chat"
      >
        <MessageCircle size={24} />
      </button>
    )
  }

  return (
    <div className={`fixed bottom-6 right-6 z-50 transition-all ${isMinimized ? 'h-14' : 'h-96'} w-96 max-w-[calc(100vw-32px)]`}>
      <div className="bg-surface border border-border rounded-lg shadow-2xl flex flex-col h-full overflow-hidden">
        {/* Header */}
        <div className="bg-primary text-white p-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MessageCircle size={20} />
            <div>
              <h3 className="font-semibold">Diamond AI</h3>
              {isStudent && (
                <p className="text-xs text-primary-light">Messages: {messageCount}/{STUDENT_MESSAGE_LIMIT}</p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsMinimized(!isMinimized)}
              className="p-1 hover:bg-primary-dark rounded-lg transition-colors"
              title={isMinimized ? 'Expand' : 'Minimize'}
            >
              {isMinimized ? <Maximize2 size={18} /> : <Minimize2 size={18} />}
            </button>
            <button
              onClick={() => setIsOpen(false)}
              className="p-1 hover:bg-primary-dark rounded-lg transition-colors"
              title="Close chat"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {!isMinimized && (
          <>
            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-xs px-4 py-2 rounded-lg ${
                      message.role === 'user'
                        ? 'bg-primary text-white rounded-br-none'
                        : 'bg-surface-hover text-text-primary rounded-bl-none border border-border'
                    }`}
                  >
                    <p className="text-sm">{message.content}</p>
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex justify-start">
                  <div className="bg-surface-hover text-text-primary rounded-lg rounded-bl-none border border-border px-4 py-2">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-text-secondary rounded-full animate-bounce" />
                      <div className="w-2 h-2 bg-text-secondary rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                      <div className="w-2 h-2 bg-text-secondary rounded-full animate-bounce" style={{ animationDelay: '0.4s' }} />
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Warning Message */}
            {showLimitWarning && isStudent && (
              <div className="bg-red-100 border border-red-300 text-red-700 px-4 py-2 text-xs">
                <p className="font-semibold">Limit Reached!</p>
                <p>You&apos;ve used {STUDENT_MESSAGE_LIMIT} messages. Next message will cost 5 D&apos;Coins.</p>
              </div>
            )}

            {/* Input */}
            <div className="border-t border-border p-3 flex gap-2">
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && !loading && handleSendMessage()}
                placeholder={isLimitReached && isStudent ? 'Limit reached (-5 D\'Coins)' : 'Ask anything...'}
                disabled={loading}
                className="flex-1 px-3 py-2 border border-border rounded-lg bg-surface text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
              />
              <button
                onClick={handleSendMessage}
                disabled={!inputValue.trim() || loading}
                className="p-2 rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors disabled:opacity-50 active:scale-95"
              >
                <Send size={18} />
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
