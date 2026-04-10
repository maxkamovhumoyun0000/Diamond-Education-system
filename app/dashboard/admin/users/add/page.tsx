'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import Link from 'next/link'
import { 
  ArrowLeft, 
  ArrowRight, 
  UserPlus, 
  GraduationCap, 
  User,
  BookOpen,
  HeadphonesIcon,
  CheckCircle,
  Copy,
  AlertCircle
} from 'lucide-react'
import { useLanguage } from '@/lib/i18n'

type UserType = 'student-new' | 'student-existing' | 'teacher' | 'support'
type Subject = 'english' | 'russian'

interface FormData {
  firstName: string
  lastName: string
  phone: string
  subject: Subject | ''
}

// Generate secure login ID
function generateLoginId(type: UserType): string {
  const prefix = type === 'teacher' ? 'TR' : type === 'support' ? 'SP' : 'ST'
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
  let code = ''
  for (let i = 0; i < 5; i++) {
    code += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  return `Diamond-${prefix}-${code}`
}

// Generate 6-digit password
function generatePassword(): string {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
  let password = ''
  for (let i = 0; i < 6; i++) {
    password += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  return password
}

export default function AddUserPage() {
  const router = useRouter()
  const { t } = useLanguage()
  
  const [step, setStep] = useState(1)
  const [userType, setUserType] = useState<UserType | null>(null)
  const [formData, setFormData] = useState<FormData>({
    firstName: '',
    lastName: '',
    phone: '',
    subject: '',
  })
  const [createdUser, setCreatedUser] = useState<{
    loginId: string
    password: string
    name: string
  } | null>(null)
  const [copied, setCopied] = useState(false)
  const [loading, setLoading] = useState(false)

  const totalSteps = 3

  const userTypes = [
    {
      id: 'student-new' as UserType,
      icon: <GraduationCap size={32} />,
      label: t('addUser.newStudentTest'),
      description: t('addUser.newStudentTest'),
    },
    {
      id: 'student-existing' as UserType,
      icon: <User size={32} />,
      label: t('addUser.existingStudent'),
      description: t('addUser.existingStudent'),
    },
    {
      id: 'teacher' as UserType,
      icon: <BookOpen size={32} />,
      label: t('addUser.teacher'),
      description: t('addUser.teacher'),
    },
    {
      id: 'support' as UserType,
      icon: <HeadphonesIcon size={32} />,
      label: t('addUser.support'),
      description: t('addUser.support'),
    },
  ]

  const subjects = [
    { id: 'english' as Subject, label: t('subject.english'), flag: '🇬🇧' },
    { id: 'russian' as Subject, label: t('subject.russian'), flag: '🇷🇺' },
  ]

  const handleNext = () => {
    if (step === 1 && userType) {
      setStep(2)
    } else if (step === 2) {
      // Create user
      setLoading(true)
      setTimeout(() => {
        const loginId = generateLoginId(userType!)
        const password = generatePassword()
        setCreatedUser({
          loginId,
          password,
          name: `${formData.firstName} ${formData.lastName}`,
        })
        setLoading(false)
        setStep(3)
      }, 1500)
    }
  }

  const handleBack = () => {
    if (step > 1) {
      setStep(step - 1)
    }
  }

  const handleCopy = async () => {
    if (createdUser) {
      const text = `Login ID: ${createdUser.loginId}\nPassword: ${createdUser.password}`
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const handleReset = () => {
    setStep(1)
    setUserType(null)
    setFormData({ firstName: '', lastName: '', phone: '', subject: '' })
    setCreatedUser(null)
  }

  const isStep2Valid = formData.firstName && formData.lastName && formData.phone && formData.subject

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="bg-surface border-b border-border sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/dashboard/admin/users" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
            <div className="relative w-10 h-10 rounded-full overflow-hidden bg-primary">
              <Image src="/logo.jpg" alt="Diamond Education" width={40} height={40} className="object-cover" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-primary">Diamond</h1>
              <p className="text-xs text-text-secondary">Education</p>
            </div>
          </Link>
          <Link 
            href="/dashboard/admin/users"
            className="flex items-center gap-2 text-text-secondary hover:text-text-primary transition-colors"
          >
            <ArrowLeft size={20} />
            <span className="hidden sm:inline">{t('common.back')}</span>
          </Link>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-8">
        {/* Progress Bar */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-text-primary">
              {t('addUser.step')} {step} {t('addUser.of')} {totalSteps}
            </span>
            <span className="text-sm text-text-secondary">
              {step === 1 && t('addUser.selectType')}
              {step === 2 && t('addUser.enterInfo')}
              {step === 3 && t('common.success')}
            </span>
          </div>
          <div className="h-2 bg-surface-hover rounded-full overflow-hidden">
            <div 
              className="h-full bg-primary transition-all duration-500"
              style={{ width: `${(step / totalSteps) * 100}%` }}
            />
          </div>
        </div>

        {/* Step 1: Select User Type */}
        {step === 1 && (
          <div className="space-y-6">
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold text-text-primary mb-2">{t('addUser.title')}</h2>
              <p className="text-text-secondary">{t('addUser.selectType')}</p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {userTypes.map((type) => (
                <button
                  key={type.id}
                  onClick={() => setUserType(type.id)}
                  className={`p-6 rounded-xl border-2 transition-all text-left ${
                    userType === type.id
                      ? 'border-primary bg-primary/5'
                      : 'border-border hover:border-primary/50 bg-surface'
                  }`}
                >
                  <div className={`mb-4 ${userType === type.id ? 'text-primary' : 'text-text-secondary'}`}>
                    {type.icon}
                  </div>
                  <h3 className="font-semibold text-text-primary mb-1">{type.label}</h3>
                </button>
              ))}
            </div>

            <div className="pt-6">
              <button
                onClick={handleNext}
                disabled={!userType}
                className="w-full py-3 px-6 rounded-lg bg-primary text-white font-medium transition-all hover:bg-primary-dark disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {t('common.next')}
                <ArrowRight size={20} />
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Enter Information */}
        {step === 2 && (
          <div className="space-y-6">
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold text-text-primary mb-2">{t('addUser.enterInfo')}</h2>
              <p className="text-text-secondary">
                {userTypes.find(t => t.id === userType)?.label}
              </p>
            </div>

            <div className="bg-surface border border-border rounded-xl p-6 space-y-5">
              {/* First Name */}
              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  {t('addUser.firstName')} *
                </label>
                <input
                  type="text"
                  value={formData.firstName}
                  onChange={(e) => setFormData({ ...formData, firstName: e.target.value })}
                  placeholder={t('addUser.firstName')}
                  className="w-full px-4 py-3 border border-border rounded-lg bg-background text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                />
              </div>

              {/* Last Name */}
              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  {t('addUser.lastName')} *
                </label>
                <input
                  type="text"
                  value={formData.lastName}
                  onChange={(e) => setFormData({ ...formData, lastName: e.target.value })}
                  placeholder={t('addUser.lastName')}
                  className="w-full px-4 py-3 border border-border rounded-lg bg-background text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                />
              </div>

              {/* Phone */}
              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  {t('addUser.phone')} *
                </label>
                <input
                  type="tel"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  placeholder="+998 XX XXX XX XX"
                  className="w-full px-4 py-3 border border-border rounded-lg bg-background text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                />
              </div>

              {/* Subject Selection */}
              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  {t('addUser.selectSubject')} *
                </label>
                <div className="grid grid-cols-2 gap-3">
                  {subjects.map((subject) => (
                    <button
                      key={subject.id}
                      type="button"
                      onClick={() => setFormData({ ...formData, subject: subject.id })}
                      className={`p-4 rounded-lg border-2 transition-all flex items-center gap-3 ${
                        formData.subject === subject.id
                          ? 'border-primary bg-primary/5'
                          : 'border-border hover:border-primary/50 bg-background'
                      }`}
                    >
                      <span className="text-2xl">{subject.flag}</span>
                      <span className="font-medium text-text-primary">{subject.label}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex gap-4 pt-4">
              <button
                onClick={handleBack}
                className="flex-1 py-3 px-6 rounded-lg border border-border text-text-primary font-medium transition-colors hover:bg-surface-hover flex items-center justify-center gap-2"
              >
                <ArrowLeft size={20} />
                {t('common.back')}
              </button>
              <button
                onClick={handleNext}
                disabled={!isStep2Valid || loading}
                className="flex-1 py-3 px-6 rounded-lg bg-primary text-white font-medium transition-all hover:bg-primary-dark disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    {t('common.loading')}
                  </>
                ) : (
                  <>
                    <UserPlus size={20} />
                    {t('common.add')}
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Success */}
        {step === 3 && createdUser && (
          <div className="space-y-6">
            <div className="text-center">
              <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-green-500/10 flex items-center justify-center">
                <CheckCircle size={48} className="text-green-500" />
              </div>
              <h2 className="text-2xl font-bold text-text-primary mb-2">{t('addUser.success')}</h2>
            </div>

            <div className="bg-surface border border-border rounded-xl p-6 space-y-6">
              {/* User Info */}
              <div className="text-center pb-4 border-b border-border">
                <div className="w-16 h-16 mx-auto mb-3 rounded-full bg-primary/10 flex items-center justify-center text-primary text-2xl font-bold">
                  {createdUser.name.charAt(0)}
                </div>
                <h3 className="text-xl font-semibold text-text-primary">{createdUser.name}</h3>
                <p className="text-sm text-text-secondary capitalize">
                  {userTypes.find(t => t.id === userType)?.label}
                </p>
              </div>

              {/* Credentials */}
              <div className="space-y-4">
                <div className="bg-background rounded-lg p-4">
                  <label className="block text-xs text-text-secondary mb-1">{t('addUser.loginId')}</label>
                  <p className="text-lg font-mono font-semibold text-primary">{createdUser.loginId}</p>
                </div>
                <div className="bg-background rounded-lg p-4">
                  <label className="block text-xs text-text-secondary mb-1">{t('addUser.password')}</label>
                  <p className="text-3xl font-mono font-bold text-text-primary tracking-wider">{createdUser.password}</p>
                </div>
              </div>

              {/* Warning */}
              <div className="flex gap-3 p-4 bg-amber-500/10 border border-amber-500/30 rounded-lg">
                <AlertCircle size={20} className="text-amber-500 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-amber-700 dark:text-amber-300">
                  {t('addUser.oneTimePassword')}
                </p>
              </div>

              {/* Copy Button */}
              <button
                onClick={handleCopy}
                className="w-full py-3 px-6 rounded-lg bg-primary/10 text-primary font-medium transition-colors hover:bg-primary/20 flex items-center justify-center gap-2"
              >
                <Copy size={20} />
                {copied ? t('common.copied') : t('addUser.copyCredentials')}
              </button>
            </div>

            <div className="flex gap-4 pt-4">
              <button
                onClick={handleReset}
                className="flex-1 py-3 px-6 rounded-lg bg-primary text-white font-medium transition-colors hover:bg-primary-dark"
              >
                {t('addUser.addAnother')}
              </button>
              <Link
                href="/dashboard/admin/users"
                className="flex-1 py-3 px-6 rounded-lg border border-border text-text-primary font-medium transition-colors hover:bg-surface-hover text-center"
              >
                {t('addUser.backToPanel')}
              </Link>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
