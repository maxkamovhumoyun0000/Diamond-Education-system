import DashboardLayout from '@/components/DashboardLayout'
import { Bell, Lock, Globe, Eye, Mail, Save } from 'lucide-react'

export default function StudentSettings() {
  return (
    <DashboardLayout role="student" userName="Ahmed">
      <div className="space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-4xl font-bold text-text-primary mb-2">Settings</h1>
          <p className="text-text-secondary">Manage your account and preferences</p>
        </div>

        {/* Profile Section */}
        <div className="bg-surface border border-border rounded-lg p-8">
          <h2 className="text-2xl font-semibold text-text-primary mb-6">Profile Settings</h2>
          
          <div className="space-y-6">
            {/* Avatar */}
            <div className="flex items-center gap-6">
              <div className="w-20 h-20 rounded-full bg-primary/20 flex items-center justify-center text-3xl">
                👨‍🎓
              </div>
              <div>
                <button className="px-4 py-2 rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors font-medium text-sm">
                  Change Avatar
                </button>
              </div>
            </div>

            {/* Form Fields */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  Full Name
                </label>
                <input
                  type="text"
                  defaultValue="Ahmed Ali"
                  className="w-full px-4 py-2 border border-border rounded-lg bg-surface-hover text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  Email Address
                </label>
                <input
                  type="email"
                  defaultValue="ahmed@diamond.edu"
                  className="w-full px-4 py-2 border border-border rounded-lg bg-surface-hover text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  Phone Number
                </label>
                <input
                  type="tel"
                  placeholder="+971 50 123 4567"
                  className="w-full px-4 py-2 border border-border rounded-lg bg-surface-hover text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  Timezone
                </label>
                <select className="w-full px-4 py-2 border border-border rounded-lg bg-surface-hover text-text-primary focus:outline-none focus:ring-2 focus:ring-primary">
                  <option>GMT+4 (Dubai)</option>
                  <option>GMT+3 (Cairo)</option>
                  <option>GMT+2 (Istanbul)</option>
                </select>
              </div>
            </div>

            <button className="w-full md:w-auto px-6 py-2 rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors font-medium flex items-center justify-center gap-2">
              <Save size={18} />
              Save Changes
            </button>
          </div>
        </div>

        {/* Notification Settings */}
        <div className="bg-surface border border-border rounded-lg p-8">
          <h2 className="text-2xl font-semibold text-text-primary mb-6 flex items-center gap-2">
            <Bell size={24} className="text-primary" />
            Notification Preferences
          </h2>

          <div className="space-y-4">
            {[
              { title: 'Email Notifications', subtitle: 'Receive updates via email', enabled: true },
              { title: 'Push Notifications', subtitle: 'Get browser notifications', enabled: true },
              { title: 'Lesson Reminders', subtitle: 'Remind me before lessons', enabled: true },
              { title: 'Assignment Deadlines', subtitle: 'Alert for upcoming deadlines', enabled: false },
              { title: 'Leaderboard Updates', subtitle: 'Notify when rank changes', enabled: true },
              { title: 'Community News', subtitle: 'Updates from the community', enabled: false },
            ].map((notif) => (
              <div key={notif.title} className="flex items-center justify-between p-4 border border-border rounded-lg hover:bg-surface-hover transition-colors">
                <div>
                  <p className="font-medium text-text-primary">{notif.title}</p>
                  <p className="text-sm text-text-secondary">{notif.subtitle}</p>
                </div>
                <input
                  type="checkbox"
                  defaultChecked={notif.enabled}
                  className="w-5 h-5 rounded-lg accent-primary cursor-pointer"
                />
              </div>
            ))}
          </div>
        </div>

        {/* Privacy & Security */}
        <div className="bg-surface border border-border rounded-lg p-8">
          <h2 className="text-2xl font-semibold text-text-primary mb-6 flex items-center gap-2">
            <Lock size={24} className="text-primary" />
            Privacy & Security
          </h2>

          <div className="space-y-6">
            {/* Password */}
            <div className="pb-6 border-b border-border">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-text-primary">Password</p>
                  <p className="text-sm text-text-secondary">Last changed 3 months ago</p>
                </div>
                <button className="px-4 py-2 rounded-lg border border-border hover:bg-surface-hover transition-colors font-medium text-sm">
                  Change Password
                </button>
              </div>
            </div>

            {/* Two-Factor Authentication */}
            <div className="pb-6 border-b border-border">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-text-primary">Two-Factor Authentication</p>
                  <p className="text-sm text-text-secondary">Add extra security to your account</p>
                </div>
                <button className="px-4 py-2 rounded-lg bg-primary text-white hover:bg-primary-dark transition-colors font-medium text-sm">
                  Enable 2FA
                </button>
              </div>
            </div>

            {/* Login Activity */}
            <div>
              <p className="font-medium text-text-primary mb-4">Recent Login Activity</p>
              <div className="space-y-2">
                {[
                  { device: 'Chrome on Windows', location: 'Dubai, UAE', time: '2 hours ago' },
                  { device: 'Safari on iPhone', location: 'Dubai, UAE', time: '1 day ago' },
                  { device: 'Chrome on Android', location: 'Abu Dhabi, UAE', time: '3 days ago' },
                ].map((activity, i) => (
                  <div key={i} className="p-3 rounded-lg bg-surface-hover flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-text-primary">{activity.device}</p>
                      <p className="text-xs text-text-secondary">{activity.location} • {activity.time}</p>
                    </div>
                    <button className="text-xs text-text-secondary hover:text-text-primary">Remove</button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Learning Preferences */}
        <div className="bg-surface border border-border rounded-lg p-8">
          <h2 className="text-2xl font-semibold text-text-primary mb-6">Learning Preferences</h2>

          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-text-primary mb-3">
                Learning Level
              </label>
              <div className="flex gap-3 flex-wrap">
                {['Beginner', 'Elementary', 'Intermediate', 'Upper-Intermediate', 'Advanced'].map((level) => (
                  <button
                    key={level}
                    className="px-4 py-2 rounded-lg border border-border hover:border-primary hover:bg-primary/5 transition-colors text-sm font-medium text-text-primary"
                  >
                    {level}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-3">
                Learning Goals
              </label>
              <div className="space-y-2">
                {['Improve Speaking', 'Master Grammar', 'Build Vocabulary', 'Prepare for IELTS', 'Business English'].map((goal) => (
                  <label key={goal} className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      className="w-4 h-4 rounded accent-primary cursor-pointer"
                      defaultChecked={['Improve Speaking', 'Master Grammar'].includes(goal)}
                    />
                    <span className="text-sm text-text-primary">{goal}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Danger Zone */}
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-8">
          <h2 className="text-2xl font-semibold text-red-600 mb-6">Danger Zone</h2>
          <div className="space-y-4">
            <div>
              <p className="text-sm text-red-600 mb-3">
                Once you delete your account, there is no going back. Please be certain.
              </p>
              <button className="px-6 py-2 rounded-lg bg-red-500 text-white hover:bg-red-600 transition-colors font-medium">
                Delete Account
              </button>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
