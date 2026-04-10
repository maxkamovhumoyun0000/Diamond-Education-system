-- Diamond Education Admin Panel - Database Schema Part 3
-- Creating D'coin system tables

-- D'coin transaction types
CREATE TYPE IF NOT EXISTS dcoin_transaction_type AS ENUM (
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
  related_entity_type TEXT,
  related_entity_id UUID,
  created_by UUID REFERENCES public.profiles(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);
