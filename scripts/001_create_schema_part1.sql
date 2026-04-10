-- Diamond Education Admin Panel - Database Schema Part 1
-- Creating basic tables and types

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- User roles enum
CREATE TYPE IF NOT EXISTS user_role AS ENUM ('super_admin', 'admin', 'teacher', 'support_teacher', 'student');

-- Student status enum
CREATE TYPE IF NOT EXISTS student_status AS ENUM ('active', 'inactive', 'graduated', 'suspended');

-- Student type enum (regular or support)
CREATE TYPE IF NOT EXISTS student_type AS ENUM ('regular', 'support');

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

-- Insert default subjects if they don't exist
INSERT INTO public.subjects (name, description, icon, color) 
VALUES
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

-- Insert IELTS levels if they don't exist
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
