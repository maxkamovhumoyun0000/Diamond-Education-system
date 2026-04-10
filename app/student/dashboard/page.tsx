"use client";

import { useState, useEffect } from "react";
import { createClient } from "@/lib/supabase/client";

interface StudentProfile {
  id: string;
  full_name: string;
  email: string;
  phone?: string;
}

interface StudentSubject {
  id: string;
  student_id: string;
  subject_id: string;
  level_id: string;
  enrolled_at: string;
  progress: number;
}

interface Subject {
  id: string;
  name: string;
  color: string;
}

interface Level {
  id: string;
  name: string;
}

interface PlacementTest {
  id: string;
  subject_id: string;
  score: number;
  max_score: number;
  level_assigned: string;
  test_date: string;
}

export default function StudentDashboard() {
  const supabase = createClient();
  const [profile, setProfile] = useState<StudentProfile | null>(null);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [levels, setLevels] = useState<Level[]>([]);
  const [enrolledSubjects, setEnrolledSubjects] = useState<StudentSubject[]>([]);
  const [placementTests, setPlacementTests] = useState<PlacementTest[]>([]);
  const [dCoinBalance, setDCoinBalance] = useState(0);
  const [loading, setLoading] = useState(true);
  const [showEnrollForm, setShowEnrollForm] = useState(false);
  const [enrollData, setEnrollData] = useState({
    subjectId: "",
    levelId: "",
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);

      const {
        data: { user },
      } = await supabase.auth.getUser();

      if (!user) return;

      // Load profile
      const { data: profileData } = await supabase
        .from("profiles")
        .select("*")
        .eq("id", user.id)
        .single();

      if (profileData) {
        setProfile(profileData);
      }

      // Load subjects
      const { data: subjectsData } = await supabase
        .from("subjects")
        .select("*")
        .eq("is_active", true);

      if (subjectsData) {
        setSubjects(subjectsData);
      }

      // Load enrolled subjects
      const { data: enrolledData } = await supabase
        .from("student_subjects")
        .select("*")
        .eq("student_id", user.id)
        .order("enrolled_at");

      if (enrolledData) {
        setEnrolledSubjects(enrolledData);
        // Load levels for enrolled subjects
        if (enrolledData.length > 0) {
          const { data: levelsData } = await supabase
            .from("levels")
            .select("*")
            .in(
              "id",
              enrolledData.map((es) => es.level_id)
            );
          if (levelsData) {
            setLevels(levelsData);
          }
        }
      }

      // Load placement tests
      const { data: testsData } = await supabase
        .from("placement_tests")
        .select("*")
        .eq("student_id", user.id)
        .order("test_date", { ascending: false });

      if (testsData) {
        setPlacementTests(testsData);
      }

      // Load D'coin balance
      const { data: transactionsData } = await supabase
        .from("dcoin_transactions")
        .select("amount")
        .eq("student_id", user.id);

      if (transactionsData) {
        const balance = transactionsData.reduce((sum, txn) => sum + txn.amount, 0);
        setDCoinBalance(balance);
      }
    } catch (error) {
      console.log("[v0] Error loading data:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleEnrollSubject = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const {
        data: { user },
      } = await supabase.auth.getUser();

      if (!user) return;

      const { error } = await supabase.from("student_subjects").insert({
        student_id: user.id,
        subject_id: enrollData.subjectId,
        level_id: enrollData.levelId,
        progress: 0,
      });

      if (!error) {
        console.log("[v0] Enrolled in subject");
        setEnrollData({ subjectId: "", levelId: "" });
        setShowEnrollForm(false);
        loadData();
      }
    } catch (error) {
      console.log("[v0] Error enrolling:", error);
    }
  };

  const getSubjectName = (subjectId: string) => {
    return subjects.find((s) => s.id === subjectId)?.name || "-";
  };

  const getLevelName = (levelId: string) => {
    return levels.find((l) => l.id === levelId)?.name || "-";
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-12">
        <h1 className="text-4xl font-bold text-foreground mb-2">
          Welcome, {profile?.full_name}!
        </h1>
        <p className="text-muted-foreground">{profile?.email}</p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
        <div className="bg-background border border-muted rounded-lg p-6">
          <p className="text-muted-foreground text-sm font-medium mb-2">Active Subjects</p>
          <p className="text-4xl font-bold text-primary">{enrolledSubjects.length}</p>
        </div>

        <div className="bg-background border border-muted rounded-lg p-6">
          <p className="text-muted-foreground text-sm font-medium mb-2">Placement Tests</p>
          <p className="text-4xl font-bold text-secondary">{placementTests.length}</p>
        </div>

        <div className="bg-background border border-muted rounded-lg p-6">
          <p className="text-muted-foreground text-sm font-medium mb-2">D&apos;coins</p>
          <p className="text-4xl font-bold text-green-600">{dCoinBalance}</p>
        </div>
      </div>

      {/* Enrolled Subjects */}
      <div className="mb-12">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-foreground">My Subjects</h2>
          <button
            onClick={() => setShowEnrollForm(!showEnrollForm)}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition"
          >
            {showEnrollForm ? "Cancel" : "Enroll in Subject"}
          </button>
        </div>

        {showEnrollForm && (
          <div className="bg-background border border-muted rounded-lg p-6 mb-6">
            <h3 className="text-xl font-bold text-foreground mb-4">Enroll in a Subject</h3>
            <form onSubmit={handleEnrollSubject} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">
                    Subject
                  </label>
                  <select
                    value={enrollData.subjectId}
                    onChange={(e) =>
                      setEnrollData({ ...enrollData, subjectId: e.target.value })
                    }
                    className="w-full px-4 py-2 border border-muted rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                    required
                  >
                    <option value="">Select Subject</option>
                    {subjects.map((subject) => (
                      <option key={subject.id} value={subject.id}>
                        {subject.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">
                    Level
                  </label>
                  <select
                    value={enrollData.levelId}
                    onChange={(e) =>
                      setEnrollData({ ...enrollData, levelId: e.target.value })
                    }
                    className="w-full px-4 py-2 border border-muted rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                    required
                  >
                    <option value="">Select Level</option>
                    {levels.map((level) => (
                      <option key={level.id} value={level.id}>
                        {level.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <button
                type="submit"
                className="w-full px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition"
              >
                Enroll
              </button>
            </form>
          </div>
        )}

        {enrolledSubjects.length === 0 ? (
          <div className="bg-background border border-muted rounded-lg p-12 text-center">
            <p className="text-muted-foreground mb-4">No subjects enrolled yet</p>
            <button
              onClick={() => setShowEnrollForm(true)}
              className="px-6 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition"
            >
              Enroll in Your First Subject
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {enrolledSubjects.map((enrollment) => (
              <div
                key={enrollment.id}
                className="bg-background border border-muted rounded-lg p-6 hover:border-primary transition"
              >
                <div className="mb-4">
                  <h3 className="text-xl font-bold text-foreground">
                    {getSubjectName(enrollment.subject_id)}
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    Level: {getLevelName(enrollment.level_id)}
                  </p>
                </div>

                <div className="mb-4">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm font-medium text-foreground">Progress</span>
                    <span className="text-sm font-medium text-muted-foreground">
                      {enrollment.progress}%
                    </span>
                  </div>
                  <div className="w-full bg-muted rounded-full h-2">
                    <div
                      className="bg-primary rounded-full h-2 transition-all"
                      style={{ width: `${enrollment.progress}%` }}
                    ></div>
                  </div>
                </div>

                <p className="text-xs text-muted-foreground">
                  Enrolled: {new Date(enrollment.enrolled_at).toLocaleDateString()}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Placement Tests */}
      {placementTests.length > 0 && (
        <div>
          <h2 className="text-2xl font-bold text-foreground mb-6">Placement Tests</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {placementTests.map((test) => (
              <div
                key={test.id}
                className="bg-background border border-muted rounded-lg p-6"
              >
                <div className="flex justify-between items-start mb-4">
                  <h3 className="text-lg font-bold text-foreground">
                    {getSubjectName(test.subject_id)}
                  </h3>
                  <span className="px-3 py-1 bg-primary text-primary-foreground rounded-full text-sm font-bold">
                    {test.level_assigned.toUpperCase()}
                  </span>
                </div>

                <div className="space-y-3">
                  <div>
                    <p className="text-sm text-muted-foreground">Score</p>
                    <p className="text-2xl font-bold text-foreground">
                      {test.score}/{test.max_score}
                    </p>
                  </div>

                  <div>
                    <p className="text-sm text-muted-foreground">Test Date</p>
                    <p className="text-foreground">
                      {new Date(test.test_date).toLocaleDateString()}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
