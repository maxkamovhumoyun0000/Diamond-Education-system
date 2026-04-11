"use client";

import { useState } from "react";

export default function AIGeneratorPage() {
  const [activeTab, setActiveTab] = useState("Generate Courses");
  const [formData, setFormData] = useState({
    title: "",
    level: "Beginner",
    duration: "4",
  });

  const tabs = ["Generate Courses", "Generate Lessons", "Generate Questions", "Generate Materials"];

  const recentGenerations = [
    "Business English Course",
    "Speaking Practice Lesson",
    "Vocabulary Quiz",
    "Grammar Study Guide",
  ];

  const aiModels = [
    { name: "GPT-4 Advanced", description: "High quality, creative content generation" },
    { name: "Claude 3", description: "Detailed analysis and structured output" },
    { name: "Gemini Pro", description: "Fast generation, good for simple tasks" },
  ];

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-[#2563eb] rounded-lg text-white">
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">AI Content Generator</h1>
          <p className="text-gray-500">Generate courses, lessons, and educational content using AI</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-6 border-b border-gray-200 mb-6">
        {tabs.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`pb-3 border-b-2 transition text-sm font-medium ${
              activeTab === tab
                ? "border-[#2563eb] text-[#2563eb]"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Generate Content Form */}
        <div className="bg-white rounded-xl p-6 border border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Generate Content</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Course Title</label>
              <input
                type="text"
                placeholder="e.g., Business English Basics"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb]"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Level</label>
              <select
                value={formData.level}
                onChange={(e) => setFormData({ ...formData, level: e.target.value })}
                className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb]"
              >
                <option>Beginner</option>
                <option>Intermediate</option>
                <option>Advanced</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Duration (weeks)</label>
              <input
                type="number"
                value={formData.duration}
                onChange={(e) => setFormData({ ...formData, duration: e.target.value })}
                className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb]"
              />
            </div>
            <button className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-green-500 text-white rounded-lg hover:bg-green-600 transition font-medium">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
              Generate Content
            </button>
          </div>

          {/* Recent Generations */}
          <div className="mt-8">
            <h3 className="text-sm font-medium text-gray-700 mb-3">Recent Generations</h3>
            <div className="space-y-2">
              {recentGenerations.map((item, index) => (
                <div key={index} className="p-3 bg-gray-50 rounded-lg text-sm text-gray-600 hover:bg-gray-100 cursor-pointer transition">
                  {item}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Generated Content Preview */}
        <div className="bg-white rounded-xl p-6 border border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Generated Content</h2>
          <div className="h-64 flex items-center justify-center border-2 border-dashed border-gray-200 rounded-lg">
            <div className="text-center">
              <svg className="w-12 h-12 text-gray-300 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
              <p className="text-gray-500">Fill in the form and click &quot;Generate Content&quot; to create AI-powered educational materials.</p>
            </div>
          </div>
        </div>
      </div>

      {/* AI Models */}
      <div className="bg-white rounded-xl p-6 border border-gray-100 mt-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">AI Models</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {aiModels.map((model, index) => (
            <div
              key={index}
              className={`p-4 rounded-lg border-2 cursor-pointer transition ${
                index === 0 ? "border-[#2563eb] bg-blue-50" : "border-gray-200 hover:border-gray-300"
              }`}
            >
              <h3 className="font-semibold text-gray-900">{model.name}</h3>
              <p className="text-sm text-gray-500 mt-1">{model.description}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
