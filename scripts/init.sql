-- Diamond Education Admin Panel - Complete Database Schema
-- This is a comprehensive migration that creates all necessary tables and RLS policies

-- Part 1: Create Extensions and Types
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- User role enum
CREATE TYPE IF NOT EXISTS user_role AS ENUM ('super_admin', 'admin', 'teacher', 'support_teacher', 'student');

-- Student status enum  
CREATE TYPE IF NOT EXISTS student_status AS ENUM ('active', 'inactive', 'graduated', 'suspended');

-- Student type enum (regular or support)
CREATE TYPE IF NOT EXISTS student_type AS ENUM ('regular', 'support');

-- Part 2: Create Main Tables

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

-- Groups table
CREATE TABLE IF NOT EXISTS public.groups (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  subject_id UUID NOT NULL REFERENCES public.subjects(id) ON DELETE CASCADE,
  level_id UUID NOT NULL REFERENCES public.levels(id) ON DELETE CASCADE,
  teacher_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  description TEXT,
  max_students INTEGER DEFAULT 30,
  status TEXT DEFAULT 'active',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Student Groups junction table
CREATE TABLE IF NOT EXISTS public.student_groups (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  student_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  group_id UUID NOT NULL REFERENCES public.groups(id) ON DELETE CASCADE,
  student_type student_type DEFAULT 'regular',
  status student_status DEFAULT 'active',
  joined_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(student_id, group_id)
);

-- Placement Tests table
CREATE TABLE IF NOT EXISTS public.placement_tests (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  student_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  subject_id UUID NOT NULL REFERENCES public.subjects(id) ON DELETE CASCADE,
  score INTEGER,
  level_id UUID REFERENCES public.levels(id),
  test_date TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- D'coin Transactions table
CREATE TABLE IF NOT EXISTS public.dcoin_transactions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  student_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  amount INTEGER NOT NULL,
  transaction_type TEXT NOT NULL,
  description TEXT,
  reference_id UUID,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Articles table
CREATE TABLE IF NOT EXISTS public.articles (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  author_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  subject_id UUID REFERENCES public.subjects(id) ON DELETE SET NULL,
  is_published BOOLEAN DEFAULT false,
  visibility TEXT DEFAULT 'private',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Article Permissions table
CREATE TABLE IF NOT EXISTS public.article_permissions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  article_id UUID NOT NULL REFERENCES public.articles(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  permission_type TEXT NOT NULL,
  UNIQUE(article_id, user_id, permission_type)
);

-- Messages table (Internal email system)
CREATE TABLE IF NOT EXISTS public.messages (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  sender_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  recipient_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  subject TEXT,
  content TEXT NOT NULL,
  is_read BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Attendance table
CREATE TABLE IF NOT EXISTS public.attendance (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  student_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  group_id UUID NOT NULL REFERENCES public.groups(id) ON DELETE CASCADE,
  attendance_date DATE NOT NULL,
  status TEXT NOT NULL,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(student_id, group_id, attendance_date)
);

-- Notifications table
CREATE TABLE IF NOT EXISTS public.notifications (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  message TEXT NOT NULL,
  type TEXT NOT NULL,
  is_read BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Part 3: Enable RLS on all tables
ALTER TABLE IF EXISTS public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.subjects ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.levels ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.student_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.placement_tests ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.dcoin_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.article_permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.attendance ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.notifications ENABLE ROW LEVEL SECURITY;

-- Part 4: Create RLS Policies

-- Profiles policies
DROP POLICY IF EXISTS "Users can view own profile" ON public.profiles;
CREATE POLICY "Users can view own profile" ON public.profiles FOR SELECT USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can update own profile" ON public.profiles;
CREATE POLICY "Users can update own profile" ON public.profiles FOR UPDATE USING (auth.uid() = id);

-- Subjects policies (readable by all authenticated users)
DROP POLICY IF EXISTS "Subjects visible to all" ON public.subjects;
CREATE POLICY "Subjects visible to all" ON public.subjects FOR SELECT TO authenticated USING (true);

-- Levels policies (readable by all authenticated users)
DROP POLICY IF EXISTS "Levels visible to all" ON public.levels;
CREATE POLICY "Levels visible to all" ON public.levels FOR SELECT TO authenticated USING (true);

-- Groups policies
DROP POLICY IF EXISTS "Teachers can manage own groups" ON public.groups;
CREATE POLICY "Teachers can manage own groups" ON public.groups FOR ALL USING (
  teacher_id = auth.uid() OR EXISTS (
    SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin', 'super_admin')
  )
);

DROP POLICY IF EXISTS "Students can view groups they joined" ON public.groups;
CREATE POLICY "Students can view groups they joined" ON public.groups FOR SELECT USING (
  EXISTS (
    SELECT 1 FROM public.student_groups WHERE group_id = id AND student_id = auth.uid()
  )
);

-- Student Groups policies
DROP POLICY IF EXISTS "Students can view own enrollments" ON public.student_groups;
CREATE POLICY "Students can view own enrollments" ON public.student_groups FOR SELECT USING (student_id = auth.uid());

-- Placement Tests policies
DROP POLICY IF EXISTS "Students can view own tests" ON public.placement_tests;
CREATE POLICY "Students can view own tests" ON public.placement_tests FOR SELECT USING (student_id = auth.uid());

-- D'coin Transactions policies
DROP POLICY IF EXISTS "Students can view own transactions" ON public.dcoin_transactions;
CREATE POLICY "Students can view own transactions" ON public.dcoin_transactions FOR SELECT USING (student_id = auth.uid());

-- Articles policies
DROP POLICY IF EXISTS "Authors can manage own articles" ON public.articles;
CREATE POLICY "Authors can manage own articles" ON public.articles FOR ALL USING (author_id = auth.uid());

DROP POLICY IF EXISTS "Published articles visible to authorized" ON public.articles;
CREATE POLICY "Published articles visible to authorized" ON public.articles FOR SELECT USING (
  is_published = true OR 
  author_id = auth.uid() OR
  EXISTS (
    SELECT 1 FROM public.article_permissions 
    WHERE article_id = id AND user_id = auth.uid()
  )
);

-- Messages policies
DROP POLICY IF EXISTS "Users can view own messages" ON public.messages;
CREATE POLICY "Users can view own messages" ON public.messages FOR SELECT USING (
  sender_id = auth.uid() OR recipient_id = auth.uid()
);

DROP POLICY IF EXISTS "Users can insert messages" ON public.messages;
CREATE POLICY "Users can insert messages" ON public.messages FOR INSERT WITH CHECK (sender_id = auth.uid());

-- Attendance policies
DROP POLICY IF EXISTS "Teachers can manage attendance" ON public.attendance;
CREATE POLICY "Teachers can manage attendance" ON public.attendance FOR ALL USING (
  EXISTS (
    SELECT 1 FROM public.groups g WHERE g.id = group_id AND g.teacher_id = auth.uid()
  )
);

DROP POLICY IF EXISTS "Students can view own attendance" ON public.attendance;
CREATE POLICY "Students can view own attendance" ON public.attendance FOR SELECT USING (student_id = auth.uid());

-- Notifications policies
DROP POLICY IF EXISTS "Users can view own notifications" ON public.notifications;
CREATE POLICY "Users can view own notifications" ON public.notifications FOR SELECT USING (user_id = auth.uid());

-- Part 5: Create Trigger for Auto-creating Profiles
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public
AS $$
BEGIN
  INSERT INTO public.profiles (id, email, full_name, role)
  VALUES (
    new.id,
    new.email,
    COALESCE(new.raw_user_meta_data ->> 'full_name', new.email),
    COALESCE((new.raw_user_meta_data ->> 'role')::user_role, 'student')
  )
  ON CONFLICT (id) DO NOTHING;
  RETURN new;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user();

-- Part 6: Insert Default Data

-- Insert default subjects
INSERT INTO public.subjects (name, description, icon, color) 
VALUES
  ('IELTS', 'International English Language Testing System', 'globe', '#1e40af'),
  ('General English', 'General English language courses', 'book-open', '#059669'),
  ('Mathematics', 'Mathematics courses', 'calculator', '#dc2626'),
  ('IT/Programming', 'Information Technology and Programming', 'code', '#7c3aed'),
  ('SAT', 'Scholastic Assessment Test preparation', 'graduation-cap', '#ea580c')
ON CONFLICT (name) DO NOTHING;

-- Insert IELTS levels
INSERT INTO public.levels (subject_id, name, order_index, min_score, max_score)
SELECT id, name, order_index, min_score, max_score
FROM (
  SELECT 
    (SELECT id FROM public.subjects WHERE name = 'IELTS') as subject_id,
    'Beginner' as name, 1 as order_index, 0 as min_score, 3 as max_score
  UNION ALL
  SELECT 
    (SELECT id FROM public.subjects WHERE name = 'IELTS'),
    'Elementary', 2, 3, 4
  UNION ALL
  SELECT 
    (SELECT id FROM public.subjects WHERE name = 'IELTS'),
    'Pre-Intermediate', 3, 4, 5
  UNION ALL
  SELECT 
    (SELECT id FROM public.subjects WHERE name = 'IELTS'),
    'Intermediate', 4, 5, 6
  UNION ALL
  SELECT 
    (SELECT id FROM public.subjects WHERE name = 'IELTS'),
    'Upper-Intermediate', 5, 6, 7
  UNION ALL
  SELECT 
    (SELECT id FROM public.subjects WHERE name = 'IELTS'),
    'Advanced', 6, 7, 9
) levels
ON CONFLICT (subject_id, name) DO NOTHING;
