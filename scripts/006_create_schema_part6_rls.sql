-- Diamond Education Admin Panel - Database Schema Part 6
-- Setting up Row Level Security (RLS) policies

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

-- Subjects policies
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
  sender_id = auth.uid() OR is_announcement = true
);
CREATE POLICY "Users can send messages" ON public.messages FOR INSERT WITH CHECK (sender_id = auth.uid());

-- Message recipients policies
CREATE POLICY "Users can view own message recipients" ON public.message_recipients FOR SELECT USING (recipient_id = auth.uid() OR sender_id IN (SELECT id FROM public.profiles WHERE id = auth.uid()));
CREATE POLICY "Users can manage own message recipients" ON public.message_recipients FOR ALL USING (recipient_id = auth.uid());

-- Placement tests policies
CREATE POLICY "Anyone can view active tests" ON public.placement_tests FOR SELECT USING (is_active = true);
CREATE POLICY "Admins can manage tests" ON public.placement_tests FOR ALL USING (
  EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('super_admin', 'admin'))
);

-- Placement test results policies
CREATE POLICY "Staff can view results" ON public.placement_test_results FOR SELECT USING (
  EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('super_admin', 'admin', 'teacher'))
  OR EXISTS (SELECT 1 FROM public.students WHERE id = student_id AND profile_id = auth.uid())
);
CREATE POLICY "Admins can manage results" ON public.placement_test_results FOR ALL USING (
  EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('super_admin', 'admin', 'teacher'))
);

-- Attendance policies
CREATE POLICY "Staff can view attendance" ON public.attendance FOR SELECT USING (
  EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('super_admin', 'admin', 'teacher', 'support_teacher'))
);
CREATE POLICY "Teachers can manage attendance" ON public.attendance FOR ALL USING (
  EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('super_admin', 'admin', 'teacher'))
);

-- Notifications policies
CREATE POLICY "Users can view own notifications" ON public.notifications FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "System can create notifications" ON public.notifications FOR INSERT WITH CHECK (true);
