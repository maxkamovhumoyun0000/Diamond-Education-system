-- Diamond Education Admin Panel Database Schema
-- This script creates all necessary tables for the admin panel

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- USER ROLES AND PROFILES
-- ============================================

-- User roles enum
CREATE TYPE user_role AS ENUM ('super_admin', 'admin', 'teacher', 'support_teacher', 'student');

-- Student status enum
CREATE TYPE student_status AS ENUM ('active', 'inactive', 'graduated', 'suspended');

-- Student type enum (regular or support)
CREATE TYPE student_type AS ENUM ('regular', 'support');

-- Profiles table (extends auth.users)
CREATE TABLE IF NOT EXISTS public.profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT NOT NULL,
  full_name TEXT NOT NULL,
  phone TEXT,
  role user_role NOT NULL DEFAULT 'student',
  avatar_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- SUBJECTS AND LEVELS
-- ============================================

-- Subjects table
CREATE TABLE IF NOT EXISTS public.subjects (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL UNIQUE,
  description TEXT,
  icon TEXT,
  color TEXT,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default subjects
INSERT INTO public.subjects (name, description, icon, color) VALUES
  ('IELTS', 'International English Language Testing System', 'globe', '#1e40af'),
  ('General English', 'General English language courses', 'book-open', '#059669'),
  ('Mathematics', 'Mathematics courses', 'calculator', '#dc2626'),
  ('IT/Programming', 'Information Technology and Programming', 'code', '#7c3aed'),
  ('SAT', 'Scholastic Assessment Test preparation', 'graduation-cap', '#ea580c')
ON CONFLICT (name) DO NOTHING;

-- Levels table (per subject)
CREATE TABLE IF NOT EXISTS public.levels (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  subject_id UUID NOT NULL REFERENCES public.subjects(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  order_index INTEGER NOT NULL,
  description TEXT,
  min_score INTEGER,
  max_score INTEGER,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(subject_id, name)
);

-- Insert IELTS levels
INSERT INTO public.levels (subject_id, name, order_index, min_score, max_score)
SELECT s.id, level.name, level.order_index, level.min_score, level.max_score
FROM public.subjects s
CROSS JOIN (VALUES 
  ('Beginner', 1, 0, 3),
  ('Elementary', 2, 3, 4),
  ('Pre-Intermediate', 3, 4, 5),
  ('Intermediate', 4, 5, 6),
  ('Upper-Intermediate', 5, 6, 7),
  ('Advanced', 6, 7, 9)
) AS level(name, order_index, min_score, max_score)
WHERE s.name = 'IELTS'
ON CONFLICT (subject_id, name) DO NOTHING;

-- ============================================
-- TEACHERS
-- ============================================

-- Teachers table
CREATE TABLE IF NOT EXISTS public.teachers (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  profile_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  subject_id UUID NOT NULL REFERENCES public.subjects(id) ON DELETE CASCADE,
  is_support_teacher BOOLEAN DEFAULT false,
  specialization TEXT,
  bio TEXT,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(profile_id, subject_id)
);

-- ============================================
-- GROUPS
-- ============================================

-- Groups table
CREATE TABLE IF NOT EXISTS public.groups (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  subject_id UUID NOT NULL REFERENCES public.subjects(id) ON DELETE CASCADE,
  level_id UUID NOT NULL REFERENCES public.levels(id) ON DELETE CASCADE,
  teacher_id UUID REFERENCES public.teachers(id) ON DELETE SET NULL,
  support_teacher_id UUID REFERENCES public.teachers(id) ON DELETE SET NULL,
  max_students INTEGER DEFAULT 15,
  schedule JSONB, -- { days: ['Monday', 'Wednesday'], time: '14:00' }
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- STUDENTS
-- ============================================

-- Students table
CREATE TABLE IF NOT EXISTS public.students (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  profile_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  student_type student_type NOT NULL DEFAULT 'regular',
  status student_status NOT NULL DEFAULT 'active',
  parent_name TEXT,
  parent_phone TEXT,
  address TEXT,
  birth_date DATE,
  notes TEXT,
  registered_by UUID REFERENCES public.profiles(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(profile_id)
);

-- Student subjects (many-to-many with additional fields)
CREATE TABLE IF NOT EXISTS public.student_subjects (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  student_id UUID NOT NULL REFERENCES public.students(id) ON DELETE CASCADE,
  subject_id UUID NOT NULL REFERENCES public.subjects(id) ON DELETE CASCADE,
  level_id UUID REFERENCES public.levels(id) ON DELETE SET NULL,
  group_id UUID REFERENCES public.groups(id) ON DELETE SET NULL,
  placement_test_score INTEGER,
  placement_test_date TIMESTAMPTZ,
  enrolled_at TIMESTAMPTZ DEFAULT NOW(),
  is_active BOOLEAN DEFAULT true,
  UNIQUE(student_id, subject_id)
);

-- ============================================
-- D'COIN SYSTEM
-- ============================================

-- D'coin transaction types
CREATE TYPE dcoin_transaction_type AS ENUM (
  'initial_award',
  'attendance_bonus',
  'homework_completion',
  'test_performance',
  'participation',
  'achievement',
  'penalty',
  'purchase',
  'transfer',
  'admin_adjustment'
);

-- D'coin balances
CREATE TABLE IF NOT EXISTS public.dcoin_balances (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  student_id UUID NOT NULL REFERENCES public.students(id) ON DELETE CASCADE,
  balance INTEGER NOT NULL DEFAULT 0,
  total_earned INTEGER NOT NULL DEFAULT 0,
  total_spent INTEGER NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(student_id)
);

-- D'coin transactions
CREATE TABLE IF NOT EXISTS public.dcoin_transactions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  student_id UUID NOT NULL REFERENCES public.students(id) ON DELETE CASCADE,
  amount INTEGER NOT NULL,
  transaction_type dcoin_transaction_type NOT NULL,
  description TEXT,
  related_entity_type TEXT, -- 'article', 'homework', 'test', etc.
  related_entity_id UUID,
  created_by UUID REFERENCES public.profiles(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- ARTICLES SYSTEM
-- ============================================

-- Article status
CREATE TYPE article_status AS ENUM ('draft', 'published', 'archived');

-- Articles table
CREATE TABLE IF NOT EXISTS public.articles (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  title TEXT NOT NULL,
  slug TEXT NOT NULL UNIQUE,
  content TEXT NOT NULL,
  excerpt TEXT,
  cover_image TEXT,
  subject_id UUID REFERENCES public.subjects(id) ON DELETE SET NULL,
  level_id UUID REFERENCES public.levels(id) ON DELETE SET NULL,
  status article_status NOT NULL DEFAULT 'draft',
  is_featured BOOLEAN DEFAULT false,
  view_count INTEGER DEFAULT 0,
  reading_time_minutes INTEGER,
  author_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  published_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Article tags
CREATE TABLE IF NOT EXISTS public.article_tags (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL UNIQUE,
  slug TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Article-tag relationship
CREATE TABLE IF NOT EXISTS public.article_tag_relations (
  article_id UUID NOT NULL REFERENCES public.articles(id) ON DELETE CASCADE,
  tag_id UUID NOT NULL REFERENCES public.article_tags(id) ON DELETE CASCADE,
  PRIMARY KEY (article_id, tag_id)
);

-- Article permissions (which teachers can edit which articles)
CREATE TABLE IF NOT EXISTS public.article_permissions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  article_id UUID NOT NULL REFERENCES public.articles(id) ON DELETE CASCADE,
  teacher_id UUID NOT NULL REFERENCES public.teachers(id) ON DELETE CASCADE,
  can_edit BOOLEAN DEFAULT false,
  can_delete BOOLEAN DEFAULT false,
  granted_by UUID REFERENCES public.profiles(id),
  granted_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(article_id, teacher_id)
);

-- Article read tracking
CREATE TABLE IF NOT EXISTS public.article_reads (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  article_id UUID NOT NULL REFERENCES public.articles(id) ON DELETE CASCADE,
  student_id UUID NOT NULL REFERENCES public.students(id) ON DELETE CASCADE,
  read_at TIMESTAMPTZ DEFAULT NOW(),
  time_spent_seconds INTEGER,
  completed BOOLEAN DEFAULT false,
  UNIQUE(article_id, student_id)
);

-- ============================================
-- INTERNAL EMAIL SYSTEM
-- ============================================

-- Messages table
CREATE TABLE IF NOT EXISTS public.messages (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  sender_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  subject TEXT NOT NULL,
  body TEXT NOT NULL,
  is_announcement BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Message recipients
CREATE TABLE IF NOT EXISTS public.message_recipients (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  message_id UUID NOT NULL REFERENCES public.messages(id) ON DELETE CASCADE,
  recipient_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  is_read BOOLEAN DEFAULT false,
  read_at TIMESTAMPTZ,
  is_starred BOOLEAN DEFAULT false,
  is_deleted BOOLEAN DEFAULT false,
  UNIQUE(message_id, recipient_id)
);

-- ============================================
-- PLACEMENT TESTS
-- ============================================

-- Placement test templates
CREATE TABLE IF NOT EXISTS public.placement_tests (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  subject_id UUID NOT NULL REFERENCES public.subjects(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  duration_minutes INTEGER DEFAULT 60,
  questions JSONB NOT NULL, -- Array of question objects
  scoring_rules JSONB, -- Rules for determining level
  is_active BOOLEAN DEFAULT true,
  created_by UUID REFERENCES public.profiles(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Placement test results
CREATE TABLE IF NOT EXISTS public.placement_test_results (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  student_id UUID NOT NULL REFERENCES public.students(id) ON DELETE CASCADE,
  test_id UUID NOT NULL REFERENCES public.placement_tests(id) ON DELETE CASCADE,
  subject_id UUID NOT NULL REFERENCES public.subjects(id) ON DELETE CASCADE,
  answers JSONB,
  score INTEGER NOT NULL,
  max_score INTEGER NOT NULL,
  percentage DECIMAL(5,2),
  assigned_level_id UUID REFERENCES public.levels(id),
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ DEFAULT NOW(),
  evaluated_by UUID REFERENCES public.profiles(id),
  notes TEXT
);

-- ============================================
-- ATTENDANCE
-- ============================================

-- Attendance records
CREATE TABLE IF NOT EXISTS public.attendance (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  student_id UUID NOT NULL REFERENCES public.students(id) ON DELETE CASCADE,
  group_id UUID NOT NULL REFERENCES public.groups(id) ON DELETE CASCADE,
  date DATE NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('present', 'absent', 'late', 'excused')),
  notes TEXT,
  marked_by UUID REFERENCES public.profiles(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(student_id, group_id, date)
);

-- ============================================
-- NOTIFICATIONS
-- ============================================

-- Notifications table
CREATE TABLE IF NOT EXISTS public.notifications (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  message TEXT NOT NULL,
  type TEXT NOT NULL, -- 'info', 'success', 'warning', 'error'
  link TEXT,
  is_read BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- ROW LEVEL SECURITY POLICIES
-- ============================================

-- Enable RLS on all tables
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.subjects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.levels ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.teachers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.students ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.student_subjects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dcoin_balances ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dcoin_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.article_tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.article_tag_relations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.article_permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.article_reads ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.message_recipients ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.placement_tests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.placement_test_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.attendance ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;

-- Profiles policies
CREATE POLICY "Users can view all profiles" ON public.profiles FOR SELECT USING (true);
CREATE POLICY "Users can update own profile" ON public.profiles FOR UPDATE USING (auth.uid() = id);
CREATE POLICY "Admins can insert profiles" ON public.profiles FOR INSERT WITH CHECK (
  EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('super_admin', 'admin'))
  OR auth.uid() = id
);

-- Subjects policies (read-only for most, admin can modify)
CREATE POLICY "Anyone can view subjects" ON public.subjects FOR SELECT USING (true);
CREATE POLICY "Admins can manage subjects" ON public.subjects FOR ALL USING (
  EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('super_admin', 'admin'))
);

-- Levels policies
CREATE POLICY "Anyone can view levels" ON public.levels FOR SELECT USING (true);
CREATE POLICY "Admins can manage levels" ON public.levels FOR ALL USING (
  EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('super_admin', 'admin'))
);

-- Teachers policies
CREATE POLICY "Anyone can view teachers" ON public.teachers FOR SELECT USING (true);
CREATE POLICY "Admins can manage teachers" ON public.teachers FOR ALL USING (
  EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('super_admin', 'admin'))
);

-- Groups policies
CREATE POLICY "Anyone can view groups" ON public.groups FOR SELECT USING (true);
CREATE POLICY "Admins and teachers can manage groups" ON public.groups FOR ALL USING (
  EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('super_admin', 'admin', 'teacher'))
);

-- Students policies
CREATE POLICY "Staff can view all students" ON public.students FOR SELECT USING (
  EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('super_admin', 'admin', 'teacher', 'support_teacher'))
  OR profile_id = auth.uid()
);
CREATE POLICY "Admins can manage students" ON public.students FOR ALL USING (
  EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('super_admin', 'admin'))
);

-- Student subjects policies
CREATE POLICY "Staff can view student subjects" ON public.student_subjects FOR SELECT USING (
  EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('super_admin', 'admin', 'teacher', 'support_teacher'))
  OR EXISTS (SELECT 1 FROM public.students WHERE id = student_id AND profile_id = auth.uid())
);
CREATE POLICY "Admins can manage student subjects" ON public.student_subjects FOR ALL USING (
  EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('super_admin', 'admin'))
);

-- D'coin balances policies
CREATE POLICY "Staff can view dcoin balances" ON public.dcoin_balances FOR SELECT USING (
  EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('super_admin', 'admin', 'teacher', 'support_teacher'))
  OR EXISTS (SELECT 1 FROM public.students WHERE id = student_id AND profile_id = auth.uid())
);
CREATE POLICY "Staff can manage dcoin balances" ON public.dcoin_balances FOR ALL USING (
  EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('super_admin', 'admin', 'teacher', 'support_teacher'))
);

-- D'coin transactions policies
CREATE POLICY "Staff can view dcoin transactions" ON public.dcoin_transactions FOR SELECT USING (
  EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('super_admin', 'admin', 'teacher', 'support_teacher'))
  OR EXISTS (SELECT 1 FROM public.students WHERE id = student_id AND profile_id = auth.uid())
);
CREATE POLICY "Staff can create dcoin transactions" ON public.dcoin_transactions FOR INSERT WITH CHECK (
  EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('super_admin', 'admin', 'teacher', 'support_teacher'))
);

-- Articles policies
CREATE POLICY "Anyone can view published articles" ON public.articles FOR SELECT USING (
  status = 'published' OR author_id = auth.uid()
  OR EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('super_admin', 'admin'))
  OR EXISTS (SELECT 1 FROM public.article_permissions ap 
    JOIN public.teachers t ON ap.teacher_id = t.id 
    WHERE ap.article_id = articles.id AND t.profile_id = auth.uid())
);
CREATE POLICY "Authors can manage own articles" ON public.articles FOR ALL USING (
  author_id = auth.uid()
  OR EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('super_admin', 'admin'))
);

-- Article tags policies
CREATE POLICY "Anyone can view tags" ON public.article_tags FOR SELECT USING (true);
CREATE POLICY "Staff can manage tags" ON public.article_tags FOR ALL USING (
  EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('super_admin', 'admin', 'teacher'))
);

-- Article tag relations policies
CREATE POLICY "Anyone can view tag relations" ON public.article_tag_relations FOR SELECT USING (true);
CREATE POLICY "Staff can manage tag relations" ON public.article_tag_relations FOR ALL USING (
  EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('super_admin', 'admin', 'teacher'))
);

-- Article permissions policies
CREATE POLICY "Admins can manage article permissions" ON public.article_permissions FOR ALL USING (
  EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('super_admin', 'admin'))
);
CREATE POLICY "Teachers can view own permissions" ON public.article_permissions FOR SELECT USING (
  EXISTS (SELECT 1 FROM public.teachers WHERE id = teacher_id AND profile_id = auth.uid())
);

-- Article reads policies
CREATE POLICY "Students can manage own reads" ON public.article_reads FOR ALL USING (
  EXISTS (SELECT 1 FROM public.students WHERE id = student_id AND profile_id = auth.uid())
);
CREATE POLICY "Staff can view all reads" ON public.article_reads FOR SELECT USING (
  EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('super_admin', 'admin', 'teacher'))
);

-- Messages policies
CREATE POLICY "Users can view own messages" ON public.messages FOR SELECT USING (
  sender_id = auth.uid()
  OR is_announcement = true
);
CREATE POLICY "Users can send messages" ON public.messages FOR INSERT WITH CHECK (sender_id = auth.uid());

-- Message recipients policies
CREATE POLICY "Users can view own message recipients" ON public.message_recipients FOR SELECT USING (recipient_id = auth.uid());
CREATE POLICY "Users can update own message recipients" ON public.message_recipients FOR UPDATE USING (recipient_id = auth.uid());
CREATE POLICY "Senders can insert recipients" ON public.message_recipients FOR INSERT WITH CHECK (
  EXISTS (SELECT 1 FROM public.messages WHERE id = message_id AND sender_id = auth.uid())
);

-- Placement tests policies
CREATE POLICY "Anyone can view active tests" ON public.placement_tests FOR SELECT USING (is_active = true);
CREATE POLICY "Admins can manage tests" ON public.placement_tests FOR ALL USING (
  EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('super_admin', 'admin'))
);

-- Placement test results policies
CREATE POLICY "Staff can view test results" ON public.placement_test_results FOR SELECT USING (
  EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('super_admin', 'admin', 'teacher'))
  OR EXISTS (SELECT 1 FROM public.students WHERE id = student_id AND profile_id = auth.uid())
);
CREATE POLICY "Staff can manage test results" ON public.placement_test_results FOR ALL USING (
  EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('super_admin', 'admin', 'teacher'))
);

-- Attendance policies
CREATE POLICY "Staff can view attendance" ON public.attendance FOR SELECT USING (
  EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('super_admin', 'admin', 'teacher', 'support_teacher'))
  OR EXISTS (SELECT 1 FROM public.students WHERE id = student_id AND profile_id = auth.uid())
);
CREATE POLICY "Teachers can manage attendance" ON public.attendance FOR ALL USING (
  EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('super_admin', 'admin', 'teacher', 'support_teacher'))
);

-- Notifications policies
CREATE POLICY "Users can view own notifications" ON public.notifications FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "Users can update own notifications" ON public.notifications FOR UPDATE USING (user_id = auth.uid());
CREATE POLICY "System can create notifications" ON public.notifications FOR INSERT WITH CHECK (true);

-- ============================================
-- TRIGGERS FOR AUTO-UPDATE
-- ============================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ language 'plpgsql';

-- Add triggers for updated_at
CREATE TRIGGER update_profiles_updated_at BEFORE UPDATE ON public.profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_students_updated_at BEFORE UPDATE ON public.students FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_articles_updated_at BEFORE UPDATE ON public.articles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_placement_tests_updated_at BEFORE UPDATE ON public.placement_tests FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- PROFILE CREATION TRIGGER
-- ============================================

-- Function to auto-create profile on user signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.profiles (id, email, full_name, role)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data ->> 'full_name', NEW.email),
    COALESCE((NEW.raw_user_meta_data ->> 'role')::user_role, 'student')
  )
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$;

-- Create trigger for new user
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user();
