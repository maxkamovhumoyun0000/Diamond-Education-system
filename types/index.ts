export type UserRole = 'admin' | 'student' | 'teacher' | 'support'

export interface User {
  id: string
  name: string
  email: string
  role: UserRole
  avatar?: string
  joinDate: Date
}

export interface Course {
  id: string
  title: string
  description: string
  category: string
  students: number
  rating: number
  image?: string
}

export interface Group {
  id: string
  name: string
  students: number
  teacher: string
  description: string
}

export interface DCoins {
  amount: number
  earnedToday: number
  level: number
}

export interface StudentStats {
  completedLessons: number
  totalPoints: number
  streakDays: number
  rank: number
  dcoins: DCoins
}

export interface TeacherStats {
  activeGroups: number
  totalStudents: number
  lessonsCreated: number
  averageRating: number
}

export interface AdminStats {
  totalUsers: number
  activeStudents: number
  courseCount: number
  totalRevenue: number
  monthlyGrowth: number
}

export interface Lesson {
  id: string
  title: string
  duration: number
  completed: boolean
  date: Date
}

export interface SupportTicket {
  id: string
  title: string
  status: 'open' | 'in-progress' | 'resolved'
  createdAt: Date
  priority: 'low' | 'medium' | 'high'
}

export type BookingPurpose = 'speaking' | 'grammar' | 'writing' | 'reading' | 'listening' | 'general'
export type BookingStatus = 'pending' | 'approved' | 'completed' | 'cancelled'
export type AttendanceStatus = 'present' | 'late' | 'absent'
export type Branch = 'branch1' | 'branch2'

export interface TimeSlot {
  id: string
  time: string
  available: boolean
  blocked: boolean
  blockReason?: string
}

export interface SupportBooking {
  id: string
  studentId: string
  studentName: string
  date: string
  time: string
  branch: Branch
  purpose: BookingPurpose
  status: BookingStatus
  teacherId?: string
  teacherName?: string
  attendance?: AttendanceStatus
  dcoinCost: number
  dcoinBonus?: number
  bonusReason?: string
  createdAt: number
  updatedAt: number
}

export interface BookingDate {
  date: string
  closed: boolean
  closeReason?: string
  slots: TimeSlot[]
}

// Subject types
export type Subject = 'english' | 'russian'
export type Level = 'A1' | 'A2' | 'B1' | 'B2' | 'C1'
export type StudentType = 'new_with_test' | 'existing_no_test'

// Enhanced User with subjects and internal email
export interface EnhancedUser {
  id: string
  firstName: string
  lastName: string
  phone: string
  loginId: string
  internalEmail: string // format: firstname.lastname@diamond-education.uz
  role: UserRole
  studentType?: StudentType
  subjects: {
    subject: Subject
    level: Level
    dcoins: number
  }[]
  avatar?: string
  createdAt: number
  updatedAt: number
  canCreateArticles?: boolean // for teachers/support
}

// Article types
export type ArticleStatus = 'draft' | 'published'
export type ArticleCategory = 'grammar' | 'vocabulary' | 'motivation' | 'tips' | 'culture' | 'news' | 'general'
export type ArticleVisibility = 'all' | 'students' | 'teachers'

export interface Article {
  id: string
  title: string
  slug: string
  content: string
  excerpt: string
  featuredImage?: string
  category: ArticleCategory
  tags: string[]
  status: ArticleStatus
  visibility: ArticleVisibility
  authorId: string
  authorName: string
  authorRole: UserRole
  metaTitle?: string
  metaDescription?: string
  views: number
  createdAt: number
  updatedAt: number
  publishedAt?: number
}
