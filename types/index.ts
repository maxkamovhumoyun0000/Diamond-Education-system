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
