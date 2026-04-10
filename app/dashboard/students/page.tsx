"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";

interface Student {
  id: string;
  email: string;
  full_name: string;
  phone?: string;
  role: string;
  created_at: string;
}

interface PlacementTest {
  id: string;
  student_id: string;
  score: number;
  max_score: number;
  level_assigned: string;
  test_date: string;
}

export default function StudentsPage() {
  const supabase = createClient();
  const [students, setStudents] = useState<Student[]>([]);
  const [placementTests, setPlacementTests] = useState<PlacementTest[]>([]);
  const [showAddForm, setShowAddForm] = useState(false);
  const [showTestForm, setShowTestForm] = useState(false);
  const [selectedStudent, setSelectedStudent] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"students" | "tests">("students");

  const [formData, setFormData] = useState({
    fullName: "",
    email: "",
    phone: "",
    type: "regular",
  });

  const [testData, setTestData] = useState({
    studentId: "",
    subject: "english",
    score: "",
    maxScore: "100",
    levelAssigned: "a1",
    notes: "",
  });

  const handleAddStudent = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await supabase.auth.signUp({
        email: formData.email,
        password: Math.random().toString(36).slice(-12),
        options: {
          data: {
            full_name: formData.fullName,
            phone: formData.phone,
            type: formData.type,
          },
        },
      });

      if (!response.error && response.data.user) {
        console.log("[v0] Student added:", response.data.user.email);
        setFormData({ fullName: "", email: "", phone: "", type: "regular" });
        setShowAddForm(false);
      } else {
        console.log("[v0] Error adding student:", response.error);
      }
    } catch (error) {
      console.log("[v0] Error:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddPlacementTest = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const { data, error } = await supabase.from("placement_tests").insert({
        student_id: testData.studentId,
        score: parseInt(testData.score),
        max_score: parseInt(testData.maxScore),
        level_assigned: testData.levelAssigned,
        notes: testData.notes,
        status: "completed",
      });

      if (!error) {
        console.log("[v0] Placement test added");
        setTestData({
          studentId: "",
          subject: "english",
          score: "",
          maxScore: "100",
          levelAssigned: "a1",
          notes: "",
        });
        setShowTestForm(false);
      } else {
        console.log("[v0] Error adding test:", error);
      }
    } catch (error) {
      console.log("[v0] Error:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteStudent = async (studentId: string) => {
    if (!confirm("Are you sure you want to delete this student?")) return;

    try {
      const { error } = await supabase.from("profiles").delete().eq("id", studentId);
      if (!error) {
        setStudents(students.filter((s) => s.id !== studentId));
        console.log("[v0] Student deleted");
      }
    } catch (error) {
      console.log("[v0] Error deleting student:", error);
    }
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-4xl font-bold text-primary">Students Management</h1>
        <div className="space-x-3">
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="px-6 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition"
          >
            {showAddForm ? "Cancel" : "Add Student"}
          </button>
          <button
            onClick={() => setShowTestForm(!showTestForm)}
            className="px-6 py-2 bg-secondary text-secondary-foreground rounded-lg hover:opacity-90 transition"
          >
            {showTestForm ? "Cancel" : "Add Test"}
          </button>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-4 mb-8 border-b border-muted">
        <button
          onClick={() => setActiveTab("students")}
          className={`px-4 py-2 font-medium border-b-2 transition ${
            activeTab === "students"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          Students ({students.length})
        </button>
        <button
          onClick={() => setActiveTab("tests")}
          className={`px-4 py-2 font-medium border-b-2 transition ${
            activeTab === "tests"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          Placement Tests ({placementTests.length})
        </button>
      </div>

      {/* Add Student Form */}
      {showAddForm && (
        <div className="bg-background border border-muted rounded-lg p-6 mb-8">
          <h2 className="text-2xl font-bold text-foreground mb-6">Add New Student</h2>
          <form onSubmit={handleAddStudent} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Full Name
                </label>
                <input
                  type="text"
                  value={formData.fullName}
                  onChange={(e) =>
                    setFormData({ ...formData, fullName: e.target.value })
                  }
                  className="w-full px-4 py-2 border border-muted rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Email
                </label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) =>
                    setFormData({ ...formData, email: e.target.value })
                  }
                  className="w-full px-4 py-2 border border-muted rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Phone
                </label>
                <input
                  type="tel"
                  value={formData.phone}
                  onChange={(e) =>
                    setFormData({ ...formData, phone: e.target.value })
                  }
                  className="w-full px-4 py-2 border border-muted rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Student Type
                </label>
                <select
                  value={formData.type}
                  onChange={(e) =>
                    setFormData({ ...formData, type: e.target.value })
                  }
                  className="w-full px-4 py-2 border border-muted rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="regular">Regular</option>
                  <option value="support">Support</option>
                </select>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition disabled:opacity-50"
            >
              {loading ? "Adding..." : "Add Student"}
            </button>
          </form>
        </div>
      )}

      {/* Add Placement Test Form */}
      {showTestForm && (
        <div className="bg-background border border-muted rounded-lg p-6 mb-8">
          <h2 className="text-2xl font-bold text-foreground mb-6">Add Placement Test</h2>
          <form onSubmit={handleAddPlacementTest} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Student
                </label>
                <select
                  value={testData.studentId}
                  onChange={(e) =>
                    setTestData({ ...testData, studentId: e.target.value })
                  }
                  className="w-full px-4 py-2 border border-muted rounded-lg focus:outline-none focus:ring-2 focus:ring-secondary"
                  required
                >
                  <option value="">Select Student</option>
                  {students.map((student) => (
                    <option key={student.id} value={student.id}>
                      {student.full_name} ({student.email})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Subject
                </label>
                <select
                  value={testData.subject}
                  onChange={(e) =>
                    setTestData({ ...testData, subject: e.target.value })
                  }
                  className="w-full px-4 py-2 border border-muted rounded-lg focus:outline-none focus:ring-2 focus:ring-secondary"
                >
                  <option value="english">English</option>
                  <option value="math">Mathematics</option>
                  <option value="science">Science</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Score
                </label>
                <input
                  type="number"
                  value={testData.score}
                  onChange={(e) =>
                    setTestData({ ...testData, score: e.target.value })
                  }
                  className="w-full px-4 py-2 border border-muted rounded-lg focus:outline-none focus:ring-2 focus:ring-secondary"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Max Score
                </label>
                <input
                  type="number"
                  value={testData.maxScore}
                  onChange={(e) =>
                    setTestData({ ...testData, maxScore: e.target.value })
                  }
                  className="w-full px-4 py-2 border border-muted rounded-lg focus:outline-none focus:ring-2 focus:ring-secondary"
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-foreground mb-1">
                  Assigned Level
                </label>
                <select
                  value={testData.levelAssigned}
                  onChange={(e) =>
                    setTestData({ ...testData, levelAssigned: e.target.value })
                  }
                  className="w-full px-4 py-2 border border-muted rounded-lg focus:outline-none focus:ring-2 focus:ring-secondary"
                >
                  <option value="a1">A1</option>
                  <option value="a2">A2</option>
                  <option value="b1">B1</option>
                  <option value="b2">B2</option>
                  <option value="c1">C1</option>
                  <option value="c2">C2</option>
                </select>
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-foreground mb-1">
                  Notes
                </label>
                <textarea
                  value={testData.notes}
                  onChange={(e) =>
                    setTestData({ ...testData, notes: e.target.value })
                  }
                  className="w-full px-4 py-2 border border-muted rounded-lg focus:outline-none focus:ring-2 focus:ring-secondary h-24"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full px-4 py-2 bg-secondary text-secondary-foreground rounded-lg hover:opacity-90 transition disabled:opacity-50"
            >
              {loading ? "Adding..." : "Add Test"}
            </button>
          </form>
        </div>
      )}

      {/* Students List */}
      {activeTab === "students" && (
        <div className="bg-background border border-muted rounded-lg p-6">
          <h2 className="text-2xl font-bold text-foreground mb-6">Students List</h2>

          {students.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground">No students added yet</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-muted">
                    <th className="text-left py-3 px-4 font-semibold text-foreground">
                      Name
                    </th>
                    <th className="text-left py-3 px-4 font-semibold text-foreground">
                      Email
                    </th>
                    <th className="text-left py-3 px-4 font-semibold text-foreground">
                      Phone
                    </th>
                    <th className="text-left py-3 px-4 font-semibold text-foreground">
                      Joined
                    </th>
                    <th className="text-left py-3 px-4 font-semibold text-foreground">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {students.map((student) => (
                    <tr key={student.id} className="border-b border-muted hover:bg-muted/50">
                      <td className="py-3 px-4 text-foreground">{student.full_name}</td>
                      <td className="py-3 px-4 text-foreground">{student.email}</td>
                      <td className="py-3 px-4 text-muted-foreground">{student.phone || "-"}</td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {new Date(student.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-3 px-4">
                        <button
                          onClick={() => handleDeleteStudent(student.id)}
                          className="text-red-600 hover:text-red-800 text-sm font-medium"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Placement Tests List */}
      {activeTab === "tests" && (
        <div className="bg-background border border-muted rounded-lg p-6">
          <h2 className="text-2xl font-bold text-foreground mb-6">Placement Tests</h2>

          {placementTests.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground">No placement tests yet</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {placementTests.map((test) => (
                <div
                  key={test.id}
                  className="border border-muted rounded-lg p-4 bg-background hover:border-primary transition"
                >
                  <div className="mb-3">
                    <p className="text-sm text-muted-foreground">Test Date</p>
                    <p className="text-foreground font-medium">
                      {new Date(test.test_date).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="mb-3">
                    <p className="text-sm text-muted-foreground">Score</p>
                    <p className="text-foreground font-medium">
                      {test.score} / {test.max_score}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Level Assigned</p>
                    <p className="text-lg font-bold text-secondary">
                      {test.level_assigned.toUpperCase()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
