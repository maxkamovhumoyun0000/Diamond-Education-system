'use client'

import { useState } from 'react'
import DashboardLayout from '@/components/DashboardLayout'
import { Sparkles, Send, Copy, Trash2, Download, Plus } from 'lucide-react'

export default function AdminAIGenerator() {
  const [activeTab, setActiveTab] = useState('courses')
  const [generatePrompt, setGeneratePrompt] = useState('')
  const [generatedContent, setGeneratedContent] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)

  const handleGenerate = async () => {
    setIsGenerating(true)
    // Simulate generation delay
    setTimeout(() => {
      setGeneratedContent(`Generated content for: "${generatePrompt}"\n\nThis is a sample AI-generated course description or lesson plan that would be created based on your prompt. The AI system can help generate:\n- Course descriptions\n- Lesson plans\n- Quiz questions\n- Learning materials\n\nYou can copy this content to the clipboard or download it for further editing.`)
      setIsGenerating(false)
    }, 2000)
  }

  const copyToClipboard = () => {
    navigator.clipboard.writeText(generatedContent)
  }

  return (
    <DashboardLayout role="admin" userName="Admin">
      <div className="space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-4xl font-bold text-text-primary mb-2 flex items-center gap-3">
            <Sparkles className="w-8 h-8 text-accent" />
            AI Content Generator
          </h1>
          <p className="text-text-secondary">Generate courses, lessons, and educational content using AI</p>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 border-b border-border overflow-x-auto">
          {[
            { id: 'courses', label: 'Generate Courses' },
            { id: 'lessons', label: 'Generate Lessons' },
            { id: 'questions', label: 'Generate Questions' },
            { id: 'materials', label: 'Generate Materials' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-3 font-medium whitespace-nowrap border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-primary text-primary'
                  : 'border-transparent text-text-secondary hover:text-text-primary'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Generator Interface */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Input Panel */}
          <div className="lg:col-span-1 space-y-4">
            <div className="bg-surface border border-border rounded-lg p-6">
              <h2 className="text-lg font-semibold text-text-primary mb-4">Generate Content</h2>
              
              <div className="space-y-4">
                {activeTab === 'courses' && (
                  <>
                    <div>
                      <label className="block text-sm font-medium text-text-primary mb-2">Course Title</label>
                      <input
                        type="text"
                        placeholder="e.g., Business English Basics"
                        className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-text-primary mb-2">Level</label>
                      <select className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-primary">
                        <option>Beginner</option>
                        <option>Intermediate</option>
                        <option>Advanced</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-text-primary mb-2">Duration (weeks)</label>
                      <input
                        type="number"
                        placeholder="4"
                        className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary"
                      />
                    </div>
                  </>
                )}

                {activeTab === 'lessons' && (
                  <>
                    <div>
                      <label className="block text-sm font-medium text-text-primary mb-2">Lesson Topic</label>
                      <input
                        type="text"
                        placeholder="e.g., Present Perfect Tense"
                        className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-text-primary mb-2">Duration (minutes)</label>
                      <input
                        type="number"
                        placeholder="30"
                        className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-text-primary mb-2">Target Audience</label>
                      <select className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-primary">
                        <option>All Levels</option>
                        <option>Beginners</option>
                        <option>Intermediate</option>
                      </select>
                    </div>
                  </>
                )}

                {activeTab === 'questions' && (
                  <>
                    <div>
                      <label className="block text-sm font-medium text-text-primary mb-2">Topic</label>
                      <input
                        type="text"
                        placeholder="e.g., English Grammar"
                        className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-text-primary mb-2">Question Type</label>
                      <select className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-primary">
                        <option>Multiple Choice</option>
                        <option>True/False</option>
                        <option>Short Answer</option>
                        <option>Essay</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-text-primary mb-2">Number of Questions</label>
                      <input
                        type="number"
                        placeholder="10"
                        className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary"
                      />
                    </div>
                  </>
                )}

                {activeTab === 'materials' && (
                  <>
                    <div>
                      <label className="block text-sm font-medium text-text-primary mb-2">Material Type</label>
                      <select className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-primary">
                        <option>Study Guide</option>
                        <option>Worksheet</option>
                        <option>Infographic</option>
                        <option>Summary</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-text-primary mb-2">Topic/Subject</label>
                      <input
                        type="text"
                        placeholder="e.g., Vocabulary Building"
                        className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-text-primary mb-2">Additional Details</label>
                      <textarea
                        placeholder="Any specific requirements..."
                        rows={3}
                        className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary"
                      />
                    </div>
                  </>
                )}

                <button
                  onClick={handleGenerate}
                  disabled={isGenerating}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-accent text-white hover:opacity-90 disabled:opacity-50 transition-all font-medium"
                >
                  <Sparkles size={20} />
                  {isGenerating ? 'Generating...' : 'Generate Content'}
                </button>
              </div>
            </div>

            {/* Recent Generations */}
            <div className="bg-surface border border-border rounded-lg p-6">
              <h3 className="text-sm font-semibold text-text-primary mb-3">Recent Generations</h3>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {[
                  'Business English Course',
                  'Speaking Practice Lesson',
                  'Vocabulary Quiz',
                  'Grammar Study Guide',
                ].map((item, i) => (
                  <button
                    key={i}
                    className="w-full text-left px-3 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors text-sm text-text-primary"
                  >
                    {item}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Output Panel */}
          <div className="lg:col-span-2">
            <div className="bg-surface border border-border rounded-lg p-6 sticky top-4 max-h-[calc(100vh-120px)] overflow-y-auto">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-text-primary">Generated Content</h2>
                {generatedContent && (
                  <div className="flex gap-2">
                    <button
                      onClick={copyToClipboard}
                      className="p-2 hover:bg-surface-hover rounded-lg transition-colors"
                      title="Copy to clipboard"
                    >
                      <Copy size={20} className="text-text-secondary" />
                    </button>
                    <button
                      className="p-2 hover:bg-surface-hover rounded-lg transition-colors"
                      title="Download"
                    >
                      <Download size={20} className="text-text-secondary" />
                    </button>
                  </div>
                )}
              </div>

              {!generatedContent ? (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <Sparkles className="w-12 h-12 text-text-secondary/30 mb-4" />
                  <p className="text-text-secondary">Fill in the form and click &quot;Generate Content&quot; to create AI-powered educational materials.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="bg-primary/5 border border-primary/20 rounded-lg p-4">
                    <p className="text-text-primary whitespace-pre-wrap leading-relaxed">{generatedContent}</p>
                  </div>
                  <div className="flex gap-2">
                    <button className="flex-1 px-4 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors font-medium">
                      Edit
                    </button>
                    <button className="flex-1 px-4 py-2 rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors font-medium">
                      Save to Library
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Available Models */}
        <div className="bg-surface border border-border rounded-lg p-6">
          <h2 className="text-lg font-semibold text-text-primary mb-4">AI Models</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { name: 'GPT-4 Advanced', description: 'High quality, creative content generation', status: 'Available' },
              { name: 'Claude 3', description: 'Detailed analysis and structured output', status: 'Available' },
              { name: 'Gemini Pro', description: 'Fast generation, good for simple tasks', status: 'Available' },
            ].map((model) => (
              <div key={model.name} className="border border-border rounded-lg p-4">
                <h3 className="font-semibold text-text-primary mb-2">{model.name}</h3>
                <p className="text-sm text-text-secondary mb-3">{model.description}</p>
                <span className="inline-block px-3 py-1 rounded-full text-xs font-medium bg-green-500/10 text-green-600">
                  {model.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
