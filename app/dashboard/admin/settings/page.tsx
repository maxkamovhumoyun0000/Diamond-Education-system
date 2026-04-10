'use client'

import { useState } from 'react'
import DashboardLayout from '@/components/DashboardLayout'
import { Settings, Bell, Lock, Users, BarChart3, Mail, Save, AlertCircle } from 'lucide-react'

export default function AdminSettings() {
  const [activeTab, setActiveTab] = useState('general')
  const [settings, setSettings] = useState({
    siteName: 'Diamond Education',
    siteUrl: 'https://diamond-education.com',
    adminEmail: 'admin@diamond.edu',
    timezone: 'UTC+3',
    emailNotifications: true,
    systemAlerts: true,
    userReports: true,
    paymentAlerts: true,
    secureMode: true,
    twoFactor: false,
    sessionTimeout: 30,
  })

  const [unsavedChanges, setUnsavedChanges] = useState(false)

  const handleSettingChange = (key: string, value: any) => {
    setSettings(prev => ({ ...prev, [key]: value }))
    setUnsavedChanges(true)
  }

  const saveSettings = () => {
    setUnsavedChanges(false)
  }

  const tabs = [
    { id: 'general', label: 'General', icon: Settings },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'security', label: 'Security', icon: Lock },
    { id: 'users', label: 'User Management', icon: Users },
    { id: 'analytics', label: 'Analytics', icon: BarChart3 },
  ]

  return (
    <DashboardLayout role="admin" userName="Admin">
      <div className="space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-4xl font-bold text-text-primary mb-2">System Settings</h1>
          <p className="text-text-secondary">Configure system-wide settings and preferences</p>
        </div>

        {/* Unsaved Changes Alert */}
        {unsavedChanges && (
          <div className="bg-orange-50 border border-orange-200 rounded-lg p-4 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-orange-600 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <h3 className="font-semibold text-orange-900">Unsaved Changes</h3>
              <p className="text-sm text-orange-800">You have unsaved changes. Click Save to apply them.</p>
            </div>
            <button 
              onClick={saveSettings}
              className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors font-medium text-sm flex-shrink-0"
            >
              Save Changes
            </button>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-2 border-b border-border overflow-x-auto">
          {tabs.map((tab) => {
            const TabIcon = tab.icon
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-3 font-medium whitespace-nowrap border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-primary text-primary'
                    : 'border-transparent text-text-secondary hover:text-text-primary'
                }`}
              >
                <TabIcon size={18} />
                {tab.label}
              </button>
            )
          })}
        </div>

        {/* Tab Content */}
        <div className="space-y-6">
          {activeTab === 'general' && (
            <div className="space-y-6">
              <div className="bg-surface border border-border rounded-lg p-6">
                <h2 className="text-lg font-semibold text-text-primary mb-4">Basic Information</h2>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-text-primary mb-2">Site Name</label>
                    <input
                      type="text"
                      value={settings.siteName}
                      onChange={(e) => handleSettingChange('siteName', e.target.value)}
                      className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-text-primary mb-2">Site URL</label>
                    <input
                      type="url"
                      value={settings.siteUrl}
                      onChange={(e) => handleSettingChange('siteUrl', e.target.value)}
                      className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-text-primary mb-2">Admin Email</label>
                    <input
                      type="email"
                      value={settings.adminEmail}
                      onChange={(e) => handleSettingChange('adminEmail', e.target.value)}
                      className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-text-primary mb-2">Timezone</label>
                    <select
                      value={settings.timezone}
                      onChange={(e) => handleSettingChange('timezone', e.target.value)}
                      className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
                    >
                      <option>UTC+0</option>
                      <option>UTC+1</option>
                      <option>UTC+3</option>
                      <option>UTC+5</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'notifications' && (
            <div className="space-y-6">
              <div className="bg-surface border border-border rounded-lg p-6">
                <h2 className="text-lg font-semibold text-text-primary mb-4">Email Notifications</h2>
                <div className="space-y-3">
                  {[
                    { key: 'emailNotifications', label: 'Email Notifications Enabled' },
                    { key: 'systemAlerts', label: 'System Alerts' },
                    { key: 'userReports', label: 'User Activity Reports' },
                    { key: 'paymentAlerts', label: 'Payment Alerts' },
                  ].map((notification) => (
                    <label key={notification.key} className="flex items-center gap-3 p-3 border border-border rounded-lg hover:bg-surface-hover cursor-pointer">
                      <input
                        type="checkbox"
                        checked={settings[notification.key as keyof typeof settings] as boolean}
                        onChange={(e) => handleSettingChange(notification.key, e.target.checked)}
                        className="w-4 h-4"
                      />
                      <span className="text-text-primary font-medium">{notification.label}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'security' && (
            <div className="space-y-6">
              <div className="bg-surface border border-border rounded-lg p-6">
                <h2 className="text-lg font-semibold text-text-primary mb-4">Security Settings</h2>
                <div className="space-y-4">
                  <label className="flex items-center gap-3 p-3 border border-border rounded-lg hover:bg-surface-hover cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.secureMode}
                      onChange={(e) => handleSettingChange('secureMode', e.target.checked)}
                      className="w-4 h-4"
                    />
                    <span className="text-text-primary font-medium">Secure Mode (HTTPS Only)</span>
                  </label>
                  <label className="flex items-center gap-3 p-3 border border-border rounded-lg hover:bg-surface-hover cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.twoFactor}
                      onChange={(e) => handleSettingChange('twoFactor', e.target.checked)}
                      className="w-4 h-4"
                    />
                    <span className="text-text-primary font-medium">Two-Factor Authentication</span>
                  </label>
                  <div>
                    <label className="block text-sm font-medium text-text-primary mb-2">Session Timeout (minutes)</label>
                    <input
                      type="number"
                      value={settings.sessionTimeout}
                      onChange={(e) => handleSettingChange('sessionTimeout', parseInt(e.target.value))}
                      className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                  </div>
                </div>
              </div>

              <div className="bg-red-50 border border-red-200 rounded-lg p-6">
                <h3 className="text-lg font-semibold text-red-900 mb-4">Danger Zone</h3>
                <button className="px-4 py-2 rounded-lg border border-red-500 text-red-600 hover:bg-red-100 transition-colors font-medium">
                  Reset All Settings
                </button>
              </div>
            </div>
          )}

          {activeTab === 'users' && (
            <div className="bg-surface border border-border rounded-lg p-6">
              <h2 className="text-lg font-semibold text-text-primary mb-4">User Management Policies</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-text-primary mb-2">Default User Role</label>
                  <select className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-primary">
                    <option>Student</option>
                    <option>Teacher</option>
                    <option>Support</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-text-primary mb-2">Auto-Delete Inactive Accounts (days)</label>
                  <input type="number" defaultValue={365} className="w-full px-4 py-2 border border-border rounded-lg bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-primary" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-text-primary mb-2">Require Email Verification</label>
                  <label className="flex items-center gap-3 p-3 border border-border rounded-lg hover:bg-surface-hover cursor-pointer">
                    <input type="checkbox" defaultChecked className="w-4 h-4" />
                    <span className="text-text-primary font-medium">Enabled</span>
                  </label>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'analytics' && (
            <div className="bg-surface border border-border rounded-lg p-6">
              <h2 className="text-lg font-semibold text-text-primary mb-4">Analytics Configuration</h2>
              <div className="space-y-4">
                <label className="flex items-center gap-3 p-3 border border-border rounded-lg hover:bg-surface-hover cursor-pointer">
                  <input type="checkbox" defaultChecked className="w-4 h-4" />
                  <span className="text-text-primary font-medium">Track User Activity</span>
                </label>
                <label className="flex items-center gap-3 p-3 border border-border rounded-lg hover:bg-surface-hover cursor-pointer">
                  <input type="checkbox" defaultChecked className="w-4 h-4" />
                  <span className="text-text-primary font-medium">Track Page Performance</span>
                </label>
                <label className="flex items-center gap-3 p-3 border border-border rounded-lg hover:bg-surface-hover cursor-pointer">
                  <input type="checkbox" defaultChecked className="w-4 h-4" />
                  <span className="text-text-primary font-medium">Enable Heatmaps</span>
                </label>
              </div>
            </div>
          )}
        </div>

        {/* Save Button */}
        {unsavedChanges && (
          <div className="flex gap-3 justify-end">
            <button className="px-6 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors font-medium">
              Discard
            </button>
            <button 
              onClick={saveSettings}
              className="flex items-center gap-2 px-6 py-2 rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors font-medium"
            >
              <Save size={20} />
              Save Changes
            </button>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
